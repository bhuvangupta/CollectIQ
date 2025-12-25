from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from app.schemas.user import validate_password_strength


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class RegisterRequest(BaseModel):
    """User registration request (for organization admins)."""
    email: EmailStr
    password: str
    first_name: str
    last_name: Optional[str] = None
    organization_name: str
    organization_type: str = "agency"

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class CurrentUserResponse(BaseModel):
    """Current user response."""
    id: UUID
    email: str
    first_name: str
    last_name: Optional[str]
    role: str
    organization_id: UUID
    organization_name: str
    is_active: bool
    avatar_url: Optional[str]

    class Config:
        from_attributes = True
