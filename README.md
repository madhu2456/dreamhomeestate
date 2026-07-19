# RealEstateSocial

A production-ready real estate listings communication platform.

Create a listing once, publish it on your public website, and asynchronously distribute it to multiple connected Instagram and X/Twitter accounts.

## Status

This repository implements the MVP described in the product brief:

- Secure, role-based authentication
- Multi-organization scoping
- Listing CRUD with media upload and ordering
- Public listing website with SEO
- Multiple Instagram and X/Twitter OAuth connections per organization (live only)
- Platform-specific social content previews
- Asynchronous publication engine with outbox, idempotency, retries, and partial-success handling
- Live Instagram Graph + X API v2 publishing (no mock publish path)
- Docker-based local development
- Automated tests

## Quick start

```bash
cp .env.example .env
# Edit .env — set Instagram and X OAuth credentials for live multi-account publishing.
docker compose up --build -d
```

Required for live connect/publish:

```bash
INSTAGRAM_APP_ID=...
INSTAGRAM_APP_SECRET=...
INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/v1/social-accounts/instagram/callback
X_CLIENT_ID=...
X_CLIENT_SECRET=...
X_REDIRECT_URI=http://localhost:8000/api/v1/social-accounts/x/callback
LIVE_INSTAGRAM_PUBLISHING=true
LIVE_X_PUBLISHING=true
```

- Public site: http://localhost:3000
- Admin app: http://localhost:3000/admin
- API docs: http://localhost:8000/docs

Run migrations after first start:

```bash
docker compose exec api alembic upgrade head
```

Create the first owner account:

```bash
docker compose exec api python -m app.cli create-owner owner@example.com "First Last" --password "change-me"
```

## Production deploy

Domain: **https://dreamhomeestate.madhudadi.in**

```bash
# On server (once, as root)
export DOMAIN=dreamhomeestate.madhudadi.in
export APP_DIR=/opt/dreamhomeestate
export REPO_URL=https://github.com/madhu2456/dreamhomeestate.git
git clone "$REPO_URL" "$APP_DIR" && cd "$APP_DIR" && chmod +x deploy.sh
sudo DOMAIN=$DOMAIN APP_DIR=$APP_DIR REPO_URL=$REPO_URL ./deploy.sh
certbot --nginx -d dreamhomeestate.madhudadi.in
```

GitHub Actions deploys on push to `main` via `./deploy.sh --update`.  
See [docs/deployment.md](docs/deployment.md) for secrets and full checklist.

## Documentation

- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [Social provider architecture](docs/social-provider-architecture.md)
- [Implementation checklist](docs/implementation-checklist.md)
- [Deployment](docs/deployment.md)

## Local development commands

```bash
# Lint / typecheck backend
docker compose exec api ruff check app tests
docker compose exec api mypy app tests

# Run backend tests
docker compose exec api pytest

# Lint / typecheck frontend
docker compose exec web pnpm lint
docker compose exec web pnpm typecheck

# Run frontend tests
docker compose exec web pnpm test

# Run build
docker compose exec web pnpm build
```

## License

Proprietary. See [LICENSE](LICENSE).
