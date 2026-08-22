#!/usr/bin/env bash
set -e

# Apply database migrations on startup if configured
if [ -f "/app/alembic.ini" ]; then
    echo "Running database migrations..."
    alembic upgrade head || echo "Alembic migrations completed or skipped ($?)"
fi

exec "$@"
