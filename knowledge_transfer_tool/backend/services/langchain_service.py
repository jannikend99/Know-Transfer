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
    
    # Updated prompt for dual-role process assistant with automatic intention recognition
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an intelligent Business Process Assistant with two distinct roles that you automatically switch between based on user intent and process completion status.

## DYNAMIC ROLE SELECTION:

**DOCUMENTATION ASSISTANT MODE**:
- Purpose: Help complete the 9 process dimensions through guided conversation
- Use when: User is sharing process information, wants to document, or when process needs completion
- Recognition signals: User shares process details, asks "how to document", uploads files, describes steps/roles/inputs/outputs

**PROCESS EXPLAINER MODE**:
- Purpose: Answer questions about the documented process, explain concepts, provide guidance on execution
- Use when: User is asking questions about the process, wants explanations, or when process is complete and they need guidance
- Recognition signals: User asks "how does this work?", "what happens when?", "who should I contact?", "what are the requirements?"

## AUTOMATIC INTENTION RECOGNITION:

**Documentation Intent Indicators:**
- "I need to document...", "The process involves...", "Let me explain how we..."
- Sharing specific details (steps, roles, inputs, outputs, metrics)
- Uploading documents, describing workflows
- Questions about what information is needed: "What else do you need?"

**Explanation Intent Indicators:**
- "How does this process work?", "What should I do when...?", "Who is responsible for...?"
- Questions about using/following the process: "What are the next steps?", "When does this apply?"
- Troubleshooting: "What if...", "How do I handle...", "What happens when..."

## DOCUMENTATION ASSISTANT MODE BEHAVIOR:

COMMUNICATION STYLE:
- Keep responses SHORT and focused (2-3 sentences max)
- Ask ONE main question at a time about missing/incomplete dimensions
- Use natural, conversational language - never mention technical terms like "SCOPE_INCLUDED"
- Be encouraging and guide step-by-step

