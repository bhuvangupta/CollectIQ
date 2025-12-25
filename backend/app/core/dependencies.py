from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_token, TokenPayload
from app.models.user import User


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user."""
    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(User).where(User.id == payload.sub)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_roles(*roles: str):
    """Dependency factory to require specific roles."""
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(roles)}"
            )
        return current_user
    return role_checker


# Common role dependencies
require_admin = require_roles("admin")
require_manager = require_roles("admin", "manager")
require_agent = require_roles("admin", "manager", "agent")


class OrgContext:
    """Context for organization-scoped queries."""

    def __init__(self, org_id: str, user: User):
        self.org_id = org_id
        self.user = user

    @property
    def is_admin(self) -> bool:
        return self.user.role == "admin"

    @property
    def is_manager(self) -> bool:
        return self.user.role in ("admin", "manager")

    @property
    def is_agent(self) -> bool:
        return self.user.role == "agent"

    @property
    def can_see_all_data(self) -> bool:
        """Returns True if user can see all org data (admin/manager)."""
        return self.user.role in ("admin", "manager")


async def get_org_context(
    current_user: User = Depends(get_current_user)
) -> OrgContext:
    """Get organization context for the current user."""
    return OrgContext(
        org_id=str(current_user.organization_id),
        user=current_user
    )


async def get_agent_case_ids(
    user: User,
    db: AsyncSession
) -> Optional[list]:
    """
    Get list of case IDs assigned to the agent.
    Returns None if user is admin/manager (meaning they can see all).
    Returns list of case IDs if user is agent.
    """
    from app.models.case import CaseAssignment

    if user.role in ("admin", "manager"):
        return None  # Can see all cases

    # Agent can only see assigned cases
    result = await db.execute(
        select(CaseAssignment.case_id).where(
            CaseAssignment.agent_id == user.id,
            CaseAssignment.is_active == True
        )
    )
    return [row[0] for row in result.all()]


async def get_agent_borrower_ids(
    user: User,
    db: AsyncSession
) -> Optional[list]:
    """
    Get list of borrower IDs accessible to the agent based on assigned cases.
    Returns None if user is admin/manager (meaning they can see all).
    """
    from app.models.case import Case, CaseAssignment
    from app.models.loan import Loan

    if user.role in ("admin", "manager"):
        return None  # Can see all borrowers

    # Get case IDs assigned to agent
    case_ids = await get_agent_case_ids(user, db)
    if not case_ids:
        return []  # Agent has no assigned cases

    # Get borrower IDs from those cases via loans
    result = await db.execute(
        select(Loan.borrower_id).distinct()
        .join(Case, Case.loan_id == Loan.id)
        .where(Case.id.in_(case_ids))
    )
    return [row[0] for row in result.all()]
