"""Social account connections router — OAuth flows, revoke, validate, test."""

import base64
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.connectors.registry import get_connector
from app.database import get_db
from app.dependencies import CurrentUser, require_role
from app.models import (
    AccountConnectionStatus,
    MembershipRole,
)
from app.repositories.encrypted_credentials import EncryptedCredentialsRepository
from app.repositories.social_account import SocialAccountRepository
from app.schemas.social_account import (
    OAuthConnectRequest,
    OAuthConnectResponse,
    SocialAccountOut,
)
from app.services.audit import AuditService
from app.services.oauth_state import (
    generate_pkce_pair,
    generate_state,
    pop_oauth_state,
    store_oauth_state,
)

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter(tags=["social-accounts"])


def _instagram_configured() -> bool:
    return bool(
        settings.instagram_app_id
        and settings.instagram_app_secret
        and settings.instagram_redirect_uri
    )


def _x_configured() -> bool:
    return bool(
        settings.x_client_id
        and settings.x_client_secret
        and settings.x_redirect_uri
    )


def _build_redirect_url(redirect_after: str, **params: str) -> str:
    separator = "&" if "?" in redirect_after else "?"
    return f"{redirect_after}{separator}{urlencode(params)}"


# ──────────────────────── Management routes ────────────────────────