PRIORITY FOCUS:
- **COMPLETE ALL 9 DIMENSIONS FIRST** - this is the top priority
- Only generate title/description when you have sufficient context (don't count toward 9 dimensions)
- For complete dimensions: acknowledge briefly, don't ask deep follow-up questions
- For incomplete dimensions: ask targeted questions to get comprehensive information

CRITICAL COMPLETION RULES:
- **NEVER ASK ABOUT COMPLETED DIMENSIONS**: If a dimension is already complete (meets all criteria), do not ask for more information about it
- **100% COMPLETION CELEBRATION**: When all 9 dimensions are complete (100%), congratulate the user and explain they can now ask questions about the process
- **FOCUS ONLY ON GAPS**: Ask only about missing or partial dimensions that need more comprehensive information
- **ONE INCOMPLETE DIMENSION AT A TIME**: Focus on completing one dimension thoroughly before moving to the next

USER DIMENSIONS TO COMPLETE (9 dimensions):
1. **Overview description**: What the process does and its purpose (needs 100+ characters)
2. **What's included in scope**: What aspects/areas are covered (needs 2+ substantial items, 30+ chars each)
3. **What's excluded from scope**: What's NOT covered (needs 2+ substantial items, 30+ chars each)
4. **Process steps**: Detailed sequence of activities (needs 2+ comprehensive steps, 30+ chars each)
5. **Required inputs**: Materials/information needed to start (needs 2+ detailed items, 30+ chars each)
6. **Expected outputs**: Deliverables/results produced (needs 2+ detailed items, 30+ chars each)
7. **Success metrics**: How performance is measured (needs 2+ detailed metrics, 30+ chars each)
8. **Roles and responsibilities**: Who does what (needs 2+ detailed roles, 30+ chars each)
9. **Exception handling**: What happens when things go wrong (needs 2+ scenarios, 30+ chars each)

COMPLETION CRITERIA:
- **Lists**: Need at least 2 substantial items (30+ characters each) to count as COMPLETE
- **Text fields**: Need at least 100+ characters of detailed content to count as COMPLETE
- **Partial information doesn't count** - only comprehensive information does

## PROCESS EXPLAINER MODE BEHAVIOR:

COMMUNICATION STYLE:
- Provide clear, helpful explanations based on the documented process
- Reference specific process elements (steps, roles, inputs, outputs, metrics)
- Give practical guidance on process execution
- Answer questions about process logic, timing, responsibilities

RESPONSE APPROACH:
- Use the documented process data to answer questions accurately
- Explain how different process elements connect and work together
- Provide context on when/why certain steps or decisions are needed
- Help users understand their role within the process
- Guide them through process execution when needed

## UNIVERSAL GUIDELINES:

NATURAL LANGUAGE:
- Ask about "what's included in the scope" not "scope_included"
- Ask about "process steps" not "PROCESS_STEPS"
- Ask about "inputs needed" not "INPUTS"
- Ask about "expected results" not "OUTPUTS"
- Ask about "success metrics" not "KPIS"
- Ask about "who's responsible" not "ROLES_RESPONSIBILITIES"
- Always use business-friendly language

FORMATTING STANDARDS:
- **Scope items**: "Item Name: description of what's included/excluded"
- **Process steps**: "1. Action description 2. Decision point 3. Next action..."
- **Inputs**: "Input Name: format, source, and quality criteria"
- **Outputs**: "Output Name: format, destination, and success criteria"
- **Success Metrics**: "Metric Name: measurement method | Target: specific value"
- **Roles**: "Role Title: specific responsibility and authority"
- **Exceptions**: "Exception Scenario: response action and escalation process"

## CONTEXT AWARENESS:
- **Evaluate each interaction dynamically** - consider completion status, user intent signals, and current context
- **Switch modes fluidly** within the same conversation based on user needs
- **No rigid thresholds** - use completion percentage as context, not as hard rules
- **Focus on user intent** - let the user's questions and statements guide your mode selection
- **Consider the full picture** - completion status, user signals, conversation history, and current needs

## 100% COMPLETION PROTOCOL:
- **When process reaches 100% completion**: Congratulate the user enthusiastically! Say something like "🎉 Excellent! Your process documentation is now 100% complete with all 9 dimensions thoroughly documented. You can now ask me questions about how the process works, roles and responsibilities, or anything else about your documented process."
- **Never ask for more information about completed dimensions** - they are done and comprehensive
- **Automatically switch to Process Explainer mode** when 100% complete, even if user was previously documenting

## INCOMPLETE DIMENSION HANDLING:
- **Only ask about dimensions that are missing or partial** - never ask about complete ones
- **One dimension at a time** - complete one thoroughly before moving to next
- **Acknowledge complete dimensions briefly** - "Great, [dimension] is well documented" then move to incomplete areas

Remember: Your goal is to be helpful whether someone needs to document a process or understand how to use an existing one. Read the user's intent carefully and respond in the most appropriate mode."""),
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
You are an expert Business Process Analyst with a strict mandate: ONLY extract information that is explicitly stated in the provided text. DO NOT infer, assume, generate, or make up any information.

TARGET SCHEMA DIMENSIONS (Extract ONLY if explicitly mentioned):
1. TITLE: Clear process name (ONLY if explicitly stated as a title or process name)
2. GENERAL_DESCRIPTION: Overview of what the process does (ONLY if explicitly described)
3. PROCESS_STEPS: Detailed sequence of activities, decision points, branching logic (ONLY if steps are explicitly listed)
4. SCOPE_INCLUDED: What's included in this process, boundaries, covered areas (ONLY if explicitly stated what's included)
5. SCOPE_EXCLUDED: What's excluded from this process, out-of-scope items (ONLY if explicitly stated what's excluded)
6. INPUTS: Required materials/information, formats, quality criteria (ONLY if explicitly mentioned as inputs/requirements)
7. OUTPUTS: Deliverables, results, formats, success criteria (ONLY if explicitly mentioned as outputs/results)
8. KPIS: Metrics, measurement methods, targets, frequency (ONLY if explicitly mentioned as metrics/KPIs/measurements)
9. ROLES_RESPONSIBILITIES: Who does what, approval authorities, accountability (ONLY if explicitly mentioned who is responsible)
10. EXCEPTIONS_SPECIAL_CASES: Error scenarios, alternative paths, contingency procedures (ONLY if explicitly mentioned what happens in exceptions)
11. VISUALIZATION_GRAPH: Process flow representation (ONLY if explicitly described)

