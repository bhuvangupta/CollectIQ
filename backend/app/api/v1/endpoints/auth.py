from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    RegisterRequest,
    CurrentUserResponse,
)
from app.services.audit_service import log_audit_event, get_client_ip

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return tokens."""
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        # Log failed login attempt
        if user:
            await log_audit_event(
                db=db,
                action="login_failed",
                category="security",
                organization_id=user.organization_id,
                user_id=user.id,
                user_email=user.email,
                description="Failed login attempt - invalid password",
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:500],
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        await log_audit_event(
            db=db,
            action="login_failed",
            category="security",
            organization_id=user.organization_id,
            user_id=user.id,
            user_email=user.email,
            description="Failed login attempt - account disabled",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        role=user.role
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        role=user.role
    )

    # Log successful login
    await log_audit_event(
        db=db,
        action="login_success",
        category="security",
        organization_id=user.organization_id,
        user_id=user.id,
        user_email=user.email,
        user_name=user.full_name,
        description="User logged in successfully",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == payload.sub)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        role=user.role
    )
    new_refresh_token = create_refresh_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        role=user.role
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user info."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one()

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        organization_id=current_user.organization_id,
        organization_name=org.name,
        is_active=current_user.is_active,
        avatar_url=current_user.avatar_url
    )


@router.post("/change-password")
@limiter.limit("3/minute")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        await log_audit_event(
            db=db,
            action="password_change_failed",
            category="security",
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            user_email=current_user.email,
            description="Password change failed - incorrect current password",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)

    await log_audit_event(
        db=db,
        action="password_changed",
        category="security",
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name,
        description="User changed their password",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    await db.commit()

    return {"message": "Password changed successfully"}


@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/minute")
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new organization and admin user."""
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == register_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization
    org_slug = register_data.organization_name.lower().replace(" ", "-")
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    if result.scalar_one_or_none():
        org_slug = f"{org_slug}-{int(datetime.now().timestamp())}"

    org = Organization(
        name=register_data.organization_name,
        slug=org_slug,
        org_type=register_data.organization_type
    )
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        email=register_data.email,
        hashed_password=get_password_hash(register_data.password),
        first_name=register_data.first_name,
        last_name=register_data.last_name,
        role="admin",
        organization_id=org.id,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.flush()

    # Log registration
    await log_audit_event(
        db=db,
        action="user_registered",
        category="security",
        organization_id=org.id,
        user_id=user.id,
        user_email=user.email,
        user_name=f"{user.first_name} {user.last_name}",
        entity_type="organization",
        entity_id=org.id,
        entity_name=org.name,
        description=f"New organization '{org.name}' and admin user registered",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    await db.commit()

    # Generate tokens
    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(org.id),
        role=user.role
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        org_id=str(org.id),
        role=user.role
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


from datetime import datetime
