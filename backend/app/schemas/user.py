from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import re


def validate_password_strength(password: str) -> str:
    """Validate password meets security requirements."""
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[@!_\-$#]', password):
        raise ValueError('Password must contain at least one special character (@, !, _, -, $, #)')
    return password


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "agent"


class UserCreate(UserBase):
    """Create user schema."""
    password: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    """Update user schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    agent_settings: Optional[Dict[str, Any]] = None
    password: Optional[str] = None  # For admin password reset

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != '':
            return validate_password_strength(v)
        return v


class UserResponse(UserBase):
    """User response schema."""
    id: UUID
    organization_id: UUID
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str]
    timezone: str
    language: str
    agent_settings: Dict[str, Any]
    total_cases_handled: Dict[str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list item response (lighter)."""
    id: UUID
    email: str
    first_name: str
    last_name: Optional[str]
    role: str
    is_active: bool
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class AgentStats(BaseModel):
    """Agent performance statistics."""
    total_cases: int
    open_cases: int
    resolved_cases: int
    total_calls: int
    total_call_duration: int
    successful_contacts: int
    promises_secured: int
    amount_collected: float
