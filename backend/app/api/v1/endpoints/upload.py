"""Bulk upload endpoints for Borrowers, Loans, and Cases.

Supports:
- CSV file upload
- JSON bulk API
"""

import csv
import io
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.case import Case, CaseAssignment

router = APIRouter()


# =============================================================================
# Pydantic Models for Validation
# =============================================================================

class BorrowerUploadItem(BaseModel):
    """Single borrower for bulk upload."""
    external_id: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    primary_phone: str
    secondary_phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    pan: Optional[str] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    monthly_income: Optional[str] = None
    preferred_language: Optional[str] = "en"

    @validator('primary_phone')
    def validate_phone(cls, v):
        # Remove spaces and dashes
        phone = ''.join(c for c in v if c.isdigit() or c == '+')
        if len(phone) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return phone


class LoanUploadItem(BaseModel):
    """Single loan for bulk upload."""
    # Borrower reference (use one of these)
    borrower_external_id: Optional[str] = None
    borrower_phone: Optional[str] = None

    # Loan details
    external_loan_id: Optional[str] = None
    loan_account_number: str
    loan_type: str = "personal"
    product_name: Optional[str] = None
    principal_amount: float
    emi_amount: float
    interest_rate: Optional[float] = None
    tenure_months: Optional[int] = None
    disbursement_date: Optional[str] = None

    # Outstanding amounts
    total_outstanding: float
    overdue_amount: Optional[float] = 0
    dpd: Optional[int] = 0
    overdue_emis: Optional[int] = 0
    next_due_date: Optional[str] = None
    last_payment_date: Optional[str] = None


class CaseUploadItem(BaseModel):
    """Combined borrower + loan + case for bulk upload."""
    # Borrower fields
    borrower_external_id: Optional[str] = None
    borrower_first_name: str
    borrower_last_name: Optional[str] = None
    borrower_phone: str
    borrower_secondary_phone: Optional[str] = None
    borrower_email: Optional[str] = None
    borrower_address: Optional[str] = None
    borrower_city: Optional[str] = None
    borrower_state: Optional[str] = None
    borrower_pincode: Optional[str] = None

    # Loan fields
    loan_account_number: str
    loan_type: str = "personal"
    principal_amount: float
    emi_amount: float
    total_outstanding: float
    overdue_amount: Optional[float] = 0
    dpd: Optional[int] = 0
    overdue_emis: Optional[int] = 0
    next_due_date: Optional[str] = None

    # Case fields
    priority: Optional[int] = 3
    case_type: Optional[str] = "collection"
    assign_to_email: Optional[str] = None  # Agent email to assign

    @validator('borrower_phone')
    def validate_phone(cls, v):
        phone = ''.join(c for c in v if c.isdigit() or c == '+')
        if len(phone) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return phone


class BulkUploadRequest(BaseModel):
    """Request body for bulk uploads."""
    items: List[Dict[str, Any]]
    update_existing: bool = False  # If true, update existing records


class UploadResult(BaseModel):
    """Result of a bulk upload operation."""
    success: bool
    total_rows: int
    created: int
    updated: int
    failed: int
    errors: List[Dict[str, Any]] = []


# =============================================================================
# Helper Functions
# =============================================================================

