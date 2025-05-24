from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field # Already imported by schemas, but good for clarity if used here directly
from typing import List, Optional # For Pydantic model
import os

from .openai_service import get_openai_client # To ensure client is available or for direct use if needed
from ..schemas.process import ProcessBase # Import our target Pydantic schema for output
from ..database import VECTOR_STORE_PATH, UPLOAD_DIRECTORY # Ensure VECTOR_STORE_PATH is imported
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document

# Initialize LLM first
llm = None
if get_openai_client(): # Ensure openai_service.get_openai_client() is defined before this block
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    print("LangChain ChatOpenAI LLM initialized.")
else:
    print("WARNING: OpenAI client not available, LangChain LLM not initialized. AI chat features may not work.")

# Initialize Embeddings Model next, as it might be used by chains/services defined below
embeddings_model = None
if get_openai_client():
    try:
        embeddings_model = OpenAIEmbeddings()
        print("LangChain OpenAIEmbeddings model initialized.")
    except Exception as e:
        print(f"Error initializing OpenAIEmbeddings: {e}. Document chat features might be limited.")
else:
    print("WARNING: OpenAI client not available, LangChain Embeddings not initialized.")

# Now define functions that might use llm or embeddings_model

# Example: A very simple chain for demonstration
def get_basic_chat_chain():
    if not llm:
        print("LLM not initialized, cannot create RAG chat chain.")
        return None
    
    # Updated prompt for RAG
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant. Answer the user's questions based on the ongoing conversation and the following retrieved context from relevant documents. If the context isn't relevant or doesn't provide an answer, say you don't know based on the documents and rely on the conversation or your general knowledge. Be concise."),
        MessagesPlaceholder(variable_name="chat_history"), # Existing conversation history
        ("user", "Based on our conversation and the following context from documents:\n--- CONTEXT START ---\n{retrieved_context}\n--- CONTEXT END ---\nMy question is: {text}") # User's current input, framed with context
    ])
    
    chain = prompt_template | llm
    return chain

async def run_basic_chat_chain(input_text: str, process_id: str, chat_history: List = []):
    chain = get_basic_chat_chain()
    if not chain or not embeddings_model: # also check embeddings_model for retriever
        return "RAG chat chain not available (LLM or Embeddings likely not initialized)."
    
    retrieved_context_str = "No relevant context found in documents for this query."
    print(f"[RAG DEBUG] Initializing for process_id: {process_id}, query: '{input_text[:50]}...'")
    try:
        vector_store = get_vector_store(process_id)
        print(f"[RAG DEBUG] Value of vector_store after calling get_vector_store: {vector_store}")
        print(f"[RAG DEBUG] Type of vector_store: {type(vector_store)}")
        if vector_store is not None:
            print("[RAG DEBUG] Vector store IS NOT NONE. (Inside if)")
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            try:
                retrieved_docs: List[Document] = await retriever.ainvoke(input_text)
                if retrieved_docs:
                    print(f"[RAG DEBUG] Retrieved {len(retrieved_docs)} documents.")
                    retrieved_context_str = "\n\n".join([doc.page_content for doc in retrieved_docs])
                    print(f"[RAG DEBUG] Retrieved context string (first 300 chars): {retrieved_context_str[:300]}...")
                else:
                    print("[RAG DEBUG] No documents retrieved.")
            except Exception as e:
                print(f"[RAG DEBUG] Error during vector store retrieval: {e}")
        else:
            print("[RAG DEBUG] Vector store NOT found.")

        payload_to_llm = {
            "text": input_text, 
            "chat_history": [f"{type(msg).__name__}: {msg.content[:50]}..." for msg in chat_history], # Log history snippets
            "retrieved_context": retrieved_context_str
        }
        print(f"[RAG DEBUG] Payload to LLM (history summarized): {payload_to_llm}")
        
        response_message = await chain.ainvoke({
            "text": input_text, 
            "chat_history": chat_history, # Pass the actual BaseMessage objects
            "retrieved_context": retrieved_context_str
        })
        return response_message.content 
    except Exception as e:
        print(f"Error running RAG chat chain: {e}")
        return f"Error in LangChain RAG chat: {e}"

# Placeholder for more complex chains or agents
# e.g., a chain for process extraction from text

# Placeholder for LangChain document loaders and text splitters
# from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter

# Placeholder for vector store setup
# from langchain_openai import OpenAIEmbeddings
# from langchain.vectorstores import Chroma

# --- Structured Output for Process Extraction ---

# Define a Pydantic model for the output. We can reuse/adapt ProcessBase or create a specific one.
# For this example, let's assume ProcessBase from schemas.process is suitable.
process_output_parser = PydanticOutputParser(pydantic_object=ProcessBase)

EXTRACT_PROCESS_PROMPT_TEMPLATE = """
From the following text, extract the details of a business process. 
If a field is not mentioned, leave it as null or an empty list as appropriate.

{format_instructions}

Text to parse:
{text_to_parse}
"""

def get_process_extraction_chain():
    if not llm:
        print("LLM not initialized, cannot create process extraction chain.")
        return None

    prompt = ChatPromptTemplate(
        messages=[
            HumanMessagePromptTemplate.from_template(EXTRACT_PROCESS_PROMPT_TEMPLATE)
        ],
        input_variables=["text_to_parse"],
        partial_variables={"format_instructions": process_output_parser.get_format_instructions()}
    )

    # LCEL syntax with the parser included in the chain
    chain = prompt | llm | process_output_parser
    return chain

