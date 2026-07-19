"""Unit tests for webhook signature validation — pure functions, no mocking needed."""

import base64
import hashlib
import hmac

import pytest

from app.services.webhook_validator import (
    generate_challenge_response,
    verify_instagram_signature,
    verify_x_signature,
)


class TestVerifyInstagramSignature:
    SECRET = "instagram-app-secret-123"
    BODY = b'{"entry":[{"changes":[{"value":{"id":"123"}}]}]}'

    def _make_valid_signature(self, body: bytes, secret: str) -> str:
        """Compute a valid X-Hub-Signature-256 header value."""
        computed = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return f"sha256={computed}"

    def test_verify_instagram_signature_valid(self):
        """A valid signature computed with the correct secret and body returns True."""
        sig = self._make_valid_signature(self.BODY, self.SECRET)
        assert verify_instagram_signature(self.BODY, sig, self.SECRET) is True

    def test_verify_instagram_signature_invalid_tampered_body(self):
        """Tampering the body after the signature was generated must return False."""
        sig = self._make_valid_signature(self.BODY, self.SECRET)
        tampered_body = b'{"entry":[{"changes":[{"value":{"id":"hacked"}}]}]}'
        assert verify_instagram_signature(tampered_body, sig, self.SECRET) is False

    def test_verify_instagram_signature_invalid_wrong_secret(self):
        """Using the wrong secret must return False."""
        sig = self._make_valid_signature(self.BODY, self.SECRET)
        assert verify_instagram_signature(self.BODY, sig, "wrong-secret") is False

    def test_verify_instagram_signature_invalid_malformed_header(self):
        """A header that doesn't start with 'sha256=' is rejected."""
        result = verify_instagram_signature(self.BODY, "not-sha256=abc123", self.SECRET)
        assert result is False

    def test_verify_instagram_signature_missing_header(self):
        """A None signature_header returns False."""
        assert verify_instagram_signature(self.BODY, None, self.SECRET) is False

    def test_verify_instagram_signature_empty_header(self):
        """An empty string signature_header should fail the prefix check."""
        assert verify_instagram_signature(self.BODY, "", self.SECRET) is False

    def test_verify_instagram_signature_empty_secret(self):
        """An empty secret always returns False (cannot compute HMAC)."""
        sig = self._make_valid_signature(self.BODY, self.SECRET)
        assert verify_instagram_signature(self.BODY, sig, "") is False

    def test_verify_instagram_signature_invalid_hex_in_header(self):
        """A header with the right prefix but non-hex chars is rejected."""
        result = verify_instagram_signature(
            self.BODY, "sha256=not-a-valid-hex-digest!", self.SECRET
        )
        assert result is False


class TestVerifyXSignature:
    SECRET = "x-webhook-secret-456"
    BODY = b'{"for_user_id":"12345","tweet_create_events":[{"id":"678"}]}'

    def _make_valid_x_signature(self, body: bytes, secret: str) -> str:
        """Compute a valid x-twitter-webhooks-signature (base64 HMAC-SHA256)."""
        digest = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def test_verify_x_signature_valid(self):
        """A valid base64-encoded HMAC-SHA256 signature returns True."""
        sig = self._make_valid_x_signature(self.BODY, self.SECRET)
        assert verify_x_signature(self.BODY, sig, self.SECRET) is True

    def test_verify_x_signature_invalid_tampered_body(self):
        """Tampering the body after signature generation must return False."""
        sig = self._make_valid_x_signature(self.BODY, self.SECRET)
        tampered = b'{"for_user_id":"12345","tweet_create_events":[{"id":"hacked"}]}'
        assert verify_x_signature(tampered, sig, self.SECRET) is False

    def test_verify_x_signature_wrong_secret(self):
        """Using the wrong consumer secret returns False."""
        sig = self._make_valid_x_signature(self.BODY, self.SECRET)
        assert verify_x_signature(self.BODY, sig, "wrong-secret") is False

    def test_verify_x_signature_missing_header(self):
        """None signature_header returns False."""
        assert verify_x_signature(self.BODY, None, self.SECRET) is False

    def test_verify_x_signature_empty_header(self):
        """Empty signature_header returns False (constant-time compare fails)."""
        sig = self._make_valid_x_signature(self.BODY, self.SECRET)
        assert verify_x_signature(self.BODY, "", self.SECRET) is False

    def test_verify_x_signature_empty_secret(self):
        """Empty secret returns False."""
        sig = self._make_valid_x_signature(self.BODY, self.SECRET)
        assert verify_x_signature(self.BODY, sig, "") is False

    def test_verify_x_signature_not_base64(self):
        """A non-base64-encoded header value returns False on comparison."""
        assert verify_x_signature(self.BODY, "!!!not-base64!!!", self.SECRET) is False


class TestGenerateChallengeResponse:
    def test_generate_challenge_response_correct_format(self):
        """The response token must be in the format 'sha256=<base64-encoded-HMAC>'."""
        crc_token = "crc-token-from-twitter"
        secret = "x-consumer-secret"

        response = generate_challenge_response(crc_token, secret)

        assert response.startswith("sha256=")
        # The part after "sha256=" should be valid base64
        b64_part = response[7:]
        try:
            base64.b64decode(b64_part)
        except Exception:
            pytest.fail("Response token payload is not valid base64")

    def test_generate_challenge_response_is_deterministic(self):
        """The same crc_token and secret always produce the same response."""
        crc_token = "deterministic-test"
        secret = "my-secret"

        r1 = generate_challenge_response(crc_token, secret)
        r2 = generate_challenge_response(crc_token, secret)

        assert r1 == r2

    def test_generate_challenge_response_differs_with_different_secret(self):
        """Different secrets produce different response tokens."""
        crc_token = "same-token"

        r1 = generate_challenge_response(crc_token, "secret-a")
        r2 = generate_challenge_response(crc_token, "secret-b")

        assert r1 != r2

    def test_generate_challenge_response_differs_with_different_token(self):
        """Different crc_tokens produce different response tokens."""
        secret = "same-secret"

        r1 = generate_challenge_response("token-a", secret)
        r2 = generate_challenge_response("token-b", secret)

        assert r1 != r2
