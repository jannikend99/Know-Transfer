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
    llm = ChatOpenAI(model_name="gpt-4.1-2025-04-14", temperature=0.7)
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
- **Scope items**: "Item Name: description of what's included/excluded"
- **Process steps**: "1. Action description 2. Decision point 3. Next action..."
- **Inputs**: "Input Name: format, source, and quality criteria"
- **Outputs**: "Output Name: format, destination, and success criteria"
- **Success Metrics**: "Metric Name: measurement method | Target: specific value"
- **Roles**: "Role Title: specific responsibility and authority"
- **Exceptions**: "Exception Scenario: response action and escalation process"

RESPONSE GUIDELINES:
- Start with brief acknowledgment of what they shared
- Ask ONE specific follow-up question about missing/incomplete dimensions
- Apply consistent formatting standards to collected information
- Keep it conversational and encouraging
- Focus on getting COMPLETE information for each dimension
- Use natural business language, never technical field names

FORMATTING STANDARDS FOR OUTPUT:
- Use "Name: Description" format for structured items
- For inputs/outputs/roles/exceptions: "Clear Name: specific description"
- For KPIs: "Metric Name: measurement description. Target: specific value."
- For scope items: "Area Name: description of inclusion/exclusion"
- Always use plain text, never markdown formatting
- Make names specific and descriptive, not generic

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
- Extract ONLY information that is explicitly mentioned in the text
- DO NOT infer, assume, or guess missing information
- If a field is not explicitly mentioned in the text, leave it as null or empty list
- Be specific and detailed - avoid generic or assumed information  
- Focus on actionable, measurable, and verifiable details that are directly stated
- Preserve exact terminology used in the source material
- Only extract what is directly available in the source text

FORMATTING STANDARDS FOR LISTS:
- Use "Name: Description" format for items that have clear names and descriptions
- For INPUTS: "Material Name: description of requirements and specifications"
- For OUTPUTS: "Deliverable Name: description of format and success criteria"
- For ROLES_RESPONSIBILITIES: "Role Title: specific responsibilities and authorities"
- For EXCEPTIONS_SPECIAL_CASES: "Exception Name: description of scenario and handling"
- For SCOPE_INCLUDED: "Area Name: description of what's covered"
- For SCOPE_EXCLUDED: "Area Name: description of what's not covered"
- For KPIS: "Metric Name: measurement description and method. Target: specific target value."

QUALITY STANDARDS:
- Extract only factual information that is explicitly present in the text
- Maintain specificity - "Sales Manager" not just "Manager"  
- Include only quantitative details that are explicitly stated (timeframes, quantities, percentages)
- NEVER make assumptions about missing information - leave dimensions empty if not explicitly mentioned
- Only extract dimensions that are clearly and directly stated in the source material
- If information is ambiguous or unclear, do not extract it

{format_instructions}

TEXT TO ANALYZE:
{text_to_parse}

Remember: Extract ONLY what is explicitly stated in the source text. Leave dimensions empty if not clearly mentioned. Do not infer or assume missing information."""

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

# --- Mermaid Visualization Generation ---
async def generate_mermaid_from_process_data(process_data: dict) -> str:
    """Generate Mermaid diagram code from process data using AI."""
    if not llm:
        print("LLM not initialized, cannot generate Mermaid visualization.")
        return generate_basic_mermaid_from_steps(process_data.get('process_steps', []))
    
    # Prepare process data for the prompt
    process_context = f"""
Process Title: {process_data.get('title', 'Untitled Process')}
General Description: {process_data.get('general_description', 'No description available')}

Process Steps:
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(process_data.get('process_steps', []))])}

Inputs: {', '.join(process_data.get('inputs', []))}
Outputs: {', '.join(process_data.get('outputs', []))}

Roles & Responsibilities:
{chr(10).join(process_data.get('roles_responsibilities', []))}

Exceptions & Special Cases:
{chr(10).join(process_data.get('exceptions_special_cases', []))}
    """
    
    mermaid_prompt = f"""You are an expert at creating Mermaid flowchart diagrams for business processes. 
Create a comprehensive flowchart that shows the process with branches, decisions, and parallel paths where appropriate.

