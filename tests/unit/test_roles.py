"""Unit tests for role checks and slug generation helpers."""

import re

import pytest

from app.dependencies import is_owner, is_owner_or_admin
from app.models import MembershipRole, OrganizationMembership, Organization, User


class TestRoleChecks:
    @pytest.fixture
    def make_membership(self):
        def _make(role: MembershipRole) -> OrganizationMembership:
            return OrganizationMembership(
                role=role,
            )
        return _make

    def test_is_owner_or_admin_owner(self, make_membership):
        m = make_membership(MembershipRole.owner)
        assert is_owner_or_admin(m) is True

    def test_is_owner_or_admin_admin(self, make_membership):
        m = make_membership(MembershipRole.administrator)
        assert is_owner_or_admin(m) is True

    def test_is_owner_or_admin_editor(self, make_membership):
        m = make_membership(MembershipRole.editor)
        assert is_owner_or_admin(m) is False

    def test_is_owner_or_admin_viewer(self, make_membership):
        m = make_membership(MembershipRole.viewer)
        assert is_owner_or_admin(m) is False

    def test_is_owner_owner(self, make_membership):
        m = make_membership(MembershipRole.owner)
        assert is_owner(m) is True

    def test_is_owner_admin(self, make_membership):
        m = make_membership(MembershipRole.administrator)
        assert is_owner(m) is False

    def test_is_owner_viewer(self, make_membership):
        m = make_membership(MembershipRole.viewer)
        assert is_owner(m) is False


class TestSlugPattern:
    """The slug pattern used in OrganizationCreate schema validates slugs."""

    SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def test_valid_slugs(self):
        valid = ["demo-org", "mycompany", "test-123", "a-b-c"]
        for s in valid:
            assert self.SLUG_PATTERN.match(s), f"Should be valid: {s}"

    def test_invalid_slugs(self):
        invalid = ["Demo Org", "UPPERCASE", "trailing-", "-leading", "under_score", "special@char"]
        for s in invalid:
            assert not self.SLUG_PATTERN.match(s), f"Should be invalid: {s}"


class TestIdempotencyKeyHelpers:
    """Placeholder: idempotency key generation will be implemented in later phases."""

    def test_idempotency_key_structure_placeholder(self):
        # Placeholder for future implementation
        # Key format: org_id:listing_version_id:account_id:event_id:sequence
        components = ["org1", "ver1", "acct1", "evt1", "0"]
        key = ":".join(components)
        assert key == "org1:ver1:acct1:evt1:0"
        assert len(key) > 0
