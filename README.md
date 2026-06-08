# Neomnix Healthcare Compliance Tracker

A strictly English platform built exclusively for **HIPAA-2026** and **Washington MHMDA (RCW 19.373)** compliance tracking. All legacy frameworks (SOC2, NIST, SEC, etc.) have been completely removed.

## What it does

Neomnix automates network-level compliance evidence for healthcare vendors that hold federal or state grants. A passive PCAP tap (SharkTap) is matched against HIPAA-2026 and WA-MHMDA rule sets, the most critical findings are pushed to the dashboard over a live WebSocket, and an admin-only PDF audit report is generated per scan.

Three dashboard modules:

- **Active Data Leak Status** — flashing-red warning when a critical data-leak event is in progress.
- **Grant Loss Risk Indicator** — green/red WA-MHMDA compliance state.
- **HIPAA Violation Summary** — breach points from the latest scan.

## Repository layout

```
backend/   FastAPI + SQLAlchemy + Celery. Rule engine, cross-mapping analyzer,
           gap analysis, PDF exporter, WebSocket alert queue, Alembic migrations.
frontend/  React + TypeScript + Vite + Tailwind. Dashboard, login, scan detail,
           audit log, real-time alert overlay. Runtime white-label theme via
           theme.json mounted at /theme.json.
theme.json White-label branding fetched by the frontend at runtime.
```

## Tech stack

- **Backend:** Python 3, FastAPI, SQLAlchemy, Alembic, Celery
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **Database:** PostgreSQL (SQLite for dev/test)
- **Cache / broker:** Redis
- **PDF:** fpdf2 with optional TrueType font registration

## API surface (current)

| Method | Path                                | Role         | Purpose                                |
|--------|-------------------------------------|--------------|----------------------------------------|
| POST   | `/auth/login`                       | public       | Obtain JWT                             |
| POST   | `/auth/register`                    | admin        | Create user                            |
| GET    | `/auth/me`                          | authenticated| Current user                           |
| POST   | `/auth/change-password`             | authenticated| Rotate password                        |
| GET    | `/stats`                            | authenticated| Dashboard aggregates                   |
| GET    | `/reports/pdf/{job_id}/{framework}` | **admin**    | Download executive PDF                 |
| GET    | `/health`                           | public       | Liveness probe                         |
| WS     | `/ws/alerts`                        | authenticated| Live critical-data-leak events        |
| POST   | `/api/gap/analyze`                  | authenticated| Queue gap analysis                     |
| GET    | `/api/gap/results/{task_id}`        | authenticated| Poll gap analysis result               |
| GET    | `/api/gap/report/{org_id}`          | authenticated| Full gap report                        |

Only `HIPAA-2026` and `WA-MHMDA` are accepted at the PDF endpoint. Any other framework string returns 400.

## Local development

### 1. Configure secrets

```bash
cp secrets.env.example secrets.env
# Edit secrets.env — at minimum set JWT_SECRET_KEY (>=32 chars).
```

### 2. Start the stack

```bash
docker compose up -d
docker compose logs -f api
```

### 3. Backend tests (no live services required)

```bash
cd backend
APP_ENV=test pytest
```

Coverage is reported by `pytest --cov=src` and is currently 99% across `auth.py`, `gap.py`, `models.py`, and `pdf_exporter.py`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev      # dev server with HMR
npm run build    # production build → dist/
npm run lint
```

### 5. Database migrations

```bash
cd backend
alembic upgrade head
```

A migration removing the legacy Stripe billing and dead scan-job columns is included under `alembic/versions/`.

## License

Proprietary. All rights reserved. See `LICENSE`.

Unauthorized distribution, copying, modification, or external hosting of this project, via any medium, is prohibited.
