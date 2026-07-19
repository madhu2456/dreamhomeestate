"""FastAPI dependencies for auth session, current user, role checks, organization scoping."""

import uuid
from typing import Annotated, Sequence

import structlog
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    Session,
    User,
)
from app.security import hash_token, unsign_session_id
from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


async def _get_session_token(request: Request) -> str | None:
    """Extract session token from cookie or Authorization Bearer header (for API clients)."""
    # Try cookie first
    cookie = request.cookies.get(settings.session_cookie_name)
    if cookie:
        return cookie

    # Try Bearer token
    auth: str = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]

    return None


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """FastAPI dependency: validates session cookie/token and returns the authenticated User."""
    token = await _get_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session_id_str = unsign_session_id(token, max_age=settings.session_max_age_seconds)
    if not session_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    token_hash = hash_token(token)
    result = await db.execute(
        select(Session)
        .options(joinedload(Session.user))
        .where(Session.token_hash == token_hash)
    )
    session_record = result.scalar_one_or_none()

    if session_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )

    user = session_record.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    request.state.current_user = user
    request.state.session_id = session_record.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _get_org_id_from_request(request: Request) -> str | None:
    """Read organization id from path or query parameters."""
    return request.path_params.get("org_id") or request.query_params.get("org_id")


class RoleChecker:
    """Dependency factory that checks the current user has one of the allowed roles
    for the organization identified by `org_id` path or query parameter."""

    def __init__(self, *allowed_roles: MembershipRole | str):
        self.allowed_roles: set[str] = {
            r.value if isinstance(r, MembershipRole) else r
            for r in allowed_roles
        }

    async def __call__(
        self,
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> OrganizationMembership:
        org_id = _get_org_id_from_request(request)
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization identifier required",
            )

        try:
            org_uuid = uuid.UUID(org_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID",
            )

        result = await db.execute(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.organization_id == org_uuid,
            )
        )
        membership = result.scalar_one_or_none()

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )

        if membership.role.value not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )

        return membership


def require_role(*allowed: MembershipRole | str) -> RoleChecker:
    """FastAPI dependency factory: require the current user to have one of the given roles."""
    return RoleChecker(*allowed)


async def get_organization(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Organization:
    """FastAPI dependency: load organization and verify current user is a member.

    Supports `org_id` as a path parameter (e.g. /organizations/{org_id}) or as a
    query parameter for routes where the organization is specified by the caller.
    """
    org_id = _get_org_id_from_request(request)
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization identifier required",
        )

    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID",
        )

    org_result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    membership_result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == org_uuid,
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    return org


def is_owner_or_admin(membership: OrganizationMembership) -> bool:
    return membership.role in (MembershipRole.owner, MembershipRole.administrator)


def is_owner(membership: OrganizationMembership) -> bool:
    return membership.role == MembershipRole.owner
