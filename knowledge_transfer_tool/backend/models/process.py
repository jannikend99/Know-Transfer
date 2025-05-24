import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Process(Base):
    __tablename__ = "processes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    general_description = Column(String)
    process_steps = Column(JSON)  # List[str]
    scope_included = Column(JSON)  # List[str]
    scope_excluded = Column(JSON)  # List[str]
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