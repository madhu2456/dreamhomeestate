"""Audit log schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogEntryOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    details: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
