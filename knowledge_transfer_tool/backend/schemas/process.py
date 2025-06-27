from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProcessBase(BaseModel):
    title: Optional[str] = None
    general_description: Optional[str] = Field(
        None, 
        description="Overview: max 3 sentences describing what this process accomplishes and its main purpose"
    )
    process_steps: Optional[List[str]] = Field(
        [], 
        description="Detailed process steps: max 15 steps, each describing a specific action or decision point"
    )
    scope_included: Optional[List[str]] = Field(
        [], 
        description="Scope included: max 10 items describing what is covered within this process boundaries"
    )
    scope_excluded: Optional[List[str]] = Field(
        [], 
        description="Scope excluded: max 10 items describing what is explicitly not covered by this process"
    )
    inputs: Optional[List[str]] = Field(
        [], 
        description="Required inputs: max 10 items, each describing materials, information, or resources needed to start the process"
    )
    outputs: Optional[List[str]] = Field(
        [], 
        description="Expected outputs: max 10 items, each describing deliverables, results, or outcomes produced by the process"
    )
    kpis: Optional[List[str]] = Field(
        [], 
        description="Key Performance Indicators: max 8 metrics, each with name, description, and target value"
    )
    roles_responsibilities: Optional[List[str]] = Field(
        [], 
        description="Roles and responsibilities: max 12 items, each describing who does what specific task or has what authority"
    )
    exceptions_special_cases: Optional[List[str]] = Field(
        [], 
        description="Exceptions and special cases: max 10 items, each describing error scenarios, alternative paths, or special handling situations"
    )
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