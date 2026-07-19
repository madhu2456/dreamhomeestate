"""Publication router — campaign creation, job lifecycle actions."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, get_organization, require_role
from app.models import JobStatus, MembershipRole, Organization
from app.repositories.publication import (
    PublicationCampaignRepository,
    PublicationJobRepository,
)
from app.schemas.publication import (
    AttemptOut,
    CreateCampaignRequest,
    CreateQuickPostRequest,
    JobActionResponse,
    PublicationCampaignOut,
    PublicationJobOut,
)
from app.services.audit import AuditService
from app.services.publication import PublicationService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["publications"])


# ─── Campaigns ──────────────────────────────────────────────────────


@router.get("/campaigns", response_model=list[PublicationCampaignOut])
async def list_campaigns(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: JobStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PublicationCampaignOut]:
    repo = PublicationCampaignRepository(db)
    campaigns = await repo.list_for_org(
        org_id=org.id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [PublicationCampaignOut.model_validate(c) for c in campaigns]


@router.post("/campaigns", response_model=PublicationCampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CreateCampaignRequest,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)),
) -> PublicationCampaignOut:
    svc = PublicationService(db)
    try:
        campaign = await svc.create_campaign(
            org_id=org.id,
            listing_id=body.listing_id,
            created_by=current_user.id if current_user else None,
            auto_distribute=body.auto_distribute,
            scheduled_at=body.scheduled_at,
            account_overrides=body.account_overrides,
            social_account_ids=body.social_account_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Audit: campaign.created
    audit_svc = AuditService(db)
    await audit_svc.log_campaign_action(
        org_id=org.id,
        user_id=current_user.id,
        campaign_id=campaign.id,
        action="campaign.created",
        details={
            "listing_id": str(body.listing_id),
            "social_account_ids": [str(i) for i in (body.social_account_ids or [])],
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return PublicationCampaignOut.model_validate(campaign)


@router.post(
    "/quick-posts",
    response_model=PublicationCampaignOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_quick_post(
    body: CreateQuickPostRequest,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> PublicationCampaignOut:
    """Compose a freeform multi-account post (caption + media URLs)."""
    svc = PublicationService(db)
    try:
        campaign = await svc.create_quick_post(
            org_id=org.id,
            body=body.body,
            media_urls=body.media_urls,
            social_account_ids=body.social_account_ids,
            title=body.title,
            created_by=current_user.id if current_user else None,
            auto_distribute=body.auto_distribute,
            scheduled_at=body.scheduled_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        msg = str(exc)
        logger.exception("quick_post_create_failed", error=msg)
        # Detect real schema problems only (avoid false positives on any error
        # that merely mentions "listing_id" in a stack/SQL fragment).
        low = msg.lower()
        schema_hint = (
            ("undefinedcolumn" in low and "publication_campaigns" in low)
            or ("column" in low and "campaign_kind" in low and "does not exist" in low)
            or (
                "null value in column" in low
                and "listing_id" in low
                and "publication_campaigns" in low
            )
            or ("notnullviolation" in low and "listing_id" in low)
        )
        if schema_hint:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Quick-post schema incomplete: listing_id must be NULLABLE and "
                    "campaign_kind/body/media_urls must exist. On the server run:\n"
                    "docker compose -f docker-compose.prod.yml exec -T postgres "
                    "psql -U postgres -d realestate -c "
                    "\"ALTER TABLE publication_campaigns ALTER COLUMN listing_id DROP NOT NULL;\""
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create quick post: {msg[:500]}",
        ) from exc

    audit_svc = AuditService(db)
    await audit_svc.log_campaign_action(
        org_id=org.id,
        user_id=current_user.id,
        campaign_id=campaign.id,
        action="campaign.quick_post_created",
        details={
            "account_count": len(body.social_account_ids),
            "media_count": len(body.media_urls),
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        return PublicationCampaignOut.model_validate(campaign)
    except Exception as exc:
        logger.exception("quick_post_response_validate_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick post saved but response failed: {exc!s}"[:500],
        ) from exc


@router.get("/campaigns/{campaign_id}", response_model=PublicationCampaignOut)
async def get_campaign(
    campaign_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicationCampaignOut:
    repo = PublicationCampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    if not campaign or campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return PublicationCampaignOut.model_validate(campaign)


# ─── Jobs ───────────────────────────────────────────────────────────


@router.get("/jobs", response_model=list[PublicationJobOut])
async def list_jobs(
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: JobStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PublicationJobOut]:
    repo = PublicationJobRepository(db)
    jobs = await repo.list_for_org(
        org_id=org.id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [PublicationJobOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=PublicationJobOut)
async def get_job(
    job_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicationJobOut:
    repo = PublicationJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job or job.campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return PublicationJobOut.model_validate(job)


@router.post("/jobs/{job_id}/approve", response_model=JobActionResponse)
async def approve_job(
    job_id: uuid.UUID,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> JobActionResponse:
    repo = PublicationJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job or job.campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    svc = PublicationService(db)
    try:
        job = await svc.approve_job(job, approved_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Audit: job.approved
    audit_svc = AuditService(db)
    await audit_svc.log_campaign_action(
        org_id=org.id,
        user_id=current_user.id,
        campaign_id=job.campaign_id,
        action="job.approved",
        details={"job_id": str(job_id), "campaign_id": str(job.campaign_id)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return JobActionResponse(id=job.id, status=job.status, message="Job approved")


@router.post("/jobs/{job_id}/reject", response_model=JobActionResponse)
async def reject_job(
    job_id: uuid.UUID,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> JobActionResponse:
    repo = PublicationJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job or job.campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    svc = PublicationService(db)
    try:
        job = await svc.reject_job(job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Audit: job.rejected
    audit_svc = AuditService(db)
    await audit_svc.log_campaign_action(
        org_id=org.id,
        user_id=current_user.id,
        campaign_id=job.campaign_id,
        action="job.rejected",
        details={"job_id": str(job_id), "campaign_id": str(job.campaign_id)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return JobActionResponse(id=job.id, status=job.status, message="Job rejected")


@router.post("/jobs/{job_id}/retry", response_model=JobActionResponse)
async def retry_job(
    job_id: uuid.UUID,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> JobActionResponse:
    repo = PublicationJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job or job.campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    svc = PublicationService(db)
    try:
        job = await svc.retry_job(job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Audit: job.retried
    audit_svc = AuditService(db)
    await audit_svc.log_campaign_action(
        org_id=org.id,
        user_id=current_user.id,
        campaign_id=job.campaign_id,
        action="job.retried",
        details={"job_id": str(job_id), "campaign_id": str(job.campaign_id)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return JobActionResponse(id=job.id, status=job.status, message="Job queued for retry")


@router.post("/jobs/{job_id}/cancel", response_model=JobActionResponse)
async def cancel_job(
    job_id: uuid.UUID,
    request: Request,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    _membership=Depends(require_role(MembershipRole.owner, MembershipRole.administrator)),
) -> JobActionResponse:
    repo = PublicationJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job or job.campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    svc = PublicationService(db)
    try:
        job = await svc.cancel_job(job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Audit: job.cancelled
    audit_svc = AuditService(db)
    await audit_svc.log_campaign_action(
        org_id=org.id,
        user_id=current_user.id,
        campaign_id=job.campaign_id,
        action="job.cancelled",
        details={"job_id": str(job_id), "campaign_id": str(job.campaign_id)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return JobActionResponse(id=job.id, status=job.status, message="Job cancelled")


# ─── Attempts ──────────────────────────────────────────────────────


@router.get("/jobs/{job_id}/attempts", response_model=list[AttemptOut])
async def list_attempts(
    job_id: uuid.UUID,
    org: Annotated[Organization, Depends(get_organization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttemptOut]:
    repo = PublicationJobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job or job.campaign.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    from app.repositories.publication import PublicationAttemptRepository

    attempt_repo = PublicationAttemptRepository(db)
    attempts = await attempt_repo.list_for_job(job_id)
    return [AttemptOut.model_validate(a) for a in attempts]
