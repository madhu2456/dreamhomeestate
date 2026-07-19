"""Integration tests for publication engine (campaigns, jobs, approve/reject/retry/cancel)."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobStatus, Listing, MembershipRole, PublicationJob
from app.repositories.listing import ListingRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.publication import PublicationJobRepository
from app.repositories.user import UserRepository


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession, test_org):
    from app.models import User
    repo = UserRepository(db)
    user = await repo.create(
        email=f"admin-pub-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Admin User",
        password="adminpass123",
    )
    org_repo = OrganizationRepository(db)
    await org_repo.add_member(test_org, user, MembershipRole.administrator)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient, db: AsyncSession, admin_user, test_org
) -> AsyncClient:
    from app.repositories.session_repo import SessionRepository
    from app.security import sign_session_id
    from datetime import datetime, timedelta, timezone

    session_repo = SessionRepository(db)
    session_id = uuid.uuid4()
    session_token = sign_session_id(session_id)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    await session_repo.create(
        user_id=admin_user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    await db.flush()
    client.cookies.set("res_session", session_token)
    return client


@pytest_asyncio.fixture
async def test_listing(db: AsyncSession, test_org) -> Listing:
    repo = ListingRepository(db)
    listing = await repo.create(
        org_id=test_org.id,
        title="Publish Test Property",
        transaction_type="sale",
        property_type="house",
        city="Austin",
        country="USA",
        price=450000,
        currency="USD",
    )
    return listing


@pytest_asyncio.fixture
async def test_social_account(db: AsyncSession, test_org):
    from app.models import ProviderEnum, SocialAccount
    from app.services.encryption import encrypt_text

    account = SocialAccount(
        organization_id=test_org.id,
        provider=ProviderEnum.x,
        provider_account_id="test_x_001",
        display_name="Test X",
        username="testx",
        connection_status="active",
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    from app.models import EncryptedOAuthCredentials

    creds = EncryptedOAuthCredentials(
        social_account_id=account.id,
        encrypted_access_token=encrypt_text("live_token"),
    )
    db.add(creds)
    await db.flush()
    return account


@pytest_asyncio.fixture
async def test_template(db: AsyncSession, test_org):
    from app.repositories.content import ContentTemplateRepository

    repo = ContentTemplateRepository(db)
    template = await repo.create(
        org_id=test_org.id,
        name="Pub Test Template",
        platform="x",
        body_template="{{ title }} - ${{ price }}",
        variables=["title", "price"],
        is_default=True,
    )
    return template


@pytest_asyncio.fixture
async def test_campaign(
    db: AsyncSession,
    test_org,
    test_listing,
    test_social_account,
    test_template,
):
    from app.services.publication import PublicationService

    svc = PublicationService(db)
    campaign = await svc.create_campaign(
        org_id=test_org.id,
        listing_id=test_listing.id,
    )
    return campaign


class TestCreateCampaign:
    async def test_create_campaign_creates_jobs(
        self, admin_client: AsyncClient, test_org, test_listing,
        test_social_account, test_template,
    ):
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/campaigns",
            json={"listing_id": str(test_listing.id), "auto_distribute": False},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending_approval"
        assert len(data["jobs"]) >= 1
        assert data["jobs"][0]["status"] == "pending_approval"

    async def test_create_campaign_with_missing_listing(
        self, admin_client: AsyncClient, test_org
    ):
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/campaigns",
            json={"listing_id": str(uuid.uuid4())},
        )
        assert response.status_code == 400


class TestListCampaigns:
    async def test_list_campaigns(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/campaigns"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestApproveJob:
    async def test_approve_job(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/approve"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("approved", "queued")

    async def test_approve_already_approved_job(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/approve"
        )
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/approve"
        )
        assert response.status_code == 400


class TestRejectJob:
    async def test_reject_job(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/reject"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"


class TestRetryJob:
    async def test_retry_failed_job(
        self, admin_client: AsyncClient, test_org, test_campaign, db,
    ):
        job_id = test_campaign.jobs[0].id
        await db.execute(
            update(PublicationJob).where(PublicationJob.id == job_id).values(
                status=JobStatus.failed, retry_count=1
            )
        )
        await db.flush()

        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/retry"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("queued",)

    async def test_retry_pending_job_fails(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/retry"
        )
        assert response.status_code == 400


class TestCancelJob:
    async def test_cancel_pending_job(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/cancel"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_cancel_published_job_fails(
        self, admin_client: AsyncClient, test_org, test_campaign, db,
    ):
        job_id = test_campaign.jobs[0].id
        await db.execute(
            update(PublicationJob).where(PublicationJob.id == job_id).values(
                status=JobStatus.published
            )
        )
        await db.flush()

        response = await admin_client.post(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/cancel"
        )
        assert response.status_code == 400


class TestListJobs:
    async def test_list_jobs(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/jobs"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestAttempts:
    async def test_list_attempts_empty(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}/attempts"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetJob:
    async def test_get_job(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        job_id = test_campaign.jobs[0].id
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{job_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert str(job_id) == data["id"]

    async def test_get_job_not_found(
        self, admin_client: AsyncClient, test_org,
    ):
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/jobs/{uuid.uuid4()}"
        )
        assert response.status_code == 404


class TestGetCampaign:
    async def test_get_campaign(
        self, admin_client: AsyncClient, test_org, test_campaign,
    ):
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/campaigns/{test_campaign.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert str(test_campaign.id) == data["id"]

    async def test_get_campaign_not_found(
        self, admin_client: AsyncClient, test_org,
    ):
        response = await admin_client.get(
            f"/api/v1/organizations/{test_org.id}/publications/campaigns/{uuid.uuid4()}"
        )
        assert response.status_code == 404