CRITICAL REQUIREMENTS:
1. Use 'graph TD' (top-down flowchart) format
2. MUST show ALL process steps from the process steps list
3. Analyze each step for branching patterns:
   - DECISION POINTS: If step contains decision/choice language (if, when, decide, approve/reject, yes/no, check if, verify, condition), create diamond decision nodes
   - PARALLEL PROCESSES: If step mentions simultaneous/parallel/concurrent activities, create parallel branches
   - LINEAR FLOW: Connect regular steps sequentially
4. Node types to use:
   - Start(( START )) - for the beginning
   - Step1["Step Description"] - for regular process steps 
   - Decision1{{"Decision Question?"}} - for decision points (diamond shape)
   - End(( END )) - for completion
5. Decision branching:
   - Decision1 -->|Yes| ActionYes["Yes Path"]
   - Decision1 -->|No| ActionNo["No Path"]  
   - Merge branches back: ActionYes --> Merge1(( ))
6. Parallel processing:
   - Split: Step1 --> Branch1["Task A"] and Step1 --> Branch2["Task B"]
   - Merge: Branch1 --> Merge1(( )) and Branch2 --> Merge1(( ))
7. Keep step labels clear but concise (max 50 characters per step)
8. IMPORTANT: Clean all text - remove bullets, markdown, special characters that could break Mermaid

TEXT CLEANING RULES:
- Remove all bullet points (•, *, -, etc.)
- Remove numbered list markers (1., 2., etc.)
- Replace quotes with single quotes
- Remove line breaks and replace with spaces
- Replace brackets [], braces {{}}, and angle brackets <> with parentheses ()
- Keep text simple and readable

STYLING REQUIREMENTS:
- Green for Start: style Start fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
- Blue for End: style End fill:#e3f2fd,stroke:#2196f3,stroke-width:2px  
- Gray for process steps: style StepX fill:#f9f9f9,stroke:#666,stroke-width:1px
- Yellow for decisions: style DecisionX fill:#fff3cd,stroke:#f59e0b,stroke-width:2px
- Light blue for parallel tasks: style ParallelX fill:#e0f2fe,stroke:#0ea5e9,stroke-width:1px
- Light green for Yes paths: style YesX fill:#d1fae5,stroke:#10b981,stroke-width:1px
- Light red for No paths: style NoX fill:#fee2e2,stroke:#ef4444,stroke-width:1px
- Gray dots for merge points: style MergeX fill:#f3f4f6,stroke:#6b7280,stroke-width:1px

STRUCTURE EXAMPLE:
```
graph TD
    Start(( START )) --> Step1
    Step1["1. Review incoming request"] --> Step2
    Step2["2. Validate requirements"] --> Step3
    Step3["3. Process and approve"] --> End
    End(( END ))
    
    style Start fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    style End fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style Step1 fill:#f9f9f9,stroke:#666,stroke-width:1px
    style Step2 fill:#f9f9f9,stroke:#666,stroke-width:1px
    style Step3 fill:#f9f9f9,stroke:#666,stroke-width:1px
```

PROCESS DATA:
{process_context}

