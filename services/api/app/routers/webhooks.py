"""Webhook endpoints for Instagram and X (Twitter) platform callbacks.

These endpoints receive events from third-party platforms. They do NOT require
authentication — the platforms call them directly. Platform-specific signature
validation is performed on every request.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.schemas.webhook import WebhookResponse
from app.services.webhook_validator import (
    generate_challenge_response,
    verify_instagram_signature,
    verify_x_signature,
)

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter(tags=["webhooks"])


# ──────────────────────── Instagram webhook ────────────────────────


@router.api_route(
    "/api/v1/webhooks/instagram",
    methods=["GET", "POST"],
    response_model=WebhookResponse,
    summary="Instagram webhook receiver",
)
async def instagram_webhook(request: Request) -> str | WebhookResponse:
    """Receive Instagram webhook events and handle initial verification.

    GET  — Verification: Instagram sends hub.mode, hub.challenge, hub.verify_token.
           Must confirm verify_token matches our configured value and echo back hub.challenge.

    POST — Event delivery: Instagram sends JSON body. Validate the X-Hub-Signature-256
           header using HMAC-SHA256 with the configured app secret.
    """
    if request.method == "GET":
        return await _instagram_verify(request)
    return await _instagram_event(request)


async def _instagram_verify(request: Request) -> str:
    """Handle Instagram's initial webhook verification (GET request)."""
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    # Instagram sends hub.mode=subscribe when verifying
    if hub_mode != "subscribe":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid hub.mode; expected 'subscribe'",
        )

    if not hub_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing hub.challenge",
        )

    expected_token = settings.instagram_webhook_verify_token
    if not expected_token:
        logger.warning("instagram_webhook_verify_token_not_configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification not configured",
        )

    if not hub_verify_token or hub_verify_token != expected_token:
        logger.warning(
            "instagram_webhook_verify_token_mismatch",
            provided=hub_verify_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verify_token",
        )

    logger.info("instagram_webhook_verified")
    # Must return exactly the hub.challenge value as the response body (plain text)
    return hub_challenge


async def _instagram_event(request: Request) -> WebhookResponse:
    """Handle an Instagram webhook event (POST request)."""
    secret = settings.instagram_webhook_secret
    if not secret:
        logger.warning("instagram_webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook secret not configured",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_instagram_signature(body, signature, secret):
        logger.warning(
            "instagram_webhook_signature_invalid",
            signature_header=signature,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Read JSON once for logging (body is already consumed as bytes for sig check)
    try:
        payload = await request.json()
    except Exception:
        payload = None

    logger.info(
        "instagram_webhook_event_received",
        event_count=len(payload) if isinstance(payload, (list, dict)) else 0,
    )

    return WebhookResponse()


# ──────────────────────── X / Twitter webhook ──────────────────────


@router.api_route(
    "/api/v1/webhooks/x",
    methods=["GET", "POST"],
    response_model=WebhookResponse,
    summary="X (Twitter) webhook receiver",
)
async def x_webhook(request: Request) -> dict | WebhookResponse:
    """Receive X/Twitter webhook events and handle CRC (Challenge-Response Check).

    GET  — CRC: X sends ?crc_token=... and expects a JSON response
           {"response_token": "sha256=..."} containing an HMAC-SHA256 base64 signature.

    POST — Event delivery: X sends JSON body. Validate the x-twitter-webhooks-signature
           header using HMAC-SHA256 (base64-encoded).
    """
    if request.method == "GET":
        return await _x_crc(request)
    return await _x_event(request)


async def _x_crc(request: Request) -> dict:
    """Handle X/Twitter CRC (Challenge-Response Check) for webhook registration."""
    crc_token = request.query_params.get("crc_token")
    if not crc_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing crc_token",
        )

    secret = settings.x_webhook_secret
    if not secret:
        logger.warning("x_webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook secret not configured",
        )

    response_token = generate_challenge_response(crc_token, secret)

    logger.info("x_webhook_crc_completed")
    return {"response_token": response_token}


async def _x_event(request: Request) -> WebhookResponse:
    """Handle an X/Twitter webhook event (POST request)."""
    secret = settings.x_webhook_secret
    if not secret:
        logger.warning("x_webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook secret not configured",
        )

    body = await request.body()
    signature = request.headers.get("x-twitter-webhooks-signature")

    if not verify_x_signature(body, signature, secret):
        logger.warning(
            "x_webhook_signature_invalid",
            signature_header=signature,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    try:
        payload = await request.json()
    except Exception:
        payload = None

    logger.info(
        "x_webhook_event_received",
        event_count=len(payload) if isinstance(payload, (list, dict)) else 0,
    )

    return WebhookResponse()
