from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_manager
from app.models.user import User
from app.models.campaign import Campaign, CampaignBorrower
from app.models.loan import Loan
from app.models.borrower import Borrower
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignStatsResponse,
    CampaignBorrowerResponse,
    AddBorrowersToCampaignRequest,
    CampaignPreviewResponse,
    TargetCriteria,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CampaignListResponse])
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    campaign_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List campaigns."""
    query = select(Campaign).where(
        Campaign.organization_id == current_user.organization_id
    )

    if status_filter:
        query = query.where(Campaign.status == status_filter)
    if campaign_type:
        query = query.where(Campaign.campaign_type == campaign_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Campaign.created_at.desc())

    result = await db.execute(query)
    campaigns = result.scalars().all()

    return PaginatedResponse(
        items=[CampaignListResponse.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign."""
    campaign = Campaign(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        target_criteria=campaign_data.target_criteria.model_dump() if campaign_data.target_criteria else {},
        **campaign_data.model_dump(exclude={'target_criteria'})
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    update_data: CampaignUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Update a campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # Don't allow editing running campaigns
    if campaign.status == "running" and update_data.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit running campaign. Pause it first."
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    if 'target_criteria' in update_dict and update_dict['target_criteria']:
        update_dict['target_criteria'] = update_dict['target_criteria'].model_dump()

    for field, value in update_dict.items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)

    return campaign


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Start a campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is already running"
        )

    if campaign.total_targets == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No targets in campaign. Add borrowers first."
        )

    campaign.status = "running"
    campaign.actual_start = datetime.utcnow()
    await db.commit()

    # TODO: Trigger Celery task to execute campaign

    return {"message": "Campaign started", "status": "running"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Pause a running campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not running"
        )

    campaign.status = "paused"
    await db.commit()

    return {"message": "Campaign paused", "status": "paused"}


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    campaign.status = "cancelled"
    campaign.actual_end = datetime.utcnow()
    await db.commit()

    return {"message": "Campaign cancelled", "status": "cancelled"}