Focus primarily on the Process Steps section and create a clear sequential flow. Generate ONLY the Mermaid code:"""

    try:
        response_message = await llm.ainvoke([("user", mermaid_prompt)])
        mermaid_code = response_message.content.strip()
        
        # Clean up the response to ensure it's valid Mermaid code
        if not mermaid_code.startswith('graph'):
            # Extract Mermaid code from response if it's wrapped in markdown or other text
            lines = mermaid_code.split('\n')
            start_idx = None
            end_idx = None
            
            for i, line in enumerate(lines):
                if line.strip().startswith('graph'):
                    start_idx = i
                elif start_idx is not None and (line.strip() == '' or line.strip().startswith('```')):
                    end_idx = i
                    break
            
            if start_idx is not None:
                end_idx = end_idx or len(lines)
                mermaid_code = '\n'.join(lines[start_idx:end_idx])
        
        return mermaid_code
        
    except Exception as e:
        print(f"Error generating Mermaid visualization with AI: {e}")
        # Fallback to basic generation
        return generate_basic_mermaid_from_steps(process_data.get('process_steps', []))

def clean_text_for_mermaid(text: str) -> str:
    """Clean text to be safe for Mermaid node labels."""
    if not text:
        return ""
    
    import re
    
    print(f"[DEBUG] Cleaning text: {text[:100]}...")
    
    # Start with basic cleanup
    clean_text = str(text).strip()
    
    # Remove HTML/XML tags
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    # Remove markdown formatting aggressively
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)  # Remove images
    clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)   # Remove links
    clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)  # Remove bold
    clean_text = re.sub(r'\*(.+?)\*', r'\1', clean_text)      # Remove italic
    clean_text = re.sub(r'`(.+?)`', r'\1', clean_text)        # Remove code
    clean_text = re.sub(r'#{1,6}\s*', '', clean_text)         # Remove headers
    
    # Remove bullet points and list markers more aggressively
    clean_text = re.sub(r'^[\s]*[-•*+]\s*', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'^[\s]*\d+\.\s*', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'^[\s]*[a-zA-Z]\.\s*', '', clean_text, flags=re.MULTILINE)
    
    # Remove problematic characters
    clean_text = clean_text.replace('"', "'").replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    clean_text = clean_text.replace('[', '(').replace(']', ')')
    clean_text = clean_text.replace('{', '(').replace('}', ')')
    clean_text = clean_text.replace('<', '(').replace('>', ')')
    clean_text = clean_text.replace('|', '-').replace('&', 'and')
    clean_text = clean_text.replace(':', ' -').replace(';', ',')
    
    # Remove any remaining special characters that could break Mermaid
    clean_text = re.sub(r'[^\w\s\-\.,()\']+', ' ', clean_text)
    
    # Remove multiple spaces and normalize
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    print(f"[DEBUG] Cleaned result: {clean_text[:100]}...")
    
    return clean_text

def generate_basic_mermaid_from_steps(process_steps: list) -> str:
    """Generate a basic Mermaid diagram from process steps."""
    print(f"[DEBUG] generate_basic_mermaid_from_steps called with {len(process_steps) if process_steps else 0} steps")
    if process_steps:
        print(f"[DEBUG] First step example: {process_steps[0][:100] if process_steps[0] else 'None'}...")
    
    if not process_steps or len(process_steps) == 0:
        return """graph TD
    Start(( START )) --> NoSteps
    NoSteps["No Process Steps Defined"] --> Helper
    Helper["Use AI Assistant to add steps"] --> End
    End(( END ))
    
    style Start fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    style End fill:#e3f2fd,stroke:#2196f3,stroke-width:2px"""
    
    mermaid_code = "graph TD\n"
    
    # Add start node and connect to first step
    mermaid_code += "    Start(( START )) --> Step1\n"
    
    # Add all process steps with connections
    for i, step in enumerate(process_steps):
        step_id = f"Step{i + 1}"
        print(f"[DEBUG] Processing step {i+1}: {step[:50]}...")
        
        # Clean and truncate step text
        clean_step = clean_text_for_mermaid(step)
        print(f"[DEBUG] Cleaned step {i+1}: {clean_step[:50]}...")
        
        if len(clean_step) > 60:
            clean_step = clean_step[:57] + "..."
        
        # Ensure we have some text
        if not clean_step:
            clean_step = f"Process Step {i + 1}"
        
        # Add the step node
        mermaid_code += f'    {step_id}["{i + 1}. {clean_step}"]\n'
        
        # Connect to next step or end
        if i < len(process_steps) - 1:
            next_step_id = f"Step{i + 2}"
            mermaid_code += f"    {step_id} --> {next_step_id}\n"
        else:
            mermaid_code += f"    {step_id} --> End\n"
    
    # Add end node
    mermaid_code += "    End(( END ))\n\n"
    
    # Add styling
    mermaid_code += "    style Start fill:#e8f5e8,stroke:#4caf50,stroke-width:2px\n"
    mermaid_code += "    style End fill:#e3f2fd,stroke:#2196f3,stroke-width:2px\n"
    
    # Style all process steps
    for i in range(len(process_steps)):
        step_id = f"Step{i + 1}"
        mermaid_code += f"    style {step_id} fill:#f9f9f9,stroke:#666,stroke-width:1px\n"
    
    print(f"[DEBUG] Generated mermaid code: {mermaid_code[:200]}...")
    return mermaid_code

# --- Basic HTML Visualization Placeholder (Deprecated) ---
async def generate_simple_html_visualization(process_data_text: str) -> str:
    """Takes text and wraps it in simple HTML for placeholder visualization."""
    # Deprecated - use generate_mermaid_from_process_data instead
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
        <h2>Process Details (Deprecated - Use Mermaid)</h2>
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

