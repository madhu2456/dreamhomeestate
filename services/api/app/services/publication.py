"""Publication service — campaign creation, job lifecycle, outbox."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import get_connector
from app.models import (
    AttemptStatus,
    JobStatus,
    Listing,
    PublicationCampaign,
    PublicationJob,
)
from app.repositories.content import ContentTemplateRepository
from app.repositories.listing import ListingRepository
from app.repositories.publication import (
    PublicationAttemptRepository,
    PublicationCampaignRepository,
    PublicationJobRepository,
    PublicationOutboxRepository,
)
from app.repositories.social_account import SocialAccountRepository
from app.services.content_builder import build_variables
from app.services.content_renderer import render_for_platform


def _public_media_urls_for_listing(listing: Listing, *, max_items: int = 10) -> list[str]:
    """Build absolute public URLs for listing images/videos (cover first).

    Instagram Graph requires publicly reachable media URLs.
    """
    from app.config import get_settings

    settings = get_settings()
    base = (settings.s3_public_url or "").rstrip("/")
    media_list = list(getattr(listing, "media", None) or [])
    # Cover first, then order_index
    media_list.sort(
        key=lambda m: (
            0 if getattr(m, "is_cover", False) else 1,
            getattr(m, "order_index", 0) or 0,
        )
    )

    urls: list[str] = []
    for m in media_list:
        kind = getattr(m, "kind", None)
        kind_val = kind.value if hasattr(kind, "value") else str(kind or "image")
        if kind_val not in ("image", "video"):
            continue
        variants = m.variants or {}
        # Prefer platform-ready variants when present
        key = (
            variants.get("instagram")
            or variants.get("web")
            or variants.get("og")
            or variants.get("original")
            or m.original_object_key
        )
        if not key:
            continue
        if str(key).startswith("http://") or str(key).startswith("https://"):
            urls.append(str(key))
        elif base:
            urls.append(f"{base}/{str(key).lstrip('/')}")
        if len(urls) >= max_items:
            break
    return urls


def _active_accounts_for_org(
    accounts: list,
    social_account_ids: list[uuid.UUID] | None,
) -> list:
    """Filter to active IG/X accounts, optionally restricted to selected ids."""
    selected = set(social_account_ids) if social_account_ids else None
    out = []
    for a in accounts:
        if a.provider.value not in ("instagram", "x"):
            continue
        if a.connection_status.value != "active" or a.revoked_at:
            continue
        if selected is not None and a.id not in selected:
            continue
        out.append(a)
    return out


class PublicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.campaign_repo = PublicationCampaignRepository(db)
        self.job_repo = PublicationJobRepository(db)
        self.attempt_repo = PublicationAttemptRepository(db)
        self.outbox_repo = PublicationOutboxRepository(db)
        self.listing_repo = ListingRepository(db)
        self.template_repo = ContentTemplateRepository(db)
        self.social_account_repo = SocialAccountRepository(db)

    async def create_campaign(
        self,
        org_id: uuid.UUID,
        listing_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
        auto_distribute: bool = False,
        scheduled_at: datetime | None = None,
        account_overrides: dict | None = None,
        social_account_ids: list[uuid.UUID] | None = None,
    ) -> PublicationCampaign:
        listing = await self.listing_repo.get_by_id(org_id, listing_id)
        if not listing:
            raise ValueError("Listing not found")

        from sqlalchemy import select

        from app.models import ListingVersion

        result = await self.db.execute(
            select(ListingVersion).where(
                ListingVersion.listing_id == listing_id,
            ).order_by(ListingVersion.version_number.desc()).limit(1)
        )
        listing_version = result.scalar_one_or_none()
        listing_version_id = listing_version.id if listing_version else None

        campaign = await self.campaign_repo.create(
            org_id=org_id,
            listing_id=listing_id,
            created_by=created_by,
            listing_version_id=listing_version_id,
            auto_distribute=auto_distribute,
            account_overrides=account_overrides,
            campaign_kind="listing",
        )

        all_accounts = await self.social_account_repo.list_for_org(org_id)
        accounts = _active_accounts_for_org(all_accounts, social_account_ids)
        if not accounts:
            raise ValueError(
                "No active Instagram or X accounts selected. "
                "Connect accounts and select at least one destination."
            )

        variables = build_variables(listing)
        default_media_urls = _public_media_urls_for_listing(listing)

        for account in accounts:
            templates = await self.template_repo.list_for_org(
                org_id=org_id,
                platform=account.provider,
                limit=1,
            )
            default_template = next((t for t in templates if t.is_default), templates[0] if templates else None)

            # Check for account-level overrides in the campaign
            override = None
            if campaign.account_overrides:
                override = campaign.account_overrides.get(str(account.id))

            # Resolve body and title templates: override takes precedence, then fall back to default
            body_template_str = None
            title_template_str = None
            media_urls = list(default_media_urls)

            if override:
                body_template_str = override.get("body_template")
                title_template_str = override.get("title_template")
                if override.get("media_urls"):
                    media_urls = list(override["media_urls"])

            # Platform media caps
            if account.provider.value == "x":
                media_urls = media_urls[:4]
            elif account.provider.value == "instagram":
                media_urls = media_urls[:10]

            if not body_template_str and default_template:
                body_template_str = default_template.body_template
            if not title_template_str and default_template:
                title_template_str = default_template.title_template

            # Fallback body if no template configured
            if not body_template_str:
                body_template_str = (
                    "{{ title }} — {{ price_formatted }}\n"
                    "{{ city }}{% if locality %}, {{ locality }}{% endif %}\n"
                    "{{ public_url }}"
                )

            idempotency_key = f"pub_{campaign.id}_{account.id}"

            job = await self.job_repo.create(
                campaign_id=campaign.id,
                social_account_id=account.id,
                template_id=default_template.id if default_template else None,
                idempotency_key=idempotency_key,
                scheduled_at=scheduled_at,
            )

            render_result = render_for_platform(
                body_template=body_template_str,
                variables=variables,
                platform=account.provider,
                title_template=title_template_str,
            )
            if not render_result.errors:
                await self.job_repo.update_status(
                    job,
                    job.status,
                    rendered_title=render_result.title,
                    rendered_body=render_result.body,
                    media_urls=media_urls or None,
                )
            else:
                await self.job_repo.update_status(
                    job,
                    job.status,
                    media_urls=media_urls or None,
                    error_code="render_error",
                    error_message="; ".join(render_result.errors)[:1000],
                )

            if auto_distribute:
                await self._enqueue_approval(job, created_by)

        await self.db.refresh(campaign, ["jobs"])
        return campaign

    async def create_quick_post(
        self,
        org_id: uuid.UUID,
        *,
        body: str,
        media_urls: list[str],
        social_account_ids: list[uuid.UUID],
        title: str | None = None,
        created_by: uuid.UUID | None = None,
        auto_distribute: bool = False,
        scheduled_at: datetime | None = None,
    ) -> PublicationCampaign:
        """Freeform multi-account post (no listing required)."""
        body = (body or "").strip()
        media_urls = [u.strip() for u in (media_urls or []) if u and str(u).strip()]
        if not body and not media_urls:
            raise ValueError("Quick post requires caption text and/or media URLs")
        if not social_account_ids:
            raise ValueError("Select at least one social account")

        all_accounts = await self.social_account_repo.list_for_org(org_id)
        accounts = _active_accounts_for_org(all_accounts, social_account_ids)
        if not accounts:
            raise ValueError("None of the selected accounts are active Instagram/X destinations")

        # Instagram Graph cannot create a feed post without a public media URL
        has_instagram = any(a.provider.value == "instagram" for a in accounts)
        if has_instagram and not media_urls:
            raise ValueError(
                "Instagram requires at least one public image or video. "
                "Upload a poster/photo in Quick Post (or pick from the media library), "
                "then select it before creating the campaign."
            )

        campaign = await self.campaign_repo.create(
            org_id=org_id,
            listing_id=None,
            created_by=created_by,
            listing_version_id=None,
            auto_distribute=auto_distribute,
            account_overrides=None,
            campaign_kind="quick_post",
            title=title,
            body=body,
            media_urls=media_urls,
        )

        for account in accounts:
            media_for_account = list(media_urls)
            if account.provider.value == "x":
                media_for_account = media_for_account[:4]
            elif account.provider.value == "instagram":
                media_for_account = media_for_account[:10]

            idempotency_key = f"qp_{campaign.id}_{account.id}"
            job = await self.job_repo.create(
                campaign_id=campaign.id,
                social_account_id=account.id,
                template_id=None,
                idempotency_key=idempotency_key,
                scheduled_at=scheduled_at,
            )
            await self.job_repo.update_status(
                job,
                job.status,
                rendered_title=title,
                rendered_body=body,
                media_urls=media_for_account or None,
            )
            if auto_distribute:
                await self._enqueue_approval(job, created_by)

        await self.db.refresh(campaign, ["jobs"])
        return campaign

    async def approve_job(
        self,
        job: PublicationJob,
        approved_by: uuid.UUID,
    ) -> PublicationJob:
        if job.status not in (JobStatus.pending_approval,):
            raise ValueError(f"Cannot approve job in status {job.status.value}")

        now = datetime.now(UTC)
        job = await self.job_repo.update_status(
            job,
            JobStatus.approved,
            approved_at=now,
            approved_by=approved_by,
        )

        await self._emit_event("job.approved", job)

        if not job.scheduled_at or job.scheduled_at <= now:
            await self._enqueue_job(job)

        return job

    async def reject_job(
        self,
        job: PublicationJob,
    ) -> PublicationJob:
        if job.status not in (JobStatus.pending_approval,):
            raise ValueError(f"Cannot reject job in status {job.status.value}")

        job = await self.job_repo.update_status(job, JobStatus.rejected)
        await self._emit_event("job.rejected", job)
        return job

    async def retry_job(
        self,
        job: PublicationJob,
    ) -> PublicationJob:
        if job.status not in (JobStatus.failed,):
            raise ValueError(f"Cannot retry job in status {job.status.value}")

        if job.retry_count >= job.max_retries:
            raise ValueError("Max retries reached")

        job = await self.job_repo.update_status(
            job,
            JobStatus.queued,
            retry_count=job.retry_count + 1,
            error_code=None,
            error_message=None,
        )

        await self._enqueue_job(job)
        return job

    async def cancel_job(
        self,
        job: PublicationJob,
    ) -> PublicationJob:
        if job.status in (JobStatus.published, JobStatus.partially_published, JobStatus.cancelled):
            raise ValueError(f"Cannot cancel job in status {job.status.value}")

        job = await self.job_repo.update_status(job, JobStatus.cancelled)
        await self._emit_event("job.cancelled", job)
        return job

    async def execute_job(self, job: PublicationJob) -> PublicationJob:
        import time

        import structlog

        logger = structlog.get_logger(__name__)

        account = job.social_account
        if not account:
            await self._fail_job(job, "account_not_found", "Social account not found")
            return job

        provider = account.provider.value
        if provider not in ("instagram", "x"):
            await self._fail_job(
                job,
                "unsupported_provider",
                f"Provider '{provider}' is not supported for live publishing. Use Instagram or X.",
            )
            return job

        if account.connection_status and account.connection_status.value in ("revoked", "expired"):
            await self._fail_job(
                job,
                "account_inactive",
                f"Social account is {account.connection_status.value}; reconnect before publishing.",
            )
            return job

        try:
            connector = get_connector(provider)
        except KeyError as exc:
            await self._fail_job(job, "unsupported_provider", str(exc))
            return job

        credentials = account.credentials
        if not credentials:
            await self._fail_job(job, "missing_credentials", "OAuth credentials not found for account")
            return job

        # Refresh token if expired (or about to expire within 60s)
        expires_at = credentials.expires_at
        if expires_at:
            expires_at_utc = (
                expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
            )
            now = datetime.now(UTC)
            if expires_at_utc <= now + timedelta(seconds=60):
                logger.info("token_refresh_attempt", account_id=str(account.id), provider=provider)
                refresh_result = await connector.refresh_token(account, credentials)
                if refresh_result and "access_token" in refresh_result:
                    from app.repositories.encrypted_credentials import (
                        EncryptedCredentialsRepository,
                    )

                    creds_repo = EncryptedCredentialsRepository(self.db)
                    expires_at_dt = None
                    if refresh_result.get("expires_at"):
                        expires_at_dt = datetime.fromisoformat(refresh_result["expires_at"])
                    await creds_repo.create_or_update(
                        social_account_id=account.id,
                        access_token=refresh_result["access_token"],
                        refresh_token=refresh_result.get("refresh_token"),
                        expires_at=expires_at_dt,
                        token_type=credentials.token_type,
                        scope=credentials.scope,
                    )
                    await self.db.refresh(credentials)
                elif expires_at_utc <= now:
                    await self._fail_job(job, "token_expired", "Token expired and refresh failed")
                    return job

        # Multi-item content (X threads): each item is published sequentially.
        # For X, later tweets reply to the previous tweet id.
        has_content_items = bool(job.content_items and len(job.content_items) > 0)

        if has_content_items:
            items_to_publish = list(job.content_items)
        else:
            items_to_publish = [{
                "title": job.rendered_title,
                "body": job.rendered_body,
                "media_urls": job.media_urls or [],
                "order": 0,
            }]

        await self.job_repo.update_status(job, JobStatus.publishing)

        attempt_number = (job.retry_count or 0) + 1

        # results: (success, error_code, error_message, provider_id)
        results: list[tuple[bool, str | None, str | None, str | None]] = []
        previous_provider_id: str | None = None

        for item in items_to_publish:
            content = {
                "title": item.get("title"),
                "body": item.get("body"),
                "media_urls": item.get("media_urls") or job.media_urls or [],
            }
            if provider == "x" and previous_provider_id:
                content["in_reply_to_tweet_id"] = previous_provider_id

            start = time.monotonic()

            try:
                result = await connector.publish(account, credentials, content)

                duration_ms = int((time.monotonic() - start) * 1000)

                await self.attempt_repo.create(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    status=AttemptStatus.success.value,
                    request_payload=content,
                    response_payload=result,
                    duration_ms=duration_ms,
                )

                provider_id = str(result.get("id", "")) if result else ""
                if provider_id:
                    previous_provider_id = provider_id
                results.append((True, None, None, provider_id or None))

            except Exception as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                error_message = str(exc)
                error_code = getattr(exc, "code", None) or type(exc).__name__

                await self.attempt_repo.create(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    status=AttemptStatus.failed.value,
                    request_payload=content,
                    error_code=error_code,
                    error_message=error_message,
                    duration_ms=duration_ms,
                )

                results.append((False, error_code, error_message, None))
                # Stop thread on first failure so we don't orphan replies
                if provider == "x" and len(items_to_publish) > 1:
                    break

        # Determine final status from aggregate results
        successes = sum(1 for r in results if r[0])
        total = len(results)

        if successes == total:
            # All succeeded
            now = datetime.now(UTC)
            provider_ids = [r[3] for r in results if r[3]]
            job = await self.job_repo.update_status(
                job,
                JobStatus.published,
                published_at=now,
                provider_job_id=provider_ids[0] if provider_ids else None,
            )

            if account:
                from app.repositories.social_account import SocialAccountRepository
                sa_repo = SocialAccountRepository(self.db)
                await sa_repo.update(account, last_successful_publication_at=now)

            await self._emit_event("job.published", job)

        elif successes == 0:
            # All failed — retry logic as before
            errors = [r for r in results if not r[0]]
            combined_error = "; ".join(f"[{r[1]}]: {r[2]}" for r in errors)
            should_retry = job.retry_count < job.max_retries
            new_status = JobStatus.queued if should_retry else JobStatus.failed

            job = await self.job_repo.update_status(
                job,
                new_status,
                error_code=errors[0][1] if errors else "unknown",
                error_message=combined_error[:1000],
                retry_count=job.retry_count + 1 if should_retry else job.retry_count,
            )

            if not should_retry:
                await self._emit_event("job.failed", job)

        else:
            # Partial success — some items succeeded, others failed
            now = datetime.now(UTC)
            failed_items = "; ".join(
                f"[item {idx}][{r[1]}]: {r[2]}"
                for idx, r in enumerate(results)
                if not r[0]
            )

            job = await self.job_repo.update_status(
                job,
                JobStatus.partially_published,
                published_at=now,
                error_code="partial_failure",
                error_message=failed_items[:1000],
            )

            if account:
                from app.repositories.social_account import SocialAccountRepository
                sa_repo = SocialAccountRepository(self.db)
                await sa_repo.update(account, last_successful_publication_at=now)

            await self._emit_event("job.partially_published", job)

        return job

    async def _enqueue_job(self, job: PublicationJob) -> None:
        await self.job_repo.update_status(job, JobStatus.queued)
        await self._emit_event("job.queued", job)
        # Dispatch Celery immediately so jobs do not wait for beat/outbox poll
        try:
            from app.worker.tasks import execute_job, process_outbox

            execute_job.delay(str(job.id))
            process_outbox.delay()
        except Exception:
            # Outbox + beat remain as fallback if broker is briefly unavailable
            import structlog

            structlog.get_logger(__name__).warning(
                "celery_dispatch_failed",
                job_id=str(job.id),
                exc_info=True,
            )

    async def _enqueue_approval(self, job: PublicationJob, approved_by: uuid.UUID | None) -> None:
        if approved_by:
            await self.approve_job(job, approved_by)
        else:
            await self._enqueue_job(job)

    async def _fail_job(self, job: PublicationJob, error_code: str, error_message: str) -> None:
        await self.job_repo.update_status(
            job,
            JobStatus.failed,
            error_code=error_code,
            error_message=error_message,
        )

    async def _emit_event(self, event_type: str, job: PublicationJob) -> None:
        await self.outbox_repo.create(
            event_type=event_type,
            aggregate_type="publication_job",
            aggregate_id=job.id,
            payload={
                "job_id": str(job.id),
                "campaign_id": str(job.campaign_id),
                "status": job.status.value,
                "social_account_id": str(job.social_account_id),
            },
            organization_id=job.campaign.organization_id,
        )
