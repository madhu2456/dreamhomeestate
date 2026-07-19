# Implementation checklist

## Phase 0: Audit and planning

- [x] Inspect repository (empty)
- [x] Define architecture and stack
- [x] Define data model
- [x] Define social provider architecture
- [x] Create initial documentation

## Phase 1: Foundation

- [ ] Directory structure and packages
- [ ] Docker Compose (postgres, redis, minio, api, web, worker, nginx optional)
- [ ] `packages/config` environment loader
- [ ] `services/api` FastAPI project layout
- [ ] SQLAlchemy base models, async engine, session
- [ ] Alembic configuration and first migration
- [ ] User model, password hashing, password reset token flow
- [ ] Session middleware, dependency-injection protected routes
- [ ] Organization model, memberships, roles
- [ ] CLI to create owner and seed organization
- [ ] Health and readiness endpoints
- [ ] Structured logging with correlation ID
- [ ] `apps/web` Next.js project with Tailwind, shadcn/ui, Zod, React Hook Form
- [ ] Auth UI: login, logout, password reset request
- [ ] Admin layout with role-based navigation guards

## Phase 2: Listings and website

- [ ] Listing model, enums, lifecycle state machine
- [ ] Listing CRUD API
- [ ] Listing repository with organization scoping and slug uniqueness
- [ ] Listing media model and upload endpoint (image only for MVP, video optional behind flag)
- [ ] S3/MinIO service with presigned URLs
- [ ] Image validation (mime, signature, size, dimensions)
- [ ] Image processing with Pillow (thumbnails, OG, Instagram, X variants)
- [ ] Media ordering and cover selection API
- [ ] Public listing index with filters, pagination, empty states
- [ ] Public listing detail page with SEO, structured data, share actions
- [ ] Contact inquiry form with spam/rate-limit guards
- [ ] Sitemap and robots

## Phase 3: Social connections

- [ ] Social account model and encrypted OAuth credentials table
- [ ] Fernet encryption utilities and key management
- [ ] OAuth state store in Redis with PKCE
- [ ] Instagram OAuth route and callback
- [ ] X/Twitter OAuth 2.0 route and callback
- [ ] Connector registry and base interface
- [ ] Instagram connector, mock mode
- [ ] X/Twitter connector, mock mode
- [ ] Validate/revoke/test connection endpoints
- [ ] Admin social accounts page

## Phase 4: Content and previews

- [ ] Canonical content object builder from listing version
- [ ] Template model and version history
- [ ] Sandbox Jinja2 renderer with allowed variable allow-list
- [ ] Unresolved variable validation
- [ ] Account override storage on campaign destinations
- [ ] Platform-specific renderers (Instagram caption, X post/thread)
- [ ] Length calculator per provider using capability snapshot
- [ ] Destination preview builder with warnings/errors
- [ ] UTM generator

## Phase 5: Publication engine

- [ ] Campaign and campaign destination models
- [ ] Publication job state machine
- [ ] Publication attempt immutable logging
- [ ] Idempotency key generation
- [ ] Outbox event handling in same transaction as publish
- [ ] Celery worker tasks: outbox processor, job processor
- [ ] Redis locks for job leases
- [ ] Token refresh before publish
- [ ] Error classification and retry policy
- [ ] Partial success handling (threads, carousels)
- [ ] Status dashboard UI
- [ ] Retry and cancel endpoints

## Phase 6: Production hardening

- [ ] Audit event logging for every important action
- [ ] Webhook endpoints for Instagram and X with signature validation
- [ ] CSP, security headers, CORS, CSRF
- [ ] Rate limiting
- [ ] Feature flags service
- [ ] Error monitoring integration point
- [ ] Metrics/logging runbooks
- [ ] Backup/restore docs
- [ ] CI/CD workflow skeleton

## Phase 7: QA

- [ ] Backend unit tests
- [ ] Integration tests (DB, outbox, retry, idempotency)
- [ ] Frontend tests
- [ ] E2E test covering full publish flow with mocks
- [ ] Migrations on clean DB
- [ ] Production container builds
- [ ] Lint/typecheck pass

## Documentation

- [ ] README.md
- [ ] docs/architecture.md
- [ ] docs/data-model.md
- [ ] docs/social-provider-architecture.md
- [ ] docs/instagram-setup.md
- [ ] docs/x-setup.md
- [ ] docs/oauth-security.md
- [ ] docs/publishing-state-machine.md
- [ ] docs/idempotency-and-retries.md
- [ ] docs/media-processing.md
- [ ] docs/deployment.md
- [ ] docs/backup-and-restore.md
- [ ] docs/operations-runbook.md
- [ ] docs/security-review.md
- [ ] docs/testing.md
- [ ] docs/known-limitations.md
