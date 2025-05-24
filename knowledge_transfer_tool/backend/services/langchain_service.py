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
    llm = ChatOpenAI(model_name="gpt-4.1-mini-2025-04-14", temperature=0.7)
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
    
    # Updated prompt for comprehensive process documentation with progress tracking
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Business Process Documentation Assistant. Help users create complete process documentation through natural, step-by-step conversation.

COMMUNICATION STYLE:
- Keep responses SHORT and focused (2-3 sentences max)
- Ask ONE main question at a time 
- Use **markdown formatting** for better structure
- Be conversational and natural, not overwhelming
- Use your judgment - if information seems incomplete, ask for more details
- Guide users step-by-step, don't dump everything at once
- Use NATURAL LANGUAGE - never mention technical field names like "SCOPE_INCLUDED" or system terminology

TITLE & DESCRIPTION GENERATION:
- **GENERATE TITLE**: Only after you understand what the process does (usually after 2-3 exchanges)
- **GENERATE DESCRIPTION**: Only after you have sufficient context about purpose, scope, and basic flow (usually after 4-5 exchanges or when user provides substantial detail)
- These are AI-generated and don't count toward user's 9-dimension progress
- Wait until you have enough context to write meaningful title

USER DIMENSIONS TO COLLECT (9 dimensions for progress tracking):
1. **Overview description**: What the process does and its purpose (needs 100+ characters)
2. **What's included in scope**: What aspects, areas, or activities are covered by this process (needs 2+ substantial items)
3. **What's excluded from scope**: What's specifically NOT covered or handled by this process (needs 2+ substantial items)
4. **Process steps**: Detailed sequence of activities and decision points (needs comprehensive steps)
5. **Required inputs**: Materials, information, or resources needed to start (needs 2+ detailed items)
6. **Expected outputs**: Deliverables, results, or outcomes produced (needs 2+ detailed items)
7. **Success metrics**: How performance is measured and tracked (needs 2+ detailed metrics)
8. **Roles and responsibilities**: Who does what and has authority for decisions (needs 2+ detailed roles)
9. **Exception handling**: What happens when things go wrong or unusual situations arise (needs 2+ detailed scenarios)

COMPLETION CRITERIA (for progress tracking):
- **Lists**: Need at least 2 substantial items (30+ characters each) to count as COMPLETE
- **Text fields**: Need at least 100+ characters of detailed content to count as COMPLETE
- **Partial information doesn't count toward progress** - only comprehensive information does

NATURAL LANGUAGE GUIDELINES:
- Ask about "what's included in the scope" not "scope_included"
- Ask about "process steps" not "PROCESS_STEPS" 
- Ask about "inputs needed" not "INPUTS"
- Ask about "expected results" not "OUTPUTS"
- Ask about "success metrics" not "KPIS"
- Ask about "who's responsible" not "ROLES_RESPONSIBILITIES"
- Ask about "exception handling" not "EXCEPTIONS_SPECIAL_CASES"
- Always use conversational, business-friendly language

FORMATTING STANDARDS (always use these formats when generating structured content):
- **Scope items**: "• [Item 1] • [Item 2] • [Item 3]..."
- **Process steps**: "1. [Action] 2. [Action] 3. [Decision Point] 4. [Action]..."
- **Inputs**: "• [Input Name]: [Format/Source/Quality criteria]"
- **Outputs**: "• [Output Name]: [Format/Destination/Success criteria]"
- **Success Metrics**: "• [Metric Name]: [Measurement method] | **Target:** [value] | **Frequency:** [timing]"
- **Roles**: "• **[Role]:** [Specific responsibility and authority]"
- **Exceptions**: "• **[Scenario]:** [Response/Action] | **Escalation:** [process]"