# --- React Flow Visualization Generation ---
async def generate_reactflow_from_process_data(process_data: dict) -> dict:
    """Generate React Flow nodes and edges from process data using AI."""
    if not llm:
        print("LLM not initialized, cannot generate React Flow visualization.")
        return generate_basic_reactflow_from_steps(process_data.get('process_steps', []))
    
    # Prepare process data for the prompt
    process_context = f"""
Process Title: {process_data.get('title', 'Untitled Process')}
General Description: {process_data.get('general_description', 'No description available')}

Process Steps:
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(process_data.get('process_steps', []))])}

Inputs: {', '.join(process_data.get('inputs', []))}
Outputs: {', '.join(process_data.get('outputs', []))}

Roles & Responsibilities:
{chr(10).join(process_data.get('roles_responsibilities', []))}

Exceptions & Special Cases:
{chr(10).join(process_data.get('exceptions_special_cases', []))}
    """
    
    reactflow_prompt = f"""You are an expert at creating React Flow diagrams for business processes. 
Create a comprehensive flowchart with nodes and edges that shows the process with branches, decisions, loops, and early termination paths where appropriate.

CRITICAL REQUIREMENTS:
1. Analyze each step for patterns:
   - DECISION POINTS: If step contains decision/choice language (if, when, decide, approve/reject, yes/no, check if, verify, condition, meets criteria, passes/fails, complies)
   - EARLY TERMINATION: If step mentions ending early (end process, terminate, stop, abort, cancel, exit, discontinue, halt, fail and stop)
   - LOOP/REWORK: If step mentions going back (return to, go back, loop back, repeat, rework, redo, back to step, retry, revert to, restart from)
   - PARALLEL PROCESSES: If step mentions simultaneous/parallel/concurrent activities
   - LINEAR FLOW: Connect regular steps sequentially

2. Node types to use:
   - 'startEnd' for start/end nodes (including early termination ends)
   - 'process' for regular process steps
   - 'decision' for decision points
   - 'parallel' for parallel processing nodes

3. Advanced Decision Handling:
   - STANDARD DECISIONS: Yes/No branches that merge back to main flow
   - EARLY TERMINATION: No branch leads to early END node, Yes continues main flow
   - LOOP DECISIONS: No branch loops back to earlier step (use dashed orange line), Yes continues forward
   - Use appropriate edge styling: solid for normal flow, dashed for loops, red for termination paths

4. Create a JSON structure with 'nodes' and 'edges' arrays:
   - Each node needs: id, type, position (x, y), data (label, description, etc.)
   - Each edge needs: id, source, target, type, markerEnd, style (optional)
   - For loop edges, add: style: {{"stroke": "#f59e0b", "strokeDasharray": "5,5"}}, label: "Rework"

5. Use 10-column grid layout with maximum spacing for crystal-clear organization:
   - Column 1 (x: 50): Far left - Extra branches
   - Column 2 (x: 300): Left-2 - Secondary branches  
   - Column 3 (x: 550): Left-1 - Yes paths, Parallel Task A
   - Column 4 (x: 800): Left-Center - Merge points
   - Column 5 (x: 1050): CENTER - Main flow (START, steps, decisions, END)
   - Column 6 (x: 1300): Right-Center - Merge points
   - Column 7 (x: 1550): Right-1 - No paths, Parallel Task B
   - Column 8 (x: 1800): Right-2 - Secondary branches
   - Column 9 (x: 2050): Right-3 - Alternative paths
   - Column 10 (x: 2300): Far right - Early termination ends
   - Space rows 250px apart vertically for maximum clarity and readability

6. Enhanced Node Descriptions: Include detailed descriptions with step context and process guidance:
   - START nodes: "START" with initiation guidance
   - Process steps: "Step X" with detailed execution context
   - Decision points: Clear decision labels with evaluation criteria
   - Parallel nodes: "Parallel" with synchronization details
   - Yes paths: "Yes - Approved" with continuation context
   - No paths: "No - Alternative" with alternative handling
   - END nodes: "END" with completion verification

6. Enhanced Decision Examples:
   - "If quality check passes" → Standard decision with merge
   - "If critical error found, stop process" → Early termination (No leads to EARLY END)
   - "If rework needed, return to validation step" → Loop decision (No loops back)

7. Clean all text - remove bullets, markdown, special characters

EXAMPLE ENHANCED STRUCTURE:
```json
{{
  "nodes": [
    {{
      "id": "start",
      "type": "startEnd", 
      "position": {{"x": 1050, "y": 120}},
      "data": {{"label": "START", "description": "Process Initiation Point", "isStart": true}}
    }},
    {{
      "id": "step-1", 
      "type": "decision",
      "position": {{"x": 1050, "y": 370}},
      "data": {{"label": "Quality check passes?", "description": "Critical decision point for quality validation", "stepNumber": 1}}
    }},
    {{
      "id": "step-1-yes",
      "type": "process",
      "position": {{"x": 550, "y": 620}},
      "data": {{"label": "Yes - Approved", "description": "Quality standards met, continue process", "isConditionResult": true}}
    }},
    {{
      "id": "step-1-no-rework",
      "type": "process", 
      "position": {{"x": 1550, "y": 620}},
      "data": {{"label": "No - Rework Required", "description": "Quality standards not met, rework needed", "isLoop": true}}
    }},
    {{
      "id": "step-1-merge",
      "type": "process",
      "position": {{"x": 1050, "y": 870}},
      "data": {{"label": "Continue Process", "description": "Paths converge here", "isMerge": true}}
    }}
  ],
  "edges": [
    {{
      "id": "e-start-step1",
      "source": "start", 
      "target": "step-1",
      "type": "smoothstep",
      "markerEnd": {{"type": "ArrowClosed"}}
    }},
    {{
      "id": "e-step1-yes",
      "source": "step-1",
      "target": "step-1-yes", 
      "type": "smoothstep",
      "label": "Yes",
      "labelStyle": {{"fill": "#10b981", "fontWeight": 600}},
      "markerEnd": {{"type": "ArrowClosed"}},
      "style": {{"stroke": "#10b981"}}
    }},
    {{
      "id": "e-step1-no-loop",
      "source": "step-1",
      "target": "step-1-no-rework",
      "type": "smoothstep", 
      "label": "No",
      "labelStyle": {{"fill": "#ef4444", "fontWeight": 600}},
      "markerEnd": {{"type": "ArrowClosed"}},
      "style": {{"stroke": "#ef4444"}}
    }},
    {{
      "id": "e-rework-loop-start",
      "source": "step-1-no-rework",
      "target": "start",
      "type": "smoothstep",
      "label": "Rework", 
      "labelStyle": {{"fill": "#f59e0b", "fontWeight": 600}},
      "markerEnd": {{"type": "ArrowClosed"}},
      "style": {{"stroke": "#f59e0b", "strokeDasharray": "5,5"}}
    }}
  ]
}}
```

PROCESS DATA:
{process_context}

Generate a React Flow JSON structure with nodes and edges for this process, including sophisticated decision handling with loops and early termination:"""

    try:
        response_message = await llm.ainvoke([("user", reactflow_prompt)])
        reactflow_response = response_message.content.strip()
        
        # Extract JSON from response
        import json
        import re
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', reactflow_response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                reactflow_data = json.loads(json_str)
                
                # Validate the structure
                if 'nodes' in reactflow_data and 'edges' in reactflow_data:
                    return reactflow_data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from LLM response: {e}")
        
        # Fallback to basic generation if JSON parsing fails
        return generate_basic_reactflow_from_steps(process_data.get('process_steps', []))
        
    except Exception as e:
        print(f"Error generating React Flow visualization with AI: {e}")
        # Fallback to basic generation
        return generate_basic_reactflow_from_steps(process_data.get('process_steps', []))

