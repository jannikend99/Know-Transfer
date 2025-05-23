import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey("processes.id"), nullable=False)
    
    sender_type = Column(String, nullable=False)  # e.g., 'user', 'ai', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True) # Renamed from metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    process = relationship("Process", back_populates="chat_messages") 