async def extract_process_from_text(text_content: str) -> Optional[ProcessBase]:
    chain = get_process_extraction_chain()
    if not chain:
        print("Process extraction chain not available.")
        return None

    try:
        # The PydanticOutputParser is now part of the chain, so invoke should return the parsed object.
        parsed_output = await chain.ainvoke({"text_to_parse": text_content})
        return parsed_output
    except Exception as e:
        # This can include OutputParserException if the LLM doesn't format well,
        # or other errors during chain execution.
        print(f"Error extracting or parsing process data: {e}")
        import traceback # For more detailed error logging
        traceback.print_exc()
        return None

# --- Vector Store and Document Chat --- #

def get_vector_store(process_id: str = "_global"):
    """Gets a Chroma vector store instance, persisted on disk, namespaced by process_id."""
    print(f"[VS DEBUG] get_vector_store called for process_id: {process_id}") # New debug line
    if not embeddings_model:
        print("[VS DEBUG] Embeddings model IS NONE inside get_vector_store. Cannot create/access vector store.") # Modified debug line
        return None
    print("[VS DEBUG] Embeddings model seems available inside get_vector_store.") # New debug line
    
    persist_directory = os.path.join(VECTOR_STORE_PATH, f"process_{process_id}") 
    print(f"[VS DEBUG] Vector store persist_directory: {persist_directory}") # New debug line
    os.makedirs(persist_directory, exist_ok=True)

    try: # Add try-except around Chroma initialization
        vector_store = Chroma(
            collection_name=f"process_collection_{process_id}",
            embedding_function=embeddings_model,
            persist_directory=persist_directory
        )
        print(f"[VS DEBUG] Chroma vector store initialized/loaded for {process_id}.") # New debug line
        return vector_store
    except Exception as e:
        print(f"[VS DEBUG] Error initializing Chroma vector store for {process_id}: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for Chroma errors
        return None

async def add_text_to_vector_store(text_content: str, process_id: str, document_id: Optional[str] = None):
    print(f"[VS ADD DEBUG] Called for process_id: {process_id}, doc_id: {document_id}, text snippet: '{text_content[:100]}...'")
    if not embeddings_model:
        print("[VS ADD DEBUG] Embeddings model IS NONE. Cannot add text to vector store.") # Simplified this check
        return False
    # Removed llm check as it's not strictly needed for adding to vector store, only embeddings_model

    vector_store = get_vector_store(process_id)
    if vector_store is None:
        print(f"[VS ADD DEBUG] Failed to get vector store for process_id: {process_id}. Cannot add text.")
        return False
    print(f"[VS ADD DEBUG] Successfully got vector store for process_id: {process_id}.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_text(text_content)
    print(f"[VS ADD DEBUG] Split content into {len(texts)} chunks.")
    if not texts:
        print("[VS ADD DEBUG] No text chunks to add after splitting.")
        return False
    
    metadatas = None
    if document_id:
        metadatas = [{"source_document_id": document_id, "process_id": process_id} for _ in texts]
    else:
        metadatas = [{"process_id": process_id} for _ in texts]
    print(f"[VS ADD DEBUG] Metadatas prepared: {metadatas[0] if metadatas else 'None'}")

    try:
        print(f"[VS ADD DEBUG] Attempting to add {len(texts)} chunks to vector store for process {process_id} (doc: {document_id})")
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        print("[VS ADD DEBUG] add_texts successful.")
        # Note: In newer versions of ChromaDB, persistence is automatic when persist_directory is set
        print(f"[VS ADD DEBUG] Successfully added texts to vector store for process {process_id} (doc: {document_id}).")
        return True
    except Exception as e:
        print(f"[VS ADD DEBUG] Error adding texts to vector store: {e}")
        import traceback
        traceback.print_exc()
        return False

async def query_document_store(query_text: str, process_id: str):
    if not llm or not embeddings_model:
        print("LLM or embeddings model not available for document query.")
        return "Document query service not available."

    vector_store = get_vector_store(process_id)
    if not vector_store:
        return "Vector store for this process not available or not initialized."

    # Simple RetrievalQA chain
    # RetrievalQA itself is okay, but its .arun method is deprecated.
    # We'll use .ainvoke and adapt to its expected output.
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff", # Other types: map_reduce, refine, map_rerank
        retriever=vector_store.as_retriever()
    )
    
    try:
        # .ainvoke for RetrievalQA typically returns a dict like {'result': 'answer'}
        response_dict = await qa_chain.ainvoke({"query": query_text}) # 'query' is the default input key for RetrievalQA
        return response_dict.get("result", "No result found in response.")
    except Exception as e:
        print(f"Error querying document store: {e}")
        return f"Error during document query: {e}"

# --- Basic HTML Visualization Placeholder ---
async def generate_simple_html_visualization(process_data_text: str) -> str:
    """Takes text and wraps it in simple HTML for placeholder visualization."""
    # In a real scenario, this would take structured process data (e.g., ProcessBase model)
    # and use a more sophisticated method to generate meaningful HTML (e.g., using templates, libraries for diagrams).
    # For now, just a very basic formatting.
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Process Visualization</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .process-box {{ border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; border-radius: 5px; background-color: #f9f9f9; }}
        h2 {{ color: #333; }}
        pre {{ background-color: #eee; padding: 10px; border-radius: 3px; white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <div class=\"process-box\">
        <h2>Process Details (Placeholder Visualization)</h2>
        <pre>{process_data_text}</pre>
    </div>
</body>
</html>"""
    return html_content

print("LangChain service module loaded - with vector store capabilities.") 