@router.get("/{campaign_id}/stats", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get campaign statistics."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    completion_rate = campaign.completion_rate
    success_rate = campaign.success_rate
    contact_rate = (campaign.total_contacted / campaign.total_attempted * 100) if campaign.total_attempted else 0

    # Count promises from results_summary
    promises = campaign.results_summary.get("promises", 0) if campaign.results_summary else 0
    promise_rate = (promises / campaign.total_contacted * 100) if campaign.total_contacted else 0

    cost_per_contact = (float(campaign.actual_cost) / campaign.total_contacted) if campaign.total_contacted else 0

    return CampaignStatsResponse(
        completion_rate=round(completion_rate, 2),
        success_rate=round(success_rate, 2),
        contact_rate=round(contact_rate, 2),
        promise_rate=round(promise_rate, 2),
        total_cost=campaign.actual_cost,
        cost_per_contact=round(cost_per_contact, 2),
        by_outcome=campaign.results_summary or {},
        by_hour={}  # TODO: Implement hourly breakdown
    )


@router.post("/{campaign_id}/preview", response_model=CampaignPreviewResponse)
async def preview_campaign_targets(
    campaign_id: UUID,
    criteria: Optional[TargetCriteria] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Preview campaign targets based on criteria."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # Use provided criteria or campaign's criteria
    target_criteria = criteria.model_dump() if criteria else campaign.target_criteria

    # Build query for matching loans
    query = select(Loan).where(
        Loan.organization_id == current_user.organization_id,
        Loan.status == "active"
    )

    if target_criteria.get("buckets"):
        query = query.where(Loan.bucket.in_(target_criteria["buckets"]))
    if target_criteria.get("loan_types"):
        query = query.where(Loan.loan_type.in_(target_criteria["loan_types"]))
    if target_criteria.get("dpd_min") is not None:
        query = query.where(Loan.dpd >= target_criteria["dpd_min"])
    if target_criteria.get("dpd_max") is not None:
        query = query.where(Loan.dpd <= target_criteria["dpd_max"])

    # Exclude DNC if specified
    if target_criteria.get("exclude_do_not_call", True):
        dnc_borrowers = select(Borrower.id).where(Borrower.do_not_call == True)
        query = query.where(~Loan.borrower_id.in_(dnc_borrowers))

    # Get count
    count = await db.scalar(select(func.count()).select_from(query.subquery()))

    # Get sample (first 5)
    result = await db.execute(query.limit(5))
    sample_loans = result.scalars().all()

    sample_borrowers = []
    for loan in sample_loans:
        result = await db.execute(
            select(Borrower).where(Borrower.id == loan.borrower_id)
        )
        borrower = result.scalar_one()
        sample_borrowers.append({
            "name": borrower.full_name,
            "phone": borrower.primary_phone,
            "loan_type": loan.loan_type,
            "dpd": loan.dpd,
            "outstanding": float(loan.total_outstanding) if loan.total_outstanding else 0
        })

    # Bucket breakdown
    bucket_result = await db.execute(
        select(Loan.bucket, func.count(Loan.id))
        .where(Loan.organization_id == current_user.organization_id)
        .group_by(Loan.bucket)
    )
    by_bucket = {row[0] or "unknown": row[1] for row in bucket_result.all()}

    # Loan type breakdown
    type_result = await db.execute(
        select(Loan.loan_type, func.count(Loan.id))
        .where(Loan.organization_id == current_user.organization_id)
        .group_by(Loan.loan_type)
    )
    by_loan_type = {row[0]: row[1] for row in type_result.all()}

    # Estimate cost (mock: Rs 2 per call)
    estimated_cost = count * 2.0

    return CampaignPreviewResponse(
        total_matches=count,
        sample_borrowers=sample_borrowers,
        by_bucket=by_bucket,
        by_loan_type=by_loan_type,
        estimated_cost=estimated_cost
    )


@router.post("/{campaign_id}/borrowers")
async def add_borrowers_to_campaign(
    campaign_id: UUID,
    request: AddBorrowersToCampaignRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Add borrowers to a campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status not in ["draft", "scheduled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add borrowers to active campaign"
        )

    added = 0

    if request.use_criteria:
        # Add based on target criteria
        criteria = campaign.target_criteria
        query = select(Loan).where(
            Loan.organization_id == current_user.organization_id,
            Loan.status == "active"
        )

        if criteria.get("buckets"):
            query = query.where(Loan.bucket.in_(criteria["buckets"]))
        if criteria.get("dpd_min") is not None:
            query = query.where(Loan.dpd >= criteria["dpd_min"])
        if criteria.get("dpd_max") is not None:
            query = query.where(Loan.dpd <= criteria["dpd_max"])

        result = await db.execute(query)
        loans = result.scalars().all()

        for loan in loans:
            # Check if already added
            existing = await db.execute(
                select(CampaignBorrower).where(
                    CampaignBorrower.campaign_id == campaign_id,
                    CampaignBorrower.borrower_id == loan.borrower_id
                )
            )
            if not existing.scalar_one_or_none():
                cb = CampaignBorrower(
                    campaign_id=campaign_id,
                    borrower_id=loan.borrower_id,
                    loan_id=loan.id
                )
                db.add(cb)
                added += 1

    elif request.loan_ids:
        for loan_id in request.loan_ids:
            result = await db.execute(
                select(Loan).where(
                    Loan.id == loan_id,
                    Loan.organization_id == current_user.organization_id
                )
            )
            loan = result.scalar_one_or_none()
            if loan:
                cb = CampaignBorrower(
                    campaign_id=campaign_id,
                    borrower_id=loan.borrower_id,
                    loan_id=loan.id
                )
                db.add(cb)
                added += 1

    elif request.borrower_ids:
        for borrower_id in request.borrower_ids:
            cb = CampaignBorrower(
                campaign_id=campaign_id,
                borrower_id=borrower_id
            )
            db.add(cb)
            added += 1

    # Update campaign counts
    campaign.total_targets += added
    campaign.total_pending += added

    await db.commit()

    return {"message": f"Added {added} borrowers to campaign", "added": added}


@router.get("/{campaign_id}/borrowers", response_model=PaginatedResponse[CampaignBorrowerResponse])
async def get_campaign_borrowers(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get borrowers in a campaign."""
    # Verify campaign access
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user.organization_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    query = select(CampaignBorrower).where(
        CampaignBorrower.campaign_id == campaign_id
    )

    if status_filter:
        query = query.where(CampaignBorrower.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(CampaignBorrower.priority.desc())

    result = await db.execute(query)
    campaign_borrowers = result.scalars().all()

    return PaginatedResponse(
        items=[CampaignBorrowerResponse.model_validate(cb) for cb in campaign_borrowers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )
