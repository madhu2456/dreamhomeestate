"""Shared pytest fixtures for database, HTTP client, and test data.

Tests run each test inside a single database savepoint transaction. The FastAPI
`get_db` dependency is overridden to yield the same `AsyncSession` used by test
fixtures, so changes are visible to the HTTP test client and rolled back
automatically after each test.
"""

import os
import uuid
from typing import AsyncGenerator
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def _derive_test_database_url() -> str:
    """Point tests at a dedicated test database, never the main app database."""
    original = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/realestate_test",
    )
    parsed = urlparse(original)
    # Strip any trailing path and always use /realestate_test
    return parsed._replace(path="/realestate_test").geturl()


# Force test config before any imports
os.environ["DATABASE_URL"] = _derive_test_database_url()
os.environ.setdefault("ENV", "testing")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long-for-testing")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")
os.environ.setdefault("S3_BUCKET_NAME", "test")
os.environ.setdefault("S3_PUBLIC_URL", "http://localhost:9000/test")
# Valid 32-byte url-safe base64 Fernet key (test-only)
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "E14MeR_CCL3_Z1DPIjLdwyKaesR31uBoRFNFregVs-A=")

from app.database import Base
from app.models import (
    MembershipRole,
    Organization,
    User,
)
from app.repositories.user import UserRepository
from app.repositories.organization import OrganizationRepository
from app.security import hash_password


TEST_DATABASE_URL = os.environ["DATABASE_URL"]


async def _ensure_test_database_exists(db_url: str) -> None:
    """Create the test database if it does not already exist."""
    parsed = urlparse(db_url)
    maintenance_url = parsed._replace(path="/postgres").geturl()
    db_name = parsed.path.lstrip("/")

    admin_engine = create_async_engine(maintenance_url, poolclass=NullPool)
    try:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            exists = result.scalar_one_or_none() is not None
            if not exists:
                await conn.execute(text("commit"))
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def _engine():
    """Create the async engine and all tables once per session."""
    await _ensure_test_database_exists(TEST_DATABASE_URL)

    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed roles reference table
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO roles (name, description) VALUES "
                "('owner', 'Full control'), "
                "('administrator', 'Admin role'), "
                "('editor', 'Editor role'), "
                "('viewer', 'Viewer role') "
                "ON CONFLICT (name) DO NOTHING"
            )
        )

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db(_engine) -> AsyncGenerator[AsyncSession, None]:
    """Open a connection, begin a transaction, and override `get_db` for the app.

    All DB operations during a test run inside the same transaction and are
    rolled back at teardown, keeping tests isolated without truncating tables.
    """
    from app.database import get_db
    from app.main import app

    conn = await _engine.connect()

    session = AsyncSession(
        bind=conn,
        expire_on_commit=False,
    )
    await session.begin()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        await session.rollback()
        await session.close()
        await conn.close()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client pointing at the FastAPI app."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a plain test user with no organization membership."""
    repo = UserRepository(db)
    user = await repo.create(
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test User",
        password="testpass123",
    )
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_org(db: AsyncSession, test_user: User) -> Organization:
    """Create an organization owned by test_user."""
    org_repo = OrganizationRepository(db)
    slug = f"test-org-{uuid.uuid4().hex[:8]}"
    org = await org_repo.create(name="Test Org", slug=slug)
    await org_repo.add_member(org, test_user, MembershipRole.owner)
    await db.flush()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient, db: AsyncSession, test_user: User, test_org: Organization
) -> AsyncClient:
    """Return a client authenticated as test_user with a valid session cookie."""
    from app.repositories.session_repo import SessionRepository
    from app.security import sign_session_id
    from datetime import datetime, timedelta, timezone

    session_repo = SessionRepository(db)
    session_id = uuid.uuid4()
    session_token = sign_session_id(session_id)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    await session_repo.create(
        user_id=test_user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    await db.flush()

    client.cookies.set("res_session", session_token)
    return client
