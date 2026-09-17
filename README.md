# Neomnix

Security evidence analysis using FastAPI, PostgreSQL, Redis/Celery, tshark and a
React/TypeScript interface. This repository is a release candidate, not a legal
compliance certification or an unconditional production-readiness guarantee.
See [the release audit](AUDIT-REPORT.md) for verification results and release gates.

## Implemented workflow

Authenticate with an HttpOnly cookie, change the bootstrap password, upload an
authorized PCAP, process it with a real Celery worker, inspect persisted findings,
and download administrator-only PDF evidence reports. Scan records, audit records
and asynchronous gap tasks are tenant-scoped. Production alerts use tenant-specific
Redis channels. The UI does not use localStorage as proof of authentication.

Framework names are application identifiers. Packet observations and heuristic
scores cannot establish HIPAA or Washington MHMDA compliance, a legal violation,
grant eligibility, or the absence of a breach. Regulatory mapping and report
language require qualified review before customer use.

## Deployment

Requirements: Docker Engine, Docker Compose 2.20 or later, OpenSSL, a real HTTPS
domain, a TLS reverse proxy, persistent storage and an approved backup policy.

From the repository root:

```bash
bash scripts/init-env.sh https://your-domain.example admin@your-domain.example
# Review secrets.env locally. Never commit or share it.
# Set SCAN_ALLOWED_CIDRS only to networks explicitly authorized for testing.
docker compose --env-file secrets.env -f docker-compose.production.yml config --quiet
docker compose --env-file secrets.env -f docker-compose.production.yml build
docker compose --env-file secrets.env -f docker-compose.production.yml up -d
docker compose --env-file secrets.env -f docker-compose.production.yml ps
curl --fail http://127.0.0.1:3000/api/ready
```

The example domain/email above must be replaced. The environment generator creates
independent random secrets with file permissions 0600 and refuses to overwrite an
existing file. Retrieve the bootstrap password locally from that protected file,
sign in through your HTTPS domain, and change it immediately. Then set
`SEED_ADMIN=false`, remove `ADMIN_DEFAULT_PASSWORD` and recreate the API/worker.

The frontend binds only to `127.0.0.1:3000`. Terminate HTTPS at your reverse proxy
and forward traffic there, including WebSocket Upgrade headers and sufficiently
long connection timeouts. Do not expose the database, broker or ZAP to the internet.
Secure cookies intentionally do not support production login over plain HTTP.
The default and beta Compose files include the same production configuration.

API startup waits for database access and runs Alembic with fail-fast behavior.
Back up any existing database before upgrading: historical cleanup migrations
remove legacy fields. Duplicate user emails cause the new uniqueness migration
to stop rather than silently delete data. Review and resolve duplicates first.

## Configuration

`secrets.env.example` documents deployment settings; `frontend/.env.example`
documents the Vite API prefix. The default `/api` is routed by Vite locally and
Nginx in the container. Keep frontend and API on the same origin in production.

Required: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `ALLOWED_ORIGINS`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `ZAP_API_KEY`.
Bootstrap-only: `SEED_ADMIN`, `ADMIN_EMAIL`, `ADMIN_DEFAULT_PASSWORD`.
Operational: `APP_ENV`, `JWT_EXPIRE_MINUTES`, `SCAN_ALLOWED_CIDRS`,
`ZAP_HOST`, `ZAP_PORT`. An empty scan allowlist denies active scans.

Optional AI: `LLM_API_BASE`, `LLM_MODEL`, `REMEDIATION_CACHE_TTL`. The supplied
Compose stack does not deploy Ollama. AI remediation defaults off; requesting it
without a healthy configured service returns an explicit unavailable result,
not fabricated remediation.

Optional PDF settings: `PLATFORM_NAME`, `NEOMNIX_TTF_FONT_PATH`,
`NEOMNIX_TTF_BOLD_PATH`, `NEOMNIX_DISABLE_TTF`. The production image includes
DejaVu fonts. Built-in-font fallback transliterates unsupported characters.

## Local checks

Backend targets Python 3.12; frontend targets Node 22.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
(cd backend && ../.venv/bin/pytest -q)
(cd backend && ../.venv/bin/bandit -r src -q)
.venv/bin/pip install pip-audit
.venv/bin/pip-audit -r backend/requirements.lock
(cd frontend && npm ci && npm run lint && npm test && npm run build)
(cd frontend && npm audit --audit-level=high)
git diff --check
```

`.github/workflows/ci.yml` runs frontend/backend checks, PostgreSQL 17 migrations
and container builds. Local verification does not replace a successful run of
this workflow and a staging deployment.

## Operational boundaries

- Upload only data you are permitted to process. Captures may contain sensitive
  information; define encryption, retention, deletion, access logging and backups.
- Unit-test mocks are intentionally retained for isolated failure-mode testing.
  Production analysis uses actual tshark, database and queue operations.
- No external network scan was performed during this audit. Active Nmap/ZAP
  operations require an explicitly authorized test scope and staging validation.
- Gap analysis requires a reviewed control catalog; an empty or incomplete catalog
  is not evidence of compliance.
- Production TLS, restore drills, load tests, image validation and security/legal
  approval remain release gates, not tasks silently marked complete.
