"""Users router: list/create users within an organization scope."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_organization, require_role
from app.models import MembershipRole, Organization, User
from app.repositories import UserRepository
from app.repositories.organization import OrganizationRepository
from app.schemas.user import UserCreateInOrg, UserOut

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger(__name__)


def _user_to_out(user: User) -> UserOut:
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
async def list_users(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> list[UserOut]:
    """List all users belonging to the organization. Owner/Admin only."""
    org_repo = OrganizationRepository(db)
    memberships = await org_repo.list_members(org.id)
    # Ensure memberships have user loaded
    users = [m.user for m in memberships if m.user is not None]
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateInOrg,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> UserOut:
    """Invite/create a user and add them to the organization. Owner/Admin only."""
    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)

    # Check if user already exists
    existing_user = await user_repo.get_by_email(body.email)

    if existing_user:
        # Check if already a member
        existing_membership = await org_repo.get_membership(org.id, existing_user.id)
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization",
            )
        user = existing_user
    else:
        # Create new user — generate temp password if none provided
        password = body.password or _generate_temp_password()
        user = await user_repo.create(
            email=body.email,
            full_name=body.full_name,
            password=password,
            is_active=True,
        )
        logger.info("user_created", user_id=str(user.id), email=user.email)

    # Add membership
    role = MembershipRole(body.role)
    await org_repo.add_member(org, user, role)
    logger.info(
        "member_added",
        org_id=str(org.id),
        user_id=str(user.id),
        role=body.role,
    )

    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> UserOut:
    """Get a single user within the organization scope."""
    import uuid as uuid_mod

    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID") from None

    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)

    # Ensure membership exists
    membership = await org_repo.get_membership(org.id, user_uuid)
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in organization")

    user = await user_repo.get_by_id(user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserOut.model_validate(user)


def _generate_temp_password(length: int = 16) -> str:
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
