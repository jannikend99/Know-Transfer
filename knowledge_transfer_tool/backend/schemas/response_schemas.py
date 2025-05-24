from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime # For timestamp
from .process import ProcessBase # For extracted_process_data

class FileUploadResponse(BaseModel):
    filename: str
    location: str
    content_type: Optional[str] = None
    message: str
    transcript: Optional[str] = None
    extracted_text_snippet: Optional[str] = None
    extracted_process_data: Optional[ProcessBase] = None # Reuse ProcessBase or a sub-model
    vector_store_status: Optional[str] = None
    ai_response: Optional[str] = None  # Add AI response text

class ChatResponse(BaseModel):
    user_message: str
    ai_chat_response: str
    extracted_process_data: Optional[ProcessBase] = None

class DocumentQueryResponse(BaseModel):
    user_query: str
    ai_response: str

# Schema for a single chat message for history
class ChatMessageResponse(BaseModel):
    id: UUID
    process_id: UUID
    sender_type: str # 'user' or 'ai' or 'system'
    content: str
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# You can add other generic or specific response schemas here 