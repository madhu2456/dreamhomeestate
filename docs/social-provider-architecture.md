# Social provider architecture

## Design goals

- One provider-independent interface.
- Platform differences isolated in connector implementations.
- Capability discovery drives validation, media rules, and content limits.
- **Live-only publishing** for Instagram and X (no mock publish path).
- No browser automation or unofficial APIs.

## Connector interface

`services/api/app/platform/connectors/base.py`:

```python
class SocialPublisher(Protocol):
    provider: str

    async def get_capabilities(self, account: SocialAccount) -> PlatformCapabilities: ...
    async def validate_connection(self, account: SocialAccount) -> ConnectionHealth: ...
    async def validate_content(self, payload: PublishPayload, account: SocialAccount) -> ContentValidation: ...
    async def prepare_media(self, media: list[ListingMedia], account: SocialAccount) -> PreparedMedia: ...
    async def publish(self, payload: PublishPayload, account: SocialAccount, idempotency_key: str) -> PublishResult: ...
    async def get_publication_status(self, provider_post_id: str, account: SocialAccount) -> PublicationStatus: ...
    async def refresh_credentials(self, account: SocialAccount) -> OAuthTokenBundle: ...
    async def revoke_credentials(self, account: SocialAccount) -> bool: ...
    async def normalize_error(self, provider_error: Any) -> ProviderError: ...

class PublishPayload:
    title: str | None
    body: str
    media: list[MediaRef]
    link_url: str | None
    hashtags: list[str]
    alt_text: str | None
    thread_mode: bool = False
    sequence: int = 0
```

`PlatformCapabilities` describes:

- supported post types
- text length rules
- media counts, formats, sizes, aspect ratios
- carousel support
- thread support
- scheduling support
- link handling
- hashtag handling
- required permissions
- async media processing flag

## Instagram connector

- Uses **Instagram API with Instagram Login** (Business/Creator accounts).
- OAuth scopes: `instagram_business_basic`, `instagram_business_content_publish`.
- Tokens are exchanged for long-lived user tokens (~60 days) and refreshed via `ig_refresh_token`.
- Flow:
  1. Validate account via `GET graph.instagram.com/me`.
  2. Require at least one **public** image URL (Instagram fetches the media).
  3. `POST /{ig-user-id}/media` — single image or carousel children + parent.
  4. Poll container `status_code` until `FINISHED`.
  5. `POST /{ig-user-id}/media_publish` with `creation_id`.
  6. Return provider media ID and permalink.

## X/Twitter connector

- Uses the **X API v2** with OAuth 2.0 PKCE user context.
- OAuth scopes: `tweet.read tweet.write users.read offline.access media.write`.
- Flow:
  1. Validate via `GET /2/users/me`.
  2. Optionally download listing image URLs and upload via `upload.twitter.com/1.1/media/upload.json`.
  3. `POST /2/tweets` with text and/or `media_ids`.
  4. For threads (`content_items`), each subsequent tweet sets `reply.in_reply_to_tweet_id`.
  5. Return tweet ID and `https://x.com/{username}/status/{id}`.

## Provider registry

`social_account.provider` maps to a connector class via `ConnectorRegistry`. Adding a new provider means registering a new class and migration for capabilities snapshots.

## Capability snapshots

On connection and periodically, the connector fetches current capabilities and stores them in `social_accounts.capabilities_snapshot`. Validation reads this snapshot rather than hard-coded values.
