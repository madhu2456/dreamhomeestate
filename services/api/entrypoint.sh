#!/bin/sh
set -e
cd /app/services/api

# Only the API process should migrate (workers/beat use the same image).
if [ "$1" = "uvicorn" ]; then
  echo "Running database migrations..."
  alembic upgrade head
  echo "Migrations complete."
fi

exec "$@"
