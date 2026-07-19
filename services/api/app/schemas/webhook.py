"""Webhook response schemas."""

from pydantic import BaseModel


class WebhookResponse(BaseModel):
    status: str = "ok"
