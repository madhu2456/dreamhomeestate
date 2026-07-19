"""Auth-related schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut
from app.schemas.organization import OrganizationMemberOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user: UserOut
    memberships: list[OrganizationMemberOut]


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[OrganizationMemberOut]


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    detail: str
