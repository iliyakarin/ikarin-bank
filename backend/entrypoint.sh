#!/usr/bin/env bash
set -e

# Apply database migrations on startup if configured (workers set RUN_MIGRATIONS=0)
if [ "${RUN_MIGRATIONS:-1}" = "1" ] && [ -f "/app/alembic.ini" ]; then
    echo "Running database migrations..."
    alembic upgrade head || echo "Alembic migrations completed or skipped ($?)"
fi

exec "$@"