RESPONSE GUIDELINES:
- Use **markdown formatting** for structure and emphasis
- Start with brief acknowledgment of what they shared
- Ask ONE specific follow-up question about missing/incomplete dimensions
- Apply consistent formatting standards to collected information
- Keep it conversational and encouraging
- Focus on getting COMPLETE information for each dimension
- Use natural business language, never technical field names

Remember: Only generate title/description when you have sufficient context. Focus on getting complete, comprehensive information for each user dimension using natural, conversational language."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "Context from uploaded documents:\n--- DOCUMENT CONTEXT ---\n{retrieved_context}\n--- END CONTEXT ---\n\nUser input: {text}")
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
You are an expert Business Process Analyst. Your task is to extract comprehensive process information from the provided text to create complete documentation.

TARGET SCHEMA DIMENSIONS (Extract all available information):
1. TITLE: Clear process name (if explicitly mentioned)
2. GENERAL_DESCRIPTION: Overview of what the process does (if explicitly described)
3. PROCESS_STEPS: Detailed sequence of activities, decision points, branching logic
4. SCOPE_INCLUDED: What's included in this process, boundaries, covered areas
5. SCOPE_EXCLUDED: What's excluded from this process, out-of-scope items
6. INPUTS: Required materials/information, formats, quality criteria
7. OUTPUTS: Deliverables, results, formats, success criteria
8. KPIS: Metrics, measurement methods, targets, frequency
9. ROLES_RESPONSIBILITIES: Who does what, approval authorities, accountability
10. EXCEPTIONS_SPECIAL_CASES: Error scenarios, alternative paths, contingency procedures  
11. VISUALIZATION_GRAPH: Process flow representation (if described in text)

EXTRACTION GUIDELINES:
- Extract ALL information that is explicitly mentioned or clearly implied
- Be specific and detailed - avoid generic or assumed information  
- If a field is not mentioned in the text, leave it as null or empty list
- Focus on actionable, measurable, and verifiable details
- Preserve exact terminology used in the source material
- Extract everything available - title/description will be refined by AI if needed

QUALITY STANDARDS:
- Extract only factual information present in the text
- Maintain specificity - "Sales Manager" not just "Manager"  
- Include quantitative details (timeframes, quantities, percentages)
- Flag ambiguous information rather than making assumptions
- Extract all 11 dimensions when available in source material

{format_instructions}

TEXT TO ANALYZE:
{text_to_parse}

