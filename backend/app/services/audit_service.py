"""Audit logging service for security-sensitive operations."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit_event(
    db: AsyncSession,
    action: str,
    category: str,
    organization_id: UUID,
    user_id: Optional[UUID] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    entity_name: Optional[str] = None,
    description: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> AuditLog:
    """
    Log an audit event for compliance and security tracking.

    Actions for security:
    - login_success, login_failed, logout
    - password_changed, password_reset
    - user_created, user_updated, user_deleted
    - role_changed
    - token_refreshed
    """
    audit = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        user_email=user_email,
        user_name=user_name,
        action=action,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data or {},
        performed_at=datetime.utcnow(),
    )
    db.add(audit)
    await db.flush()
    return audit


def get_client_ip(request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