CRITICAL EXTRACTION RULES:
1. **EXTRACT NOTHING UNLESS EXPLICITLY STATED**: If information is not directly mentioned in the text, leave that field empty/null
2. **NO INFERENCE ALLOWED**: Do not infer what steps "might" be needed or what roles "probably" exist
3. **NO ASSUMPTIONS**: Do not assume common business practices or standard procedures
4. **NO GENERATION**: Do not create or generate any content not present in the source text
5. **NO INTERPRETATION**: Do not interpret vague statements - only extract clear, specific information
6. **EMPTY IS CORRECT**: It is better to leave fields empty than to guess or assume

WHAT TO EXTRACT VS WHAT TO IGNORE:
✅ EXTRACT: "The process involves three steps: 1) Review application, 2) Verify documents, 3) Approve request"
❌ DON'T EXTRACT: If text says "It's a typical approval process" - don't assume what steps are involved

✅ EXTRACT: "John Smith is responsible for final approval" 
❌ DON'T EXTRACT: If text says "Someone needs to approve this" - don't assume who or what role

✅ EXTRACT: "Required inputs include customer application form and ID copy"
❌ DON'T EXTRACT: If text says "Standard documents are needed" - don't assume what documents

✅ EXTRACT: "Success is measured by processing time under 48 hours"
❌ DON'T EXTRACT: If text says "We track performance" - don't assume what metrics

✅ EXTRACT: "This process excludes international customers"
❌ DON'T EXTRACT: Don't assume what might be excluded if not explicitly stated

FORMATTING STANDARDS FOR EXTRACTED DATA:
- **Use exact wording from source text** - do not paraphrase unless necessary for formatting
- **Preserve terminology** - use the exact terms mentioned in the source
- **For structured lists, use**: "Name: Description" format only if both name and description are explicitly provided
- **For roles**: "Role Title: specific responsibilities" - only if both role and responsibilities are explicitly stated
- **For metrics**: "Metric Name: measurement description. Target: value" - only if all components are explicitly mentioned

QUALITY CONTROL:
- Before extracting any information, ask: "Is this explicitly stated in the text?"
- If you have any doubt about whether information is explicitly provided, DO NOT extract it
- Leave fields empty rather than making educated guesses
- Only extract information that is clear, specific, and directly stated

{format_instructions}

TEXT TO ANALYZE:
{text_to_parse}