@router.get(
    "/api/v1/organizations/{org_id}/social-accounts",
    response_model=list[SocialAccountOut],
)
async def list_social_accounts(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> list[SocialAccountOut]:
    """List all social accounts for an organization."""
    repo = SocialAccountRepository(db)
    accounts = await repo.list_for_org(org_id)
    return [SocialAccountOut.model_validate(a) for a in accounts]


@router.post(
    "/api/v1/organizations/{org_id}/social-accounts/{provider}/connect",
    response_model=OAuthConnectResponse,
)
async def connect_social_account(
    org_id: uuid.UUID,
    provider: str,
    body: OAuthConnectRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> OAuthConnectResponse:
    """Initiate a live OAuth connect flow for Instagram or X."""
    redirect_after = body.redirect_after
    provider = provider.lower().strip()

    if provider not in ("instagram", "x"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported provider. Connect 'instagram' or 'x' only.",
        )

    if provider == "instagram":
        if not _instagram_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Instagram is not configured. Set INSTAGRAM_APP_ID, "
                    "INSTAGRAM_APP_SECRET, and INSTAGRAM_REDIRECT_URI."
                ),
            )
        state = generate_state()
        code_verifier, code_challenge = generate_pkce_pair()
        await store_oauth_state(
            state,
            {
                "org_id": str(org_id),
                "provider": provider,
                "created_by": str(current_user.id),
                "redirect_after": redirect_after,
                "code_verifier": code_verifier,
            },
        )
        # Instagram API with Instagram Login — content publishing scopes
        params = {
            "client_id": settings.instagram_app_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "scope": "instagram_business_basic,instagram_business_content_publish",
            "response_type": "code",
            "state": state,
        }
        auth_url = f"https://www.instagram.com/oauth/authorize?{urlencode(params)}"
        return OAuthConnectResponse(authorization_url=auth_url, mock=False)

    # provider == "x"
    if not _x_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "X is not configured. Set X_CLIENT_ID, X_CLIENT_SECRET, and X_REDIRECT_URI."
            ),
        )
    state = generate_state()
    code_verifier, code_challenge = generate_pkce_pair()
    await store_oauth_state(
        state,
        {
            "org_id": str(org_id),
            "provider": provider,
            "created_by": str(current_user.id),
            "redirect_after": redirect_after,
            "code_verifier": code_verifier,
        },
    )
    scopes = "tweet.read tweet.write users.read offline.access media.write"
    params = {
        "client_id": settings.x_client_id,
        "redirect_uri": settings.x_redirect_uri,
        "scope": scopes,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
    return OAuthConnectResponse(authorization_url=auth_url, mock=False)


# ──────────────────────── Global callback route ────────────────────


@router.get(
    "/api/v1/social-accounts/{provider}/callback",
    response_model=None,
    responses={307: {"description": "Redirect to frontend"}},
)
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> Any:
    """Handle OAuth callback from Instagram or X, exchange code, store credentials."""
    provider = provider.lower().strip()
    state_data = await pop_oauth_state(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or expired OAuth state. Please try connecting again.",
        )

    redirect_after = state_data.get("redirect_after", "/")

    if provider not in ("instagram", "x"):
        return RedirectResponse(
            url=_build_redirect_url(redirect_after, error="unsupported_provider", provider=provider),
            status_code=307,
        )

    org_id = uuid.UUID(state_data["org_id"])
    created_by = uuid.UUID(state_data["created_by"]) if state_data.get("created_by") else None
    code_verifier = state_data.get("code_verifier", "")

    try:
        token_response = await _exchange_code_for_token(provider, code, code_verifier)
    except Exception as exc:
        logger.warning(
            "oauth_token_exchange_failed",
            provider=provider,
            error=str(exc),
        )
        return RedirectResponse(
            url=_build_redirect_url(
                redirect_after,
                error="oauth_failed",
                provider=provider,
            ),
            status_code=307,
        )

    access_token = token_response.get("access_token", "")
    refresh_token = token_response.get("refresh_token")
    token_type = token_response.get("token_type", "bearer")
    scope = token_response.get("scope", "")
    expires_in = token_response.get("expires_in")
    expires_at = (
        datetime.now(timezone.utc).timestamp() + expires_in
        if expires_in
        else None
    )

    account_repo = SocialAccountRepository(db)
    creds_repo = EncryptedCredentialsRepository(db)
    connector = get_connector(provider)

    provider_account_id = token_response.get("provider_account_id") or "pending"
    username = token_response.get("username") or "pending"

    # Upsert if this provider account is already connected for the org
    existing = None
    if provider_account_id != "pending":
        existing = await account_repo.get_by_provider_account(
            org_id, provider, str(provider_account_id)
        )

    if existing:
        account = existing
        await account_repo.update(
            account,
            connection_status=AccountConnectionStatus.active.value,
            revoked_at=None,
            last_error=None,
            username=username if username != "pending" else existing.username,
        )
    else:
        account = await account_repo.create(
            org_id=org_id,
            provider=provider,
            provider_account_id=str(provider_account_id),
            username=username,
            connection_status="active",
            created_by=created_by,
        )

    creds = await creds_repo.create_or_update(
        social_account_id=account.id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=token_type,
        scope=scope,
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc) if expires_at else None,
    )

    try:
        result = await connector.validate(account, creds)
        valid = result.get("valid", False)
        new_status = AccountConnectionStatus.active if valid else AccountConnectionStatus.error
        now = datetime.now(timezone.utc)

        update_kwargs: dict[str, Any] = {
            "connection_status": new_status.value,
            "capabilities_snapshot": result,
            "last_validated_at": now,
        }
        if not valid:
            update_kwargs["last_error"] = result.get("error", "Validation failed")

        if result.get("provider_account_id"):
            update_kwargs["provider_account_id"] = str(result["provider_account_id"])
        if result.get("username"):
            update_kwargs["username"] = result["username"]
        if result.get("display_name"):
            update_kwargs["display_name"] = result["display_name"]
        if result.get("profile_image_url"):
            update_kwargs["profile_image_url"] = result["profile_image_url"]
        if result.get("account_type"):
            update_kwargs["account_type"] = result["account_type"]

        await account_repo.update(account, **update_kwargs)
    except Exception as exc:
        logger.warning("oauth_validate_failed", provider=provider, error=str(exc))
        await account_repo.update(
            account,
            connection_status=AccountConnectionStatus.error.value,
            last_error=str(exc),
            last_validated_at=datetime.now(timezone.utc),
        )

    logger.info(
        "oauth_connection_complete",
        provider=provider,
        org_id=str(org_id),
        account_id=str(account.id),
    )

    audit_svc = AuditService(db)
    await audit_svc.log_action(
        organization_id=org_id,
        user_id=created_by,
        action="social_account.connected",
        entity_type="social_account",
        entity_id=account.id,
        details={"provider": provider, "live": True},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )

    return RedirectResponse(
        url=_build_redirect_url(
            redirect_after,
            connected="1",
            provider=provider,
        ),
        status_code=307,
    )


