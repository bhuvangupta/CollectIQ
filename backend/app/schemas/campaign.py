from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class TargetCriteria(BaseModel):
    """Campaign target criteria."""
    buckets: List[str] = []
    loan_types: List[str] = []
    dpd_min: Optional[int] = None
    dpd_max: Optional[int] = None
    outstanding_min: Optional[Decimal] = None
    outstanding_max: Optional[Decimal] = None
    cities: List[str] = []
    states: List[str] = []
    tags: List[str] = []
    exclude_do_not_call: bool = True


class CampaignBase(BaseModel):
    """Base campaign schema."""
    name: str
    description: Optional[str] = None
    campaign_type: str


class CampaignCreate(CampaignBase):
    """Create campaign schema."""
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    allowed_start_time: str = "09:00"
    allowed_end_time: str = "18:00"
    allowed_days: List[str] = ["mon", "tue", "wed", "thu", "fri", "sat"]
    target_criteria: TargetCriteria = TargetCriteria()
    script_template: Optional[str] = None
    message_template: Optional[str] = None
    whatsapp_template_id: Optional[str] = None
    ai_enabled: bool = False
    ai_model: Optional[str] = None
    ai_voice: Optional[str] = None
    ai_language: str = "hi"
    max_attempts_per_borrower: int = 3
    retry_interval_minutes: int = 60
    concurrent_calls: int = 10
    priority: int = 5
    tags: List[str] = []
    # Provider settings
    telephony_provider: Optional[str] = None  # bolna, exotel, mock
    retry_delays_minutes: List[int] = [30, 120, 480]  # Retry delays after failures


class CampaignUpdate(BaseModel):
    """Update campaign schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    allowed_start_time: Optional[str] = None
    allowed_end_time: Optional[str] = None
    allowed_days: Optional[List[str]] = None
    target_criteria: Optional[TargetCriteria] = None
    script_template: Optional[str] = None
    message_template: Optional[str] = None
    max_attempts_per_borrower: Optional[int] = None
    concurrent_calls: Optional[int] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    telephony_provider: Optional[str] = None
    retry_delays_minutes: Optional[List[int]] = None


class CampaignResponse(CampaignBase):
    """Campaign response schema."""
    id: UUID
    organization_id: UUID
    status: str
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    allowed_start_time: str
    allowed_end_time: str
    allowed_days: List[str]
    target_criteria: Dict[str, Any]
    script_template: Optional[str]
    message_template: Optional[str]
    whatsapp_template_id: Optional[str]
    ai_enabled: bool
    ai_model: Optional[str]
    ai_voice: Optional[str]
    ai_language: str
    max_attempts_per_borrower: int
    retry_interval_minutes: int
    concurrent_calls: int
    telephony_provider: Optional[str]
    retry_delays_minutes: List[int]
    total_targets: int
    total_attempted: int
    total_contacted: int
    total_successful: int
    total_failed: int
    total_pending: int
    estimated_cost: Decimal
    actual_cost: Decimal
    results_summary: Dict[str, Any]
    created_by: Optional[UUID]
    priority: int
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Campaign list item response."""
    id: UUID
    name: str
    campaign_type: str
    status: str
    total_targets: int
    total_attempted: int
    total_successful: int
    scheduled_start: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignStatsResponse(BaseModel):
    """Campaign statistics."""
    completion_rate: float
    success_rate: float
    contact_rate: float
    promise_rate: float
    total_cost: Decimal
    cost_per_contact: Decimal
    by_outcome: Dict[str, int]
    by_hour: Dict[int, int]


class CampaignBorrowerResponse(BaseModel):
    """Campaign borrower response."""
    id: UUID
    campaign_id: UUID
    borrower_id: UUID
    loan_id: Optional[UUID]
    status: str
    attempt_count: int
    last_attempt_at: Optional[datetime]
    next_attempt_at: Optional[datetime]
    last_attempt_outcome: Optional[str]
    outcome: Optional[str]
    priority: int

    class Config:
        from_attributes = True


class CampaignLiveStatus(BaseModel):
    """Real-time campaign monitoring status."""
    calls_in_progress: int = 0
    calls_queued: int = 0
    retries_pending: int = 0
    calls_completed_1h: int = 0
    success_rate_1h: float = 0.0
    recent_outcomes: List[Dict[str, Any]] = []
    calls_per_minute: float = 0.0
    estimated_completion_time: Optional[datetime] = None


class AddBorrowersToCampaignRequest(BaseModel):
    """Request to add borrowers to campaign."""
    borrower_ids: Optional[List[UUID]] = None
    loan_ids: Optional[List[UUID]] = None
    use_criteria: bool = False  # Use campaign's target_criteria


class CampaignPreviewResponse(BaseModel):
    """Preview of campaign targets."""
    total_matches: int
    sample_borrowers: List[Dict[str, Any]]
    by_bucket: Dict[str, int]
    by_loan_type: Dict[str, int]
    estimated_cost: Decimal