def clean_text_for_reactflow(text: str) -> str:
    """Clean text to be safe for React Flow node labels."""
    if not text:
        return ""
    
    import re
    
    # Start with basic cleanup
    clean_text = str(text).strip()
    
    # Remove HTML/XML tags
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    # Remove markdown formatting
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)  # Remove images
    clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)   # Remove links
    clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)  # Remove bold
    clean_text = re.sub(r'\*(.+?)\*', r'\1', clean_text)      # Remove italic
    clean_text = re.sub(r'`(.+?)`', r'\1', clean_text)        # Remove code
    clean_text = re.sub(r'#{1,6}\s*', '', clean_text)         # Remove headers
    
    # Remove bullet points and list markers
    clean_text = re.sub(r'^[\s]*[-•*+]\s*', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'^[\s]*\d+\.\s*', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'^[\s]*[a-zA-Z]\.\s*', '', clean_text, flags=re.MULTILINE)
    
    # Normalize whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

def is_decision_step(step_text: str) -> bool:
    """Detect if a step contains decision/branching language."""
    decision_keywords = [
        'if ', 'when ', 'decide', 'choice', 'option', 'either', 'or ',
        'depending on', 'based on', 'determine', 'check if', 'verify',
        'approve', 'reject', 'yes/no', 'true/false', 'condition',
        'meets criteria', 'passes', 'fails', 'complies', 'satisfies'
    ]
    lower_text = step_text.lower()
    return any(keyword in lower_text for keyword in decision_keywords)

