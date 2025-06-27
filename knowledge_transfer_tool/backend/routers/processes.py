from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import shutil
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus.flowables import HRFlowable
from datetime import datetime
import tempfile

from langchain_core.messages import AIMessage, HumanMessage

from .. import models, schemas
from ..database import get_db, UPLOAD_DIRECTORY
from ..services.openai_service import transcribe_audio_with_whisper
from ..services.langchain_service import (
    run_basic_chat_chain_with_progress, 
    extract_process_from_text,
    add_text_to_vector_store, # Added
    query_document_store,      # Added
    generate_simple_html_visualization,
    generate_mermaid_from_process_data,
    generate_basic_mermaid_from_steps
)
from ..services.document_service import extract_text_from_file, SUPPORTED_MIME_TYPES

router = APIRouter()



@router.post("/processes", response_model=schemas.Process)
def create_process(process: schemas.ProcessCreate, db: Session = Depends(get_db)):
    try:
        db_process = models.Process(**process.dict())
        db.add(db_process)
        db.commit()
        db.refresh(db_process)
        return db_process
    except Exception as e:
        print(f"Error creating process: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create process: {str(e)}")

@router.get("/processes", response_model=List[schemas.Process])
def read_processes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    processes = db.query(models.Process).offset(skip).limit(limit).all()
    return processes

