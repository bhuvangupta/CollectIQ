from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class AuditLogResponse(BaseModel):
    """Audit log response schema."""
    id: UUID
    user_id: Optional[UUID]
    user_email: Optional[str]
    user_name: Optional[str]
    action: str
    category: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    entity_name: Optional[str]
    description: Optional[str]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    performed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list item response."""
    id: UUID
    user_name: Optional[str]
    user_email: Optional[str]
    action: str
    category: str
    entity_type: Optional[str]
    entity_name: Optional[str]
    description: Optional[str]
    performed_at: datetime

    class Config:
        from_attributes = True


class AuditLogFilters(BaseModel):
    """Audit log filter options."""
    user_id: Optional[UUID] = None
    action: Optional[str] = None
    category: Optional[str] = None
    entity_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
