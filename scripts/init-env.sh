#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -e secrets.env ]]; then
  echo "Refusing to overwrite secrets.env" >&2
  exit 1
fi
if [[ $# -ne 2 || "$1" != https://* || "$2" != *@* || "$1$2" == *$'\n'* ]]; then
  echo "Usage: bash scripts/init-env.sh https://your-domain admin@your-domain" >&2
  exit 1
fi
umask 077
db_password="$(openssl rand -hex 32)"
jwt_secret="$(openssl rand -hex 48)"
admin_password="$(openssl rand -hex 24)"
zap_secret="$(openssl rand -hex 32)"
{
  printf 'APP_ENV=production\nSEED_ADMIN=true\n'
  printf 'ALLOWED_ORIGINS=%s\nADMIN_EMAIL=%s\n' "$1" "$2"
  printf 'ADMIN_DEFAULT_PASSWORD=%s\n' "$admin_password"
  printf 'POSTGRES_USER=neomnix\nPOSTGRES_DB=neomnix_db\nPOSTGRES_PASSWORD=%s\n' "$db_password"
  printf 'DATABASE_URL=postgresql://neomnix:%s@postgres:5432/neomnix_db\n' "$db_password"
  printf 'JWT_SECRET_KEY=%s\nJWT_EXPIRE_MINUTES=60\n' "$jwt_secret"
  printf 'REDIS_URL=redis://redis:6379/0\n'
  printf 'ZAP_HOST=zap\nZAP_PORT=8080\nZAP_API_KEY=%s\n' "$zap_secret"
  printf 'SCAN_ALLOWED_CIDRS=\nLLM_API_BASE=http://ollama:11434\nLLM_MODEL=llama3\n'
} > secrets.env
echo "Created mode-600 secrets.env. Retrieve the bootstrap password locally."
echo "After the first password change, set SEED_ADMIN=false and remove ADMIN_DEFAULT_PASSWORD."
