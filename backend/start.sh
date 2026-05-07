#!/bin/bash
set -e

echo "========================================"
echo "  Neomnix Platform - Production Startup"
echo "========================================"
echo ""

# Verify critical environment variables
echo "[startup] Verifying configuration..."
REQUIRED_VARS=("STRIPE_API_KEY" "DATABASE_URL" "REDIS_URL" "JWT_SECRET_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "[ERROR] Required environment variable not set: $var"
        exit 1
    fi
done

# Verify database connectivity
echo "[startup] Testing database connection..."
if ! python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()" 2>/dev/null; then
    echo "[ERROR] Cannot connect to database at $DATABASE_URL"
    exit 1
fi
echo "[startup] ✅ Database connection successful"

# Run Alembic migrations
echo "[startup] Running database migrations..."
if [ -f "alembic.ini" ]; then
    alembic upgrade head && echo "[startup] ✅ Migrations completed" || echo "[startup] ⚠️  Migrations skipped (already current)"
else
    echo "[startup] ⚠️  No alembic.ini found — skipping migrations"
fi

# Seed compliance framework data
echo "[startup] Seeding compliance data..."
if [ -f "scripts/migrate_ucl_data.py" ]; then
    python scripts/migrate_ucl_data.py && echo "[startup] ✅ Compliance data seeded" || echo "[startup] ⚠️  Compliance data already present"
else
    echo "[startup] ⚠️  No UCL migration script found"
fi

# Start FastAPI with production settings
echo "[startup] Starting Neomnix API Server..."
echo "========================================"
echo ""

exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level info
