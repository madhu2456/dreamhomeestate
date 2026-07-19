"""Organization schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    logo_url: str | None = None
    contact_fields: dict | None = None
    default_currency: str = "USD"
    timezone: str = "UTC"
    language: str = "en"
    website_domain: str | None = None
    legal_disclaimer: str | None = None
    default_social_rules: dict | None = None


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    contact_fields: dict | None = None
    default_currency: str
    timezone: str
    language: str
    website_domain: str | None = None
    legal_disclaimer: str | None = None
    default_social_rules: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMemberOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class AddMemberIn(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern="^(owner|administrator|editor|viewer)$")
    password: str | None = Field(default=None, min_length=8, max_length=128)