REMEMBER: Your job is to be a precise extractor, not a helpful assistant. Extract ONLY what is explicitly provided. Empty fields are better than guessed content."""

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
        # Add timeout protection to prevent hanging on LLM calls
        import asyncio
        
        # Set a reasonable timeout (30 seconds) for the extraction
        timeout_seconds = 30
        
        parsed_output = await asyncio.wait_for(
            chain.ainvoke({"text_to_parse": text_content}),
            timeout=timeout_seconds
        )
        return parsed_output
    except asyncio.TimeoutError:
        print(f"Timeout error: Process extraction took longer than {timeout_seconds} seconds")
        return None
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
    """Generate Mermaid diagram code from process data using AI, with readiness check."""
    
    # Assess visualization readiness first
    readiness = assess_visualization_readiness(process_data)
    
    # Return appropriate placeholder if not ready for full visualization
    if readiness['readiness_level'] == "PLACEHOLDER_ONLY":
        return generate_visualization_placeholder(readiness, "mermaid")
    
    # For simple visualization, use basic generation
    if readiness['readiness_level'] == "SIMPLE_VISUALIZATION":
        return generate_basic_mermaid_from_steps(process_data.get('process_steps', []))
    
    # For basic or full visualization, proceed with AI generation if available
    if not llm:
        print("LLM not initialized, cannot generate Mermaid visualization.")
        if readiness['can_generate_visualization']:
            return generate_basic_mermaid_from_steps(process_data.get('process_steps', []))
        else:
            return generate_visualization_placeholder(readiness, "mermaid")

    # Prepare process data for the prompt (only if AI generation is appropriate)
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
        if readiness['can_generate_visualization']:
            return generate_basic_mermaid_from_steps(process_data.get('process_steps', []))
        else:
            return generate_visualization_placeholder(readiness, "mermaid")

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
        'next_priority_fields': missing_fields[:2] if missing_fields else partial_fields[:2],
        'should_celebrate_completion': len(missing_fields) == 0 and len(partial_fields) == 0,
        'incomplete_dimensions': missing_fields + partial_fields,
        'focus_message': 'All documentation complete! 🎉' if (len(missing_fields) == 0 and len(partial_fields) == 0) else f'Focus on: {", ".join((missing_fields + partial_fields)[:2])}'
    }

async def run_basic_chat_chain_with_progress(input_text: str, process_id: str, chat_history: List = [], current_process_data: dict = None):
    """Enhanced chat chain that includes process documentation progress and role determination context."""
    chain = get_basic_chat_chain()
    if not chain or not embeddings_model:
        return "RAG chat chain not available (LLM or Embeddings likely not initialized)."
    
    # Assess current documentation progress
    progress_info = ""
    if current_process_data:
        progress = assess_process_documentation_progress(current_process_data)
        
        # Provide flexible context for AI to determine appropriate mode
        completion_percentage = progress['completion_percentage']
        
        # Analyze user input for intent signals (for context, not hardcoded decisions)
        input_lower = input_text.lower()
        
        # Documentation intent indicators
        doc_signals = [
            "document", "the process involves", "let me explain", "we do", "the steps are",
            "our process", "first we", "then we", "the inputs are", "the outputs are",
            "responsible for", "when something goes wrong", "exceptions include",
            "what else do you need", "is this complete", "add this", "update this"
        ]
        
        # Explanation intent indicators  
        explain_signals = [
            "how does this work", "what should i do", "who should i contact",
            "what happens when", "what are the requirements", "how do i",
            "what if", "when does this apply", "what are the next steps",
            "can you explain", "help me understand", "what does this mean"
        ]
        
        doc_signals_found = [signal for signal in doc_signals if signal in input_lower]
        explain_signals_found = [signal for signal in explain_signals if signal in input_lower]
        
        progress_info = f"""
CURRENT DOCUMENTATION STATUS:
- Overall Completion: {progress['completion_percentage']:.0f}% ({progress['complete_count']}/{progress['total_dimensions']} dimensions FULLY COMPLETE)
- Complete Areas (DO NOT ASK ABOUT THESE): {', '.join(progress['complete_fields']) if progress['complete_fields'] else 'None yet'}
- Partial Areas (NEED MORE INFO): {', '.join(progress['partial_fields']) if progress['partial_fields'] else 'None'}  
- Missing Areas (PRIORITY FOCUS): {', '.join(progress['missing_fields']) if progress['missing_fields'] else 'None'}

USER INTENT SIGNALS DETECTED:
- Documentation signals found: {', '.join(doc_signals_found) if doc_signals_found else 'None'}
- Explanation signals found: {', '.join(explain_signals_found) if explain_signals_found else 'None'}
- User input: "{input_text[:100]}{'...' if len(input_text) > 100 else ''}"

CRITICAL BEHAVIOR RULES:
- **100% COMPLETE ({progress['completion_percentage']:.0f}% = 100%)**: {'✅ CONGRATULATE USER - All dimensions complete! Switch to Process Explainer mode.' if progress['completion_percentage'] >= 100 else '❌ Still needs work - focus on incomplete areas only.'}
- **NEVER ASK ABOUT COMPLETED DIMENSIONS**: {', '.join(progress['complete_fields']) if progress['complete_fields'] else 'None yet'} are already complete - don't ask for more info about these!
- **FOCUS ONLY ON GAPS**: {', '.join(progress['missing_fields'] + progress['partial_fields']) if (progress['missing_fields'] or progress['partial_fields']) else 'Nothing - all complete!'}

