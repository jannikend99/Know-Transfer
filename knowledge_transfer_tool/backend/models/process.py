import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID # Even if using SQLite, good for compatibility/future
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Process(Base):
    __tablename__ = "processes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String)
    general_description = Column(String)
    process_steps = Column(JSON)  # List[str]
    scope = Column(String)
    inputs = Column(JSON)  # List[str]
    outputs = Column(JSON)  # List[str]
    kpis = Column(JSON)  # List[str]
    roles_responsibilities = Column(JSON)  # List[str]
    exceptions_special_cases = Column(JSON)  # List[str]
    visualization_graph = Column(String)  # HTML code
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chat_messages = relationship("ChatMessage", back_populates="process")
    documents = relationship("Document", back_populates="process") 