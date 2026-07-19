"""Webhook signature validation utilities for Instagram and X (Twitter)."""

import base64
import hashlib
import hmac


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a, b)


def verify_instagram_signature(
    body: bytes, signature_header: str | None, secret: str
) -> bool:
    """Validate the X-Hub-Signature-256 header from Instagram.

    Instagram sends a header like:
        X-Hub-Signature-256: sha256=<hex-encoded HMAC>

    We recompute HMAC-SHA256(key=secret, msg=body) and compare.
    """
    if not signature_header or not secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = signature_header[7:]  # strip "sha256=" prefix
    computed = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    return _constant_time_compare(computed, expected)


def verify_x_signature(
    body: bytes, signature_header: str | None, secret: str
) -> bool:
    """Validate the x-twitter-webhooks-signature header from X/Twitter.

    X's Account Activity API (webhook v2) sends a base64-encoded HMAC-SHA256
    in the x-twitter-webhooks-signature header.

    We recompute HMAC-SHA256(key=secret, msg=body), base64-encode it, and compare.
    """
    if not signature_header or not secret:
        return False

    computed = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).digest()
    computed_b64 = base64.b64encode(computed).decode("utf-8")

    return _constant_time_compare(computed_b64, signature_header)


def generate_challenge_response(crc_token: str, secret: str) -> str:
    """Generate the CRC challenge response token for X webhook verification.

    X sends a GET with ?crc_token=... and expects a JSON response:
        {"response_token": "sha256=<base64-encoded HMAC-SHA256>"}

    The HMAC is computed over the crc_token with the consumer secret as key,
    then base64-encoded.
    """
    digest = hmac.new(
        secret.encode("utf-8"),
        crc_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded = base64.b64encode(digest).decode("utf-8")
    return f"sha256={encoded}"
