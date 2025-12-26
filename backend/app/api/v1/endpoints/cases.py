from typing import Optional, List
from uuid import UUID
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_manager, get_agent_case_ids
from app.models.user import User
from app.models.case import Case, CaseAssignment, CaseNote
from app.models.loan import Loan
from app.models.borrower import Borrower
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseListResponse,
    CaseWithDetails,
    CaseAssignRequest,
    CaseBulkAssignRequest,
    CaseNoteCreate,
    CaseNoteResponse,
    CaseStatsResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.collection_intelligence import (
    calculate_priority_score,
    calculate_simple_risk_score,
)

router = APIRouter()


def generate_case_number() -> str:
    """Generate unique case number."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_part = str(uuid.uuid4())[:6].upper()
    return f"CASE-{timestamp}-{unique_part}"


@router.get("", response_model=PaginatedResponse[CaseListResponse])
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[int] = None,
    case_type: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
    unassigned: Optional[bool] = None,
    search: Optional[str] = None,
    follow_up_from: Optional[date] = None,
    follow_up_to: Optional[date] = None,
    has_follow_up: Optional[bool] = None,
    sort_by: Optional[str] = Query(None, description="Sort by: created_at, last_contact_date, next_follow_up, priority"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List cases in the organization. Agents only see their assigned cases.

    Filter by follow-up date range using follow_up_from and follow_up_to.
    Use has_follow_up=true to only show cases with scheduled follow-ups.
    Sort using sort_by and sort_order parameters.
    """
    query = select(Case).where(
        Case.organization_id == current_user.organization_id
    )

    # Agent role: filter to only assigned cases
    agent_case_ids = await get_agent_case_ids(current_user, db)
    if agent_case_ids is not None:  # None means admin/manager, can see all
        if not agent_case_ids:  # Empty list means no assigned cases
            return PaginatedResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
        query = query.where(Case.id.in_(agent_case_ids))

    if status_filter:
        query = query.where(Case.status == status_filter)
    if priority:
        query = query.where(Case.priority == priority)
    if case_type:
        query = query.where(Case.case_type == case_type)

    if search:
        search_filter = f"%{search}%"
        query = query.where(Case.case_number.ilike(search_filter))

    # Follow-up filters
    if has_follow_up is True:
        query = query.where(Case.next_follow_up.isnot(None))
    elif has_follow_up is False:
        query = query.where(Case.next_follow_up.is_(None))

    if follow_up_from:
        query = query.where(Case.next_follow_up >= datetime.combine(follow_up_from, datetime.min.time()))
    if follow_up_to:
        query = query.where(Case.next_follow_up <= datetime.combine(follow_up_to, datetime.max.time()))

    # Handle assignment filter (only for admin/manager)
    if assigned_to and agent_case_ids is None:
        subquery = select(CaseAssignment.case_id).where(
            CaseAssignment.agent_id == assigned_to,
            CaseAssignment.is_active == True
        )
        query = query.where(Case.id.in_(subquery))
    elif unassigned and agent_case_ids is None:
        subquery = select(CaseAssignment.case_id).where(
            CaseAssignment.is_active == True
        )
        query = query.where(~Case.id.in_(subquery))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply sorting
    sort_column = Case.created_at  # default
    if sort_by == 'last_contact_date':
        sort_column = Case.last_contact_date
    elif sort_by == 'next_follow_up':
        sort_column = Case.next_follow_up
    elif sort_by == 'priority':
        sort_column = Case.priority
    elif sort_by == 'created_at':
        sort_column = Case.created_at

    if sort_order == 'asc':
        query = query.order_by(sort_column.asc().nullslast())
    else:
        query = query.order_by(sort_column.desc().nullslast())

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    cases = result.scalars().all()

    # Fetch loan and borrower details for all cases
    case_items = []
    if cases:
        loan_ids = [c.loan_id for c in cases]
        loans_result = await db.execute(
            select(Loan).where(Loan.id.in_(loan_ids))
        )
        loans_map = {l.id: l for l in loans_result.scalars().all()}

        borrower_ids = [l.borrower_id for l in loans_map.values()]
        if borrower_ids:
            borrowers_result = await db.execute(
                select(Borrower).where(Borrower.id.in_(borrower_ids))
            )
            borrowers_map = {b.id: b for b in borrowers_result.scalars().all()}
        else:
            borrowers_map = {}

        for case in cases:
            case_dict = {
                "id": case.id,
                "case_number": case.case_number,
                "status": case.status,
                "priority": case.priority,
                "case_type": case.case_type,
                "loan_id": case.loan_id,
                "next_follow_up": case.next_follow_up,
                "last_contact_date": case.last_contact_date,
                "total_attempts": case.total_attempts,
                "tags": case.tags or [],
                "created_at": case.created_at,
            }
            loan = loans_map.get(case.loan_id)
            if loan:
                borrower = borrowers_map.get(loan.borrower_id)
                case_dict["borrower_id"] = loan.borrower_id
                case_dict["total_outstanding"] = loan.total_outstanding
                case_dict["dpd"] = loan.dpd
                case_dict["bucket"] = loan.bucket
                if borrower:
                    case_dict["borrower_name"] = f"{borrower.first_name} {borrower.last_name or ''}".strip()
                    case_dict["borrower_phone"] = borrower.primary_phone
            case_items.append(CaseListResponse(**case_dict))

    return PaginatedResponse(
        items=case_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new case."""
    # Verify loan exists and belongs to org
    result = await db.execute(
        select(Loan).where(
            Loan.id == case_data.loan_id,
            Loan.organization_id == current_user.organization_id
        )
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )

    # Calculate risk and priority from loan data
    from decimal import Decimal
    risk = calculate_simple_risk_score(
        dpd=loan.dpd or 0,
        overdue_amount=loan.overdue_amount or Decimal(0),
        principal_amount=loan.principal_amount or Decimal(1),
    )
    priority = calculate_priority_score(
        overdue_amount=loan.overdue_amount or Decimal(0),
        principal_amount=loan.principal_amount or Decimal(1),
        dpd=loan.dpd or 0,
        risk_score=risk["score"],
    )

    case = Case(
        organization_id=current_user.organization_id,
        case_number=generate_case_number(),
        priority=priority["priority_level"],
        extra_data={"ml_priority": priority},
        **case_data.model_dump()
    )
    db.add(case)

    # Update loan risk score
    loan.risk_score = risk

    await db.commit()
    await db.refresh(case)

    return case


@router.get("/stats", response_model=CaseStatsResponse)
async def get_case_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get case statistics. Agents see stats for their assigned cases only."""
    org_id = current_user.organization_id

    # Agent role: filter to only assigned cases
    agent_case_ids = await get_agent_case_ids(current_user, db)

    # Build base filter
    def add_agent_filter(query):
        if agent_case_ids is not None:
            if not agent_case_ids:
                return None  # No cases assigned
            return query.where(Case.id.in_(agent_case_ids))
        return query

    base_query = select(func.count(Case.id)).where(Case.organization_id == org_id)
    if agent_case_ids is not None:
        if not agent_case_ids:
            return CaseStatsResponse(
                total=0, open=0, in_progress=0, promise_to_pay=0,
                resolved=0, escalated=0, by_priority={}, by_bucket={}
            )
        base_query = base_query.where(Case.id.in_(agent_case_ids))

    total = await db.scalar(base_query)

    # By status
    status_counts = {}
    for s in ["open", "in_progress", "promise_to_pay", "resolved", "escalated"]:
        status_query = select(func.count(Case.id)).where(
            Case.organization_id == org_id,
            Case.status == s
        )
        if agent_case_ids is not None:
            status_query = status_query.where(Case.id.in_(agent_case_ids))
        count = await db.scalar(status_query)
        status_counts[s] = count or 0

    # By priority
    priority_query = select(Case.priority, func.count(Case.id)).where(
        Case.organization_id == org_id
    ).group_by(Case.priority)
    if agent_case_ids is not None:
        priority_query = priority_query.where(Case.id.in_(agent_case_ids))
    priority_result = await db.execute(priority_query)
    by_priority = {row[0]: row[1] for row in priority_result.all()}

    # By bucket (join with loan)
    bucket_query = select(Loan.bucket, func.count(Case.id)).join(
        Loan, Case.loan_id == Loan.id
    ).where(Case.organization_id == org_id).group_by(Loan.bucket)
    if agent_case_ids is not None:
        bucket_query = bucket_query.where(Case.id.in_(agent_case_ids))
    bucket_result = await db.execute(bucket_query)
    by_bucket = {row[0] or "unknown": row[1] for row in bucket_result.all()}

    return CaseStatsResponse(
        total=total or 0,
        open=status_counts.get("open", 0),
        in_progress=status_counts.get("in_progress", 0),
        promise_to_pay=status_counts.get("promise_to_pay", 0),
        resolved=status_counts.get("resolved", 0),
        escalated=status_counts.get("escalated", 0),
        by_priority=by_priority,
        by_bucket=by_bucket
    )


@router.get("/{case_id}", response_model=CaseWithDetails)
async def get_case(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific case with details. Agents can only access assigned cases."""
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Agent role: verify they are assigned to this case
    agent_case_ids = await get_agent_case_ids(current_user, db)
    if agent_case_ids is not None and case_id not in agent_case_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this case"
        )

    # Get loan and borrower
    result = await db.execute(
        select(Loan).where(Loan.id == case.loan_id)
    )
    loan = result.scalar_one()

    result = await db.execute(
        select(Borrower).where(Borrower.id == loan.borrower_id)
    )
    borrower = result.scalar_one()

    # Get assigned agent
    result = await db.execute(
        select(CaseAssignment).where(
            CaseAssignment.case_id == case_id,
            CaseAssignment.is_active == True
        )
    )
    assignment = result.scalar_one_or_none()
    agent_name = None
    if assignment:
        result = await db.execute(
            select(User).where(User.id == assignment.agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent:
            agent_name = agent.full_name

    case_dict = CaseResponse.model_validate(case).model_dump()
    case_dict.update({
        'borrower_id': borrower.id,
        'borrower_name': borrower.full_name,
        'borrower_phone': borrower.primary_phone,
        'borrower_preferred_language': borrower.preferred_language or 'en',
        'loan_account_number': loan.loan_account_number,
        'total_outstanding': float(loan.total_outstanding) if loan.total_outstanding else None,
        'dpd': loan.dpd,
        'bucket': loan.bucket,
        'assigned_agent_name': agent_name
    })

    return CaseWithDetails(**case_dict)


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    update_data: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a case."""
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle resolution
    if update_dict.get('status') == 'resolved' and not case.resolution_date:
        update_dict['resolution_date'] = datetime.utcnow()

    for field, value in update_dict.items():
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)

    return case


@router.post("/{case_id}/assign", response_model=CaseResponse)
async def assign_case(
    case_id: UUID,
    request: CaseAssignRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Assign a case to an agent."""
    # Verify case exists
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Verify agent exists and is in same org
    result = await db.execute(
        select(User).where(
            User.id == request.agent_id,
            User.organization_id == current_user.organization_id,
            User.is_active == True
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Deactivate existing assignments
    result = await db.execute(
        select(CaseAssignment).where(
            CaseAssignment.case_id == case_id,
            CaseAssignment.is_active == True
        )
    )
    for assignment in result.scalars():
        assignment.is_active = False
        assignment.unassigned_at = datetime.utcnow()

    # Create new assignment
    new_assignment = CaseAssignment(
        case_id=case_id,
        agent_id=request.agent_id,
        assigned_by=current_user.id,
        is_active=True
    )
    db.add(new_assignment)
    await db.commit()
    await db.refresh(case)

    return case


@router.post("/bulk-assign")
async def bulk_assign_cases(
    request: CaseBulkAssignRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Bulk assign cases to an agent."""
    assigned_count = 0

    for case_id in request.case_ids:
        try:
            result = await db.execute(
                select(Case).where(
                    Case.id == case_id,
                    Case.organization_id == current_user.organization_id
                )
            )
            case = result.scalar_one_or_none()

            if case:
                # Deactivate existing
                result = await db.execute(
                    select(CaseAssignment).where(
                        CaseAssignment.case_id == case_id,
                        CaseAssignment.is_active == True
                    )
                )
                for assignment in result.scalars():
                    assignment.is_active = False
                    assignment.unassigned_at = datetime.utcnow()

                # Create new
                new_assignment = CaseAssignment(
                    case_id=case_id,
                    agent_id=request.agent_id,
                    assigned_by=current_user.id,
                    is_active=True
                )
                db.add(new_assignment)
                assigned_count += 1
        except Exception:
            continue

    await db.commit()

    return {"assigned": assigned_count, "total": len(request.case_ids)}


@router.get("/{case_id}/notes", response_model=List[CaseNoteResponse])
async def get_case_notes(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notes for a case."""
    # Verify case access
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    result = await db.execute(
        select(CaseNote).where(CaseNote.case_id == case_id)
        .order_by(CaseNote.created_at.desc())
    )
    notes = result.scalars().all()

    response_notes = []
    for note in notes:
        author_name = None
        if note.author_id:
            result = await db.execute(
                select(User).where(User.id == note.author_id)
            )
            author = result.scalar_one_or_none()
            if author:
                author_name = author.full_name

        note_dict = CaseNoteResponse.model_validate(note).model_dump()
        note_dict['author_name'] = author_name
        response_notes.append(CaseNoteResponse(**note_dict))

    return response_notes


@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
async def add_case_note(
    case_id: UUID,
    note_data: CaseNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a note to a case."""
    # Verify case access
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    note = CaseNote(
        case_id=case_id,
        author_id=current_user.id,
        **note_data.model_dump()
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    note_dict = CaseNoteResponse.model_validate(note).model_dump()
    note_dict['author_name'] = current_user.full_name

    return CaseNoteResponse(**note_dict)
