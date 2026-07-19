"""Social account connections router — OAuth flows, revoke, validate, test."""

import base64
import uuid
from datetime import UTC, datetime, timedelta
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
    AccountType,
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
        # Instagram API with Instagram Login — match Meta app product scopes
        params = {
            "client_id": settings.instagram_app_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "scope": (
                "instagram_business_basic,"
                "instagram_business_content_publish,"
                "instagram_business_manage_comments,"
                "instagram_business_manage_insights"
            ),
            "response_type": "code",
            "state": state,
            "force_reauth": "true",
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


def _map_instagram_account_type(raw: str | None) -> AccountType | None:
    """Map Instagram Graph account_type values onto our enum."""
    if not raw:
        return None
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "personal": AccountType.personal,
        "business": AccountType.business,
        "creator": AccountType.creator,
        "media_creator": AccountType.creator,
        "page": AccountType.page,
    }
    return mapping.get(key)


def _normalize_scope(scope: Any) -> str:
    if scope is None:
        return ""
    if isinstance(scope, list):
        return ",".join(str(s) for s in scope)
    return str(scope)


@router.get(
    "/api/v1/social-accounts/{provider}/callback",
    response_model=None,
    responses={307: {"description": "Redirect to frontend"}},
)
async def oauth_callback(
    provider: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
) -> Any:
    """Handle OAuth callback from Instagram or X, exchange code, store credentials.

    Always prefer redirecting back to the admin UI with an error query param
    instead of returning a bare 500 JSON to the browser.
    """
    provider = provider.lower().strip()
    fallback_redirect = "/admin/social-accounts"

    # Instagram may append #_ to the code; strip anything after # if present
    if code:
        code = code.split("#", 1)[0].strip()

    if error:
        logger.warning(
            "oauth_provider_error",
            provider=provider,
            error=error,
            error_description=error_description,
        )
        return RedirectResponse(
            url=_build_redirect_url(
                fallback_redirect,
                error=error,
                provider=provider,
            ),
            status_code=307,
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth code or state. Please try connecting again.",
        )

    state_data = await pop_oauth_state(state)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or expired OAuth state. Please try connecting again.",
        )

    redirect_after = state_data.get("redirect_after") or fallback_redirect

    if provider not in ("instagram", "x"):
        return RedirectResponse(
            url=_build_redirect_url(redirect_after, error="unsupported_provider", provider=provider),
            status_code=307,
        )

    try:
        org_id = uuid.UUID(state_data["org_id"])
        created_by = (
            uuid.UUID(state_data["created_by"]) if state_data.get("created_by") else None
        )
        code_verifier = state_data.get("code_verifier", "")

        try:
            token_response = await _exchange_code_for_token(provider, code, code_verifier)
        except Exception as exc:
            body = ""
            if isinstance(exc, httpx.HTTPStatusError):
                body = (exc.response.text or "")[:500]
            logger.warning(
                "oauth_token_exchange_failed",
                provider=provider,
                error=str(exc),
                body=body,
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
        if not access_token:
            logger.warning("oauth_missing_access_token", provider=provider)
            return RedirectResponse(
                url=_build_redirect_url(
                    redirect_after, error="oauth_failed", provider=provider
                ),
                status_code=307,
            )

        refresh_token = token_response.get("refresh_token")
        token_type = token_response.get("token_type", "bearer")
        scope = _normalize_scope(token_response.get("scope", ""))
        expires_in_raw = token_response.get("expires_in")
        expires_at_dt: datetime | None = None
        if expires_in_raw is not None:
            try:
                expires_at_dt = datetime.now(UTC).replace(microsecond=0) + timedelta(
                    seconds=int(expires_in_raw)
                )
            except (TypeError, ValueError):
                expires_at_dt = None

        account_repo = SocialAccountRepository(db)
        creds_repo = EncryptedCredentialsRepository(db)
        connector = get_connector(provider)

        provider_account_id = str(token_response.get("provider_account_id") or "pending")
        username = token_response.get("username") or "pending"

        existing = None
        if provider_account_id != "pending":
            existing = await account_repo.get_by_provider_account(
                org_id, provider, provider_account_id
            )

        if existing:
            account = existing
            await account_repo.update(
                account,
                connection_status=AccountConnectionStatus.active,
                revoked_at=None,
                last_error=None,
                username=username if username != "pending" else existing.username,
            )
        else:
            account = await account_repo.create(
                org_id=org_id,
                provider=provider,
                provider_account_id=provider_account_id,
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
            expires_at=expires_at_dt,
        )

        try:
            result = await connector.validate(account, creds)
            valid = result.get("valid", False)
            new_status = (
                AccountConnectionStatus.active if valid else AccountConnectionStatus.error
            )
            now = datetime.now(UTC)

            update_kwargs: dict[str, Any] = {
                "connection_status": new_status,
                "capabilities_snapshot": result,
                "last_validated_at": now,
            }
            if not valid:
                update_kwargs["last_error"] = str(result.get("error") or "Validation failed")

            if result.get("provider_account_id"):
                update_kwargs["provider_account_id"] = str(result["provider_account_id"])
            if result.get("username"):
                update_kwargs["username"] = result["username"]
            if result.get("display_name"):
                update_kwargs["display_name"] = result["display_name"]
            if result.get("profile_image_url"):
                update_kwargs["profile_image_url"] = result["profile_image_url"]

            mapped_type = _map_instagram_account_type(result.get("account_type"))
            if mapped_type is not None:
                update_kwargs["account_type"] = mapped_type

            await account_repo.update(account, **update_kwargs)
        except Exception as exc:
            logger.warning(
                "oauth_validate_failed",
                provider=provider,
                error=str(exc),
                exc_info=True,
            )
            await account_repo.update(
                account,
                connection_status=AccountConnectionStatus.error,
                last_error=str(exc)[:500],
                last_validated_at=datetime.now(UTC),
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
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return RedirectResponse(
            url=_build_redirect_url(
                redirect_after,
                connected="1",
                provider=provider,
            ),
            status_code=307,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "oauth_callback_unhandled_error",
            provider=provider,
            error=str(exc),
        )
        safe_redirect = fallback_redirect
        try:
            safe_redirect = redirect_after  # set after state is loaded
        except NameError:
            pass
        return RedirectResponse(
            url=_build_redirect_url(
                safe_redirect,
                error="server_error",
                provider=provider,
            ),
            status_code=307,
        )


async def _exchange_code_for_token(
    provider: str, code: str, code_verifier: str
) -> dict[str, Any]:
    """Exchange an OAuth authorization code for a live access token."""
    # Re-read settings so production .env values are always current
    cfg = get_settings()

    async with httpx.AsyncClient(timeout=30) as client:
        if provider == "instagram":
            if not cfg.instagram_app_id or not cfg.instagram_app_secret:
                raise RuntimeError("Instagram app credentials not configured")

            # Short-lived token
            resp = await client.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": cfg.instagram_app_id,
                    "client_secret": cfg.instagram_app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": cfg.instagram_redirect_uri,
                    "code": code,
                },
            )
            if resp.status_code >= 400:
                logger.warning(
                    "instagram_short_token_error",
                    status=resp.status_code,
                    body=resp.text[:800],
                )
            resp.raise_for_status()
            data = resp.json()
            # Response may be flat or nested under data[0]
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                short = data["data"][0]
            else:
                short = data

            short_token = short.get("access_token")
            if not short_token:
                raise RuntimeError(f"Instagram token response missing access_token: {data}")

            # user_id is on short-lived response for Instagram Login
            user_id = str(short.get("user_id") or "")

            # Exchange for long-lived token (~60 days)
            long_resp = await client.get(
                "https://graph.instagram.com/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": cfg.instagram_app_secret,
                    "access_token": short_token,
                },
            )
            if long_resp.status_code >= 400:
                logger.warning(
                    "instagram_long_token_error",
                    status=long_resp.status_code,
                    body=long_resp.text[:800],
                )
                # Fall back to short-lived token so connect can still succeed
                return {
                    "access_token": short_token,
                    "token_type": "bearer",
                    "expires_in": short.get("expires_in", 3600),
                    "provider_account_id": user_id or "pending",
                    "scope": "instagram_business_basic,instagram_business_content_publish",
                }
            long_data = long_resp.json()
            long_token = long_data.get("access_token") or short_token

            return {
                "access_token": long_token,
                "token_type": long_data.get("token_type", "bearer"),
                "expires_in": long_data.get("expires_in", 5184000),
                "provider_account_id": user_id or "pending",
                "scope": "instagram_business_basic,instagram_business_content_publish",
            }

        if provider == "x":
            credentials = base64.b64encode(
                f"{cfg.x_client_id}:{cfg.x_client_secret}".encode()
            ).decode()
            resp = await client.post(
                "https://api.x.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": cfg.x_redirect_uri,
                    "code_verifier": code_verifier,
                    "client_id": cfg.x_client_id,
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
        revoked_at=datetime.now(UTC),
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
    now = datetime.now(UTC)

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
