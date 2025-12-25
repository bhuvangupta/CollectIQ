from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.organization import Organization
from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.case import Case
from app.models.campaign import Campaign
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationStats,
)

router = APIRouter()


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return org


@router.put("/current", response_model=OrganizationResponse)
async def update_current_organization(
    update_data: OrganizationUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update current organization (admin only)."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)

    return org


@router.get("/current/stats", response_model=OrganizationStats)
async def get_organization_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization statistics."""
    org_id = current_user.organization_id

    # Get counts
    users_count = await db.scalar(
        select(func.count(User.id)).where(User.organization_id == org_id)
    )
    borrowers_count = await db.scalar(
        select(func.count(Borrower.id)).where(Borrower.organization_id == org_id)
    )
    loans_count = await db.scalar(
        select(func.count(Loan.id)).where(Loan.organization_id == org_id)
    )
    cases_count = await db.scalar(
        select(func.count(Case.id)).where(Case.organization_id == org_id)
    )
    active_campaigns = await db.scalar(
        select(func.count(Campaign.id)).where(
            Campaign.organization_id == org_id,
            Campaign.status.in_(["running", "scheduled"])
        )
    )

    # TODO: Calculate total collected from payments

    return OrganizationStats(
        total_users=users_count or 0,
        total_borrowers=borrowers_count or 0,
        total_loans=loans_count or 0,
        total_cases=cases_count or 0,
        active_campaigns=active_campaigns or 0,
        total_collected=0.0
    )
