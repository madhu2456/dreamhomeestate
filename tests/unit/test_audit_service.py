"""Unit tests for AuditService with mocked database and repository."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audit import AuditService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_repo():
    """Return an AsyncMock standing in for AuditLogRepository."""
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_repo):
    """Create an AuditService with the repo attribute replaced by a mock."""
    svc = AuditService(mock_db)
    svc._repo = mock_repo
    return svc


class TestLogAction:
    async def test_log_action_creates_entry(self, service, mock_repo):
        """Verify the repository create is called with the correct arguments."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        await service.log_action(
            organization_id=org_id,
            user_id=user_id,
            action="listing.created",
            entity_type="listing",
            entity_id=entity_id,
            details={"title": "New Property"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_repo.create.assert_called_once_with(
            organization_id=org_id,
            user_id=user_id,
            action="listing.created",
            entity_type="listing",
            entity_id=entity_id,
            details={"title": "New Property"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

    async def test_log_action_with_none_optionals(self, service, mock_repo):
        """Verify log_action passes None for optional fields correctly."""
        await service.log_action(
            action="health_check",
        )

        mock_repo.create.assert_called_once_with(
            organization_id=None,
            user_id=None,
            action="health_check",
            entity_type=None,
            entity_id=None,
            details=None,
            ip_address=None,
            user_agent=None,
        )

    async def test_log_action_never_raises(self, service, mock_repo):
        """When the repository raises, log_action must not propagate the exception."""
        mock_repo.create.side_effect = RuntimeError("DB connection failed")

        # Should not raise
        await service.log_action(
            organization_id=uuid.uuid4(),
            action="listing.updated",
        )

        # The repo should have been called
        mock_repo.create.assert_called_once()

    async def test_log_action_defaults_empty_action(self, service, mock_repo):
        """When action is not specified, it defaults to an empty string."""
        await service.log_action()

        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["action"] == ""


class TestLogListingChange:
    async def test_log_listing_change_sets_entity_type_to_listing(self, service, mock_repo):
        """Verify log_listing_change calls log_action with entity_type='listing'."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        listing_id = uuid.uuid4()

        await service.log_listing_change(
            org_id=org_id,
            user_id=user_id,
            listing_id=listing_id,
            action="listing.updated",
            changes={"price": "old_value → new_value"},
        )

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["action"] == "listing.updated"
        assert call_kwargs["entity_type"] == "listing"
        assert call_kwargs["entity_id"] == listing_id
        assert call_kwargs["organization_id"] == org_id
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["details"] == {"price": "old_value → new_value"}

    async def test_log_listing_change_defaults_empty_changes(self, service, mock_repo):
        """When changes is None, it is passed as an empty dict to details."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        listing_id = uuid.uuid4()

        await service.log_listing_change(
            org_id=org_id,
            user_id=user_id,
            listing_id=listing_id,
            action="listing.deleted",
        )

        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["action"] == "listing.deleted"
        assert call_kwargs["details"] == {}


class TestLogCampaignAction:
    async def test_log_campaign_action_sets_entity_type_to_campaign(self, service, mock_repo):
        """Verify log_campaign_action calls log_action with entity_type='campaign'."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        campaign_id = uuid.uuid4()

        await service.log_campaign_action(
            org_id=org_id,
            user_id=user_id,
            campaign_id=campaign_id,
            action="campaign.published",
            details={"target_platforms": ["instagram", "x"]},
        )

        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["action"] == "campaign.published"
        assert call_kwargs["entity_type"] == "campaign"
        assert call_kwargs["entity_id"] == campaign_id
        assert call_kwargs["organization_id"] == org_id
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["details"] == {"target_platforms": ["instagram", "x"]}
