from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_manager
from app.models.user import User
from app.models.audit_log import AuditLog, DNCRegistry
from app.models.borrower import Borrower
from app.models.communication import Communication
from app.schemas.common import PaginatedResponse

router = APIRouter()


# ==================== Schemas ====================

class AuditLogResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID]
    user_email: Optional[str]
    user_name: Optional[str]
    action: str
    category: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    entity_name: Optional[str]
    description: Optional[str]
    old_value: Optional[dict]
    new_value: Optional[dict]
    extra_data: Optional[dict]
    ip_address: Optional[str]
    performed_at: datetime

    class Config:
        from_attributes = True


class DNCEntryCreate(BaseModel):
    phone_number: str
    dnc_type: str = "all"  # all, call, sms, whatsapp
    source: str = "customer_request"
    borrower_id: Optional[UUID] = None
    reason: Optional[str] = None
    valid_until: Optional[datetime] = None


class DNCEntryResponse(BaseModel):
    id: UUID
    phone_number: str
    dnc_type: str
    source: str
    borrower_id: Optional[UUID]
    reason: Optional[str]
    valid_from: datetime
    valid_until: Optional[datetime]
    is_active: str
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceStatsResponse(BaseModel):
    total_calls: int
    calls_to_dnc: int  # Should be 0 if compliant
    calls_after_hours: int
    total_sms: int
    total_whatsapp: int
    dnc_entries: int
    compliance_score: float


class RBIComplianceReport(BaseModel):
    report_date: datetime
    organization_name: str
    total_borrowers: int
    total_active_cases: int
    total_communications: int
    dnc_violations: int
    after_hours_calls: int
    call_frequency_violations: int
    compliance_percentage: float
    details: dict


# ==================== Audit Log Endpoints ====================

