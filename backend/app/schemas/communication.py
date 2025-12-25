from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class CommunicationBase(BaseModel):
    """Base communication schema."""
    channel: str
    direction: str


class CommunicationCreate(CommunicationBase):
    """Create communication schema."""
    borrower_id: UUID
    loan_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    message_content: Optional[str] = None
    template_id: Optional[str] = None


class CommunicationUpdate(BaseModel):
    """Update communication schema."""
    status: Optional[str] = None
    connected_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    outcome: Optional[str] = None
    disposition: Optional[str] = None
    sub_disposition: Optional[str] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[Decimal] = None


class CommunicationResponse(CommunicationBase):
    """Communication response schema."""
    id: UUID
    organization_id: UUID
    borrower_id: UUID
    loan_id: Optional[UUID]
    case_id: Optional[UUID]
    agent_id: Optional[UUID]
    from_number: Optional[str]
    to_number: Optional[str]
    status: str
    initiated_at: datetime
    connected_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: int
    call_sid: Optional[str]
    recording_url: Optional[str]
    message_content: Optional[str]
    template_id: Optional[str]
    is_ai_handled: bool
    outcome: Optional[str]
    disposition: Optional[str]
    sub_disposition: Optional[str]
    summary: Optional[str]
    notes: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[Decimal]
    cost: Decimal
    campaign_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class CommunicationListResponse(BaseModel):
    """Communication list item response."""
    id: UUID
    channel: str
    direction: str
    status: str
    borrower_id: Optional[UUID] = None
    borrower_name: Optional[str] = None
    case_id: Optional[UUID] = None
    case_number: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    initiated_at: datetime
    duration_seconds: Optional[int] = 0
    outcome: Optional[str] = None
    is_ai_handled: bool = False
    recording_url: Optional[str] = None
    ai_script: Optional[str] = None
    transcript: Optional[str] = None

    class Config:
        from_attributes = True


class InitiateCallRequest(BaseModel):
    """Request to initiate a call."""
    borrower_id: Optional[UUID] = None  # Can be derived from case_id
    loan_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    phone_number: Optional[str] = None  # If different from primary
    use_ai: bool = False
    script: Optional[str] = None  # AI call script for TTS
    language: str = "en"


class InitiateCallResponse(BaseModel):
    """Response from call initiation."""
    communication_id: UUID
    call_sid: str
    status: str


class SendSMSRequest(BaseModel):
    """Request to send SMS."""
    borrower_id: UUID
    loan_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    message: str
    phone_number: Optional[str] = None


class SendWhatsAppRequest(BaseModel):
    """Request to send WhatsApp message."""
    borrower_id: UUID
    loan_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    template_id: str
    template_params: Dict[str, str] = {}
    phone_number: Optional[str] = None


class CallRecordingResponse(BaseModel):
    """Call recording response."""
    id: UUID
    communication_id: UUID
    file_path: str
    duration_seconds: Optional[int]
    transcription_status: str
    transcription_text: Optional[str]
    ai_summary: Optional[str]
    key_points: List[str]
    compliance_flags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DispositionOption(BaseModel):
    """Disposition option for calls."""
    code: str
    label: str
    sub_dispositions: List[Dict[str, str]] = []


class CommunicationStatsResponse(BaseModel):
    """Communication statistics."""
    total_calls: int
    total_duration_minutes: int
    successful_contacts: int
    contact_rate: float
    avg_call_duration: float
    total_sms: int
    total_whatsapp: int
    by_outcome: Dict[str, int]
    by_channel: Dict[str, int]