async def _exchange_code_for_token(
    provider: str, code: str, code_verifier: str
) -> dict[str, Any]:
    """Exchange an OAuth authorization code for a live access token."""
    async with httpx.AsyncClient(timeout=30) as client:
        if provider == "instagram":
            # Short-lived token
            resp = await client.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": settings.instagram_app_id,
                    "client_secret": settings.instagram_app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.instagram_redirect_uri,
                    "code": code,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Response may be flat or nested under data[0]
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                short = data["data"][0]
            else:
                short = data

            short_token = short["access_token"]
            user_id = str(short.get("user_id", ""))

            # Exchange for long-lived token (~60 days)
            long_resp = await client.get(
                "https://graph.instagram.com/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": settings.instagram_app_secret,
                    "access_token": short_token,
                },
            )
            long_resp.raise_for_status()
            long_data = long_resp.json()

            return {
                "access_token": long_data["access_token"],
                "token_type": long_data.get("token_type", "bearer"),
                "expires_in": long_data.get("expires_in", 5184000),
                "provider_account_id": user_id,
                "scope": "instagram_business_basic,instagram_business_content_publish",
            }

        if provider == "x":
            credentials = base64.b64encode(
                f"{settings.x_client_id}:{settings.x_client_secret}".encode()
            ).decode()
            resp = await client.post(
                "https://api.x.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.x_redirect_uri,
                    "code_verifier": code_verifier,
                    "client_id": settings.x_client_id,
                },
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "token_type": data.get("token_type", "bearer"),
                "scope": data.get("scope", ""),
                "expires_in": data.get("expires_in"),
            }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}",
        )


# ──────────────────────── Account management routes ────────────────


@router.post(
    "/api/v1/organizations/{org_id}/social-accounts/{account_id}/revoke",
    response_model=SocialAccountOut,
)
async def revoke_social_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> SocialAccountOut:
    """Revoke a connected social account."""
    account_repo = SocialAccountRepository(db)
    account = await account_repo.get_by_id(account_id)

    if account is None or account.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
        )

    account = await account_repo.update(
        account,
        connection_status=AccountConnectionStatus.revoked.value,
        revoked_at=datetime.now(timezone.utc),
    )

    logger.info(
        "social_account_revoked",
        account_id=str(account_id),
        provider=account.provider.value,
    )

    # Audit: social_account.revoked
    audit_svc = AuditService(db)
    await audit_svc.log_action(
        organization_id=org_id,
        user_id=current_user.id,
        action="social_account.revoked",
        entity_type="social_account",
        entity_id=account_id,
        details={"provider": account.provider.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return SocialAccountOut.model_validate(account)


@router.post(
    "/api/v1/organizations/{org_id}/social-accounts/{account_id}/validate",
    response_model=SocialAccountOut,
)
async def validate_social_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> SocialAccountOut:
    """Validate a social account connection and update capability snapshot."""
    return await _do_validate_account(org_id, account_id, db)


@router.post(
    "/api/v1/organizations/{org_id}/social-accounts/{account_id}/test",
    response_model=SocialAccountOut,
)
async def test_social_account(
    org_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership=Depends(
        require_role(MembershipRole.owner, MembershipRole.administrator, MembershipRole.editor)
    ),
) -> SocialAccountOut:
    """Test a social account connection (alias for validate)."""
    return await _do_validate_account(org_id, account_id, db)


async def _do_validate_account(
    org_id: uuid.UUID, account_id: uuid.UUID, db: AsyncSession
) -> SocialAccountOut:
    """Shared validation logic for validate and test endpoints."""
    account_repo = SocialAccountRepository(db)
    creds_repo = EncryptedCredentialsRepository(db)

    account = await account_repo.get_by_id(account_id)
    if account is None or account.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
        )

    creds = await creds_repo.get_by_social_account_id(account_id)
    connector = get_connector(account.provider.value)

    try:
        result = await connector.validate(account, creds)
    except Exception as exc:
        result = {"valid": False, "error": str(exc)}

    valid = result.get("valid", False)
    now = datetime.now(timezone.utc)

    update_kwargs: dict[str, Any] = {
        "capabilities_snapshot": result,
        "last_validated_at": now,
    }

    if not valid:
        update_kwargs["connection_status"] = AccountConnectionStatus.error.value
        update_kwargs["last_error"] = result.get("error", "Validation failed")
    elif account.connection_status == AccountConnectionStatus.error:
        update_kwargs["connection_status"] = AccountConnectionStatus.active.value
        update_kwargs["last_error"] = None

    if result.get("provider_account_id"):
        update_kwargs["provider_account_id"] = result["provider_account_id"]
    if result.get("username"):
        update_kwargs["username"] = result["username"]

    account = await account_repo.update(account, **update_kwargs)

    logger.info(
        "social_account_validated",
        account_id=str(account_id),
        valid=valid,
    )

    return SocialAccountOut.model_validate(account)
