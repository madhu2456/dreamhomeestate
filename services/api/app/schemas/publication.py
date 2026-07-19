"""Publication schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

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
    listing_id: uuid.UUID | None = None
    listing_version_id: uuid.UUID | None = None
    campaign_kind: str = "listing"
    title: str | None = None
    body: str | None = None
    media_urls: list[str] | None = None
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
    # If omitted/empty → all active Instagram/X accounts
    social_account_ids: list[uuid.UUID] | None = None


class CreateQuickPostRequest(BaseModel):
    """Freeform multi-account post (images/video URLs + caption)."""

    body: str = Field(default="", max_length=2200)
    title: str | None = Field(default=None, max_length=255)
    media_urls: list[str] = Field(default_factory=list)
    social_account_ids: list[uuid.UUID] = Field(min_length=1)
    auto_distribute: bool = False
    scheduled_at: datetime | None = None

    @model_validator(mode="after")
    def _require_content(self) -> "CreateQuickPostRequest":
        urls = [u for u in self.media_urls if u and str(u).strip()]
        if not self.body.strip() and not urls:
            raise ValueError("Provide caption text and/or at least one media URL")
        object.__setattr__(self, "media_urls", urls)
        return self


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