@router.get("/processes/{process_id}", response_model=schemas.Process)
def read_process(process_id: str, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    return db_process

@router.put("/processes/{process_id}", response_model=schemas.Process)
def update_process(process_id: str, process: schemas.ProcessUpdate, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    
    try:
        update_data = process.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_process, key, value)
        
        db.add(db_process)
        db.commit()
        db.refresh(db_process)
        return db_process
    except Exception as e:
        print(f"Error updating process {process_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update process: {str(e)}")

@router.delete("/processes/{process_id}", response_model=schemas.Process)
def delete_process(process_id: str, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Delete related chat messages first
    db.query(models.ChatMessage).filter(models.ChatMessage.process_id == process_id).delete()
    
    # Delete related documents if any
    db.query(models.Document).filter(models.Document.process_id == process_id).delete()
    
    # Now delete the process
    db.delete(db_process)
    db.commit()
    return db_process

@router.post("/processes/{process_id}/upload-file", response_model=schemas.FileUploadResponse)
async def upload_file_for_process(process_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")

    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    transcript_text = None
    extracted_doc_text = None
    structured_data_from_doc_model = None
    added_to_vector_store = False

    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        # Log file upload as a user message (commit immediately so it appears first)
        db_upload_msg = models.ChatMessage(
            process_id=process_id,
            sender_type="user",
            content=f"Uploaded: {file.filename}"
        )
        db.add(db_upload_msg)
        db.commit()  # Commit user upload message immediately
        db.refresh(db_upload_msg)
        
        print(f"Saved user upload message: 'Uploaded: {file.filename}' for process {process_id}")

        text_content_for_vector_store = None
        ai_response_text = ""

        if file.content_type and file.content_type.startswith("audio/"):
            print(f"Processing audio file: {file.filename}")
            transcript_text = await transcribe_audio_with_whisper(file_location)
            if transcript_text and not transcript_text.startswith("Error"):
                # Update the user message with the actual transcription instead of the filename
                db_upload_msg.content = transcript_text
                db.commit()
                db.refresh(db_upload_msg)
                print(f"Updated user message with transcription: '{transcript_text[:50]}...' for process {process_id}")
                
                text_content_for_vector_store = transcript_text
                ai_response_text = f"**Great!** I've transcribed your voice message and found some good process information. \n\nWhat **specific steps** are involved in this process?"
            elif transcript_text: # Error in transcription
                # Update the user message to show the error instead of the filename
                db_upload_msg.content = f"Voice message transcription failed: {transcript_text}"
                db.commit()
                db.refresh(db_upload_msg)
                print(f"Updated user message with transcription error for process {process_id}")
                
                ai_response_text = f"I had trouble with that audio file. Could you try **recording again** or just tell me about your process in text?"

        elif file.content_type in SUPPORTED_MIME_TYPES:
            print(f"Processing document file: {file.filename} ({file.content_type})")
            extracted_doc_text = extract_text_from_file(file_location, file.content_type)
            if extracted_doc_text and not extracted_doc_text.startswith("Error"):
                text_content_for_vector_store = extracted_doc_text
                ai_response_text = f"**Excellent!** I've processed your document **\"{file.filename}\"** and found some useful process information. \n\nWhat are the **main steps** someone would follow in this process?"

                structured_data_from_doc_model = await extract_process_from_text(extracted_doc_text)
                if structured_data_from_doc_model:
                    ai_response_text = f"**Perfect!** I found structured process information in **\"{file.filename}\"** and updated your documentation. \n\nWhat **inputs or materials** does someone need to start this process?"
                    for key, value in structured_data_from_doc_model.model_dump(exclude_none=True).items():
                        if hasattr(db_process, key):
                            if isinstance(value, list) and isinstance(getattr(db_process, key), list):
                                current_list = getattr(db_process, key)
                                new_items = [item for item in value if item not in current_list]
                                if new_items:
                                   setattr(db_process, key, current_list + new_items)
                            elif value is not None: 
                                setattr(db_process, key, value)
                    db.commit()
                    db.refresh(db_process)
            else:
                ai_response_text = f"I couldn't extract text from **\"{file.filename}\"**. Could you try a **different format** (PDF or DOCX work best) or just describe the key steps to me?"

        # Save the AI response (after processing is complete)
        if ai_response_text:
            db_ai_response_msg = models.ChatMessage(
                process_id=process_id,
                sender_type="ai",
                content=ai_response_text
            )
            db.add(db_ai_response_msg)
            db.commit()  # Commit AI response
            db.refresh(db_ai_response_msg)
            print(f"Saved AI response message for process {process_id}")

        if text_content_for_vector_store:
            print(f"Adding text from {file.filename} to vector store for process {process_id}")
            added_to_vector_store = await add_text_to_vector_store(text_content_for_vector_store, str(process_id), file.filename)

    except Exception as e:
        print(f"Exception in upload_file_for_process: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not save or process file. Error: {str(e)}")
    finally:
        await file.close()
    
    return schemas.FileUploadResponse(
        filename=file.filename, 
        location=file_location, 
        content_type=file.content_type,
        message="File uploaded and processed",
        transcript=transcript_text,
        extracted_text_snippet=extracted_doc_text[:500] + ("..." if extracted_doc_text and len(extracted_doc_text) > 500 else "") if extracted_doc_text else None,
        extracted_process_data=structured_data_from_doc_model,
        vector_store_status="Content added to vector store" if added_to_vector_store else "Failed or not applicable",
        ai_response=ai_response_text  # Include AI response for frontend
    )

@router.post("/processes/{process_id}/chat", response_model=schemas.ChatResponse)
async def process_chat(process_id: str, message_payload: Dict[str, str], db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    
    user_message = message_payload.get("text", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    # Handle welcome message for new processes
    if user_message == "SYSTEM_WELCOME_MESSAGE":
        # Check if any messages already exist for this process
        existing_messages = db.query(models.ChatMessage).filter(models.ChatMessage.process_id == process_id).count()
        
        if existing_messages == 0:
            welcome_text = """Hello! I'm your Business Process Documentation Assistant. 

I'll help you create complete process documentation by asking targeted questions to capture every important detail. You can share information through text, voice messages, or document uploads.

What process would you like to document today?"""
            
            # Save AI welcome message to DB
            db_welcome_message = models.ChatMessage(
                process_id=process_id,
                sender_type="ai",
                content=welcome_text
            )
            db.add(db_welcome_message)
            db.commit()
            db.refresh(db_welcome_message)
            
            return schemas.ChatResponse(
                user_message="",  # No user message for welcome
                ai_chat_response=welcome_text,
                extracted_process_data=None
            )
        else:
            # If messages already exist, don't create welcome message
            return schemas.ChatResponse(
                user_message="",
                ai_chat_response="",
                extracted_process_data=None
            )

    # 1. Fetch recent chat history (e.g., last 10 messages)
    db_chat_history = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.process_id == process_id)
        .order_by(models.ChatMessage.created_at.desc()) # Get newest first
        .limit(10) # Limit the number of messages for context window
        .all()
    )
    db_chat_history.reverse() # Reverse to get chronological order (oldest to newest)

    # 2. Format history for LangChain
    langchain_history: List[Any] = [] # Using Any to represent BaseMessage types
    for msg in db_chat_history:
        if msg.sender_type == 'user':
            langchain_history.append(HumanMessage(content=msg.content))
        elif msg.sender_type == 'ai':
            langchain_history.append(AIMessage(content=msg.content))
        # We can ignore 'system' messages for the direct chat history for now, or handle as needed.

    # Save user message to DB (BEFORE calling AI, so it's part of history if AI were to see current turn)
    db_user_chat_message = models.ChatMessage(
        process_id=process_id,
        sender_type="user",
        content=user_message
    )
    db.add(db_user_chat_message)
    # Commit user message now, so if AI call fails, user message is still saved.
    db.commit()
    db.refresh(db_user_chat_message)

    # Append current user message to langchain_history for the current call
    # This is what the AI will see as the latest human input within the history context.
    langchain_history.append(HumanMessage(content=user_message))

    # 3. Call LangChain service with history and process_id for RAG, including current process state
    current_process_data = {
        'title': db_process.title,
        'general_description': db_process.general_description,
        'process_steps': db_process.process_steps or [],
        'scope_included': db_process.scope_included or [],
        'scope_excluded': db_process.scope_excluded or [],
        'inputs': db_process.inputs or [],
        'outputs': db_process.outputs or [],
        'kpis': db_process.kpis or [],
        'roles_responsibilities': db_process.roles_responsibilities or [],
        'exceptions_special_cases': db_process.exceptions_special_cases or [],
        'visualization_graph': db_process.visualization_graph
    }
    
    ai_chat_response_text = await run_basic_chat_chain_with_progress(
        input_text=user_message, 
        process_id=str(process_id), # Ensure process_id is a string if langchain_service expects it that way
        chat_history=langchain_history,
        current_process_data=current_process_data
    )
    
    # Extract structured data from user message
    extracted_data_model = await extract_process_from_text(user_message)
    
    # Also try to extract any structured data the AI might have generated in its response
    ai_generated_data = await extract_process_from_text(ai_chat_response_text)
    
    # Save AI response to DB
    db_ai_chat_message = models.ChatMessage(
        process_id=process_id,
        sender_type="ai",
        content=ai_chat_response_text
        # Potentially add metadata if extracted_data_model is not None
    )
    db.add(db_ai_chat_message)
    
    db.commit() # Commit both messages
    db.refresh(db_ai_chat_message)   # Optional

    # Update process with extracted data from user message
    if extracted_data_model:
        print(f"Extracted structured data from user message: {extracted_data_model.model_dump(exclude_none=True)}")
        for key, value in extracted_data_model.model_dump(exclude_none=True).items():
            if hasattr(db_process, key):
                current_db_value = getattr(db_process, key)
                # Special handling for list fields: append new unique items
                if isinstance(value, list) and isinstance(current_db_value, list):
                    new_items = [item for item in value if item not in current_db_value]
                    if new_items:
                        setattr(db_process, key, current_db_value + new_items)
                # For non-list fields, or if db field is not a list, overwrite if new value is provided
                elif value is not None: 
                    setattr(db_process, key, value)
    
    # Update process with AI-generated data (title, description, formatted content)
    if ai_generated_data:
        print(f"Extracted AI-generated data: {ai_generated_data.model_dump(exclude_none=True)}")
        for key, value in ai_generated_data.model_dump(exclude_none=True).items():
            if hasattr(db_process, key) and value is not None:
                # For title and description, always update if AI generated them
                if key in ['title', 'general_description']:
                    setattr(db_process, key, value)
                # For other fields, use same logic as user data
                else:
                    current_db_value = getattr(db_process, key)
                    if isinstance(value, list) and isinstance(current_db_value, list):
                        new_items = [item for item in value if item not in current_db_value]
                        if new_items:
                            setattr(db_process, key, current_db_value + new_items)
                    elif value is not None: 
                        setattr(db_process, key, value)
    
    # Commit any process updates
    if extracted_data_model or ai_generated_data:
        db.add(db_process) # Add db_process again to mark it as dirty for commit
        db.commit()        # Commit changes to the db_process
        db.refresh(db_process) # Refresh to get updated data if needed elsewhere

    return schemas.ChatResponse(
        user_message=user_message, 
        ai_chat_response=ai_chat_response_text,
        extracted_process_data=extracted_data_model or ai_generated_data
    )

@router.post("/processes/{process_id}/query-documents", response_model=schemas.DocumentQueryResponse)
async def query_process_documents(process_id: str, query_payload: Dict[str, str], db: Session = Depends(get_db)):
    user_query = query_payload.get("text", "")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query text cannot be empty")

    ai_response_text = await query_document_store(user_query, str(process_id))
    
    return schemas.DocumentQueryResponse(
        user_query=user_query, 
        ai_response=ai_response_text
    )

@router.get("/processes/{process_id}/chat-history", response_model=List[schemas.ChatMessageResponse])
def get_chat_history(process_id: str, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Query chat messages associated with this process, ordered by creation time
    chat_history = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.process_id == process_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    
    return chat_history

@router.get("/processes/{process_id}/visualize", response_class=Response)
async def get_process_visualization(process_id: str, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")

    try:
        process_schema = schemas.Process.model_validate(db_process)
        process_data_text = str(process_schema.model_dump(exclude_none=True))
    except Exception as e:
        print(f"Error converting process to schema for visualization: {type(e).__name__} - {e}")
        fallback_desc = db_process.general_description[:50] + "..." if db_process.general_description else "N/A"
        process_data_text = f"Could not load full details for process {process_id}. ID={db_process.id}, Description snippet='{fallback_desc}'"

    html_content = await generate_simple_html_visualization(process_data_text)
    
    return Response(content=html_content, media_type="text/html")

@router.get("/processes/{process_id}/mermaid", response_class=Response)
async def get_process_mermaid(process_id: str, db: Session = Depends(get_db)):
    """Get Mermaid diagram code for a process."""
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")

    try:
        # Convert DB model to dict for the mermaid generator
        process_data = {
            'title': db_process.title,
            'general_description': db_process.general_description,
            'process_steps': db_process.process_steps or [],
            'scope_included': db_process.scope_included or [],
            'scope_excluded': db_process.scope_excluded or [],
            'inputs': db_process.inputs or [],
            'outputs': db_process.outputs or [],
            'kpis': db_process.kpis or [],
            'roles_responsibilities': db_process.roles_responsibilities or [],
            'exceptions_special_cases': db_process.exceptions_special_cases or []
        }
        
        # Check if we have a cached mermaid code in the database
        if hasattr(db_process, 'mermaid_diagram') and db_process.mermaid_diagram:
            mermaid_code = db_process.mermaid_diagram
        else:
            # Generate new mermaid code
            mermaid_code = await generate_mermaid_from_process_data(process_data)
            
            # Cache it in the database if we have a field for it
            # Note: You might want to add a mermaid_diagram field to the Process model
            # db_process.mermaid_diagram = mermaid_code
            # db.commit()
        
        return Response(content=mermaid_code, media_type="text/plain")
        
    except Exception as e:
        print(f"Error generating Mermaid visualization: {e}")
        # Fallback to basic generation
        fallback_mermaid = generate_basic_mermaid_from_steps(db_process.process_steps or [])
        return Response(content=fallback_mermaid, media_type="text/plain")

@router.post("/processes/{process_id}/generate-mermaid")
async def regenerate_process_mermaid(process_id: str, db: Session = Depends(get_db)):
    """Regenerate Mermaid diagram for a process using AI."""
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")

    try:
        # Convert DB model to dict for the mermaid generator
        process_data = {
            'title': db_process.title,
            'general_description': db_process.general_description,
            'process_steps': db_process.process_steps or [],
            'scope_included': db_process.scope_included or [],
            'scope_excluded': db_process.scope_excluded or [],
            'inputs': db_process.inputs or [],
            'outputs': db_process.outputs or [],
            'kpis': db_process.kpis or [],
            'roles_responsibilities': db_process.roles_responsibilities or [],
            'exceptions_special_cases': db_process.exceptions_special_cases or []
        }
        
        # Force regeneration with AI
        mermaid_code = await generate_mermaid_from_process_data(process_data)
        
        # Cache the new diagram in the database if we have a field for it
        # Note: You might want to add a mermaid_diagram field to the Process model
        # db_process.mermaid_diagram = mermaid_code
        # db.commit()
        
        return {"success": True, "message": "Mermaid diagram regenerated successfully"}
        
    except Exception as e:
        print(f"Error regenerating Mermaid visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate visualization: {str(e)}")

@router.get("/processes/{process_id}/export-pdf")
async def export_process_to_pdf(process_id: str, db: Session = Depends(get_db)):
    """Export process details to PDF format with enhanced styling"""
    db_process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if db_process is None:
        raise HTTPException(status_code=404, detail="Process not found")

    try:
        # Create a buffer for the PDF
        buffer = BytesIO()
        
        # Create the PDF document with enhanced settings
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            topMargin=0.8*inch, 
            bottomMargin=0.8*inch,
            leftMargin=0.8*inch, 
            rightMargin=0.8*inch,
            title=db_process.title or "Process Documentation"
        )
        
        # Enhanced styles
        styles = getSampleStyleSheet()
        
        # Custom title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            spaceBefore=20,
            textColor=colors.HexColor('#1e40af'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Custom heading styles
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=25,
            textColor=colors.HexColor('#1f2937'),
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.HexColor('#e5e7eb'),
            borderPadding=8,
            backColor=colors.HexColor('#f9fafb')
        )
        
        # Custom subheading style
        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica-Bold'
        )
        
        # Enhanced normal text style
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            spaceBefore=4,
            textColor=colors.HexColor('#1f2937'),
            fontName='Helvetica',
            leading=14,
            leftIndent=12
        )
        
        # Bullet point style
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=normal_style,
            leftIndent=24,
            bulletIndent=12,
            spaceBefore=4,
            spaceAfter=4
        )
        
        # Content container
        content = []
        
        # Title page
        title = db_process.title or "Process Documentation"
        content.append(Spacer(1, 2*inch))
        content.append(Paragraph(title, title_style))
        content.append(Spacer(1, 0.5*inch))
        
        # Subtitle with process ID
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        content.append(Paragraph(f"Process ID: {process_id}", subtitle_style))
        content.append(Spacer(1, 0.3*inch))
        
        # Add a decorative line
        content.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3b82f6')))
        content.append(Spacer(1, 0.5*inch))
        
        # Generated date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#9ca3af'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        content.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}", date_style))
        
        # Page break to start content
        content.append(PageBreak())
        
        # Table of Contents
        toc_style = ParagraphStyle(
            'TOCStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceBefore=8,
            spaceAfter=8,
            leftIndent=20,
            fontName='Helvetica'
        )
        
        content.append(Paragraph("Table of Contents", heading_style))
        content.append(Spacer(1, 10))
        
        # Dynamic TOC based on available content
        toc_items = []
        section_num = 1
        
        if db_process.general_description:
            toc_items.append(f"{section_num}. Overview")
            section_num += 1
            
        if db_process.process_steps and len(db_process.process_steps) > 0:
            toc_items.append(f"{section_num}. Process Flow Diagram")
            section_num += 1
            
        if db_process.scope_included or db_process.scope_excluded:
            toc_items.append(f"{section_num}. Scope")
            section_num += 1
            
        if db_process.process_steps and len(db_process.process_steps) > 0:
            toc_items.append(f"{section_num}. Process Steps")
            section_num += 1
            
        if (db_process.inputs and len(db_process.inputs) > 0) or (db_process.outputs and len(db_process.outputs) > 0):
            toc_items.append(f"{section_num}. Inputs & Outputs")
            section_num += 1
            
        if db_process.kpis and len(db_process.kpis) > 0:
            toc_items.append(f"{section_num}. Key Performance Indicators")
            section_num += 1
            
        if db_process.roles_responsibilities and len(db_process.roles_responsibilities) > 0:
            toc_items.append(f"{section_num}. Roles & Responsibilities")
            section_num += 1
            
        if db_process.exceptions_special_cases and len(db_process.exceptions_special_cases) > 0:
            toc_items.append(f"{section_num}. Exception Handling")
        
        for item in toc_items:
            content.append(Paragraph(item, toc_style))
        
        content.append(PageBreak())
        
        # Reset section counter
        section_num = 1
        
        # 1. Overview Section
        if db_process.general_description:
            content.append(Paragraph(f"{section_num}. Overview", heading_style))
            content.append(Spacer(1, 10))
            section_num += 1
            
            # Create a styled box for the overview with proper text wrapping
            overview_para = Paragraph(db_process.general_description, ParagraphStyle(
                'OverviewStyle',
                parent=normal_style,
                fontSize=11,
                leading=14,
                leftIndent=0,
                spaceBefore=6,
                spaceAfter=6,
                textColor=colors.HexColor('#1e40af')
            ))
            
            overview_data = [[overview_para]]
            overview_table = Table(overview_data, colWidths=[6.5*inch])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f9ff')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bfdbfe')),
            ]))
            content.append(overview_table)
            content.append(Spacer(1, 20))
        

        
        # 2. Scope Section
        if db_process.scope_included or db_process.scope_excluded:
            content.append(Paragraph(f"{section_num}. Scope", heading_style))
            content.append(Spacer(1, 10))
            section_num += 1
            
            if db_process.scope_included and len(db_process.scope_included) > 0:
                content.append(Paragraph("What's Included:", subheading_style))
                for item in db_process.scope_included:
                    content.append(Paragraph(f"• {item}", bullet_style))
                content.append(Spacer(1, 10))
            
            if db_process.scope_excluded and len(db_process.scope_excluded) > 0:
                content.append(Paragraph("What's Excluded:", subheading_style))
                for item in db_process.scope_excluded:
                    content.append(Paragraph(f"• {item}", bullet_style))
                content.append(Spacer(1, 10))
            
            content.append(Spacer(1, 15))
        
        # 3. Process Steps Section (Fixed formatting)
        if db_process.process_steps and len(db_process.process_steps) > 0:
            content.append(Paragraph(f"{section_num}. Process Steps", heading_style))
            content.append(Spacer(1, 10))
            section_num += 1
            
            # Create a table for process steps with proper text wrapping
            steps_data = [['Step', 'Description']]
            for i, step in enumerate(db_process.process_steps, 1):
                # Use Paragraph for description to enable text wrapping
                description_para = Paragraph(step, ParagraphStyle(
                    'StepDescription',
                    parent=normal_style,
                    fontSize=10,
                    leading=12,
                    leftIndent=0,
                    spaceBefore=4,
                    spaceAfter=4
                ))
                steps_data.append([str(i), description_para])
            
            steps_table = Table(steps_data, colWidths=[0.6*inch, 6.0*inch])
            steps_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),  # Step numbers
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (0, -1), 11),  # Step numbers
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f9fafb'), colors.white]),
            ]))
            content.append(steps_table)
            content.append(Spacer(1, 20))
        
        # 4. Inputs & Outputs Section (Fixed formatting)
        if (db_process.inputs and len(db_process.inputs) > 0) or (db_process.outputs and len(db_process.outputs) > 0):
            content.append(Paragraph(f"{section_num}. Inputs & Outputs", heading_style))
            content.append(Spacer(1, 10))
            section_num += 1
            
            # Create separate tables for better formatting
            if db_process.inputs and len(db_process.inputs) > 0:
                content.append(Paragraph("Required Inputs:", subheading_style))
                
                inputs_data = [['Input']]
                for inp in db_process.inputs:
                    input_para = Paragraph(f"• {inp}", ParagraphStyle(
                        'InputDescription',
                        parent=normal_style,
                        fontSize=10,
                        leading=12,
                        leftIndent=0,
                        spaceBefore=3,
                        spaceAfter=3
                    ))
                    inputs_data.append([input_para])
                
                inputs_table = Table(inputs_data, colWidths=[6.5*inch])
                inputs_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0fdf4'), colors.white]),
                ]))
                content.append(inputs_table)
                content.append(Spacer(1, 15))
            
            if db_process.outputs and len(db_process.outputs) > 0:
                content.append(Paragraph("Expected Outputs:", subheading_style))
                
                outputs_data = [['Output']]
                for output in db_process.outputs:
                    output_para = Paragraph(f"• {output}", ParagraphStyle(
                        'OutputDescription',
                        parent=normal_style,
                        fontSize=10,
                        leading=12,
                        leftIndent=0,
                        spaceBefore=3,
                        spaceAfter=3
                    ))
                    outputs_data.append([output_para])
                
                outputs_table = Table(outputs_data, colWidths=[6.5*inch])
                outputs_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0fdf4'), colors.white]),
                ]))
                content.append(outputs_table)
                content.append(Spacer(1, 20))
        
        # 6. Key Performance Indicators Section
        if db_process.kpis and len(db_process.kpis) > 0:
            content.append(Paragraph(f"{section_num}. Key Performance Indicators", heading_style))
            content.append(Spacer(1, 10))
            section_num += 1
            
            for i, kpi in enumerate(db_process.kpis, 1):
                content.append(Paragraph(f"{i}. {kpi}", normal_style))
            content.append(Spacer(1, 15))
        
        # 7. Roles & Responsibilities Section
        if db_process.roles_responsibilities and len(db_process.roles_responsibilities) > 0:
            content.append(Paragraph(f"{section_num}. Roles & Responsibilities", heading_style))
            content.append(Spacer(1, 10))
            section_num += 1
            
            for role in db_process.roles_responsibilities:
                content.append(Paragraph(f"• {role}", bullet_style))
            content.append(Spacer(1, 15))
        
        # 8. Exception Handling Section
        if db_process.exceptions_special_cases and len(db_process.exceptions_special_cases) > 0:
            content.append(Paragraph(f"{section_num}. Exception Handling", heading_style))
            content.append(Spacer(1, 10))
            
            for exception in db_process.exceptions_special_cases:
                content.append(Paragraph(f"• {exception}", bullet_style))
            content.append(Spacer(1, 15))
        
        # Footer with process info
        content.append(Spacer(1, 30))
        content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        content.append(Spacer(1, 10))
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        content.append(Paragraph(f"Generated by Knowledge Transfer Tool | Process ID: {process_id}", footer_style))
        
        # Build the PDF
        doc.build(content)
        
        # Clean up temporary files after PDF is built
        temp_files_to_cleanup = getattr(content, '_temp_files', [])
        for temp_file in temp_files_to_cleanup:
            try:
                os.unlink(temp_file)
                print(f"Cleaned up temporary file: {temp_file}")
            except Exception as cleanup_error:
                print(f"Could not clean up temporary file {temp_file}: {cleanup_error}")
        
        # Get the PDF content
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Return the PDF as a response
        filename = f"{title.replace(' ', '_').replace('/', '_')}_Process_Documentation.pdf"
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"Error generating enhanced PDF: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not generate PDF: {str(e)}")