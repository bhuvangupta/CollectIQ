from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_agent_case_ids
from app.models.user import User
from app.models.payment import Payment, PaymentPromise
from app.models.loan import Loan
from app.models.borrower import Borrower
from app.models.case import Case
from app.models.audit_log import AuditLog
from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentListResponse,
    PaymentWithDetails,
    PromiseCreate,
    PromiseResponse,
    PaymentStats,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


def generate_receipt_number(org_id: str) -> str:
    """Generate a unique receipt number."""
    import random
    import string
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"RCP-{timestamp}-{random_suffix}"


@router.get("", response_model=PaginatedResponse[PaymentListResponse])
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    borrower_id: Optional[UUID] = None,
    loan_id: Optional[UUID] = None,
    case_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    payment_mode: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List payments. Agents only see payments for their assigned cases."""
    query = select(Payment).where(
        Payment.organization_id == current_user.organization_id
    )

    # Agent role: filter to only payments from assigned cases
    agent_case_ids = await get_agent_case_ids(current_user, db)
    if agent_case_ids is not None:
        if not agent_case_ids:
            return PaginatedResponse(
                items=[], total=0, page=page, page_size=page_size, total_pages=0
            )
        # Get loan IDs from assigned cases
        loan_result = await db.execute(
            select(Case.loan_id).where(Case.id.in_(agent_case_ids))
        )
        agent_loan_ids = [row[0] for row in loan_result.all()]
        if agent_loan_ids:
            query = query.where(Payment.loan_id.in_(agent_loan_ids))
        else:
            return PaginatedResponse(
                items=[], total=0, page=page, page_size=page_size, total_pages=0
            )

    if borrower_id:
        query = query.where(Payment.borrower_id == borrower_id)
    if loan_id:
        query = query.where(Payment.loan_id == loan_id)
    if status_filter:
        query = query.where(Payment.status == status_filter)
    if payment_mode:
        query = query.where(Payment.payment_mode == payment_mode)
    if date_from:
        query = query.where(Payment.payment_date >= date_from)
    if date_to:
        query = query.where(Payment.payment_date <= date_to)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.order_by(Payment.payment_date.desc(), Payment.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    payments = result.scalars().all()

    return PaginatedResponse(
        items=[PaymentListResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payment_data: PaymentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record a new payment."""
    # Verify loan exists and belongs to org
    loan_result = await db.execute(
        select(Loan).where(
            Loan.id == payment_data.loan_id,
            Loan.organization_id == current_user.organization_id
        )
    )
    loan = loan_result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    # Verify borrower
    borrower_result = await db.execute(
        select(Borrower).where(
            Borrower.id == payment_data.borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    borrower = borrower_result.scalar_one_or_none()
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")

    # Agent role: verify they have access to this case
    agent_case_ids = await get_agent_case_ids(current_user, db)
    if agent_case_ids is not None:
        # Check if agent is assigned to a case for this loan
        case_result = await db.execute(
            select(Case.id).where(
                Case.loan_id == payment_data.loan_id,
                Case.id.in_(agent_case_ids)
            )
        )
        if not case_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this case"
            )

    # Create payment
    payment = Payment(
        organization_id=current_user.organization_id,
        borrower_id=payment_data.borrower_id,
        loan_id=payment_data.loan_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date,
        payment_mode=payment_data.payment_mode,
        transaction_reference=payment_data.transaction_reference,
        bank_name=payment_data.bank_name,
        notes=payment_data.notes,
        source="manual",
        status="confirmed",
        receipt_number=generate_receipt_number(str(current_user.organization_id))
    )
    db.add(payment)

    # Update loan outstanding (reduce by payment amount)
    if loan.total_outstanding:
        loan.total_outstanding = max(0, float(loan.total_outstanding) - float(payment_data.amount))
    if loan.overdue_amount:
        loan.overdue_amount = max(0, float(loan.overdue_amount) - float(payment_data.amount))

    # Check if there are any pending promises for this loan that should be fulfilled
    promise_result = await db.execute(
        select(PaymentPromise).where(
            PaymentPromise.loan_id == payment_data.loan_id,
            PaymentPromise.status == "pending",
            PaymentPromise.promised_date >= payment_data.payment_date - timedelta(days=7),
            PaymentPromise.promised_date <= payment_data.payment_date + timedelta(days=3)
        ).order_by(PaymentPromise.promised_date)
    )
    pending_promise = promise_result.scalar()
    if pending_promise:
        pending_promise.fulfilled_amount = (pending_promise.fulfilled_amount or 0) + float(payment_data.amount)
        pending_promise.fulfilled_date = payment_data.payment_date
        if pending_promise.fulfilled_amount >= float(pending_promise.promised_amount):
            pending_promise.status = "fulfilled"
        else:
            pending_promise.status = "partial"
        payment.promise_id = pending_promise.id

    # Create audit log
    audit_log = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name,
        action="payment_recorded",
        category="payment",
        entity_type="payment",
        entity_name=f"₹{payment_data.amount} from {borrower.first_name}",
        description=f"Recorded payment of ₹{payment_data.amount} via {payment_data.payment_mode}",
        new_value={
            "amount": str(payment_data.amount),
            "payment_mode": payment_data.payment_mode,
            "payment_date": str(payment_data.payment_date),
            "loan_id": str(payment_data.loan_id)
        },
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(payment)

    return payment


@router.get("/stats", response_model=PaymentStats)
async def get_payment_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment statistics."""
    org_id = current_user.organization_id

    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # Agent filtering
    agent_case_ids = await get_agent_case_ids(current_user, db)
    agent_loan_ids = None
    if agent_case_ids is not None:
        if not agent_case_ids:
            return PaymentStats(
                total_collected=Decimal(0),
                total_payments=0,
                pending_promises=0,
                fulfilled_promises=0,
                broken_promises=0
            )
        loan_result = await db.execute(
            select(Case.loan_id).where(Case.id.in_(agent_case_ids))
        )
        agent_loan_ids = [row[0] for row in loan_result.all()]

    # Total collected
    payment_query = select(func.sum(Payment.amount), func.count(Payment.id)).where(
        Payment.organization_id == org_id,
        Payment.status == "confirmed",
        Payment.payment_date >= date_from,
        Payment.payment_date <= date_to
    )
    if agent_loan_ids is not None:
        payment_query = payment_query.where(Payment.loan_id.in_(agent_loan_ids))

    result = await db.execute(payment_query)
    row = result.one()
    total_collected = row[0] or Decimal(0)
    total_payments = row[1] or 0

    # Promise stats
    promise_base = select(PaymentPromise).where(
        PaymentPromise.organization_id == org_id
    )
    if agent_loan_ids is not None:
        promise_base = promise_base.where(PaymentPromise.loan_id.in_(agent_loan_ids))

    pending_promises = await db.scalar(
        select(func.count()).select_from(
            promise_base.where(PaymentPromise.status == "pending").subquery()
        )
    ) or 0

    fulfilled_promises = await db.scalar(
        select(func.count()).select_from(
            promise_base.where(PaymentPromise.status == "fulfilled").subquery()
        )
    ) or 0

    broken_promises = await db.scalar(
        select(func.count()).select_from(
            promise_base.where(PaymentPromise.status == "broken").subquery()
        )
    ) or 0

    return PaymentStats(
        total_collected=total_collected,
        total_payments=total_payments,
        pending_promises=pending_promises,
        fulfilled_promises=fulfilled_promises,
        broken_promises=broken_promises
    )


@router.get("/{payment_id}", response_model=PaymentWithDetails)
async def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific payment."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.organization_id == current_user.organization_id
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Get borrower and loan details
    borrower_result = await db.execute(select(Borrower).where(Borrower.id == payment.borrower_id))
    borrower = borrower_result.scalar_one_or_none()

    loan_result = await db.execute(select(Loan).where(Loan.id == payment.loan_id))
    loan = loan_result.scalar_one_or_none()

    payment_dict = PaymentResponse.model_validate(payment).model_dump()
    payment_dict['borrower_name'] = f"{borrower.first_name} {borrower.last_name or ''}" if borrower else None
    payment_dict['loan_account_number'] = loan.loan_account_number if loan else None

    return PaymentWithDetails(**payment_dict)


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: UUID,
    payment_data: PaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a payment (managers only can change status)."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.organization_id == current_user.organization_id
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Only managers can reverse payments
    if payment_data.status and payment_data.status != payment.status:
        if current_user.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers can change payment status"
            )

    update_dict = payment_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment)

    return payment


# ==================== Promise to Pay Endpoints ====================

@router.get("/promises", response_model=PaginatedResponse[PromiseResponse])
async def list_promises(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    borrower_id: Optional[UUID] = None,
    loan_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List payment promises."""
    query = select(PaymentPromise).where(
        PaymentPromise.organization_id == current_user.organization_id
    )

    if borrower_id:
        query = query.where(PaymentPromise.borrower_id == borrower_id)
    if loan_id:
        query = query.where(PaymentPromise.loan_id == loan_id)
    if status_filter:
        query = query.where(PaymentPromise.status == status_filter)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.order_by(PaymentPromise.promised_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    promises = result.scalars().all()

    return PaginatedResponse(
        items=[PromiseResponse.model_validate(p) for p in promises],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/promises", response_model=PromiseResponse, status_code=status.HTTP_201_CREATED)
async def record_promise(
    promise_data: PromiseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Record a promise to pay."""
    # Verify loan exists
    loan_result = await db.execute(
        select(Loan).where(
            Loan.id == promise_data.loan_id,
            Loan.organization_id == current_user.organization_id
        )
    )
    if not loan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Loan not found")

    promise = PaymentPromise(
        organization_id=current_user.organization_id,
        borrower_id=promise_data.borrower_id,
        loan_id=promise_data.loan_id,
        case_id=promise_data.case_id,
        promised_amount=promise_data.promised_amount,
        promised_date=promise_data.promised_date,
        notes=promise_data.notes,
        source="agent",
        recorded_by=current_user.id,
        status="pending"
    )
    db.add(promise)

    # Update case status to promise_to_pay if case_id provided
    if promise_data.case_id:
        case_result = await db.execute(
            select(Case).where(Case.id == promise_data.case_id)
        )
        case = case_result.scalar_one_or_none()
        if case:
            case.status = "promise_to_pay"

    await db.commit()
    await db.refresh(promise)

    return promise
