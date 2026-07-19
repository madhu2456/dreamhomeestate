"""User schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    """Public-safe user representation. Never includes password_hash or tokens."""
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Payload for creating a standalone user (CLI or service)."""
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserCreateInOrg(BaseModel):
    """Payload for creating a user within an organization scope."""
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str = Field(default="viewer", pattern="^(owner|administrator|editor|viewer)$")
