"""Async SQLAlchemy engine, session factory, declarative base, and FastAPI dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Naming convention for Alembic autogenerate
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

meta = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = meta


def _get_database_url() -> str:
    from app.config import get_settings
    return str(get_settings().database_url)


def _get_pool_size() -> int:
    from app.config import get_settings
    return get_settings().database_pool_size


# Cache engine after first creation
_engine = None
_async_session_local = None


def get_engine():
    global _engine, _async_session_local
    if _engine is None:
        _engine = create_async_engine(
            _get_database_url(),
            pool_size=_get_pool_size(),
            echo=False,
        )
        _async_session_local = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


def get_async_session_local():
    global _async_session_local
    if _async_session_local is None:
        get_engine()
    return _async_session_local


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_async_session_local()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
