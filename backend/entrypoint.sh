#!/bin/sh
# ============================================================================
# Container entrypoint.
#
# If RUN_MIGRATIONS=true (set only on the backend service), apply Alembic
# migrations before starting. This way `docker compose up` on a fresh database
# automatically creates the schema — no manual migration step.
#
# `exec "$@"` then runs whatever CMD/command the container was given (uvicorn
# for the backend, celery for the worker), replacing this shell as PID 1 so
# signals (Ctrl+C, container stop) reach it properly.
# ============================================================================
set -e

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "[entrypoint] Running database migrations (alembic upgrade head)..."
  alembic upgrade head
fi

echo "[entrypoint] Starting: $*"
exec "$@"
