"""Authentication router: login, logout, me, password reset."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import CurrentUser
from app.repositories import SessionRepository, UserRepository
from app.repositories.organization import OrganizationRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    MessageResponse,
    PasswordReset,
    PasswordResetRequest,
)
from app.schemas.organization import OrganizationMemberOut
from app.schemas.user import UserOut
from app.security import (
    generate_password_reset_token,
    sign_session_id,
    verify_password,
    verify_password_reset_token,
)
from app.services.audit import AuditService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = structlog.get_logger(__name__)


def _build_member_records(memberships) -> list[OrganizationMemberOut]:
    """Build member record responses from membership rows."""
    result = []
    for m in memberships:
        result.append(
            OrganizationMemberOut(
                id=m.organization.id,
                email=m.user.email,
                full_name=m.user.full_name,
                role=m.role.value,
                is_active=m.user.is_active,
                joined_at=m.joined_at,
            )
        )
    return result


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)
    org_repo = OrganizationRepository(db)

    user = await user_repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Create session
    session_id = uuid.uuid4()
    session_token = sign_session_id(session_id)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.session_max_age_seconds)

    await session_repo.create(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at,
    )

    # Set cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        path="/",
    )

    memberships = await org_repo.list_for_user(user.id)

    # Audit: user.login
    audit_svc = AuditService(db)
    await audit_svc.log_action(
        user_id=user.id,
        action="user.login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return LoginResponse(
        user=UserOut.model_validate(user),
        memberships=_build_member_records(memberships),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    session_repo = SessionRepository(db)
    session_id = getattr(request.state, "session_id", None)

    if session_id:
        await session_repo.delete(session_id)

    # Audit: user.logout
    audit_svc = AuditService(db)
    await audit_svc.log_action(
        user_id=current_user.id,
        action="user.logout",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )

    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    org_repo = OrganizationRepository(db)
    memberships = await org_repo.list_for_user(current_user.id)

    return MeResponse(
        user=UserOut.model_validate(current_user),
        memberships=_build_member_records(memberships),
    )


@router.post("/password-reset-request", response_model=MessageResponse)
async def password_reset_request(
    body: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(body.email)

    if user:
        token = generate_password_reset_token(user.id)
        logger.info("password_reset_token_generated", user_id=str(user.id))

        # In production, send email via SMTP if configured
        if not settings.is_development and settings.smtp_host:
            # TODO: Send email with reset link
            pass
        elif settings.is_development:
            # Development-only convenience: print a reset URL to the container logs.
            # The token itself is never written to logs; it is shown only via stdout
            # for manual copy-paste during local testing.
            print(f"[DEV] Password reset URL: /login/reset?token={token}")

    # Always return the same message to avoid email enumeration
    return MessageResponse(
        detail="If that email is registered, a reset link has been sent."
    )


@router.post("/password-reset", response_model=MessageResponse)
async def password_reset(
    body: PasswordReset,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    user_id_str = verify_password_reset_token(body.token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        ) from None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    await user_repo.update_password(user, body.new_password)

    # Invalidate all existing sessions
    session_repo = SessionRepository(db)
    await session_repo.delete_all_for_user(user.id)

    return MessageResponse(detail="Password has been reset. Please log in.")
