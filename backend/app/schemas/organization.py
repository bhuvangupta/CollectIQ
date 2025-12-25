from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str
    org_type: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Create organization schema."""
    slug: str


class OrganizationUpdate(BaseModel):
    """Update organization schema."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""
    id: UUID
    slug: str
    is_active: bool
    logo_url: Optional[str]
    primary_color: str
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationStats(BaseModel):
    """Organization statistics."""
    total_users: int
    total_borrowers: int
    total_loans: int
    total_cases: int
    active_campaigns: int
    total_collected: float
