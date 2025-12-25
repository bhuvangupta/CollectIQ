from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_manager
from app.models.user import User
from app.models.loan import Loan
from app.models.borrower import Borrower
from app.schemas.loan import (
    LoanCreate,
    LoanUpdate,
    LoanResponse,
    LoanListResponse,
    LoanWithBorrower,
    LoanImportResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LoanListResponse])
async def list_loans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    borrower_id: Optional[UUID] = None,
    loan_type: Optional[str] = None,
    status: Optional[str] = None,
    bucket: Optional[str] = None,
    collection_status: Optional[str] = None,
    dpd_min: Optional[int] = None,
    dpd_max: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List loans in the organization."""
    query = select(Loan).where(
        Loan.organization_id == current_user.organization_id
    )

    if borrower_id:
        query = query.where(Loan.borrower_id == borrower_id)
    if loan_type:
        query = query.where(Loan.loan_type == loan_type)
    if status:
        query = query.where(Loan.status == status)
    if bucket:
        query = query.where(Loan.bucket == bucket)
    if collection_status:
        query = query.where(Loan.collection_status == collection_status)
    if dpd_min is not None:
        query = query.where(Loan.dpd >= dpd_min)
    if dpd_max is not None:
        query = query.where(Loan.dpd <= dpd_max)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Loan.external_loan_id.ilike(search_filter),
                Loan.loan_account_number.ilike(search_filter)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Loan.dpd.desc(), Loan.created_at.desc())

    result = await db.execute(query)
    loans = result.scalars().all()

    return PaginatedResponse(
        items=[LoanListResponse.model_validate(l) for l in loans],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    loan_data: LoanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new loan."""
    # Verify borrower exists and belongs to org
    result = await db.execute(
        select(Borrower).where(
            Borrower.id == loan_data.borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    loan = Loan(
        organization_id=current_user.organization_id,
        **loan_data.model_dump()
    )
    loan.update_bucket()
    db.add(loan)
    await db.commit()
    await db.refresh(loan)

    return loan


@router.get("/{loan_id}", response_model=LoanWithBorrower)
async def get_loan(
    loan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific loan with borrower details."""
    result = await db.execute(
        select(Loan).where(
            Loan.id == loan_id,
            Loan.organization_id == current_user.organization_id
        )
    )
    loan = result.scalar_one_or_none()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )

    # Get borrower
    result = await db.execute(
        select(Borrower).where(Borrower.id == loan.borrower_id)
    )
    borrower = result.scalar_one()

    loan_dict = LoanResponse.model_validate(loan).model_dump()
    loan_dict['borrower_name'] = borrower.full_name
    loan_dict['borrower_phone'] = borrower.primary_phone

    return LoanWithBorrower(**loan_dict)


@router.put("/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: UUID,
    update_data: LoanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a loan."""
    result = await db.execute(
        select(Loan).where(
            Loan.id == loan_id,
            Loan.organization_id == current_user.organization_id
        )
    )
    loan = result.scalar_one_or_none()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(loan, field, value)

    # Update bucket if DPD changed
    if 'dpd' in update_dict:
        loan.update_bucket()

    await db.commit()
    await db.refresh(loan)

    return loan


@router.post("/import", response_model=LoanImportResponse)
async def import_loans(
    file: UploadFile = File(...),
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Import loans from CSV/Excel file."""
    import pandas as pd
    from io import BytesIO
    from decimal import Decimal

    # Read file
    content = await file.read()

    if file.filename.endswith('.csv'):
        df = pd.read_csv(BytesIO(content))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(BytesIO(content))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Use CSV or Excel."
        )

    imported = 0
    updated = 0
    failed = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            external_loan_id = str(row.get('external_loan_id'))
            borrower_external_id = str(row.get('borrower_external_id'))

            # Find borrower
            result = await db.execute(
                select(Borrower).where(
                    Borrower.organization_id == current_user.organization_id,
                    Borrower.external_id == borrower_external_id
                )
            )
            borrower = result.scalar_one_or_none()

            if not borrower:
                failed += 1
                errors.append({"row": idx + 2, "error": f"Borrower not found: {borrower_external_id}"})
                continue

            # Check if loan exists
            result = await db.execute(
                select(Loan).where(
                    Loan.organization_id == current_user.organization_id,
                    Loan.external_loan_id == external_loan_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing loan
                existing.dpd = int(row.get('dpd', 0))
                if pd.notna(row.get('outstanding_principal')):
                    existing.outstanding_principal = Decimal(str(row['outstanding_principal']))
                if pd.notna(row.get('overdue_amount')):
                    existing.overdue_amount = Decimal(str(row['overdue_amount']))
                existing.update_bucket()
                updated += 1
            else:
                # Create new loan
                loan = Loan(
                    organization_id=current_user.organization_id,
                    borrower_id=borrower.id,
                    external_loan_id=external_loan_id,
                    loan_type=row.get('loan_type', 'personal'),
                    principal_amount=Decimal(str(row['principal_amount'])),
                    emi_amount=Decimal(str(row['emi_amount'])),
                    dpd=int(row.get('dpd', 0)),
                    outstanding_principal=Decimal(str(row.get('outstanding_principal', row['principal_amount']))),
                )
                loan.update_bucket()
                db.add(loan)
                imported += 1

        except Exception as e:
            failed += 1
            errors.append({"row": idx + 2, "error": str(e)})

    await db.commit()

    return LoanImportResponse(
        total=len(df),
        imported=imported,
        updated=updated,
        failed=failed,
        errors=errors[:10]
    )


@router.get("/buckets/summary")
async def get_bucket_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get loan count by bucket."""
    result = await db.execute(
        select(Loan.bucket, func.count(Loan.id))
        .where(Loan.organization_id == current_user.organization_id)
        .group_by(Loan.bucket)
    )

    buckets = {row[0] or "unknown": row[1] for row in result.all()}
    return buckets
