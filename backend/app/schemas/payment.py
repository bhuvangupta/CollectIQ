from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal


class PaymentCreate(BaseModel):
    """Create payment schema."""
    loan_id: UUID
    borrower_id: UUID
    case_id: Optional[UUID] = None
    amount: Decimal
    payment_date: date
    payment_mode: str = "cash"  # cash, cheque, neft, imps, upi, auto_debit, card
    transaction_reference: Optional[str] = None
    bank_name: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v

    @field_validator('payment_mode')
    @classmethod
    def validate_payment_mode(cls, v: str) -> str:
        valid_modes = ['cash', 'cheque', 'neft', 'imps', 'upi', 'auto_debit', 'card', 'other']
        if v.lower() not in valid_modes:
            raise ValueError(f'Payment mode must be one of: {", ".join(valid_modes)}')
        return v.lower()


class PaymentUpdate(BaseModel):
    """Update payment schema."""
    amount: Optional[Decimal] = None
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = None
    status: Optional[str] = None
    transaction_reference: Optional[str] = None
    bank_name: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    """Payment response schema."""
    id: UUID
    organization_id: UUID
    borrower_id: UUID
    loan_id: UUID
    amount: Decimal
    payment_date: date
    payment_mode: Optional[str]
    status: str
    transaction_reference: Optional[str]
    receipt_number: Optional[str]
    bank_name: Optional[str]
    source: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Payment list item response."""
    id: UUID
    borrower_id: UUID
    loan_id: UUID
    amount: Decimal
    payment_date: date
    payment_mode: Optional[str]
    status: str
    transaction_reference: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentWithDetails(PaymentResponse):
    """Payment with borrower/loan details."""
    borrower_name: Optional[str] = None
    loan_account_number: Optional[str] = None


# Promise to Pay schemas
class PromiseCreate(BaseModel):
    """Create promise to pay schema."""
    loan_id: UUID
    borrower_id: UUID
    case_id: Optional[UUID] = None
    promised_amount: Decimal
    promised_date: date
    notes: Optional[str] = None

    @field_validator('promised_amount')
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v


class PromiseResponse(BaseModel):
    """Promise response schema."""
    id: UUID
    borrower_id: UUID
    loan_id: UUID
    case_id: Optional[UUID]
    promised_amount: Decimal
    promised_date: date
    status: str
    fulfilled_amount: Optional[Decimal]
    fulfilled_date: Optional[date]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentStats(BaseModel):
    """Payment statistics."""
    total_collected: Decimal
    total_payments: int
    pending_promises: int
    fulfilled_promises: int
    broken_promises: int