@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """List audit logs with filters."""
    query = select(AuditLog).where(
        AuditLog.organization_id == current_user.organization_id
    )

    if category:
        query = query.where(AuditLog.category == category)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if date_from:
        query = query.where(AuditLog.performed_at >= date_from)
    if date_to:
        query = query.where(AuditLog.performed_at <= date_to)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.order_by(AuditLog.performed_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    date_from: datetime,
    date_to: datetime,
    format: str = Query("json", enum=["json", "csv"]),
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Export audit logs for a date range."""
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.organization_id == current_user.organization_id,
            AuditLog.performed_at >= date_from,
            AuditLog.performed_at <= date_to
        ).order_by(AuditLog.performed_at.desc())
    )
    logs = result.scalars().all()

    if format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp", "User", "Action", "Category",
            "Entity Type", "Entity", "Description", "IP Address"
        ])
        for log in logs:
            writer.writerow([
                log.performed_at.isoformat(),
                log.user_email,
                log.action,
                log.category,
                log.entity_type,
                log.entity_name,
                log.description,
                log.ip_address
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{date_from.date()}_{date_to.date()}.csv"}
        )

    return [AuditLogResponse.model_validate(log) for log in logs]


# ==================== DNC Registry Endpoints ====================

@router.get("/dnc-registry", response_model=PaginatedResponse[DNCEntryResponse])
async def list_dnc_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    dnc_type: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List DNC registry entries."""
    query = select(DNCRegistry).where(
        DNCRegistry.organization_id == current_user.organization_id
    )

    if dnc_type:
        query = query.where(DNCRegistry.dnc_type == dnc_type)
    if source:
        query = query.where(DNCRegistry.source == source)
    if search:
        query = query.where(DNCRegistry.phone_number.ilike(f"%{search}%"))
    if active_only:
        query = query.where(DNCRegistry.is_active == "active")

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.order_by(DNCRegistry.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    entries = result.scalars().all()

    return PaginatedResponse(
        items=[DNCEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/dnc-registry", response_model=DNCEntryResponse)
async def add_dnc_entry(
    entry: DNCEntryCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a phone number to DNC registry."""
    # Check if already exists
    existing = await db.execute(
        select(DNCRegistry).where(
            DNCRegistry.organization_id == current_user.organization_id,
            DNCRegistry.phone_number == entry.phone_number,
            DNCRegistry.dnc_type == entry.dnc_type,
            DNCRegistry.is_active == "active"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already in DNC registry for this type"
        )

    dnc_entry = DNCRegistry(
        organization_id=current_user.organization_id,
        phone_number=entry.phone_number,
        dnc_type=entry.dnc_type,
        source=entry.source,
        borrower_id=entry.borrower_id,
        added_by_id=current_user.id,
        reason=entry.reason,
        valid_until=entry.valid_until
    )
    db.add(dnc_entry)

    # Also update borrower flags if borrower_id is provided
    if entry.borrower_id:
        borrower_result = await db.execute(
            select(Borrower).where(Borrower.id == entry.borrower_id)
        )
        borrower = borrower_result.scalar_one_or_none()
        if borrower:
            if entry.dnc_type in ["all", "call"]:
                borrower.do_not_call = True
            if entry.dnc_type in ["all", "sms"]:
                borrower.do_not_sms = True
            if entry.dnc_type in ["all", "whatsapp"]:
                borrower.do_not_whatsapp = True

    # Create audit log
    audit_log = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name,
        action="dnc_added",
        category="compliance",
        entity_type="dnc_registry",
        description=f"Added {entry.phone_number} to DNC registry ({entry.dnc_type})",
        new_value=entry.model_dump(),
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(dnc_entry)

    return dnc_entry


@router.delete("/dnc-registry/{entry_id}")
async def remove_dnc_entry(
    entry_id: UUID,
    request: Request,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Remove a phone number from DNC registry."""
    result = await db.execute(
        select(DNCRegistry).where(
            DNCRegistry.id == entry_id,
            DNCRegistry.organization_id == current_user.organization_id
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="DNC entry not found")

    entry.is_active = "removed"

    # Create audit log
    audit_log = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name,
        action="dnc_removed",
        category="compliance",
        entity_type="dnc_registry",
        entity_id=entry_id,
        description=f"Removed {entry.phone_number} from DNC registry",
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)

    await db.commit()

    return {"status": "removed"}


@router.get("/dnc-registry/check/{phone_number}")
async def check_dnc_status(
    phone_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if a phone number is in DNC registry."""
    result = await db.execute(
        select(DNCRegistry).where(
            DNCRegistry.organization_id == current_user.organization_id,
            DNCRegistry.phone_number == phone_number,
            DNCRegistry.is_active == "active"
        )
    )
    entries = result.scalars().all()

    restrictions = []
    for entry in entries:
        restrictions.append({
            "type": entry.dnc_type,
            "source": entry.source,
            "reason": entry.reason,
            "valid_until": entry.valid_until.isoformat() if entry.valid_until else None
        })

    return {
        "phone_number": phone_number,
        "is_restricted": len(restrictions) > 0,
        "restrictions": restrictions
    }


# ==================== Compliance Reports ====================

@router.get("/stats", response_model=ComplianceStatsResponse)
async def get_compliance_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance statistics."""
    org_id = current_user.organization_id

    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # Total calls
    total_calls = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    ) or 0

    # Calls to DNC numbers (violations)
    dnc_phones = select(DNCRegistry.phone_number).where(
        DNCRegistry.organization_id == org_id,
        DNCRegistry.is_active == "active",
        DNCRegistry.dnc_type.in_(["all", "call"])
    )
    calls_to_dnc = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.channel == "call",
            Communication.to_number.in_(dnc_phones),
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    ) or 0

    # Calls after hours (before 8 AM or after 9 PM)
    # This is a simplified check - in production you'd use proper timezone handling
    calls_after_hours = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to,
            func.extract("hour", Communication.initiated_at).notin_(range(8, 21))
        )
    ) or 0

    # SMS and WhatsApp counts
    total_sms = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.channel == "sms",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    ) or 0

    total_whatsapp = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.channel == "whatsapp",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    ) or 0

    # DNC entries
    dnc_entries = await db.scalar(
        select(func.count(DNCRegistry.id)).where(
            DNCRegistry.organization_id == org_id,
            DNCRegistry.is_active == "active"
        )
    ) or 0

    # Calculate compliance score
    violations = calls_to_dnc + calls_after_hours
    total_comms = total_calls + total_sms + total_whatsapp
    compliance_score = ((total_comms - violations) / total_comms * 100) if total_comms > 0 else 100

    return ComplianceStatsResponse(
        total_calls=total_calls,
        calls_to_dnc=calls_to_dnc,
        calls_after_hours=calls_after_hours,
        total_sms=total_sms,
        total_whatsapp=total_whatsapp,
        dnc_entries=dnc_entries,
        compliance_score=round(compliance_score, 1)
    )


