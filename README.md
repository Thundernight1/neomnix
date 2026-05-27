# Neomnix — AI-Powered Multi-Framework Compliance Platform

> Scan once. Map everywhere. Stay compliant.

Neomnix is an AI-driven GRC (Governance, Risk & Compliance) platform that automatically maps security vulnerabilities to multiple compliance frameworks simultaneously — HIPAA, SOC2, NIST-800-53, WA-MHMDA, CCM-4.0, and SEC-2023 — from a single scan.

[![CI](https://github.com/Thundernight1/neomnix/actions/workflows/ci.yml/badge.svg)](https://github.com/Thundernight1/neomnix/actions)

---

## How It Works

1. **Scan** — Target a domain/IP or upload a PCAP file
2. **Detect** — Scanner agents find vulnerabilities and misconfigurations
3. **Map** — CrossMap engine maps every finding to relevant compliance controls across all frameworks using TF-IDF cosine similarity + Jaccard keyword matching
4. **Report** — PDF and JSON reports generated per framework, audit-ready

---

## Features

### Multi-Framework Cross-Mapping
- Every finding is automatically mapped to HIPAA, SOC2, NIST-800-53, WA-MHMDA, CCM-4.0, and SEC-2023 controls in a single pass
- Scoring engine: 60% semantic similarity + 30% keyword match + 10% expert weight
- Auto-match (≥0.75), review-required (≥0.50), or unique buckets assigned per mapping
- Full N×N framework overlap matrix computed via SQL

### SharkTap — Passive Network Analysis
- Upload `.pcap`, `.pcapng`, or `.cap` files via `POST /scan/pcap`
- Detects DNS tunneling, unencrypted database traffic, FTP/Telnet sessions, large data exfiltration patterns
- All detected threats fed directly into the compliance pipeline

### Gap Analysis
- `POST /api/gap/analyze` — triggers async gap analysis via Celery worker
- Identifies missing UCL controls against target frameworks
- AI-generated remediation recommendations per gap
- `GET /api/gap/report/{org_id}` — returns full report with framework filter support

### Cloud Security Posture Management (CSPM)
- Prowler-powered scanning for AWS, Azure, and GCP
- Triggered via natural language: `"scan aws"`, `"check azure security"`
- Results returned with failed check counts and report path

### AI Hub — Natural Language Command Routing
- `POST /command` accepts plain English instructions
- Intent detection routes to: `scanner`, `cross_mapper`, `cloud_scanner`, or `llm` agent
- Ollama LLM integration for explain and chat commands

### Compliance Scoring
- Real-time score computed from scan findings
- Critical finding: −15 pts | High: −8 pts | Medium: −3 pts
- Partial recovery bonus (up to +10 pts) based on control mapping coverage
- Score clamped to [0, 100]

### PDF & Markdown Reports
- Auto-generated per framework after every scan
- Download via `GET /reports/pdf/{job_id}/{framework}`
- Supported frameworks: `HIPAA-2026`, `WA-MHMDA`, `NIST-800-53`, `SOC2`

### Security & Auth
- JWT-based authentication with role hierarchy: `admin` / `analyst` / `viewer`
- Multi-tenancy: every user is fully isolated to their own tenant
- Rate limiting: 200 req/min global, 10 req/min on login
- Production CORS enforcement (`ALLOWED_ORIGINS` required, `*` rejected)
- Full audit trail on every action (scan, login, download, command)

### Billing (Stripe)
- Opt-in via `STRIPE_ENABLED=true`
- Webhook signature verification included
- `GET /billing/status` for live configuration status

---

## Quick Start

```bash
# Copy environment file
cp secrets.env.example .env

# Start all services
docker compose up -d

# Follow logs
docker logs -f neomnix-api
docker logs -f neomnix-worker

# Stop
docker compose down
```

---

## Services

| Service  | Port | Description                   |
|----------|------|-------------------------------|
| API      | 8000 | FastAPI backend               |
| Frontend | 3000 | React + Vite web UI           |
| Redis    | 6379 | Celery message broker         |
| ZAP      | 8080 | OWASP ZAP security scanner    |
| Worker   | —    | Celery async task processor   |

---

## Environment Variables

| Variable                 | Required | Description                                         |
|--------------------------|----------|-----------------------------------------------------|
| `JWT_SECRET_KEY`         | ✅        | Secret key for JWT signing                          |
| `ADMIN_DEFAULT_PASSWORD` | ✅        | Initial admin password (when `SEED_ADMIN=true`)     |
| `ADMIN_EMAIL`            |          | Admin email address (default: `admin@neomnix.io`)  |
| `DATABASE_URL`           |          | PostgreSQL connection URL                           |
| `REDIS_URL`              |          | Redis connection URL                                |
| `OLLAMA_API_KEY`         |          | LLM API key for AI commands                        |
| `ZAP_API_KEY`            |          | OWASP ZAP API key                                   |
| `STRIPE_ENABLED`         |          | Set `true` to enable billing                        |
| `STRIPE_API_KEY`         |          | Stripe secret key                                   |
| `STRIPE_WEBHOOK_SECRET`  |          | Stripe webhook signing secret                       |
| `ALLOWED_ORIGINS`        | ✅ prod   | Comma-separated CORS origins (required in prod)     |
| `APP_ENV`                |          | `development` / `production` / `test`               |
| `SEED_ADMIN`             |          | `true` to auto-create default admin on startup      |

---

## API Reference

### Authentication

| Method | Endpoint                | Auth         | Description                  |
|--------|-------------------------|--------------|------------------------------|
| POST   | `/auth/login`           | Public       | Obtain JWT token             |
| POST   | `/auth/register`        | Admin        | Create a new user            |
| GET    | `/auth/me`              | Authenticated| Get current user info        |
| POST   | `/auth/change-password` | Authenticated| Update password              |

### Scanning

| Method | Endpoint          | Auth            | Description                          |
|--------|-------------------|-----------------|--------------------------------------|
| POST   | `/scan`           | Admin / Analyst | Start a scan (`quick`/`deep`/`full`) |
| GET    | `/scan/{job_id}`  | Authenticated   | Get scan status and results          |
| GET    | `/scans`          | Viewer+         | List scan history (paginated)        |
| POST   | `/scan/pcap`      | Admin / Analyst | Upload and analyze a PCAP file       |
| POST   | `/command`        | Authenticated   | Execute a natural language AI command|

### Reports

| Method | Endpoint                              | Auth          | Description                      |
|--------|---------------------------------------|---------------|----------------------------------|
| GET    | `/reports/pdf/{job_id}/{framework}`   | Authenticated | Download PDF compliance report   |
| GET    | `/stats`                              | Authenticated | Dashboard aggregated statistics  |

### Gap Analysis

| Method | Endpoint                    | Auth          | Description                         |
|--------|-----------------------------|---------------|-------------------------------------|
| POST   | `/api/gap/analyze`          | Authenticated | Start gap analysis (async)          |
| GET    | `/api/gap/results/{task_id}`| Authenticated | Poll gap analysis result            |
| GET    | `/api/gap/report/{org_id}`  | Authenticated | Retrieve full gap report            |

### Admin & System

| Method | Endpoint         | Auth    | Description                    |
|--------|------------------|---------|--------------------------------|
| GET    | `/audit/logs`    | Admin   | View audit trail               |
| GET    | `/billing/status`| Public  | Stripe billing configuration   |
| POST   | `/billing/webhook`| Stripe | Handle Stripe webhook event    |
| GET    | `/health`        | Public  | Health check                   |

---

## Supported Compliance Frameworks

| Framework   | Full Name                                            | Region |
|-------------|------------------------------------------------------|--------|
| HIPAA-2026  | Health Insurance Portability and Accountability Act  | US     |
| WA-MHMDA    | Washington My Health My Data Act                     | US-WA  |
| NIST-800-53 | NIST Special Publication 800-53 Security Controls    | US Fed |
| SOC2        | Service Organization Control 2                       | Global |
| CCM-4.0     | Cloud Security Alliance Cloud Controls Matrix        | Global |
| SEC-2023    | SEC Cybersecurity Disclosure Rules (2023)            | US     |

---

## Local Development

**Backend**
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
uvicorn src.api.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Celery Worker**
```bash
cd backend
celery -A src.worker.tasks worker --loglevel=info
```

---

## Testing

```bash
cd backend

# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=html
```

Test coverage includes: JWT auth, cross-mapping engine, compliance agent, PDF export, billing flag, artifact serialization, LLM disabled mode, production readiness, and E2E flows.

---

## Default Admin Credentials

```
Email:    admin@neomnix.io   (or ADMIN_EMAIL env variable)
Password: set via ADMIN_DEFAULT_PASSWORD
```

> Password change is enforced on first login.

---

## Database Reset

```bash
docker compose down -v
docker compose up -d
```

---

## CI/CD

GitHub Actions runs on every push to `main`:
- Docker Compose syntax validation
- Dockerfile build verification
- Test suite

Pipeline status: [GitHub Actions](https://github.com/Thundernight1/neomnix/actions)

---

## License

Proprietary. All rights reserved.
