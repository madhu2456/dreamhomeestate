"""Audit log router — read-only access for org owners and admins."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_organization, require_role
from app.models import MembershipRole, Organization
from app.repositories.audit import AuditLogRepository
from app.schemas.audit import AuditLogEntryOut

router = APIRouter(tags=["audit"])


@router.get("", response_model=list[AuditLogEntryOut])
async def list_audit_log(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
    action: str | None = Query(default=None),
    after: str | None = Query(default=None),
    before: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLogEntryOut]:
    """List audit log entries for the organization.  Owner/Admin only."""
    repo = AuditLogRepository(db)
    entries = await repo.list_for_org(
        org_id=org.id,
        action=action,
        before=before,
        after=after,
        limit=limit,
        offset=offset,
    )
    return [AuditLogEntryOut.model_validate(e) for e in entries]