def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string in various formats."""
    if not date_str:
        return None
    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(value: Any) -> Optional[Decimal]:
    """Parse numeric value to Decimal."""
    if value is None or value == '':
        return None
    try:
        # Handle comma-formatted numbers
        if isinstance(value, str):
            value = value.replace(',', '')
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_int(value: Any) -> Optional[int]:
    """Parse value to int."""
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def normalize_phone(phone: str) -> str:
    """Normalize phone number."""
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    if not phone.startswith('+'):
        if phone.startswith('91') and len(phone) == 12:
            phone = '+' + phone
        elif len(phone) == 10:
            phone = '+91' + phone
        else:
            phone = '+' + phone
    return phone


async def find_or_create_borrower(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: Dict[str, Any],
    update_existing: bool = False
) -> tuple[Borrower, bool]:
    """Find existing borrower or create new one.

    Returns: (borrower, is_new)
    """
    phone = normalize_phone(data.get('borrower_phone') or data.get('primary_phone', ''))
    external_id = data.get('borrower_external_id') or data.get('external_id')

    # Try to find by external_id first
    if external_id:
        result = await db.execute(
            select(Borrower).where(
                Borrower.organization_id == org_id,
                Borrower.external_id == external_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if update_existing:
                # Update fields
                for key in ['first_name', 'last_name', 'email', 'city', 'state', 'pincode']:
                    bkey = f'borrower_{key}' if f'borrower_{key}' in data else key
                    if data.get(bkey):
                        setattr(existing, key, data[bkey])
                if data.get('borrower_secondary_phone'):
                    existing.secondary_phone = normalize_phone(data['borrower_secondary_phone'])
            return existing, False

    # Try to find by phone
    result = await db.execute(
        select(Borrower).where(
            Borrower.organization_id == org_id,
            Borrower.primary_phone == phone
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if update_existing and external_id:
            existing.external_id = external_id
        return existing, False

    # Create new borrower
    borrower = Borrower(
        organization_id=org_id,
        external_id=external_id,
        first_name=data.get('borrower_first_name') or data.get('first_name', ''),
        last_name=data.get('borrower_last_name') or data.get('last_name'),
        primary_phone=phone,
        secondary_phone=normalize_phone(data.get('borrower_secondary_phone') or data.get('secondary_phone', '')) if data.get('borrower_secondary_phone') or data.get('secondary_phone') else None,
        email=data.get('borrower_email') or data.get('email'),
        address_line1=data.get('borrower_address') or data.get('address_line1'),
        city=data.get('borrower_city') or data.get('city'),
        state=data.get('borrower_state') or data.get('state'),
        pincode=data.get('borrower_pincode') or data.get('pincode'),
        preferred_language=data.get('preferred_language', 'en')
    )
    db.add(borrower)
    return borrower, True


async def find_or_create_loan(
    db: AsyncSession,
    org_id: uuid.UUID,
    borrower_id: uuid.UUID,
    data: Dict[str, Any],
    update_existing: bool = False
) -> tuple[Loan, bool]:
    """Find existing loan or create new one.

    Returns: (loan, is_new)
    """
    loan_account = data.get('loan_account_number', '')

    # Try to find existing loan
    result = await db.execute(
        select(Loan).where(
            Loan.organization_id == org_id,
            Loan.loan_account_number == loan_account
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if update_existing:
            # Update outstanding amounts
            existing.total_outstanding = parse_decimal(data.get('total_outstanding')) or existing.total_outstanding
            existing.overdue_amount = parse_decimal(data.get('overdue_amount')) or existing.overdue_amount
            existing.dpd = parse_int(data.get('dpd')) or existing.dpd
            existing.overdue_emis = parse_int(data.get('overdue_emis')) or existing.overdue_emis
            existing.next_due_date = parse_date(data.get('next_due_date')) or existing.next_due_date
            existing.update_bucket()
        return existing, False

    # Create new loan
    loan = Loan(
        organization_id=org_id,
        borrower_id=borrower_id,
        external_loan_id=data.get('external_loan_id'),
        loan_account_number=loan_account,
        loan_type=data.get('loan_type', 'personal'),
        product_name=data.get('product_name'),
        principal_amount=parse_decimal(data.get('principal_amount')) or Decimal('0'),
        emi_amount=parse_decimal(data.get('emi_amount')) or Decimal('0'),
        interest_rate=parse_decimal(data.get('interest_rate')),
        tenure_months=parse_int(data.get('tenure_months')),
        disbursement_date=parse_date(data.get('disbursement_date')),
        total_outstanding=parse_decimal(data.get('total_outstanding')) or Decimal('0'),
        overdue_amount=parse_decimal(data.get('overdue_amount')) or Decimal('0'),
        dpd=parse_int(data.get('dpd')) or 0,
        overdue_emis=parse_int(data.get('overdue_emis')) or 0,
        next_due_date=parse_date(data.get('next_due_date')),
        last_payment_date=parse_date(data.get('last_payment_date')),
        status='active'
    )
    loan.update_bucket()
    db.add(loan)
    return loan, True


async def create_case_for_loan(
    db: AsyncSession,
    org_id: uuid.UUID,
    loan_id: uuid.UUID,
    data: Dict[str, Any],
    agent_id: Optional[uuid.UUID] = None,
    assigned_by: Optional[uuid.UUID] = None
) -> Case:
    """Create a case for a loan."""
    # Generate case number
    import random
    case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    case = Case(
        organization_id=org_id,
        loan_id=loan_id,
        case_number=case_number,
        status='open',
        priority=parse_int(data.get('priority')) or 3,
        case_type=data.get('case_type', 'collection')
    )
    db.add(case)
    await db.flush()  # Get case ID

    # Create assignment if agent specified
    if agent_id:
        assignment = CaseAssignment(
            case_id=case.id,
            agent_id=agent_id,
            assigned_by=assigned_by,
            is_active=True
        )
        db.add(assignment)

    return case


# =============================================================================
# CSV Upload Endpoints
# =============================================================================

@router.post("/borrowers/upload", response_model=UploadResult)
async def upload_borrowers_csv(
    file: UploadFile = File(...),
    update_existing: bool = Query(False, description="Update existing records if found"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload borrowers via CSV file.

    CSV columns:
    - external_id (optional): Your internal customer ID
    - first_name (required): First name
    - last_name (optional): Last name
    - primary_phone (required): Primary phone number
    - secondary_phone (optional): Secondary phone
    - email (optional): Email address
    - date_of_birth (optional): Date of birth (YYYY-MM-DD)
    - gender (optional): Gender
    - address_line1, address_line2, city, state, pincode (optional)
    - pan (optional): PAN number
    - employment_type, employer_name, monthly_income (optional)
    - preferred_language (optional): en, hi, hinglish
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    org_id = current_user.organization_id
    content = await file.read()

    try:
        decoded = content.decode('utf-8')
    except UnicodeDecodeError:
        decoded = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))

    created = 0
    updated = 0
    failed = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            # Validate required fields
            if not row.get('first_name'):
                raise ValueError("first_name is required")
            if not row.get('primary_phone'):
                raise ValueError("primary_phone is required")

            borrower, is_new = await find_or_create_borrower(db, org_id, row, update_existing)

            if is_new:
                created += 1
            elif update_existing:
                updated += 1

        except Exception as e:
            failed += 1
            errors.append({
                "row": row_num,
                "data": dict(row),
                "error": str(e)
            })

    if created > 0 or updated > 0:
        await db.commit()

    return UploadResult(
        success=failed == 0,
        total_rows=created + updated + failed,
        created=created,
        updated=updated,
        failed=failed,
        errors=errors[:50]  # Limit errors returned
    )


@router.post("/cases/upload", response_model=UploadResult)
async def upload_cases_csv(
    file: UploadFile = File(...),
    update_existing: bool = Query(False, description="Update existing loans if found"),
    create_cases: bool = Query(True, description="Create cases for new loans"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload cases via CSV file (includes borrower and loan data).

    CSV columns:
    Borrower:
    - borrower_external_id (optional): Your internal customer ID
    - borrower_first_name (required): First name
    - borrower_last_name (optional): Last name
    - borrower_phone (required): Primary phone
    - borrower_secondary_phone, borrower_email (optional)
    - borrower_address, borrower_city, borrower_state, borrower_pincode (optional)

    Loan:
    - loan_account_number (required): Loan account number
    - loan_type (optional): personal, home, auto, business, credit_card
    - principal_amount (required): Original loan amount
    - emi_amount (required): Monthly EMI amount
    - total_outstanding (required): Current outstanding amount
    - overdue_amount (optional): Overdue amount
    - dpd (optional): Days past due
    - overdue_emis (optional): Number of overdue EMIs
    - next_due_date (optional): Next EMI due date

    Case:
    - priority (optional): 1-5, default 3
    - case_type (optional): collection, settlement, legal
    - assign_to_email (optional): Agent email to assign case to
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    org_id = current_user.organization_id
    content = await file.read()

    try:
        decoded = content.decode('utf-8')
    except UnicodeDecodeError:
        decoded = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))

    created = 0
    updated = 0
    failed = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            # Validate required fields
            if not row.get('borrower_first_name'):
                raise ValueError("borrower_first_name is required")
            if not row.get('borrower_phone'):
                raise ValueError("borrower_phone is required")
            if not row.get('loan_account_number'):
                raise ValueError("loan_account_number is required")
            if not row.get('principal_amount'):
                raise ValueError("principal_amount is required")
            if not row.get('emi_amount'):
                raise ValueError("emi_amount is required")
            if not row.get('total_outstanding'):
                raise ValueError("total_outstanding is required")

            # Create/update borrower
            borrower, borrower_is_new = await find_or_create_borrower(db, org_id, row, update_existing)
            await db.flush()

            # Create/update loan
            loan, loan_is_new = await find_or_create_loan(db, org_id, borrower.id, row, update_existing)
            await db.flush()

            # Create case if new loan and create_cases is True
            if loan_is_new and create_cases:
                # Find agent if specified
                agent_id = None
                if row.get('assign_to_email'):
                    agent_result = await db.execute(
                        select(User).where(
                            User.organization_id == org_id,
                            User.email == row['assign_to_email']
                        )
                    )
                    agent = agent_result.scalar_one_or_none()
                    if agent:
                        agent_id = agent.id

                await create_case_for_loan(
                    db, org_id, loan.id, row,
                    agent_id=agent_id,
                    assigned_by=current_user.id
                )
                created += 1
            elif not loan_is_new and update_existing:
                updated += 1
            elif loan_is_new:
                created += 1

        except Exception as e:
            failed += 1
            errors.append({
                "row": row_num,
                "loan_account": row.get('loan_account_number', 'N/A'),
                "error": str(e)
            })

    if created > 0 or updated > 0:
        await db.commit()

    return UploadResult(
        success=failed == 0,
        total_rows=created + updated + failed,
        created=created,
        updated=updated,
        failed=failed,
        errors=errors[:50]
    )


# =============================================================================
# JSON Bulk API Endpoints
# =============================================================================

@router.post("/borrowers/bulk", response_model=UploadResult)
async def bulk_create_borrowers(
    request: BulkUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create/update borrowers via JSON API.

    Request body:
    ```json
    {
        "items": [
            {
                "external_id": "CUST001",
                "first_name": "John",
                "last_name": "Doe",
                "primary_phone": "9876543210",
                "email": "john@example.com"
            }
        ],
        "update_existing": false
    }
    ```
    """
    org_id = current_user.organization_id

    created = 0
    updated = 0
    failed = 0
    errors = []

    for idx, item in enumerate(request.items):
        try:
            # Validate
            validated = BorrowerUploadItem(**item)

            borrower, is_new = await find_or_create_borrower(
                db, org_id, item, request.update_existing
            )

            if is_new:
                created += 1
            elif request.update_existing:
                updated += 1

        except Exception as e:
            failed += 1
            errors.append({
                "index": idx,
                "data": item,
                "error": str(e)
            })

    if created > 0 or updated > 0:
        await db.commit()

    return UploadResult(
        success=failed == 0,
        total_rows=len(request.items),
        created=created,
        updated=updated,
        failed=failed,
        errors=errors[:50]
    )


