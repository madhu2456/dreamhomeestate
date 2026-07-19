"""Unit tests for PublicationService methods with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    AccountConnectionStatus,
    AttemptStatus,
    JobStatus,
    ProviderEnum,
)
from app.services.publication import PublicationService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    svc = PublicationService(mock_db)
    svc.campaign_repo = AsyncMock()
    svc.job_repo = AsyncMock()
    svc.attempt_repo = AsyncMock()
    svc.outbox_repo = AsyncMock()
    svc.listing_repo = AsyncMock()
    svc.template_repo = AsyncMock()
    svc.social_account_repo = AsyncMock()
    return svc


def make_mock_account(provider="x", status="active"):
    account = MagicMock()
    account.id = "account-uuid"
    account.provider = ProviderEnum(provider)
    account.provider_account_id = "test_account"
    account.connection_status = AccountConnectionStatus(status)
    account.revoked_at = None
    account.credentials = MagicMock()
    account.credentials.encrypted_access_token = "live_token"
    account.credentials.expires_at = None
    account.credentials.token_type = "bearer"
    account.credentials.scope = "tweet.write"
    account.username = "tester"
    return account


def make_mock_job(account, status=JobStatus.queued, retry_count=0, max_retries=3):
    job = MagicMock()
    job.id = "job-uuid"
    job.campaign_id = "campaign-uuid"
    job.social_account_id = account.id if account else None
    job.social_account = account
    job.status = status
    job.retry_count = retry_count
    job.max_retries = max_retries
    job.rendered_title = "Test Title"
    job.rendered_body = "Test body for publication"
    job.media_urls = []
    job.content_items = None
    job.provider_job_id = None
    job.error_code = None
    job.error_message = None
    job.campaign = MagicMock()
    job.campaign.organization_id = "org-uuid"
    return job


def make_update_status_mock():
    """Return an AsyncMock that mutates the job's attributes when called."""
    async def _update_status(job, status, **extra):
        job.status = status
        for key, val in extra.items():
            setattr(job, key, val)
        return job
    return AsyncMock(side_effect=_update_status)


class TestExecuteJob:
    async def test_execute_job_success(self, service):
        account = make_mock_account(provider="x")
        job = make_mock_job(account)

        service.job_repo.update_status = make_update_status_mock()
        service.attempt_repo.create = AsyncMock()
        service.outbox_repo.create = AsyncMock()

        with patch("app.services.publication.get_connector") as mock_get_connector:
            mock_connector = AsyncMock()
            mock_connector.publish.return_value = {
                "id": "provider-123",
                "url": "https://x.com/tester/status/provider-123",
            }
            mock_get_connector.return_value = mock_connector

            result = await service.execute_job(job)

        assert result.status == JobStatus.published
        assert result.provider_job_id == "provider-123"

        update_calls = service.job_repo.update_status.call_args_list
        statuses = [call[0][1] for call in update_calls]
        assert JobStatus.publishing in statuses
        assert JobStatus.published in statuses

        attempt_calls = service.attempt_repo.create.call_args_list
        assert len(attempt_calls) == 1
        assert attempt_calls[0][1]["status"] == AttemptStatus.success.value

        assert service.outbox_repo.create.called

    async def test_execute_job_rejects_mock_provider(self, service):
        account = make_mock_account(provider="mock")
        job = make_mock_job(account)
        service.job_repo.update_status = make_update_status_mock()

        result = await service.execute_job(job)

        assert result.status == JobStatus.failed
        assert result.error_code == "unsupported_provider"

    async def test_execute_job_account_not_found(self, service):
        job = make_mock_job(None)

        service.job_repo.update_status = make_update_status_mock()

        result = await service.execute_job(job)

        assert result.status == JobStatus.failed
        assert result.error_code == "account_not_found"

    async def test_execute_job_connector_failure_with_retry(self, service):
        account = make_mock_account(provider="instagram")
        job = make_mock_job(account, retry_count=0, max_retries=3)

        service.job_repo.update_status = make_update_status_mock()
        service.attempt_repo.create = AsyncMock()
        service.outbox_repo.create = AsyncMock()

        with patch("app.services.publication.get_connector") as mock_get_connector:
            mock_connector = AsyncMock()
            mock_connector.publish.side_effect = ValueError("API rate limit exceeded")
            mock_get_connector.return_value = mock_connector

            result = await service.execute_job(job)

        assert result.status == JobStatus.queued
        assert result.retry_count == 1

        update_calls = service.job_repo.update_status.call_args_list
        statuses = [call[0][1] for call in update_calls]
        assert JobStatus.queued in statuses

        attempt_calls = service.attempt_repo.create.call_args_list
        assert attempt_calls[0][1]["status"] == AttemptStatus.failed.value
        assert attempt_calls[0][1]["error_code"] == "ValueError"

        assert not service.outbox_repo.create.called

    async def test_execute_job_connector_failure_no_retry(self, service):
        account = make_mock_account(provider="x")
        job = make_mock_job(account, retry_count=3, max_retries=3)

        service.job_repo.update_status = make_update_status_mock()
        service.attempt_repo.create = AsyncMock()
        service.outbox_repo.create = AsyncMock()

        with patch("app.services.publication.get_connector") as mock_get_connector:
            mock_connector = AsyncMock()
            mock_connector.publish.side_effect = RuntimeError("Permanent failure")
            mock_get_connector.return_value = mock_connector

            result = await service.execute_job(job)

        assert result.status == JobStatus.failed
        assert result.retry_count == 3

        update_calls = service.job_repo.update_status.call_args_list
        statuses = [call[0][1] for call in update_calls]
        assert JobStatus.failed in statuses

        assert service.outbox_repo.create.called

    async def test_execute_job_x_thread_chains_replies(self, service):
        account = make_mock_account(provider="x")
        job = make_mock_job(account)
        job.content_items = [
            {"body": "tweet 1", "media_urls": []},
            {"body": "tweet 2", "media_urls": []},
        ]

        service.job_repo.update_status = make_update_status_mock()
        service.attempt_repo.create = AsyncMock()
        service.outbox_repo.create = AsyncMock()

        with patch("app.services.publication.get_connector") as mock_get_connector:
            mock_connector = AsyncMock()
            mock_connector.publish.side_effect = [
                {"id": "t1", "url": "https://x.com/t/1"},
                {"id": "t2", "url": "https://x.com/t/2"},
            ]
            mock_get_connector.return_value = mock_connector

            result = await service.execute_job(job)

        assert result.status == JobStatus.published
        assert mock_connector.publish.call_count == 2
        second_content = mock_connector.publish.call_args_list[1][0][2]
        assert second_content["in_reply_to_tweet_id"] == "t1"
