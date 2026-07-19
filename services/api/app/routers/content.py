"""Content template CRUD and preview router."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, get_organization, require_role
from app.models import MembershipRole, Organization, ProviderEnum
from app.repositories.content import ContentTemplateRepository
from app.repositories.listing import ListingRepository
from app.schemas.content import (
    ContentTemplateCreate,
    ContentTemplateOut,
    ContentTemplateUpdate,
    PreviewDryRunRequest,
    PreviewRequest,
    PreviewResponse,
)
from app.services.audit import AuditService
from app.services.content_builder import build_variables
from app.services.content_renderer import (
    calculate_length,
    render_for_platform,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["content"])


# ─── Template CRUD ──────────────────────────────────────────────────


@router.get("/templates", response_model=list[ContentTemplateOut])
async def list_templates(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    platform: ProviderEnum | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ContentTemplateOut]:
    repo = ContentTemplateRepository(db)
    templates = await repo.list_for_org(
        org_id=org.id,
        platform=platform,
        limit=limit,
        offset=offset,
    )
    return [ContentTemplateOut.model_validate(t) for t in templates]


@router.post("/templates", response_model=ContentTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: ContentTemplateCreate,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)),
) -> ContentTemplateOut:
    repo = ContentTemplateRepository(db)
    fields = body.model_dump()
    template = await repo.create(org_id=org.id, **fields)

    # Audit: template.created
    audit_svc = AuditService(db)
    await audit_svc.log_action(
        organization_id=org.id,
        user_id=current_user.id,
        action="template.created",
        entity_type="template",
        entity_id=template.id,
        details={"name": template.name, "platform": template.platform.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ContentTemplateOut.model_validate(template)


@router.get("/templates/{template_id}", response_model=ContentTemplateOut)
async def get_template(
    template_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContentTemplateOut:
    repo = ContentTemplateRepository(db)
    template = await repo.get_by_id(org_id=org.id, template_id=template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return ContentTemplateOut.model_validate(template)


@router.patch("/templates/{template_id}", response_model=ContentTemplateOut)
async def update_template(
    template_id: uuid.UUID,
    body: ContentTemplateUpdate,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)),
) -> ContentTemplateOut:
    repo = ContentTemplateRepository(db)
    template = await repo.get_by_id(org_id=org.id, template_id=template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    template = await repo.update(template, **fields)

    # Audit: template.updated
    audit_svc = AuditService(db)
    await audit_svc.log_action(
        organization_id=org.id,
        user_id=current_user.id,
        action="template.updated",
        entity_type="template",
        entity_id=template.id,
        details={"changed_fields": list(fields.keys())},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ContentTemplateOut.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> None:
    repo = ContentTemplateRepository(db)
    template = await repo.get_by_id(org_id=org.id, template_id=template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    audit_name = template.name
    await repo.delete(template)

    # Audit: template.deleted
    audit_svc = AuditService(db)
    await audit_svc.log_action(
        organization_id=org.id,
        user_id=current_user.id,
        action="template.deleted",
        entity_type="template",
        entity_id=template_id,
        details={"name": audit_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ─── Preview ────────────────────────────────────────────────────────


@router.post("/preview", response_model=PreviewResponse)
async def preview_listing_with_template(
    body: PreviewRequest,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)),
) -> PreviewResponse:
    listing_repo = ListingRepository(db)
    listing = await listing_repo.get_by_id(org_id=org.id, listing_id=body.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    template_repo = ContentTemplateRepository(db)
    template = await template_repo.get_by_id(org_id=org.id, template_id=body.template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    variables = build_variables(listing)
    render_result = render_for_platform(
        body_template=template.body_template,
        variables=variables,
        platform=template.platform,
        title_template=template.title_template,
        campaign_tag=template.campaign_tag,
    )

    length, max_len, exceeded = calculate_length(render_result.body, template.platform)

    return PreviewResponse(
        title=render_result.title,
        body=render_result.body,
        platform=template.platform,
        warnings=render_result.warnings,
        errors=render_result.errors,
        length=length,
        max_length=max_len,
        length_exceeded=exceeded,
    )


@router.post("/preview/dry-run", response_model=PreviewResponse)
async def preview_dry_run(
    body: PreviewDryRunRequest,
    _org: Annotated[Organization, Depends(get_organization)],
    _current_user: CurrentUser,
) -> PreviewResponse:
    render_result = render_for_platform(
        body_template=body.body_template,
        variables=body.variables,
        platform=body.platform,
        title_template=body.title_template,
    )

    length, max_len, exceeded = calculate_length(render_result.body, body.platform)

    return PreviewResponse(
        title=render_result.title,
        body=render_result.body,
        platform=body.platform,
        warnings=render_result.warnings,
        errors=render_result.errors,
        length=length,
        max_length=max_len,
        length_exceeded=exceeded,
    )
