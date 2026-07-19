# Architecture

## Assumptions

- The repository was empty when work began, so the preferred baseline stack is used.
- Project name: **RealEstateSocial**
- Local development domain: `localhost`; planned production domain is configured via `LIVE_DOMAIN`.
- Live social posting only (Instagram + X). Mock connectors are disabled for connect and publish.
- Official platform APIs only. No browser automation or reverse-engineered endpoints.
- OAuth app credentials (`INSTAGRAM_*`, `X_*`) are required to connect accounts and publish.

## Services

```text
/
├── apps/web/              Next.js (React, TypeScript, Tailwind, shadcn/ui)
├── services/api/          FastAPI (Python, Pydantic, SQLAlchemy, Alembic)
├── services/worker/       Celery worker, reuses services/api code via PYTHONPATH
├── packages/config/       Shared environment validation (Python package)
├── infrastructure/        Docker, reverse proxy samples
├── tests/                 End-to-end and contract tests
├── docker-compose.yml
└── .env.example
```

### Frontend (apps/web)

- Next.js App Router.
- Server Components fetch data from the FastAPI backend using server-side `fetch` with the request cookie.
- Client Components are used only where interactivity is required.
- Tailwind CSS + shadcn/ui components with accessible defaults.
- Zod validates all forms.
- React Hook Form manages complex editor forms.

### Backend (services/api)

- FastAPI with dependency injection.
- PostgreSQL via SQLAlchemy 2.0 async ORM.
- Alembic for migrations.
- Redis for Celery broker/result backend and short-lived OAuth state.
- MinIO for S3-compatible object storage in development; production uses AWS S3 or Cloudflare R2.
- Structured JSON logging with correlation IDs.

### Worker (services/worker)

- Celery worker that processes:
  - Outbox events (`process_outbox_event`)
  - Publication jobs (`process_publication_job`)
  - Media processing (`process_media`)
  - Scheduled triggers, token refresh, cleanup
- Reuses `services/api/app` as a package via `PYTHONPATH`.

## Authentication

- Email/password sessions with bcrypt.
- Signed session cookies (`itsdangerous`) scoped to the backend domain.
- Server-side session records with explicit expiration.
- Role-based access control enforced in FastAPI dependencies and repository layers.
- Owner-only operations protect OAuth credentials, users, and organization settings.

## Multi-organization scoping

- Every row that belongs to an organization stores `organization_id`.
- Repositories always filter by the current membership context.
- Cross-organization access is rejected at the API dependency layer and in repository queries.

## Social publishing

- OAuth per connected account.
- Encrypted token storage (Fernet via cryptography library).
- Provider connector interface in `app/connectors/base.py`.
- Concrete live connectors for Instagram and X/Twitter.
- Capabilities are stored in the database as snapshots so the connector can adapt its behavior.

## Asynchronous distribution

1. Listing transitions to `published` inside a DB transaction.
2. A `Campaign` and per-destination `CampaignDestination` rows are created.
3. An `OutboxEvent` is inserted in the same transaction.
4. The HTTP response returns success for the website.
5. Celery worker processes the outbox event and creates one `PublicationJob` per destination.
6. Each job runs through media preparation, content validation, provider publish, and result persistence independently.

## Idempotency

- Deterministic idempotency keys derived from `organization_id + listing_version_id + account_id + distribution_event_id + sequence`.
- Unique constraint on `platform_posts.idempotency_key`.
- Job leases via Redis locks with timeouts.
- Successful provider post IDs are persisted; retries check them before calling the provider again.

## Extensibility

- New social connectors implement `SocialPublisher`.
- Content templates use a sandboxed Jinja2 environment with allow-listed variables.
- Distribution profiles capture reusable destination/template settings.
- Feature flags gate live posting, AI, scheduling, analytics, etc.
