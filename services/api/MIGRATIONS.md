# Migrations

This project uses Alembic with async PostgreSQL (asyncpg driver).

## Quick reference

```bash
# Create a new migration (autogenerate from model changes)
cd services/api
alembic revision --autogenerate -m "description of change"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history

# Generate SQL for review (without applying)
alembic upgrade head --sql
```

## Within Docker

```bash
# Build and start only postgres, then run migrations
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head

# Or if the api container is already running
docker compose exec api alembic upgrade head
```

## Initial migration

The migration `001_initial.py` creates these tables:
- `roles` — reference table for membership roles
- `organizations` — workspace/tenant
- `users` — system identity
- `organization_memberships` — many-to-many user-to-org with role
- `sessions` — server-side session records
- `audit_events` — immutable audit log

It also seeds the `roles` table with: owner, administrator, editor, viewer.

## Environment

Alembic reads `DATABASE_URL` from the environment. In Docker, this is set in `docker-compose.yml`. For local runs, export it or use a `.env` file.

## Note on async driver

`env.py` uses `async_engine_from_config` with `NullPool` for migrations.
The models are imported via `from app.models import *` to ensure all tables
are visible to Alembic's autogenerate.