Remember: Extract everything available from the source. AI will generate/refine title and description later if needed."""

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

def assess_process_documentation_progress(process_data: dict) -> dict:
    """
    Analyzes current process documentation state and returns progress assessment.
    Focuses on 9 user-provided dimensions (including overview, split scope into 2)
    Only counts dimensions as COMPLETE when they have comprehensive, detailed information.
    
    Args:
        process_data: Dictionary with current process field values
        
    Returns:
        Dictionary with progress analysis including completion status, missing fields, etc.
    """
    # Focus on the 9 dimensions users need to provide (including overview, split scope into 2)
    user_dimensions = {
        'general_description': 'Overview',
        'scope_included': 'Scope (What\'s Included)',
        'scope_excluded': 'Scope (What\'s Excluded)', 
        'process_steps': 'Process Steps',
        'inputs': 'Required Inputs',
        'outputs': 'Expected Outputs',
        'kpis': 'Success Metrics',
        'roles_responsibilities': 'Roles & Responsibilities',
        'exceptions_special_cases': 'Exception Handling'
    }
    
    complete_fields = []
    partial_fields = []
    missing_fields = []
    
    for field_name, display_name in user_dimensions.items():
        value = process_data.get(field_name)
        
        # Much stricter criteria for "complete" - must be comprehensive
        if not value:
            missing_fields.append(display_name)
        elif isinstance(value, list):
            if len(value) == 0:
                missing_fields.append(display_name)
            else:
                # For lists, need at least 2 substantial items to be "complete"
                substantial_items = [item for item in value if isinstance(item, str) and len(item.strip()) >= 30]
                if len(substantial_items) >= 2:
                    complete_fields.append(display_name)
                else:
                    partial_fields.append(display_name)
        elif isinstance(value, str):
            # For strings, need at least 100 characters of substantial content to be "complete"  
            if len(value.strip()) == 0:
                missing_fields.append(display_name)
            elif len(value.strip()) >= 100:
                complete_fields.append(display_name)
            else:
                partial_fields.append(display_name)
        else:
            # Other types considered complete if present
            complete_fields.append(display_name)
    
    total_dimensions = len(user_dimensions)  # 9 user input dimensions
    completion_percentage = (len(complete_fields) / total_dimensions) * 100
    
    return {
        'total_dimensions': total_dimensions,
        'complete_count': len(complete_fields),
        'partial_count': len(partial_fields),
        'missing_count': len(missing_fields),
        'completion_percentage': completion_percentage,
        'complete_fields': complete_fields,
        'partial_fields': partial_fields,
        'missing_fields': missing_fields,
        'is_fully_documented': len(missing_fields) == 0 and len(partial_fields) == 0,
        'next_priority_fields': missing_fields[:2] if missing_fields else partial_fields[:2]
    }

async def run_basic_chat_chain_with_progress(input_text: str, process_id: str, chat_history: List = [], current_process_data: dict = None):
    """Enhanced chat chain that includes process documentation progress in the context."""
    chain = get_basic_chat_chain()
    if not chain or not embeddings_model:
        return "RAG chat chain not available (LLM or Embeddings likely not initialized)."
    
    # Assess current documentation progress
    progress_info = ""
    if current_process_data:
        progress = assess_process_documentation_progress(current_process_data)
        
        progress_info = f"""
CURRENT DOCUMENTATION PROGRESS:
- User Input Status: {progress['completion_percentage']:.0f}% complete ({progress['complete_count']}/{progress['total_dimensions']} dimensions FULLY COMPLETE)
- Complete Areas: {', '.join(progress['complete_fields']) if progress['complete_fields'] else 'None yet'}
- Partial Areas: {', '.join(progress['partial_fields']) if progress['partial_fields'] else 'None'}  
- Missing Areas: {', '.join(progress['missing_fields']) if progress['missing_fields'] else 'None'}
- Next Priority: {', '.join(progress['next_priority_fields']) if progress['next_priority_fields'] else 'All user input complete!'}

COMPLETION STANDARDS:
- Each area needs comprehensive, detailed information to count as complete
- Partial information does not count toward progress - aim for thorough, complete answers
- Ask follow-up questions to get complete information for each area

TITLE/DESCRIPTION STATUS:
- Title: {'Generated' if current_process_data.get('title') else 'Generate when process purpose is clear'}

Focus on getting COMPLETE information for missing/partial areas using natural, conversational language. Only generate title when you have enough context.
"""
    
    retrieved_context_str = "No relevant context found in documents for this query."
    print(f"[RAG DEBUG] Initializing for process_id: {process_id}, query: '{input_text[:50]}...'")
    try:
        vector_store = get_vector_store(process_id)
        if vector_store is not None:
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            try:
                retrieved_docs: List[Document] = await retriever.ainvoke(input_text)
                if retrieved_docs:
                    retrieved_context_str = "\n\n".join([doc.page_content for doc in retrieved_docs])
            except Exception as e:
                print(f"[RAG DEBUG] Error during vector store retrieval: {e}")

        # Enhanced context with progress information
        enhanced_context = f"{progress_info}\n\nDOCUMENT CONTEXT:\n{retrieved_context_str}"
        
        response_message = await chain.ainvoke({
            "text": input_text, 
            "chat_history": chat_history,
            "retrieved_context": enhanced_context
        })
        return response_message.content 
    except Exception as e:
        print(f"Error running RAG chat chain: {e}")
        return f"Error in LangChain RAG chat: {e}"

print("LangChain service module loaded - with vector store capabilities.") 