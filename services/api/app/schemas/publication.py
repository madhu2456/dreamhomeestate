"""Publication schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import JobStatus


class PublicationJobOut(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    social_account_id: uuid.UUID
    template_id: uuid.UUID | None = None
    idempotency_key: str
    status: JobStatus
    rendered_title: str | None = None
    rendered_body: str | None = None
    media_urls: list[str] | None = None
    content_items: list[dict] | None = None
    scheduled_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: uuid.UUID | None = None
    published_at: datetime | None = None
    provider_job_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublicationCampaignOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    listing_id: uuid.UUID
    listing_version_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    status: JobStatus
    auto_distribute: bool = False
    account_overrides: dict | None = None
    created_at: datetime
    updated_at: datetime
    jobs: list[PublicationJobOut] = []

    model_config = {"from_attributes": True}


class CreateCampaignRequest(BaseModel):
    listing_id: uuid.UUID
    auto_distribute: bool = False
    scheduled_at: datetime | None = None
    account_overrides: dict[str, dict] | None = None


class JobActionResponse(BaseModel):
    id: uuid.UUID
    status: JobStatus
    message: str = ""


class AttemptOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    attempt_number: int
    status: str
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