def is_early_termination_step(step_text: str) -> bool:
    """Detect if a step mentions early termination."""
    termination_keywords = [
        'end process', 'terminate', 'stop', 'abort', 'cancel', 'exit',
        'end early', 'discontinue', 'halt', 'fail and stop'
    ]
    lower_text = step_text.lower()
    return any(keyword in lower_text for keyword in termination_keywords)

def is_loop_step(step_text: str) -> bool:
    """Detect if a step mentions looping back or rework."""
    loop_keywords = [
        'return to', 'go back', 'loop back', 'repeat', 'rework', 'redo',
        'back to step', 'retry', 'revert to', 'restart from', 'circle back'
    ]
    lower_text = step_text.lower()
    return any(keyword in lower_text for keyword in loop_keywords)

def is_parallel_step(step_text: str) -> bool:
    """Detect if a step mentions parallel or concurrent execution."""
    parallel_keywords = [
        'simultaneously', 'concurrent', 'parallel', 'at the same time',
        'in parallel', 'concurrently', 'both', 'together', 'meanwhile',
        'while also', 'split into', 'divide', 'fork', 'branch out',
        'multiple tasks', 'separate teams', 'independent', 'asynchronous'
    ]
    lower_text = step_text.lower()
    return any(keyword in lower_text for keyword in parallel_keywords)