MODE SELECTION GUIDANCE (Choose the most appropriate mode based on context):
- **DOCUMENTATION ASSISTANT MODE**: Use when user is sharing process information, wants to document, or when process needs completion
- **PROCESS EXPLAINER MODE**: Use when user is asking questions about the process, wants explanations, or when process is complete and they need guidance

DYNAMIC BEHAVIOR RULES:
- If process is 100% complete: Congratulate user and primarily use Process Explainer mode
- If user is clearly providing process information: Use Documentation Assistant mode 
- If user is asking questions about the process: Use Process Explainer mode
- If incomplete dimensions exist and user isn't clearly asking questions: Focus on Documentation Assistant mode
- Never ask about complete dimensions - acknowledge them briefly if mentioned

COMPLETION REMINDERS:
- Complete dimensions have comprehensive information (100+ chars for text, 2+ substantial items for lists)
- Don't ask follow-up questions about complete dimensions - they're done!
- When all 9 dimensions are complete, celebrate the achievement!

TITLE/DESCRIPTION STATUS:
- Title: {'Generated' if current_process_data.get('title') else 'Generate when process purpose is clear (AI-generated, not counted in 9 dimensions)'}

FOCUS: {progress['focus_message']}
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

# --- Enhanced React Flow Visualization Generation ---
async def generate_reactflow_from_process_data(process_data: dict) -> dict:
    """Generate React Flow nodes and edges from process data using AI, with readiness check."""
    
    # Assess visualization readiness first
    readiness = assess_visualization_readiness(process_data)
    
    # Return appropriate placeholder if not ready for full visualization
    if readiness['readiness_level'] == "PLACEHOLDER_ONLY":
        return generate_visualization_placeholder(readiness, "reactflow")
    
    # For simple visualization, use basic generation
    if readiness['readiness_level'] == "SIMPLE_VISUALIZATION":
        return generate_basic_reactflow_from_steps(process_data.get('process_steps', []))
    
    # For basic or full visualization, proceed with AI generation if available
    if not llm:
        print("LLM not initialized, cannot generate React Flow visualization.")
        if readiness['can_generate_visualization']:
            return generate_basic_reactflow_from_steps(process_data.get('process_steps', []))
        else:
            return generate_visualization_placeholder(readiness, "reactflow")
    
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

