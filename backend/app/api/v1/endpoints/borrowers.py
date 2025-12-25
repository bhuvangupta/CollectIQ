from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_manager, get_agent_borrower_ids
from app.models.user import User
from app.models.borrower import Borrower
from app.schemas.borrower import (
    BorrowerCreate,
    BorrowerUpdate,
    BorrowerResponse,
    BorrowerListResponse,
    BorrowerImportResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[BorrowerListResponse])
async def list_borrowers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List borrowers in the organization. Agents only see borrowers from assigned cases."""
    query = select(Borrower).where(
        Borrower.organization_id == current_user.organization_id
    )

    # Agent role: filter to only borrowers from assigned cases
    agent_borrower_ids = await get_agent_borrower_ids(current_user, db)
    if agent_borrower_ids is not None:  # None means admin/manager, can see all
        if not agent_borrower_ids:  # Empty list means no accessible borrowers
            return PaginatedResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
        query = query.where(Borrower.id.in_(agent_borrower_ids))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Borrower.first_name.ilike(search_filter),
                Borrower.last_name.ilike(search_filter),
                Borrower.primary_phone.ilike(search_filter),
                Borrower.external_id.ilike(search_filter),
                Borrower.email.ilike(search_filter)
            )
        )

    if city:
        query = query.where(Borrower.city.ilike(f"%{city}%"))
    if state:
        query = query.where(Borrower.state.ilike(f"%{state}%"))
    if is_active is not None:
        query = query.where(Borrower.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Borrower.created_at.desc())

    result = await db.execute(query)
    borrowers = result.scalars().all()

    return PaginatedResponse(
        items=[BorrowerListResponse.model_validate(b) for b in borrowers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=BorrowerResponse, status_code=status.HTTP_201_CREATED)
async def create_borrower(
    borrower_data: BorrowerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new borrower."""
    borrower = Borrower(
        organization_id=current_user.organization_id,
        **borrower_data.model_dump()
    )
    db.add(borrower)
    await db.commit()
    await db.refresh(borrower)

    return borrower


@router.get("/{borrower_id}", response_model=BorrowerResponse)
async def get_borrower(
    borrower_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific borrower. Agents can only access borrowers from their assigned cases."""
    result = await db.execute(
        select(Borrower).where(
            Borrower.id == borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    # Agent role: verify they have access to this borrower
    agent_borrower_ids = await get_agent_borrower_ids(current_user, db)
    if agent_borrower_ids is not None and borrower_id not in agent_borrower_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this borrower"
        )

    return borrower


@router.put("/{borrower_id}", response_model=BorrowerResponse)
async def update_borrower(
    borrower_id: UUID,
    update_data: BorrowerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a borrower."""
    result = await db.execute(
        select(Borrower).where(
            Borrower.id == borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(borrower, field, value)

    await db.commit()
    await db.refresh(borrower)

    return borrower


@router.delete("/{borrower_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_borrower(
    borrower_id: UUID,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a borrower."""
    result = await db.execute(
        select(Borrower).where(
            Borrower.id == borrower_id,
            Borrower.organization_id == current_user.organization_id
        )
    )
    borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    borrower.is_active = False
    await db.commit()


@router.post("/import", response_model=BorrowerImportResponse)
async def import_borrowers(
    file: UploadFile = File(...),
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Import borrowers from CSV/Excel file."""
    import pandas as pd
    from io import BytesIO

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
            # Check if borrower exists by external_id or phone
            external_id = row.get('external_id')
            phone = row.get('primary_phone', row.get('phone'))

            existing = None
            if external_id:
                result = await db.execute(
                    select(Borrower).where(
                        Borrower.organization_id == current_user.organization_id,
                        Borrower.external_id == str(external_id)
                    )
                )
                existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                for col in df.columns:
                    if col in ['external_id']:
                        continue
                    if hasattr(existing, col) and pd.notna(row[col]):
                        setattr(existing, col, row[col])
                updated += 1
            else:
                # Create new
                borrower = Borrower(
                    organization_id=current_user.organization_id,
                    external_id=str(external_id) if external_id else None,
                    first_name=row.get('first_name', 'Unknown'),
                    last_name=row.get('last_name'),
                    primary_phone=str(phone),
                    email=row.get('email'),
                    address_line1=row.get('address_line1'),
                    city=row.get('city'),
                    state=row.get('state'),
                    pincode=str(row.get('pincode')) if pd.notna(row.get('pincode')) else None,
                )
                db.add(borrower)
                imported += 1

        except Exception as e:
            failed += 1
            errors.append({"row": idx + 2, "error": str(e)})

    await db.commit()

    return BorrowerImportResponse(
        total=len(df),
        imported=imported,
        updated=updated,
        failed=failed,
        errors=errors[:10]  # Return first 10 errors
    )


@router.get("/by-phone/{phone}", response_model=BorrowerResponse)
async def get_borrower_by_phone(
    phone: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get borrower by phone number."""
    result = await db.execute(
        select(Borrower).where(
            Borrower.organization_id == current_user.organization_id,
            or_(
                Borrower.primary_phone == phone,
                Borrower.secondary_phone == phone
            )
        )
    )
    borrower = result.scalar_one_or_none()

    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found"
        )

    return borrower
