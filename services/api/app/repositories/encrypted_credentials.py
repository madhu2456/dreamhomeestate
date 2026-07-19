"""Repository for EncryptedOAuthCredentials operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EncryptedOAuthCredentials


class EncryptedCredentialsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(
        self,
        social_account_id: uuid.UUID,
        access_token: str,
        *,
        refresh_token: str | None = None,
        token_type: str | None = None,
        scope: str | None = None,
        expires_at: datetime | None = None,
    ) -> EncryptedOAuthCredentials:
        from app.services.encryption import encrypt_text

        result = await self.db.execute(
            select(EncryptedOAuthCredentials).where(
                EncryptedOAuthCredentials.social_account_id == social_account_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.encrypted_access_token = encrypt_text(access_token)
            # Only overwrite refresh_token when a new one is provided (X may rotate)
            if refresh_token:
                existing.encrypted_refresh_token = encrypt_text(refresh_token)
            if token_type is not None:
                existing.token_type = token_type
            if scope is not None:
                existing.scope = scope
            if expires_at is not None:
                existing.expires_at = expires_at
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        creds = EncryptedOAuthCredentials(
            social_account_id=social_account_id,
            encrypted_access_token=encrypt_text(access_token),
            encrypted_refresh_token=(
                encrypt_text(refresh_token) if refresh_token else None
            ),
            token_type=token_type,
            scope=scope,
            expires_at=expires_at,
        )
        self.db.add(creds)
        await self.db.flush()
        await self.db.refresh(creds)
        return creds

    async def get_by_social_account_id(
        self, social_account_id: uuid.UUID
    ) -> EncryptedOAuthCredentials | None:
        result = await self.db.execute(
            select(EncryptedOAuthCredentials).where(
                EncryptedOAuthCredentials.social_account_id == social_account_id
            )
        )
        return result.scalar_one_or_none()
