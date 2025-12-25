from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from io import StringIO
import csv

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse, AuditLogListResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()

# Categories we expose (case & payment only per requirement)
ALLOWED_CATEGORIES = ["case", "payment"]

# Action labels for display
ACTION_LABELS = {
    "case_created": "Case Created",
    "case_updated": "Case Updated",
    "case_assigned": "Case Assigned",
    "case_status_changed": "Status Changed",
    "case_note_added": "Note Added",
    "payment_recorded": "Payment Recorded",
    "payment_updated": "Payment Updated",
    "promise_created": "Promise Created",
    "promise_fulfilled": "Promise Fulfilled",
    "promise_broken": "Promise Broken",
}


@router.get("", response_model=PaginatedResponse[AuditLogListResponse])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List audit logs for the organization. Admin only.

    Filters:
    - user_id: Filter by user who performed the action
    - action: Filter by action type (case_created, payment_recorded, etc.)
    - category: Filter by category (case, payment)
    - entity_type: Filter by entity type (case, payment, promise)
    - date_from/date_to: Filter by date range
    - search: Search in entity name or description
    """
    query = select(AuditLog).where(
        AuditLog.organization_id == current_user.organization_id,
        AuditLog.category.in_(ALLOWED_CATEGORIES)
    )

    # Apply filters
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if category:
        if category in ALLOWED_CATEGORIES:
            query = query.where(AuditLog.category == category)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    if date_from:
        query = query.where(AuditLog.performed_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(AuditLog.performed_at <= datetime.combine(date_to, datetime.max.time()))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                AuditLog.entity_name.ilike(search_filter),
                AuditLog.description.ilike(search_filter)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply sorting and pagination
    query = query.order_by(AuditLog.performed_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return PaginatedResponse(
        items=[AuditLogListResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get a single audit log entry. Admin only."""
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.id == log_id,
            AuditLog.organization_id == current_user.organization_id
        )
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )

    return log


@router.get("/export/csv")
async def export_audit_logs_csv(
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Export audit logs to CSV. Admin only.

    Uses the same filters as the list endpoint.
    """
    query = select(AuditLog).where(
        AuditLog.organization_id == current_user.organization_id,
        AuditLog.category.in_(ALLOWED_CATEGORIES)
    )

    # Apply same filters as list endpoint
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if category:
        if category in ALLOWED_CATEGORIES:
            query = query.where(AuditLog.category == category)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    if date_from:
        query = query.where(AuditLog.performed_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(AuditLog.performed_at <= datetime.combine(date_to, datetime.max.time()))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                AuditLog.entity_name.ilike(search_filter),
                AuditLog.description.ilike(search_filter)
            )
        )

    # Order by date descending
    query = query.order_by(AuditLog.performed_at.desc())

    result = await db.execute(query)
    logs = result.scalars().all()

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Date & Time",
        "User",
        "User Email",
        "Action",
        "Category",
        "Entity Type",
        "Entity",
        "Description",
        "IP Address"
    ])

    # Data rows
    for log in logs:
        writer.writerow([
            log.performed_at.strftime("%Y-%m-%d %H:%M:%S") if log.performed_at else "",
            log.user_name or "",
            log.user_email or "",
            ACTION_LABELS.get(log.action, log.action),
            log.category,
            log.entity_type or "",
            log.entity_name or "",
            log.description or "",
            log.ip_address or ""
        ])

    output.seek(0)

    # Generate filename with current date
    filename = f"audit-logs-{datetime.now().strftime('%Y-%m-%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/actions/list")
async def list_available_actions(
    current_user: User = Depends(require_admin),
):
    """Get list of available actions for filtering."""
    return {
        "actions": [
            {"value": key, "label": label}
            for key, label in ACTION_LABELS.items()
        ]
    }


@router.get("/users/list")
async def list_users_for_filter(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get list of users for the filter dropdown."""
    result = await db.execute(
        select(User.id, User.first_name, User.last_name, User.email, User.role)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.first_name)
    )
    users = result.all()

    return {
        "users": [
            {
                "id": str(user.id),
                "name": f"{user.first_name} {user.last_name or ''}".strip(),
                "email": user.email,
                "role": user.role
            }
            for user in users
        ]
    }
