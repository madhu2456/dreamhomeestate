"""Content template and preview schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import ProviderEnum


class ContentTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scope: str | None = Field(default=None, max_length=100)
    platform: ProviderEnum
    language: str = "en"
    campaign_tag: str | None = Field(default=None, max_length=100)
    title_template: str | None = None
    body_template: str
    variables: list[str] = []
    is_default: bool = False


class ContentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    scope: str | None = Field(default=None, max_length=100)
    platform: ProviderEnum | None = None
    language: str | None = None
    campaign_tag: str | None = Field(default=None, max_length=100)
    title_template: str | None = None
    body_template: str | None = None
    variables: list[str] | None = None
    is_default: bool | None = None


class ContentTemplateOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    scope: str | None = None
    platform: ProviderEnum
    language: str
    campaign_tag: str | None = None
    title_template: str | None = None
    body_template: str
    variables: list[str] = []
    is_default: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PreviewRequest(BaseModel):
    listing_id: uuid.UUID
    template_id: uuid.UUID


class PreviewResponse(BaseModel):
    title: str | None = None
    body: str
    platform: ProviderEnum
    warnings: list[str] = []
    errors: list[str] = []
    length: int = 0
    max_length: int | None = None
    length_exceeded: bool = False


class PreviewDryRunRequest(BaseModel):
    body_template: str
    title_template: str | None = None
    platform: ProviderEnum = ProviderEnum.mock
    variables: dict[str, str] = {}
