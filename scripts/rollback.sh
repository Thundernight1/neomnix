#!/bin/bash
# Rollback script for emergency recovery
# Reverts to previous deployment version

set -e

BACKUP_DIR="${BACKUP_DIR:-.}"
ENVIRONMENT="${ENVIRONMENT:-production}"

echo "🔙 CyberSurX Rollback Tool"
echo "==========================="
echo "Environment: $ENVIRONMENT"
echo ""

# Find backups
echo "📁 Available backups:"
if ls $BACKUP_DIR/backup-compose-*.yml 1> /dev/null 2>&1; then
    ls -1t $BACKUP_DIR/backup-compose-*.yml | nl
else
    echo "❌ No backups found in $BACKUP_DIR"
    exit 1
fi
echo ""

# Get user choice
read -p "Select backup number to restore (or 'latest' for most recent): " CHOICE

if [ "$CHOICE" = "latest" ]; then
    BACKUP_FILE=$(ls -t $BACKUP_DIR/backup-compose-*.yml | head -1)
else
    BACKUP_FILE=$(ls -t $BACKUP_DIR/backup-compose-*.yml | sed -n "${CHOICE}p")
fi

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Invalid selection"
    exit 1
fi

echo ""
echo "🔄 Rolling back to: $BACKUP_FILE"
read -p "⚠️  Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "⏳ Stopping current services..."
docker compose down --remove-orphans

echo "📦 Pulling images from backup..."
docker compose -f "$BACKUP_FILE" pull

echo "🚀 Starting services..."
docker compose -f "$BACKUP_FILE" up -d --wait

echo ""
echo "✅ Rollback completed!"
echo ""
echo "Verifying health..."
sleep 5

if curl -f http://localhost:8000/health 2>/dev/null; then
    echo "✅ API is healthy"
else
    echo "⚠️  API health check failed, but container is running"
fi

if curl -f http://localhost:3000 2>/dev/null; then
    echo "✅ Frontend is healthy"
else
    echo "⚠️  Frontend health check failed, but container is running"
fi

echo ""
echo "📊 Current status:"
docker compose ps
