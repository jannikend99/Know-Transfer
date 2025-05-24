from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProcessBase(BaseModel):
    title: Optional[str] = None
    general_description: Optional[str] = None
    process_steps: Optional[List[str]] = []
    scope_included: Optional[List[str]] = []
    scope_excluded: Optional[List[str]] = []
    inputs: Optional[List[str]] = []
    outputs: Optional[List[str]] = []
    kpis: Optional[List[str]] = []
    roles_responsibilities: Optional[List[str]] = []
    exceptions_special_cases: Optional[List[str]] = []
    visualization_graph: Optional[str] = None

class ProcessCreate(ProcessBase):
    general_description: str # Required for creation

class ProcessUpdate(ProcessBase):
    pass

class Process(ProcessBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Updated from orm_mode for Pydantic V2 