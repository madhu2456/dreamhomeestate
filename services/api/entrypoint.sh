#!/bin/sh
# API image entrypoint.
# - uvicorn: wait for Postgres, run alembic upgrade head, then start the app
# - celery / other: start as-is (no migrate; deploy.sh also migrates once per deploy)
set -e
cd /app/services/api

wait_for_db() {
  # DATABASE_URL looks like postgresql+asyncpg://user:pass@host:5432/db
  # Use a short Python check so we don't need pg_isready in the image.
  i=0
  while [ "$i" -lt 40 ]; do
    if python - <<'PY'
import os, sys
from urllib.parse import urlparse
url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit(1)
# asyncpg URL → plain for a quick TCP-less SQLAlchemy connect is heavy;
# use socket connect via host/port only.
p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
host = p.hostname or "postgres"
port = p.port or 5432
import socket
s = socket.socket()
s.settimeout(2)
try:
    s.connect((host, port))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
    then
      return 0
    fi
    i=$((i + 1))
    echo "  waiting for database (${i}/40)..."
    sleep 2
  done
  echo "ERROR: database not reachable"
  return 1
}

if [ "$1" = "uvicorn" ]; then
  echo "=== API startup: migrations ==="
  wait_for_db
  echo "Running: alembic upgrade head"
  alembic upgrade head
  echo "Alembic current:"
  alembic current || true
  echo "=== Starting uvicorn ==="
fi

exec "$@"
