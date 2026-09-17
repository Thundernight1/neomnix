#!/usr/bin/env bash
set -euo pipefail
for var in DATABASE_URL REDIS_URL JWT_SECRET_KEY; do
    if [[ -z "${!var:-}" ]]; then
        printf '[startup] Missing configuration: %s\n' "$var" >&2
        exit 1
    fi
done
python -c 'from src.api.auth import init_auth_settings; init_auth_settings(); from src.db.models import engine; from sqlalchemy import text; conn = engine.connect(); conn.execute(text("SELECT 1")); conn.close()'
alembic upgrade head
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop --http httptools --log-level info
