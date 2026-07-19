"""Repository for Session operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session
from app.security import hash_token


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        session_token: str,
        expires_at: datetime,
    ) -> Session:
        session = Session(
            user_id=user_id,
            token_hash=hash_token(session_token),
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def delete(self, session_id: uuid.UUID) -> None:
        stmt = delete(Session).where(Session.id == session_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = delete(Session).where(Session.user_id == user_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        result = await self.db.execute(
            select(Session).where(Session.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
