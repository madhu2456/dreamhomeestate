"""Unit tests for password hashing, hashing consistency, and edge cases."""

import uuid

import pytest

from app.security import (
    hash_password,
    verify_password,
    sign_session_id,
    unsign_session_id,
    hash_token,
    generate_password_reset_token,
    verify_password_reset_token,
)
from app.models import MembershipRole


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "super-secret-password-123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_is_stable_per_call(self):
        # bcrypt generates a unique salt each time, so hashes differ
        pw = "mypassword"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # different salts
        assert verify_password(pw, h1)
        assert verify_password(pw, h2)

    def test_empty_password_fails(self):
        hashed = hash_password("something")
        assert verify_password("", hashed) is False


class TestSessionTokens:
    def test_sign_and_unsign(self):
        sid = uuid.uuid4()
        token = sign_session_id(sid)
        assert isinstance(token, str)
        result = unsign_session_id(token)
        assert result == str(sid)

    def test_unsign_invalid_token(self):
        assert unsign_session_id("invalid-token-here") is None

    def test_unsign_expired_token(self):
        import time

        sid = uuid.uuid4()
        token = sign_session_id(sid)
        time.sleep(1.5)
        assert unsign_session_id(token, max_age=0) is None

    def test_token_hash_is_deterministic(self):
        token = "test-token-value"
        h1 = hash_token(token)
        h2 = hash_token(token)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_token_hash_different_tokens(self):
        h1 = hash_token("token-a")
        h2 = hash_token("token-b")
        assert h1 != h2


class TestPasswordResetTokens:
    def test_generate_and_verify(self):
        user_id = uuid.uuid4()
        token = generate_password_reset_token(user_id)
        result = verify_password_reset_token(token)
        assert result == str(user_id)

    def test_expired_token(self):
        import time

        user_id = uuid.uuid4()
        token = generate_password_reset_token(user_id)
        time.sleep(1.5)
        assert verify_password_reset_token(token, max_age=0) is None

    def test_invalid_token(self):
        assert verify_password_reset_token("invalid") is None


class TestRoles:
    def test_membership_role_values(self):
        roles = {r.value for r in MembershipRole}
        assert roles == {"owner", "administrator", "editor", "viewer"}

    def test_role_from_string(self):
        assert MembershipRole("owner") == MembershipRole.owner
        assert MembershipRole("editor") == MembershipRole.editor

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            MembershipRole("superuser")
