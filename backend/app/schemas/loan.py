from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class CoApplicant(BaseModel):
    """Co-applicant schema."""
    name: str
    phone: str
    relationship: str


class LoanBase(BaseModel):
    """Base loan schema."""
    external_loan_id: Optional[str] = None
    loan_account_number: Optional[str] = None
    loan_type: str
    product_name: Optional[str] = None
    principal_amount: Decimal
    emi_amount: Decimal


class LoanCreate(LoanBase):
    """Create loan schema."""
    borrower_id: UUID
    disbursed_amount: Optional[Decimal] = None
    disbursement_date: Optional[date] = None
    interest_rate: Optional[Decimal] = None
    interest_type: str = "fixed"
    tenure_months: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    emi_day: Optional[int] = None
    total_emis: Optional[int] = None
    outstanding_principal: Optional[Decimal] = None
    outstanding_interest: Optional[Decimal] = None
    outstanding_charges: Decimal = Decimal("0")
    total_outstanding: Optional[Decimal] = None
    overdue_amount: Decimal = Decimal("0")
    overdue_emis: int = 0
    dpd: int = 0
    next_due_date: Optional[date] = None
    is_secured: bool = False
    collateral_type: Optional[str] = None
    collateral_value: Optional[Decimal] = None
    co_applicants: List[CoApplicant] = []
    lender_data: Dict[str, Any] = {}
    notes: Optional[str] = None


class LoanUpdate(BaseModel):
    """Update loan schema."""
    status: Optional[str] = None
    outstanding_principal: Optional[Decimal] = None
    outstanding_interest: Optional[Decimal] = None
    outstanding_charges: Optional[Decimal] = None
    total_outstanding: Optional[Decimal] = None
    overdue_amount: Optional[Decimal] = None
    overdue_emis: Optional[int] = None
    dpd: Optional[int] = None
    emis_paid: Optional[int] = None
    last_payment_date: Optional[date] = None
    next_due_date: Optional[date] = None
    collection_status: Optional[str] = None
    notes: Optional[str] = None
    lender_data: Optional[Dict[str, Any]] = None


class LoanResponse(LoanBase):
    """Loan response schema."""
    id: UUID
    organization_id: UUID
    borrower_id: UUID
    disbursed_amount: Optional[Decimal]
    disbursement_date: Optional[date]
    interest_rate: Optional[Decimal]
    interest_type: str
    tenure_months: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    emi_day: Optional[int]
    total_emis: Optional[int]
    emis_paid: int
    status: str
    outstanding_principal: Optional[Decimal]
    outstanding_interest: Optional[Decimal]
    outstanding_charges: Decimal
    total_outstanding: Optional[Decimal]
    overdue_amount: Decimal
    overdue_emis: int
    dpd: int
    last_payment_date: Optional[date]
    next_due_date: Optional[date]
    bucket: Optional[str]
    collection_status: str
    is_secured: bool
    collateral_type: Optional[str]
    collateral_value: Optional[Decimal]
    co_applicants: List[CoApplicant]
    risk_score: Dict[str, Any]
    payment_propensity: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoanListResponse(BaseModel):
    """Loan list item response (lighter)."""
    id: UUID
    external_loan_id: Optional[str]
    loan_account_number: Optional[str]
    loan_type: str
    principal_amount: Decimal
    emi_amount: Decimal
    total_outstanding: Optional[Decimal]
    dpd: int
    bucket: Optional[str]
    status: str
    collection_status: str
    borrower_id: UUID

    class Config:
        from_attributes = True


class LoanWithBorrower(LoanResponse):
    """Loan response with borrower details."""
    borrower_name: str
    borrower_phone: str


class LoanImportRow(BaseModel):
    """Single row for loan import."""
    external_loan_id: str
    borrower_external_id: str
    loan_type: str
    principal_amount: Decimal
    emi_amount: Decimal
    disbursement_date: Optional[date] = None
    tenure_months: Optional[int] = None
    interest_rate: Optional[Decimal] = None
    outstanding_principal: Optional[Decimal] = None
    outstanding_interest: Optional[Decimal] = None
    overdue_amount: Optional[Decimal] = None
    dpd: int = 0
    next_due_date: Optional[date] = None


class LoanImportResponse(BaseModel):
    """Loan import response."""
    total: int
    imported: int
    updated: int
    failed: int
    errors: List[Dict[str, Any]]
