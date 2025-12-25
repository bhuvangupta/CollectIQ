from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class CaseBase(BaseModel):
    """Base case schema."""
    priority: int = 3
    case_type: str = "collection"


class CaseCreate(CaseBase):
    """Create case schema."""
    loan_id: UUID
    tags: List[str] = []


class CaseUpdate(BaseModel):
    """Update case schema."""
    status: Optional[str] = None
    priority: Optional[int] = None
    case_type: Optional[str] = None
    next_follow_up: Optional[datetime] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    notes_summary: Optional[str] = None


class CaseResponse(CaseBase):
    """Case response schema."""
    id: UUID
    organization_id: UUID
    loan_id: UUID
    case_number: str
    status: str
    resolution_type: Optional[str]
    resolution_date: Optional[datetime]
    resolution_notes: Optional[str]
    next_follow_up: Optional[datetime]
    follow_up_count: int
    total_attempts: int
    successful_contacts: int
    last_contact_date: Optional[datetime]
    last_contact_outcome: Optional[str]
    ai_handled: bool
    ai_attempts: int
    ai_summary: Optional[str]
    campaign_id: Optional[UUID]
    tags: List[str]
    notes_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    """Case list item response."""
    id: UUID
    case_number: str
    status: str
    priority: int
    case_type: str
    loan_id: UUID
    next_follow_up: Optional[datetime]
    last_contact_date: Optional[datetime]
    total_attempts: int
    tags: List[str]
    created_at: datetime
    # Additional fields for list display
    borrower_id: Optional[UUID] = None
    borrower_name: Optional[str] = None
    borrower_phone: Optional[str] = None
    total_outstanding: Optional[float] = None
    dpd: Optional[int] = None
    bucket: Optional[str] = None

    class Config:
        from_attributes = True


class CaseWithDetails(CaseResponse):
    """Case response with loan and borrower details."""
    borrower_id: UUID
    borrower_name: str
    borrower_phone: str
    borrower_preferred_language: str = "en"
    loan_account_number: Optional[str]
    total_outstanding: Optional[float]
    dpd: int
    bucket: Optional[str]
    assigned_agent_name: Optional[str]


class CaseAssignRequest(BaseModel):
    """Case assignment request."""
    agent_id: UUID


class CaseBulkAssignRequest(BaseModel):
    """Bulk case assignment request."""
    case_ids: List[UUID]
    agent_id: UUID


class CaseNoteCreate(BaseModel):
    """Create case note schema."""
    content: str
    note_type: str = "general"
    is_internal: bool = True
    attachments: List[str] = []


class CaseNoteResponse(BaseModel):
    """Case note response schema."""
    id: UUID
    case_id: UUID
    author_id: Optional[UUID] = None
    author_name: Optional[str] = None
    content: str
    note_type: str
    is_system: bool
    is_internal: bool
    attachments: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CaseStatsResponse(BaseModel):
    """Case statistics response."""
    total: int
    open: int
    in_progress: int
    promise_to_pay: int
    resolved: int
    escalated: int
    by_priority: Dict[int, int]
    by_bucket: Dict[str, int]