def assess_visualization_readiness(process_data: dict) -> dict:
    """
    Determines if there's sufficient information to generate meaningful visualizations.
    Returns assessment including readiness level and recommendations.
    """
    # Essential information for meaningful visualizations
    has_title = bool(process_data.get('title', '').strip())
    has_description = bool(process_data.get('general_description', '').strip())
    process_steps = process_data.get('process_steps', [])
    has_meaningful_steps = bool(process_steps and len(process_steps) >= 2)
    
    # Calculate step quality (steps with substantial content)
    substantial_steps = 0
    if process_steps:
        for step in process_steps:
            if isinstance(step, str) and len(step.strip()) >= 20:
                substantial_steps += 1
    
    # Supporting information that enhances visualizations
    has_inputs = bool(process_data.get('inputs', []))
    has_outputs = bool(process_data.get('outputs', []))
    has_roles = bool(process_data.get('roles_responsibilities', []))
    has_exceptions = bool(process_data.get('exceptions_special_cases', []))
    
    # Determine readiness level
    essential_score = 0
    if has_title: essential_score += 1
    if has_description: essential_score += 2
    if has_meaningful_steps: essential_score += 3
    if substantial_steps >= 3: essential_score += 2
    
    enhancement_score = 0
    if has_inputs: enhancement_score += 1
    if has_outputs: enhancement_score += 1
    if has_roles: enhancement_score += 1
    if has_exceptions: enhancement_score += 1
    
    total_score = essential_score + enhancement_score
    
    # Determine visualization strategy
    if essential_score >= 6 and substantial_steps >= 3:
        readiness_level = "FULL_VISUALIZATION"
        strategy = "Generate detailed AI-powered visualization with all features"
    elif essential_score >= 4 and has_meaningful_steps:
        readiness_level = "BASIC_VISUALIZATION" 
        strategy = "Generate basic flowchart from available steps"
    elif has_meaningful_steps:
        readiness_level = "SIMPLE_VISUALIZATION"
        strategy = "Generate simple step-by-step diagram"
    else:
        readiness_level = "PLACEHOLDER_ONLY"
        strategy = "Show informative placeholder with guidance"
    
    # Missing elements for better visualizations
    missing_elements = []
    if not has_title:
        missing_elements.append("Process title")
    if not has_description:
        missing_elements.append("Process description")
    if not has_meaningful_steps:
        missing_elements.append("At least 2 process steps")
    if substantial_steps < 3:
        missing_elements.append("More detailed step descriptions")
    
    return {
        'readiness_level': readiness_level,
        'strategy': strategy,
        'essential_score': essential_score,
        'enhancement_score': enhancement_score,
        'total_score': total_score,
        'has_meaningful_steps': has_meaningful_steps,
        'substantial_steps_count': substantial_steps,
        'total_steps_count': len(process_steps) if process_steps else 0,
        'missing_elements': missing_elements,
        'can_generate_visualization': readiness_level != "PLACEHOLDER_ONLY",
        'should_use_ai_generation': readiness_level == "FULL_VISUALIZATION",
        'placeholder_message': f"Need {', '.join(missing_elements)} for meaningful visualization" if missing_elements else "Ready for visualization"
    }

