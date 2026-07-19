"""Feature flags API — read-only endpoints for client-side feature evaluation.

- ``GET /api/v1/organizations/{org_id}/feature-flags`` — scoped to an org
  (requires membership).
- ``GET /api/v1/feature-flags`` — global, no auth (for build-time checks).
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_organization
from app.models import Organization
from app.services.feature_flags import get_feature_flags

router = APIRouter(tags=["feature-flags"])


@router.get("/organizations/{org_id}/feature-flags")
async def get_org_feature_flags(
    org: Annotated[Organization, Depends(get_organization)],
) -> dict[str, bool]:
    """Return all known feature flags for an organization.

    Requires the caller to be a member of the organization.
    """
    svc = get_feature_flags()
    return svc.list_flags(org_id=str(org.id))


@router.get("/feature-flags")
async def get_global_feature_flags() -> dict[str, bool]:
    """Return global feature flags (no authentication required).

    Suitable for build-time or pre-login checks.
    """
    svc = get_feature_flags()
    return svc.list_flags()
