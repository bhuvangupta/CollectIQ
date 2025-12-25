from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date


class ReferenceContact(BaseModel):
    """Reference contact schema."""
    name: str
    phone: str
    relationship: str


class BorrowerBase(BaseModel):
    """Base borrower schema."""
    external_id: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    primary_phone: str
    secondary_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    alternate_phones: List[str] = []
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class BorrowerCreate(BorrowerBase):
    """Create borrower schema."""
    pan: Optional[str] = None
    aadhaar_last4: Optional[str] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    monthly_income: Optional[str] = None
    occupation: Optional[str] = None
    references: List[ReferenceContact] = []
    preferred_language: str = "hi"
    preferred_contact_time: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None


class BorrowerUpdate(BaseModel):
    """Update borrower schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    primary_phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    alternate_phones: Optional[List[str]] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    monthly_income: Optional[str] = None
    references: Optional[List[ReferenceContact]] = None
    preferred_language: Optional[str] = None
    preferred_contact_time: Optional[str] = None
    do_not_call: Optional[bool] = None
    do_not_sms: Optional[bool] = None
    do_not_whatsapp: Optional[bool] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class BorrowerResponse(BorrowerBase):
    """Borrower response schema."""
    id: UUID
    organization_id: UUID
    pan: Optional[str]
    aadhaar_last4: Optional[str]
    employment_type: Optional[str]
    employer_name: Optional[str]
    monthly_income: Optional[str]
    occupation: Optional[str]
    references: List[ReferenceContact]
    preferred_language: str
    preferred_contact_time: Optional[str]
    do_not_call: bool
    do_not_sms: bool
    do_not_whatsapp: bool
    reachability_score: Dict[str, Any]
    tags: List[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BorrowerListResponse(BaseModel):
    """Borrower list item response (lighter)."""
    id: UUID
    external_id: Optional[str]
    first_name: str
    last_name: Optional[str]
    primary_phone: str
    city: Optional[str]
    state: Optional[str]
    tags: List[str]
    is_active: bool

    class Config:
        from_attributes = True


class BorrowerImportRow(BaseModel):
    """Single row for borrower import."""
    external_id: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    primary_phone: str
    secondary_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    pan: Optional[str] = None


class BorrowerImportResponse(BaseModel):
    """Borrower import response."""
    total: int
    imported: int
    updated: int
    failed: int
    errors: List[Dict[str, Any]]
