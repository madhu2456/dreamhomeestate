"""Organizations router: CRUD for organizations and membership management."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    CurrentUser,
    get_organization,
    require_role,
)
from app.models import MembershipRole, Organization
from app.repositories import UserRepository
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import (
    AddMemberIn,
    OrganizationCreate,
    OrganizationMemberOut,
    OrganizationOut,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])
logger = structlog.get_logger(__name__)


@router.get("", response_model=list[OrganizationOut])
async def list_organizations(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationOut]:
    """List all organizations the current user is a member of."""
    org_repo = OrganizationRepository(db)
    memberships = await org_repo.list_for_user(current_user.id)
    orgs = [m.organization for m in memberships if m.organization is not None]
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationOut:
    """Create a new organization. The creating user becomes owner."""
    org_repo = OrganizationRepository(db)

    # Check slug uniqueness
    existing = await org_repo.get_by_slug(body.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this slug already exists",
        )

    org = await org_repo.create(
        name=body.name,
        slug=body.slug,
        logo_url=body.logo_url,
        contact_fields=body.contact_fields,
        default_currency=body.default_currency,
        timezone=body.timezone,
        language=body.language,
        website_domain=body.website_domain,
        legal_disclaimer=body.legal_disclaimer,
        default_social_rules=body.default_social_rules,
    )

    # Add creator as owner
    await org_repo.add_member(org, current_user, MembershipRole.owner)

    logger.info(
        "organization_created",
        org_id=str(org.id),
        slug=org.slug,
        user_id=str(current_user.id),
    )

    return OrganizationOut.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_org(
    org: Annotated[Organization, Depends(get_organization)],
) -> OrganizationOut:
    """Get organization details. Any member can view."""
    return OrganizationOut.model_validate(org)


@router.get("/{org_id}/members", response_model=list[OrganizationMemberOut])
async def list_members(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> list[OrganizationMemberOut]:
    """List all members of an organization. Owner/Admin only."""
    org_repo = OrganizationRepository(db)
    memberships = await org_repo.list_members(org.id)

    result = []
    for m in memberships:
        if m.user is not None:
            result.append(
                OrganizationMemberOut(
                    id=m.user.id,
                    email=m.user.email,
                    full_name=m.user.full_name,
                    role=m.role.value,
                    is_active=m.user.is_active,
                    joined_at=m.joined_at,
                )
            )
    return result


@router.post("/{org_id}/members", response_model=OrganizationMemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    body: AddMemberIn,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> OrganizationMemberOut:
    """Add an existing user to the organization, or create+add. Owner/Admin only."""
    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)

    existing_user = await user_repo.get_by_email(body.email)

    if existing_user:
        existing_membership = await org_repo.get_membership(org.id, existing_user.id)
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member",
            )
        user = existing_user
    else:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = body.password or "".join(secrets.choice(alphabet) for _ in range(16))
        user = await user_repo.create(
            email=body.email,
            full_name=body.full_name,
            password=password,
        )

    role = MembershipRole(body.role)
    membership = await org_repo.add_member(org, user, role)

    return OrganizationMemberOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role.value,
        is_active=user.is_active,
        joined_at=membership.joined_at,
    )
