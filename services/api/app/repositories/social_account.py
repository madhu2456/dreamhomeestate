"""Repository for SocialAccount CRUD."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AccountConnectionStatus,
    ProviderEnum,
    SocialAccount,
)


class SocialAccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, account_id: uuid.UUID) -> SocialAccount | None:
        result = await self.db.execute(
            select(SocialAccount).where(SocialAccount.id == account_id)
        )
        return result.scalar_one_or_none()

    async def list_for_org(self, org_id: uuid.UUID) -> list[SocialAccount]:
        result = await self.db.execute(
            select(SocialAccount).where(SocialAccount.organization_id == org_id)
        )
        return list(result.scalars().all())

    async def get_by_provider_account(
        self, org_id: uuid.UUID, provider: str, provider_account_id: str
    ) -> SocialAccount | None:
        result = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.organization_id == org_id,
                SocialAccount.provider == provider,
                SocialAccount.provider_account_id == provider_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        org_id: uuid.UUID,
        provider: str,
        provider_account_id: str,
        *,
        display_name: str | None = None,
        username: str | None = None,
        profile_image_url: str | None = None,
        account_type: str | None = None,
        connection_status: str = "active",
        granted_scopes: list[str] | None = None,
        token_expires_at: datetime | None = None,
        capabilities_snapshot: dict | None = None,
        provider_metadata: dict | None = None,
        is_default_destination: bool = False,
        created_by: uuid.UUID | None = None,
    ) -> SocialAccount:
        account = SocialAccount(
            organization_id=org_id,
            provider=ProviderEnum(provider),
            provider_account_id=provider_account_id,
            display_name=display_name,
            username=username,
            profile_image_url=profile_image_url,
            account_type=account_type,
            connection_status=AccountConnectionStatus(connection_status),
            granted_scopes=granted_scopes,
            token_expires_at=token_expires_at,
            capabilities_snapshot=capabilities_snapshot,
            provider_metadata=provider_metadata,
            is_default_destination=is_default_destination,
            created_by=created_by,
            last_validated_at=datetime.now(UTC),
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def update(self, account: SocialAccount, **kwargs) -> SocialAccount:
        for key, value in kwargs.items():
            setattr(account, key, value)
        await self.db.flush()
        await self.db.refresh(account)
        return account
