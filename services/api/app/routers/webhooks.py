"""Webhook endpoints for Instagram and X (Twitter) platform callbacks.

These endpoints receive events from third-party platforms. They do NOT require
authentication — the platforms call them directly. Platform-specific signature
validation is performed on every request.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

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


@router.get(
    "/api/v1/webhooks/instagram",
    summary="Instagram webhook verification (Meta hub.challenge)",
    response_class=PlainTextResponse,
)
async def instagram_webhook_verify(request: Request) -> PlainTextResponse:
    """Meta webhook subscription check.

    Meta sends hub.mode, hub.challenge, hub.verify_token.
    Must return hub.challenge as **plain text** (not JSON) when the token matches.
    """
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

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

    expected_token = (settings.instagram_webhook_verify_token or "").strip()
    provided_token = (hub_verify_token or "").strip()

    if not expected_token:
        logger.warning("instagram_webhook_verify_token_not_configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification not configured",
        )

    if not provided_token or provided_token != expected_token:
        logger.warning(
            "instagram_webhook_verify_token_mismatch",
            provided_len=len(provided_token),
            expected_len=len(expected_token),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verify_token",
        )

    logger.info("instagram_webhook_verified")
    # Meta requires the raw challenge string as the body, content-type text/plain
    return PlainTextResponse(content=hub_challenge, status_code=200)


@router.post(
    "/api/v1/webhooks/instagram",
    response_model=WebhookResponse,
    summary="Instagram webhook event receiver",
)
async def instagram_webhook_event(request: Request) -> WebhookResponse:
    """Receive Instagram webhook events. Validate X-Hub-Signature-256."""
    secret = settings.instagram_webhook_secret or settings.instagram_app_secret
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

    try:
        import json

        payload = json.loads(body) if body else None
    except Exception:
        payload = None

    logger.info(
        "instagram_webhook_event_received",
        event_count=len(payload) if isinstance(payload, (list, dict)) else 0,
    )

    return WebhookResponse()


# ──────────────────────── X / Twitter webhook ──────────────────────


@router.get(
    "/api/v1/webhooks/x",
    summary="X (Twitter) webhook CRC verification",
)
async def x_webhook_crc(request: Request) -> dict:
    """X Account Activity CRC: return {"response_token": "sha256=..."}."""
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


@router.post(
    "/api/v1/webhooks/x",
    response_model=WebhookResponse,
    summary="X (Twitter) webhook event receiver",
)
async def x_webhook_event(request: Request) -> WebhookResponse:
    """Receive X webhook events. Validate x-twitter-webhooks-signature."""
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
        import json

        payload = json.loads(body) if body else None
    except Exception:
        payload = None

    logger.info(
        "x_webhook_event_received",
        event_count=len(payload) if isinstance(payload, (list, dict)) else 0,
    )

    return WebhookResponse()
