"""Repository for publication entities."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    JobStatus,
    PublicationAttempt,
    PublicationCampaign,
    PublicationJob,
    PublicationOutbox,
)


class PublicationCampaignRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, campaign_id: uuid.UUID) -> PublicationCampaign | None:
        result = await self.db.execute(
            select(PublicationCampaign).where(PublicationCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        status: JobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PublicationCampaign]:
        stmt = select(PublicationCampaign).where(
            PublicationCampaign.organization_id == org_id,
        )
        if status is not None:
            stmt = stmt.where(PublicationCampaign.status == status)
        stmt = stmt.order_by(PublicationCampaign.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        org_id: uuid.UUID,
        listing_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
        listing_version_id: uuid.UUID | None = None,
        auto_distribute: bool = False,
        account_overrides: dict | None = None,
    ) -> PublicationCampaign:
        campaign = PublicationCampaign(
            organization_id=org_id,
            listing_id=listing_id,
            created_by=created_by,
            listing_version_id=listing_version_id,
            auto_distribute=auto_distribute,
            account_overrides=account_overrides,
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def update_status(self, campaign: PublicationCampaign, status: JobStatus) -> PublicationCampaign:
        campaign.status = status
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign


class PublicationJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: uuid.UUID) -> PublicationJob | None:
        from sqlalchemy.orm import joinedload, selectinload

        from app.models import SocialAccount

        result = await self.db.execute(
            select(PublicationJob)
            .where(PublicationJob.id == job_id)
            .options(
                joinedload(PublicationJob.campaign),
                joinedload(PublicationJob.social_account).selectinload(
                    SocialAccount.credentials
                ),
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_for_campaign(self, campaign_id: uuid.UUID) -> list[PublicationJob]:
        result = await self.db.execute(
            select(PublicationJob).where(
                PublicationJob.campaign_id == campaign_id,
            ).order_by(PublicationJob.created_at)
        )
        return list(result.scalars().all())

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        status: JobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PublicationJob]:
        from sqlalchemy.orm import joinedload

        stmt = (
            select(PublicationJob)
            .join(PublicationCampaign)
            .where(PublicationCampaign.organization_id == org_id)
            .options(joinedload(PublicationJob.campaign))
        )
        if status is not None:
            stmt = stmt.where(PublicationJob.status == status)
        stmt = stmt.order_by(PublicationJob.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        campaign_id: uuid.UUID,
        social_account_id: uuid.UUID,
        template_id: uuid.UUID | None,
        idempotency_key: str,
        scheduled_at: datetime | None = None,
    ) -> PublicationJob:
        job = PublicationJob(
            campaign_id=campaign_id,
            social_account_id=social_account_id,
            template_id=template_id,
            idempotency_key=idempotency_key,
            scheduled_at=scheduled_at,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def update_status(self, job: PublicationJob, status: JobStatus, **extra) -> PublicationJob:
        job.status = status
        for key, value in extra.items():
            setattr(job, key, value)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def find_by_idempotency_key(self, key: str) -> PublicationJob | None:
        result = await self.db.execute(
            select(PublicationJob).where(PublicationJob.idempotency_key == key)
        )
        return result.scalar_one_or_none()


class PublicationAttemptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        job_id: uuid.UUID,
        attempt_number: int,
        status: str,
        request_payload: dict | None = None,
        response_payload: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> PublicationAttempt:
        attempt = PublicationAttempt(
            job_id=job_id,
            attempt_number=attempt_number,
            status=status,
            request_payload=request_payload,
            response_payload=response_payload,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.db.add(attempt)
        await self.db.flush()
        await self.db.refresh(attempt)
        return attempt

    async def list_for_job(self, job_id: uuid.UUID) -> list[PublicationAttempt]:
        result = await self.db.execute(
            select(PublicationAttempt).where(
                PublicationAttempt.job_id == job_id,
            ).order_by(PublicationAttempt.attempt_number)
        )
        return list(result.scalars().all())


class PublicationOutboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: dict,
        organization_id: uuid.UUID | None = None,
    ) -> PublicationOutbox:
        entry = PublicationOutbox(
            organization_id=organization_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_pending(self, limit: int = 100) -> list[PublicationOutbox]:
        result = await self.db.execute(
            select(PublicationOutbox).where(
                PublicationOutbox.status == "pending",
            ).order_by(PublicationOutbox.created_at).limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processed(self, entry: PublicationOutbox) -> None:
        entry.status = "processed"
        entry.processed_at = datetime.utcnow()
        await self.db.flush()

    async def mark_failed(self, entry: PublicationOutbox) -> None:
        entry.status = "failed"
        await self.db.flush()