def generate_visualization_placeholder(readiness_assessment: dict, visualization_type: str = "process") -> str:
    """Generate informative placeholder content based on readiness assessment."""
    
    if visualization_type == "mermaid":
        if readiness_assessment['readiness_level'] == "PLACEHOLDER_ONLY":
            return """graph TD
    Start(("🚀 START")) --> Gather
    Gather["📝 Gather Process Information"] --> Steps
    Steps["➡️ Define Process Steps"] --> Visualize
    Visualize["📊 Generate Visualization"] --> End
    End(("✨ END"))
    
    %% Placeholder styling
    style Start fill:#e0f2fe,stroke:#0284c7,stroke-width:2px
    style Gather fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style Steps fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style Visualize fill:#dcfce7,stroke:#16a34a,stroke-width:2px
    style End fill:#e0f2fe,stroke:#0284c7,stroke-width:2px
    
    %% Add informative text
    classDef infoText fill:#f9f9f9,stroke:#666,stroke-width:1px,font-size:12px
    
    Info1["ℹ️ Add process steps through AI chat"]
    Info2["💡 Upload documents for auto-extraction"] 
    Info3["🎯 Define inputs, outputs, and roles"]
    
    Gather -.-> Info1
    Steps -.-> Info2
    Visualize -.-> Info3
    
    class Info1,Info2,Info3 infoText"""
        else:
            # For other levels, return basic structure to be filled
            return generate_basic_mermaid_from_steps(readiness_assessment.get('process_steps', []))
    
    elif visualization_type == "reactflow":
        if readiness_assessment['readiness_level'] == "PLACEHOLDER_ONLY":
            return {
                "nodes": [
                    {
                        "id": "start",
                        "type": "startEnd",
                        "position": {"x": 400, "y": 50},
                        "data": {"label": "🚀 START", "description": "Begin by documenting your process", "isStart": True}
                    },
                    {
                        "id": "gather",
                        "type": "process", 
                        "position": {"x": 300, "y": 150},
                        "data": {"label": "📝 Gather Information", "description": "Use AI chat to document process details"}
                    },
                    {
                        "id": "steps",
                        "type": "process",
                        "position": {"x": 500, "y": 150}, 
                        "data": {"label": "➡️ Define Steps", "description": "Upload documents or describe your process"}
                    },
                    {
                        "id": "enhance",
                        "type": "process",
                        "position": {"x": 400, "y": 250},
                        "data": {"label": "🎯 Add Details", "description": "Include inputs, outputs, roles & responsibilities"}
                    },
                    {
                        "id": "visualize",
                        "type": "process",
                        "position": {"x": 400, "y": 350},
                        "data": {"label": "📊 Auto-Generate", "description": "Visualization will appear automatically"}
                    },
                    {
                        "id": "end",
                        "type": "startEnd",
                        "position": {"x": 400, "y": 450},
                        "data": {"label": "✨ COMPLETE", "description": "Interactive process visualization ready", "isStart": False}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "start", "target": "gather", "type": "smoothstep", "markerEnd": {"type": "ArrowClosed"}},
                    {"id": "e2", "source": "start", "target": "steps", "type": "smoothstep", "markerEnd": {"type": "ArrowClosed"}},
                    {"id": "e3", "source": "gather", "target": "enhance", "type": "smoothstep", "markerEnd": {"type": "ArrowClosed"}},
                    {"id": "e4", "source": "steps", "target": "enhance", "type": "smoothstep", "markerEnd": {"type": "ArrowClosed"}},
                    {"id": "e5", "source": "enhance", "target": "visualize", "type": "smoothstep", "markerEnd": {"type": "ArrowClosed"}},
                    {"id": "e6", "source": "visualize", "target": "end", "type": "smoothstep", "markerEnd": {"type": "ArrowClosed"}}
                ]
            }
    
    # Default HTML placeholder
    missing_info = readiness_assessment.get('missing_elements', [])
    placeholder_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Process Visualization Placeholder</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 40px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .placeholder-container {{ 
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 600px;
            text-align: center;
        }}
        .icon {{ font-size: 4rem; margin-bottom: 20px; }}
        h1 {{ color: #1f2937; margin-bottom: 16px; }}
        .subtitle {{ color: #6b7280; font-size: 1.1rem; margin-bottom: 30px; }}
        .missing-list {{ 
            background: #fef3c7; 
            border: 1px solid #f59e0b; 
            border-radius: 8px; 
            padding: 20px; 
            margin: 20px 0;
            text-align: left;
        }}
        .missing-list h3 {{ color: #d97706; margin-top: 0; }}
        .missing-item {{ 
            display: flex; 
            align-items: center; 
            margin: 8px 0; 
            color: #92400e;
        }}
        .checkmark {{ color: #10b981; margin-right: 8px; }}
        .guidance {{ 
            background: #eff6ff; 
            border: 1px solid #3b82f6; 
            border-radius: 8px; 
            padding: 20px; 
            margin-top: 20px;
        }}
        .guidance h3 {{ color: #1e40af; margin-top: 0; }}
        .guidance-item {{ margin: 8px 0; color: #1e3a8a; }}
    </style>
</head>
<body>
    <div class="placeholder-container">
        <div class="icon">📊</div>
        <h1>Process Visualization</h1>
        <p class="subtitle">Interactive visualization will appear here once you provide process information</p>
        
        <div class="missing-list">
            <h3>🎯 Information Needed:</h3>
            {chr(10).join([f'<div class="missing-item">• {item}</div>' for item in missing_info])}
        </div>
        
        <div class="guidance">
            <h3>💡 How to Get Started:</h3>
            <div class="guidance-item">💬 <strong>Use AI Chat:</strong> Describe your process step-by-step</div>
            <div class="guidance-item">📄 <strong>Upload Documents:</strong> PDF/Word files for automatic extraction</div>
            <div class="guidance-item">🎙️ <strong>Voice Input:</strong> Record voice messages describing your process</div>
            <div class="guidance-item">✨ <strong>Auto-Generation:</strong> Visualization updates automatically as you add information</div>
        </div>
    </div>
</body>
</html>"""
    
    return placeholder_html 

def should_regenerate_visualizations(old_data: dict, new_data: dict) -> dict:
    """
    Determines if changes to process data warrant regenerating visualizations.
    Returns information about what should be regenerated and why.
    """
    
    # Fields that significantly impact visualization structure
    critical_fields = ['process_steps', 'general_description']
    
    # Fields that enhance visualizations but don't require full regeneration
    enhancement_fields = ['inputs', 'outputs', 'roles_responsibilities', 'exceptions_special_cases']
    
    # Check for critical changes
    critical_changes = []
    for field in critical_fields:
        old_value = old_data.get(field, []) if isinstance(old_data.get(field), list) else old_data.get(field, '')
        new_value = new_data.get(field, []) if isinstance(new_data.get(field), list) else new_data.get(field, '')
        
        if old_value != new_value:
            critical_changes.append(field)
    
    # Check for enhancement changes
    enhancement_changes = []
    for field in enhancement_fields:
        old_value = old_data.get(field, []) if isinstance(old_data.get(field), list) else old_data.get(field, '')
        new_value = new_data.get(field, []) if isinstance(new_data.get(field), list) else new_data.get(field, '')
        
        if old_value != new_value:
            enhancement_changes.append(field)
    
    # Assess readiness change
    old_readiness = assess_visualization_readiness(old_data)
    new_readiness = assess_visualization_readiness(new_data)
    
    readiness_improved = (
        new_readiness['readiness_level'] != old_readiness['readiness_level'] or
        new_readiness['can_generate_visualization'] != old_readiness['can_generate_visualization']
    )
    
    # Determine regeneration strategy
    should_regenerate = bool(critical_changes or readiness_improved)
    regeneration_priority = "HIGH" if critical_changes else ("MEDIUM" if readiness_improved else "LOW")
    
    # Only regenerate if it makes sense
    if new_readiness['readiness_level'] == "PLACEHOLDER_ONLY" and old_readiness['readiness_level'] == "PLACEHOLDER_ONLY":
        should_regenerate = False
        regeneration_priority = "NONE"
    
    return {
        'should_regenerate': should_regenerate,
        'priority': regeneration_priority,
        'critical_changes': critical_changes,
        'enhancement_changes': enhancement_changes,
        'readiness_improved': readiness_improved,
        'old_readiness_level': old_readiness['readiness_level'],
        'new_readiness_level': new_readiness['readiness_level'],
        'reason': f"{'Critical changes: ' + ', '.join(critical_changes) if critical_changes else ''}{'Readiness improved' if readiness_improved else ''}".strip()
    }

async def auto_regenerate_visualizations_if_needed(process_id: str, old_data: dict, new_data: dict, db_process) -> dict:
    """
    Automatically regenerates visualizations if process data changes warrant it.
    Returns information about what was regenerated.
    """
    
    regeneration_info = should_regenerate_visualizations(old_data, new_data)
    results = {
        'regeneration_needed': regeneration_info['should_regenerate'],
        'priority': regeneration_info['priority'],
        'reason': regeneration_info['reason'],
        'reactflow_regenerated': False,
        'mermaid_regenerated': False,
        'error': None
    }
    
    if not regeneration_info['should_regenerate']:
        return results
    
    try:
        print(f"Auto-regenerating visualizations for process {process_id}: {regeneration_info['reason']}")
        
        # Regenerate ReactFlow data (higher priority)
        if regeneration_info['priority'] in ['HIGH', 'MEDIUM']:
            try:
                new_reactflow_data = await generate_reactflow_from_process_data(new_data)
                if new_reactflow_data:
                    db_process.reactflow_data = new_reactflow_data
                    results['reactflow_regenerated'] = True
                    print(f"✅ ReactFlow visualization regenerated for process {process_id}")
            except Exception as e:
                print(f"❌ Error regenerating ReactFlow for process {process_id}: {e}")
                results['error'] = f"ReactFlow: {str(e)}"
        
        # Note: Mermaid regeneration is handled on-demand since it's not cached in DB
        # The updated generate_mermaid_from_process_data will automatically use new data
        results['mermaid_regenerated'] = True  # Will regenerate on next request
        
        return results
        
    except Exception as e:
        print(f"❌ Error in auto-regeneration for process {process_id}: {e}")
        results['error'] = str(e)
        return results