@router.post("/cases/bulk", response_model=UploadResult)
async def bulk_create_cases(
    request: BulkUploadRequest,
    create_cases: bool = Query(True, description="Create cases for new loans"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create cases (with borrowers and loans) via JSON API.

    Request body:
    ```json
    {
        "items": [
            {
                "borrower_first_name": "John",
                "borrower_last_name": "Doe",
                "borrower_phone": "9876543210",
                "loan_account_number": "LN001",
                "loan_type": "personal",
                "principal_amount": 100000,
                "emi_amount": 5000,
                "total_outstanding": 75000,
                "overdue_amount": 15000,
                "dpd": 45,
                "priority": 4
            }
        ],
        "update_existing": false
    }
    ```
    """
    org_id = current_user.organization_id

    created = 0
    updated = 0
    failed = 0
    errors = []

    for idx, item in enumerate(request.items):
        try:
            # Validate
            validated = CaseUploadItem(**item)

            # Create/update borrower
            borrower, _ = await find_or_create_borrower(db, org_id, item, request.update_existing)
            await db.flush()

            # Create/update loan
            loan, loan_is_new = await find_or_create_loan(
                db, org_id, borrower.id, item, request.update_existing
            )
            await db.flush()

            # Create case if new loan
            if loan_is_new and create_cases:
                agent_id = None
                if item.get('assign_to_email'):
                    agent_result = await db.execute(
                        select(User).where(
                            User.organization_id == org_id,
                            User.email == item['assign_to_email']
                        )
                    )
                    agent = agent_result.scalar_one_or_none()
                    if agent:
                        agent_id = agent.id

                await create_case_for_loan(
                    db, org_id, loan.id, item,
                    agent_id=agent_id,
                    assigned_by=current_user.id
                )
                created += 1
            elif not loan_is_new and request.update_existing:
                updated += 1
            elif loan_is_new:
                created += 1

        except Exception as e:
            failed += 1
            errors.append({
                "index": idx,
                "loan_account": item.get('loan_account_number', 'N/A'),
                "error": str(e)
            })

    if created > 0 or updated > 0:
        await db.commit()

    return UploadResult(
        success=failed == 0,
        total_rows=len(request.items),
        created=created,
        updated=updated,
        failed=failed,
        errors=errors[:50]
    )


# =============================================================================
# Template Download Endpoints
# =============================================================================

@router.get("/borrowers/template")
async def download_borrowers_template():
    """Download CSV template for borrower upload."""
    headers = [
        "external_id", "first_name", "last_name", "primary_phone", "secondary_phone",
        "email", "date_of_birth", "gender", "address_line1", "address_line2",
        "city", "state", "pincode", "pan", "employment_type", "employer_name",
        "monthly_income", "preferred_language"
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    # Sample row
    writer.writerow([
        "CUST001", "John", "Doe", "9876543210", "9876543211",
        "john@example.com", "1990-01-15", "male", "123 Main St", "Apt 4",
        "Mumbai", "Maharashtra", "400001", "ABCDE1234F", "salaried", "ABC Corp",
        "50000", "en"
    ])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=borrowers_template.csv"}
    )


@router.get("/cases/template")
async def download_cases_template():
    """Download CSV template for case upload (borrower + loan + case)."""
    headers = [
        # Borrower fields
        "borrower_external_id", "borrower_first_name", "borrower_last_name",
        "borrower_phone", "borrower_secondary_phone", "borrower_email",
        "borrower_address", "borrower_city", "borrower_state", "borrower_pincode",
        # Loan fields
        "loan_account_number", "loan_type", "principal_amount", "emi_amount",
        "total_outstanding", "overdue_amount", "dpd", "overdue_emis", "next_due_date",
        # Case fields
        "priority", "case_type", "assign_to_email"
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    # Sample row
    writer.writerow([
        "CUST001", "Rahul", "Sharma", "9876543210", "9876543211", "rahul@example.com",
        "456 Park Avenue", "Delhi", "Delhi", "110001",
        "LN2024001", "personal", "500000", "15000",
        "350000", "45000", "45", "3", "2024-02-15",
        "4", "collection", "agent@company.com"
    ])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cases_template.csv"}
    )