def generate_basic_reactflow_from_steps(process_steps: list) -> dict:
    """Generate a clean React Flow structure with organized 5-column grid layout."""
    if not process_steps or len(process_steps) == 0:
        return {
            "nodes": [
                {
                    "id": "start",
                    "type": "startEnd",
                    "position": {"x": 1050, "y": 120},
                    "data": {
                        "label": "START",
                        "description": "Process Initiation Point\n\nThis marks the beginning of the workflow. Ready to begin once process steps are defined.",
                        "isStart": True
                    }
                },
                {
                    "id": "empty",
                    "type": "process", 
                    "position": {"x": 1050, "y": 370},
                    "data": {
                        "label": "No Process Steps Defined",
                        "description": "Process Definition Required\n\nUse the AI Assistant to add detailed process steps, or manually define the workflow stages to create a comprehensive process visualization."
                    }
                },
                {
                    "id": "end",
                    "type": "startEnd",
                    "position": {"x": 1050, "y": 620},
                    "data": {
                        "label": "END",
                        "description": "Process Completion Point\n\nThis will mark the successful completion of the workflow once process steps are defined.",
                        "isStart": False
                    }
                }
            ],
            "edges": [
                {
                    "id": "e-start-empty",
                    "source": "start",
                    "target": "empty",
                    "type": "smoothstep",
                    "markerEnd": {"type": "ArrowClosed"}
                },
                {
                    "id": "e-empty-end",
                    "source": "empty", 
                    "target": "end",
                    "type": "smoothstep",
                    "markerEnd": {"type": "ArrowClosed"}
                }
            ]
        }
    
    # 10-Column Grid Layout System with Maximum Spacing
    # Column 1 (x: 50):   Far left - Extra branches 
    # Column 2 (x: 300):  Left-2 - Secondary branches
    # Column 3 (x: 550):  Left-1 - Yes paths, Parallel Task A
    # Column 4 (x: 800):  Left-Center - Merge points
    # Column 5 (x: 1050): CENTER - Main flow (START, steps, decisions, END)
    # Column 6 (x: 1300): Right-Center - Merge points
    # Column 7 (x: 1550): Right-1 - No paths, Parallel Task B
    # Column 8 (x: 1800): Right-2 - Secondary branches
    # Column 9 (x: 2050): Right-3 - Alternative paths
    # Column 10 (x: 2300): Far right - Early termination ends
    
    COL_1 = 50
    COL_2 = 300
    COL_3 = 550   # Yes paths, Parallel A
    COL_4 = 800   # Left merge area
    COL_5 = 1050  # MAIN COLUMN - Primary flow
    COL_6 = 1300  # Right merge area
    COL_7 = 1550  # No paths, Parallel B
    COL_8 = 1800  # Secondary branches
    COL_9 = 2050  # Alternative paths
    COL_10 = 2300 # Early termination
    
    nodes = []
    edges = []
    current_y = 120
    row_height = 250  # Much larger spacing between rows
    current_node_id = "start"
    
    # Add start node in center column with enhanced information
    nodes.append({
        "id": "start",
        "type": "startEnd",
        "position": {"x": COL_5, "y": current_y},
        "data": {
            "label": "START",
            "description": "Process Initiation Point\n\nThis marks the beginning of the workflow. Ensure all prerequisites are met, resources are available, and stakeholders are notified before proceeding.",
            "isStart": True,
            "processPhase": "initiation"
        }
    })
    
    current_y += row_height
    
    for i, step in enumerate(process_steps):
        node_id = f"step-{i}"
        clean_step = clean_text_for_reactflow(step)
        
        if is_decision_step(step):
            # Decision node in center column with enhanced information
            decision_description = f"Decision Point {i + 1}: {step}\n\nThis is a critical decision point in the process flow. Careful evaluation is required to determine the appropriate path forward. Consider all relevant factors, documentation, and criteria before proceeding."
            
            nodes.append({
                "id": node_id,
                "type": "decision",
                "position": {"x": COL_5, "y": current_y},
                "data": {
                    "label": clean_step,
                    "question": clean_step,
                    "description": decision_description,
                    "stepNumber": i + 1,
                    "decisionType": "evaluation",
                    "requiresApproval": True
                }
            })
            
            # Connect from previous node
            edges.append({
                "id": f"e-{current_node_id}-{node_id}",
                "source": current_node_id,
                "target": node_id,
                "type": "smoothstep",
                "markerEnd": {"type": "ArrowClosed"}
            })
            
            current_y += row_height
            
            # Yes branch in left column, No branch in right column
            yes_node_id = f"{node_id}-yes"
            no_node_id = f"{node_id}-no"
            
            nodes.extend([
                {
                    "id": yes_node_id,
                    "type": "process",
                    "position": {"x": COL_3, "y": current_y},
                    "data": {
                        "label": "Yes - Approved",
                        "description": f"Requirements met for: {clean_step[:50]}... Continue with next step in the process flow.",
                        "isConditionResult": True,
                        "resultType": "approved"
                    }
                },
                {
                    "id": no_node_id,
                    "type": "process",
                    "position": {"x": COL_7, "y": current_y},
                    "data": {
                        "label": "No - Alternative Action",
                        "description": f"Requirements not met for: {clean_step[:50]}... Alternative handling or escalation required.",
                        "isConditionResult": True,
                        "resultType": "rejected"
                    }
                }
            ])
            
            # Decision edges with clean routing
            edges.extend([
                {
                    "id": f"e-{node_id}-{yes_node_id}",
                    "source": node_id,
                    "target": yes_node_id,
                    "type": "smoothstep",
                    "label": "Yes",
                    "labelStyle": {"fill": "#10b981", "fontWeight": 600},
                    "markerEnd": {"type": "ArrowClosed"},
                    "style": {"stroke": "#10b981"}
                },
                {
                    "id": f"e-{node_id}-{no_node_id}",
                    "source": node_id,
                    "target": no_node_id,
                    "type": "smoothstep",
                    "label": "No",
                    "labelStyle": {"fill": "#ef4444", "fontWeight": 600},
                    "markerEnd": {"type": "ArrowClosed"},
                    "style": {"stroke": "#ef4444"}
                }
            ])
            
            current_y += row_height
            
            # Simple merge back to center - no extra merge node unless needed
            next_node_id = f"step-{i+1}" if i+1 < len(process_steps) else "end"
            current_node_id = node_id  # Continue from decision node
            
        elif is_parallel_step(step):
            # Parallel node in center column with enhanced information
            parallel_description = f"Parallel Processing {i + 1}: {step}\n\nThis step involves concurrent execution of multiple tasks to optimize efficiency. Both parallel branches must be completed before proceeding to the next step. Coordination and synchronization are essential."
            
            nodes.append({
                "id": node_id,
                "type": "parallel",
                "position": {"x": COL_5, "y": current_y},
                "data": {
                    "label": clean_step,
                    "description": parallel_description,
                    "stepNumber": i + 1,
                    "executionType": "concurrent",
                    "requiresSync": True
                }
            })
            
            # Connect from previous node
            edges.append({
                "id": f"e-{current_node_id}-{node_id}",
                "source": current_node_id,
                "target": node_id,
                "type": "smoothstep",
                "markerEnd": {"type": "ArrowClosed"}
            })
            
            current_y += row_height
            
            # Parallel branches
            branch1_id = f"{node_id}-branch1"
            branch2_id = f"{node_id}-branch2"
            
            nodes.extend([
                {
                    "id": branch1_id,
                    "type": "process",
                    "position": {"x": COL_3, "y": current_y},
                    "data": {
                        "label": "Parallel Task A",
                        "description": f"Concurrent execution of first part: {clean_step[:40]}... This task runs simultaneously with Task B to optimize process efficiency.",
                        "isParallel": True,
                        "taskType": "concurrent_a"
                    }
                },
                {
                    "id": branch2_id,
                    "type": "process",
                    "position": {"x": COL_7, "y": current_y},
                    "data": {
                        "label": "Parallel Task B",
                        "description": f"Concurrent execution of second part: {clean_step[:40]}... This task runs simultaneously with Task A to optimize process efficiency.",
                        "isParallel": True,
                        "taskType": "concurrent_b"
                    }
                }
            ])
            
            # Parallel edges
            edges.extend([
                {
                    "id": f"e-{node_id}-{branch1_id}",
                    "source": node_id,
                    "target": branch1_id,
                    "type": "smoothstep",
                    "markerEnd": {"type": "ArrowClosed"},
                    "style": {"stroke": "#0ea5e9"}
                },
                {
                    "id": f"e-{node_id}-{branch2_id}",
                    "source": node_id,
                    "target": branch2_id,
                    "type": "smoothstep",
                    "markerEnd": {"type": "ArrowClosed"},
                    "style": {"stroke": "#0ea5e9"}
                }
            ])
            
            current_y += row_height
            current_node_id = node_id  # Continue from parallel node
            
        else:
            # Regular process step in center column with enhanced descriptions
            step_description = f"Step {i + 1} of {len(process_steps)}: {step}"
            if len(step) > 60:
                step_description += "\n\nThis is a detailed process step that requires careful attention to ensure proper execution and compliance with established procedures."
            else:
                step_description += f"\n\nProcess Action: Execute this step as part of the overall workflow. Duration may vary based on complexity and available resources."
            
            nodes.append({
                "id": node_id,
                "type": "process",
                "position": {"x": COL_5, "y": current_y},
                "data": {
                    "label": f"{i + 1}. {clean_step}",
                    "description": step_description,
                    "stepNumber": i + 1,
                    "stepTotal": len(process_steps),
                    "processPhase": "execution"
                }
            })
            
            # Connect from previous node
            edges.append({
                "id": f"e-{current_node_id}-{node_id}",
                "source": current_node_id,
                "target": node_id,
                "type": "smoothstep",
                "markerEnd": {"type": "ArrowClosed"}
            })
            
            current_node_id = node_id
            current_y += row_height
    
    # Add end node in center column with enhanced information
    nodes.append({
        "id": "end",
        "type": "startEnd",
        "position": {"x": COL_5, "y": current_y},
        "data": {
            "label": "END",
            "description": "Process Completion Point\n\nThis marks the successful completion of the workflow. Ensure all deliverables are finalized, documentation is updated, and stakeholders are notified of completion.",
            "isStart": False,
            "processPhase": "completion"
        }
    })
    
    edges.append({
        "id": f"e-{current_node_id}-end",
        "source": current_node_id,
        "target": "end",
        "type": "smoothstep",
        "markerEnd": {"type": "ArrowClosed"}
    })
    
    return {"nodes": nodes, "edges": edges}

print("LangChain service module loaded - with vector store capabilities.") 