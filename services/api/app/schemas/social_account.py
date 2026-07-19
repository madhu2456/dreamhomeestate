"""Pydantic schemas for social account connections."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SocialAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    provider: str
    provider_account_id: str
    display_name: str | None = None
    username: str | None = None
    profile_image_url: str | None = None
    account_type: str | None = None
    connection_status: str
    granted_scopes: list[str] | None = None
    is_default_destination: bool
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None
    capabilities_snapshot: dict[str, Any] | None = None


class OAuthConnectRequest(BaseModel):
    redirect_after: str = "/admin/social-accounts"


class OAuthConnectResponse(BaseModel):
    authorization_url: str | None = None
    mock: bool = False
    account: SocialAccountOut | None = None


class OAuthCallbackResponse(BaseModel):
    message: str
    provider: str
    account_id: str | None = None