@router.get("/rbi-report", response_model=RBIComplianceReport)
async def generate_rbi_compliance_report(
    date_from: datetime,
    date_to: datetime,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Generate RBI compliance report."""
    from app.models.organization import Organization
    from app.models.case import Case

    org_id = current_user.organization_id

    # Get org name
    org_result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = org_result.scalar_one()

    # Total borrowers
    total_borrowers = await db.scalar(
        select(func.count(Borrower.id)).where(
            Borrower.organization_id == org_id
        )
    ) or 0

    # Active cases
    active_cases = await db.scalar(
        select(func.count(Case.id)).where(
            Case.organization_id == org_id,
            Case.status.in_(["open", "in_progress"])
        )
    ) or 0

    # Total communications in period
    total_comms = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    ) or 0

    # DNC violations
    dnc_phones = select(DNCRegistry.phone_number).where(
        DNCRegistry.organization_id == org_id,
        DNCRegistry.is_active == "active"
    )
    dnc_violations = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.to_number.in_(dnc_phones),
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        )
    ) or 0

    # After hours calls (before 8 AM or after 9 PM)
    after_hours = await db.scalar(
        select(func.count(Communication.id)).where(
            Communication.organization_id == org_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to,
            func.extract("hour", Communication.initiated_at).notin_(range(8, 21))
        )
    ) or 0

    # Call frequency violations (more than 3 calls per day to same number)
    # This is a simplified check
    frequency_result = await db.execute(
        select(
            Communication.to_number,
            func.date(Communication.initiated_at),
            func.count(Communication.id).label("count")
        ).where(
            Communication.organization_id == org_id,
            Communication.channel == "call",
            Communication.initiated_at >= date_from,
            Communication.initiated_at <= date_to
        ).group_by(
            Communication.to_number,
            func.date(Communication.initiated_at)
        ).having(func.count(Communication.id) > 3)
    )
    frequency_violations = len(frequency_result.all())

    # Calculate compliance percentage
    total_violations = dnc_violations + after_hours + frequency_violations
    compliance_pct = ((total_comms - total_violations) / total_comms * 100) if total_comms > 0 else 100

    return RBIComplianceReport(
        report_date=datetime.utcnow(),
        organization_name=org.name,
        total_borrowers=total_borrowers,
        total_active_cases=active_cases,
        total_communications=total_comms,
        dnc_violations=dnc_violations,
        after_hours_calls=after_hours,
        call_frequency_violations=frequency_violations,
        compliance_percentage=round(compliance_pct, 1),
        details={
            "period_start": date_from.isoformat(),
            "period_end": date_to.isoformat(),
            "allowed_call_hours": "8:00 AM - 9:00 PM",
            "max_calls_per_day": 3,
            "dnc_registry_count": await db.scalar(
                select(func.count(DNCRegistry.id)).where(
                    DNCRegistry.organization_id == org_id,
                    DNCRegistry.is_active == "active"
                )
            ) or 0
        }
    )
