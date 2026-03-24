# CyberSurX GRC — Developer Guide

> **Version:** 2.0.0 &nbsp;|&nbsp; **Audience:** Software Engineers & DevOps &nbsp;|&nbsp; **Classification:** Internal / Engineering

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Repository Structure](#2-repository-structure)
3. [Local Development Setup](#3-local-development-setup)
4. [Environment Variables Reference](#4-environment-variables-reference)
5. [Backend Development (FastAPI)](#5-backend-development-fastapi)
6. [Frontend Development (React + Vite)](#6-frontend-development-react--vite)
7. [Worker & Task Queue (Celery + Redis)](#7-worker--task-queue-celery--redis)
8. [Database Schema & Migrations](#8-database-schema--migrations)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Running Tests](#10-running-tests)
11. [CI/CD Pipeline](#11-cicd-pipeline)
12. [Docker & Containerization](#12-docker--containerization)
13. [Adding New Compliance Frameworks](#13-adding-new-compliance-frameworks)
14. [Adding New Scan Agents](#14-adding-new-scan-agents)
15. [API Reference](#15-api-reference)

---

## 1. Architecture Overview

CyberSurX GRC is a **containerized, microservices-style application** composed of five Docker services:

```
┌─────────────────────────────────────────────────────────────┐
│                    User Browser / API Client                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP :3000
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           aegis-frontend  (Nginx + React SPA)               │
│  • Serves static build + theme.json (volume-mounted)         │
│  • Proxies /api/* → aegis-api:8000                          │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP :8000 (proxied)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              aegis-api  (FastAPI + Uvicorn)                  │
│  • REST API, JWT auth, rate limiting                         │
│  • Dispatches Celery tasks to aegis-worker via Redis         │
│  • Reads/writes SQLite (or PostgreSQL) database              │
└──────────────┬────────────────────────┬─────────────────────┘
               │ Celery task dispatch    │ DB read/write
               ▼                         ▼
┌──────────────────────┐   ┌─────────────────────────────────┐
│   aegis-redis        │   │   aegis-worker  (Celery)         │
│   (Task broker +     │   │   • Executes scan jobs           │
│    result backend)   │   │   • Runs Nmap, ZAP agents        │
└──────────────────────┘   │   • Generates PDF reports        │
                            │   • Writes results to DB         │
                            └──────────────┬──────────────────┘
                                           │ ZAP API
                                           ▼
                            ┌─────────────────────────────────┐
                            │   aegis-zap  (OWASP ZAP)        │
                            │   Active web application scanner │
                            └─────────────────────────────────┘
```

### Key Technology Decisions

| Layer | Technology | Rationale |
|---|---|---|
| API | FastAPI 0.100+ | Async-native, auto-generated OpenAPI docs, Pydantic v2 validation |
| Auth | JWT (HS256) via `python-jose` | Stateless, horizontally scalable |
| ORM | SQLAlchemy + Alembic | Database-agnostic; SQLite for dev, PostgreSQL for prod |
| Task Queue | Celery + Redis | Decouples long-running scans from the API response cycle |
| Frontend | React 19 + TypeScript + Vite | Fast HMR, modern bundling |
| Styling | Tailwind CSS v4 + shadcn/ui | Consistent design system with accessible primitives |
| Security Scanning | Nmap + OWASP ZAP | Industry-standard open-source tools |
| PDF Generation | FPDF2 | Lightweight, dependency-free PDF rendering |
| Rate Limiting | SlowAPI | Per-endpoint and per-IP rate limiting |

---

## 2. Repository Structure

```
cybersurx-grc/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   └── src/
│       ├── api/
│       │   ├── main.py         # FastAPI app, endpoints, startup seeding
│       │   └── auth.py         # JWT auth, RBAC, password utilities
│       ├── agents/
│       │   ├── ai_hub.py       # Central agent registry + command dispatcher
│       │   ├── dispatch.py     # Scanner dispatcher (selects tools per target type)
│       │   ├── compliance.py   # Framework compliance analysis agent
│       │   ├── cross_mapping_analyzer.py  # Multi-framework control mapper
│       │   ├── llm_agent.py    # LLM-powered narrative generation agent
│       │   ├── cloud_scanner.py # AWS/Azure CSPM agent (via Prowler)
│       │   └── scanner.py      # Base network scanner agent (Nmap)
│       ├── core/
│       │   ├── compliance_rules.json      # Compliance rule definitions
│       │   └── recommended_settings.json  # Scan configuration presets
│       ├── db/
│       │   └── models.py       # SQLAlchemy ORM models (User, ScanJob, AuditLog)
│       ├── models/
│       │   └── contracts.py    # Pydantic contracts / shared data models
│       ├── skills/
│       │   ├── base.py         # Abstract base class for scanner skills
│       │   ├── nmap_skill.py   # Nmap integration skill
│       │   └── zap_skill.py    # OWASP ZAP integration skill
│       ├── utils/
│       │   └── pdf_exporter.py # PDF report generation (FPDF2)
│       └── worker/
│           └── tasks.py        # Celery task definitions
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf              # Nginx config (SPA + /api/ proxy)
│   ├── package.json
│   ├── vite.config.ts          # Vite + proxy configuration
│   └── src/
│       ├── App.tsx             # Root router + ForcePasswordChangeModal
│       ├── components/
│       │   ├── Dashboard.tsx        # Main dashboard view
│       │   ├── LoginScreen.tsx      # Authentication page
│       │   ├── ScanDetail.tsx       # Per-scan results view
│       │   ├── AuditLog.tsx         # Audit log viewer (admin only)
│       │   ├── AICommandTerminal.tsx # Natural-language AI interface
│       │   ├── ForcePasswordChangeModal.tsx  # First-login security gate
│       │   └── ui/                  # shadcn/ui component library
│       ├── lib/
│       │   ├── api.ts               # Typed API client
│       │   ├── useTheme.ts          # Runtime theme loader hook
│       │   └── utils.ts             # Utility helpers
│       └── main.tsx            # React entry point
│
├── theme.json                  # White-label branding (runtime configurable)
├── docker-compose.yml
├── docker-compose.test.yml     # Test environment overrides
├── .env                        # Runtime secrets (generated by setup scripts)
├── setup.sh                    # One-click deployment (Linux/macOS)
├── setup.bat                   # One-click deployment (Windows)
├── COMMERCIAL_QUICK_START.md   # End-user documentation
├── DEVELOPER_GUIDE.md          # This document
└── LICENSE.md
```

---

## 3. Local Development Setup

### Prerequisites

- Docker Desktop 24+ (for running dependencies)
- Python 3.10+ (`pyenv` recommended)
- Node.js 18+ (`nvm` recommended)

### Backend (FastAPI hot-reload)

```bash
# 1. Start dependencies (Redis, ZAP) via Docker
docker compose up -d redis zap

# 2. Create and activate a Python virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Copy environment file
cp .env.example .env         # Edit values as needed

# 5. Start the API with hot-reload
cd backend
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

### Frontend (Vite HMR)

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Start Vite dev server (proxies /api/ to localhost:8000)
npm run dev
```

The UI will be available at `http://localhost:5173`.

### Celery Worker

```bash
# In a new terminal, from the project root
source .venv/bin/activate
cd backend
celery -A src.worker.tasks worker --loglevel=debug
```

---

## 4. Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./cybersurx.db` | Database connection string. Use `postgresql://user:pass@host/db` for production. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis broker URL for Celery. |
| `ADMIN_EMAIL` | `admin@cybersurx.io` | Email for the seeded admin account. |
| `ADMIN_DEFAULT_PASSWORD` | `CyberSurX2026!` | Temporary password for the seeded admin. Force-change is enforced on login. |
| `JWT_SECRET_KEY` | *(required)* | HS256 HMAC secret. Generate with `openssl rand -hex 32`. **Never use the default in production.** |
| `JWT_EXPIRE_MINUTES` | `480` | Token lifetime in minutes (default: 8 hours). |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS allowed origins. |
| `OLLAMA_API_KEY` | — | API key for your LLM provider. |
| `LLM_MODEL` | `qwen3-coder-next:cloud` | LLM model identifier. |
| `ZAP_API_KEY` | `aegis-zap-secret` | API key for the OWASP ZAP daemon. |

---

## 5. Backend Development (FastAPI)

### Adding a New API Endpoint

```python
# backend/src/api/main.py

@app.get("/my-endpoint")
async def my_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "analyst"))
):
    """Description shown in /docs."""
    log_audit(db, current_user.email, "my_action")
    return {"data": "hello"}
```

### Authentication Pattern

All protected endpoints use FastAPI `Depends()`:

```python
# Require any authenticated user:
current_user: User = Depends(get_current_user)

# Require specific roles:
current_user: User = Depends(require_role("admin"))
current_user: User = Depends(require_role("admin", "analyst"))
```

### Rate Limiting

```python
@app.post("/sensitive-endpoint")
@limiter.limit("5/minute")
async def sensitive(request: Request, ...):
    ...
```

---

## 6. Frontend Development (React + Vite)

### Vite Proxy Configuration

The frontend uses Vite's dev proxy to route `/api/*` to the FastAPI backend. See `frontend/vite.config.ts`.

In production (Docker), the same proxying is handled by Nginx in `frontend/nginx.conf`.

### Theme Integration

Consume the runtime theme in any component:

```typescript
import { useTheme } from '../lib/useTheme';

function MyComponent() {
    const { theme } = useTheme();
    return <h1>{theme.platform.name}</h1>;
}
```

### Adding a New Page

1. Create `frontend/src/components/MyPage.tsx`
2. Add a route in `frontend/src/App.tsx`:
   ```tsx
   <Route path="/my-page" element={<ProtectedRoute><MyPage /></ProtectedRoute>} />
   ```
3. Add navigation in `Dashboard.tsx` or relevant nav component.

---

## 7. Worker & Task Queue (Celery + Redis)

### Adding a New Task

```python
# backend/src/worker/tasks.py
from celery import shared_task

@shared_task(name="my_background_task")
def my_background_task(param: str) -> dict:
    """Long-running background operation."""
    result = do_expensive_work(param)
    return {"status": "done", "result": result}
```

### Dispatching a Task from the API

```python
from src.worker.tasks import my_background_task

# Dispatch (non-blocking):
my_background_task.delay("my_param")
```

### Monitoring Tasks

For a local development dashboard, add Flower:

```bash
celery -A src.worker.tasks flower --port=5555
```

Then visit `http://localhost:5555`.

---

## 8. Database Schema & Migrations

### Current Schema

Three tables are managed by SQLAlchemy:

- **`users`** — Authentication accounts with RBAC roles and `force_password_change` flag
- **`scan_jobs`** — Scan records with JSON `findings` and `compliance_report` columns
- **`audit_logs`** — Append-only audit trail

### Running Migrations (Alembic)

```bash
cd backend

# Generate a new migration after model changes:
alembic revision --autogenerate -m "Add my_column to users"

# Apply all pending migrations:
alembic upgrade head

# Rollback one migration:
alembic downgrade -1
```

### Switching to PostgreSQL

Update `.env`:
```bash
DATABASE_URL=postgresql://aegis_user:strongpassword@db:5432/cybersurx
```

Add a `db` service to `docker-compose.yml`:
```yaml
db:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: aegis_user
    POSTGRES_PASSWORD: strongpassword
    POSTGRES_DB: cybersurx
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U aegis_user"]
    interval: 10s
    retries: 5
```

---

## 9. Authentication & Authorization

### JWT Token Flow

```
Client              FastAPI
  │                    │
  ├── POST /auth/login ──────────────────────────────────►
  │   (form: username, password)                          │
  │                    ◄─────────────── 200 OK ─── TokenResponse
  │   (access_token, role, email,                        │
  │    force_password_change)                             │
  │                    │
  ├── GET /stats ───────────────────────────────────────►
  │   (Authorization: Bearer <token>)                    │
  │                    ◄─────────────── 200 OK ──────────
```

### Password Change Flow

On first login when `force_password_change: true`:

```
Client                FastAPI
  │                      │
  ├── POST /auth/change-password ───────────────────────►
  │   { current_password, new_password }                 │
  │                      │  verify current password      │
  │                      │  hash new password            │
  │                      │  set force_password_change=false
  │                      ◄────────────── 200 OK ─────────
```

### Adding a New Role

1. Update the `User.role` check in `auth.py` if needed
2. Use `require_role("new_role")` in endpoint dependencies
3. The `role` field is a free-form string — no enum constraint in the DB

---

## 10. Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run a specific test file
pytest tests/test_api.py -v

# Run tests matching a keyword
pytest -k "scan" -v
```

Test configuration is in `backend/pytest.ini`. Tests use the in-memory SQLite database and mock external services (Nmap, ZAP, LLM).

---

## 11. CI/CD Pipeline

The GitHub Actions CI/CD pipeline is defined in `.github/`. See `CI_CD_SETUP.md` for the full reference.

### Pipeline Stages

```
Push to branch
  └── Lint & Type Check
        ├── Python: mypy, flake8
        └── TypeScript: tsc --noEmit, eslint
  └── Unit Tests
        └── pytest --cov (must meet 80% threshold)
  └── Build Docker Images
        └── docker compose build
  └── Integration Tests (main branch only)
        └── docker-compose.test.yml up + pytest integration suite
  └── Deploy (tagged releases only)
        └── Push images to registry
```

### Creating a Release

```bash
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin v2.1.0
```

---

## 12. Docker & Containerization

### Rebuilding After Code Changes

```bash
# Rebuild a specific service
docker compose build api
docker compose build frontend

# Rebuild all and restart
docker compose up -d --build
```

### Inspecting Running Containers

```bash
# Shell into the API container
docker exec -it aegis-api bash

# Shell into the frontend (Nginx) container
docker exec -it aegis-frontend sh

# View real-time API logs
docker compose logs -f api
```

### Volumes

| Volume | Mount Path | Contents |
|---|---|---|
| `./backend` | `/app` | Source code (hot-reloaded in dev) |
| `reports_data` | `/app/reports` | Generated PDF reports (persistent) |
| `./theme.json` | `/usr/share/nginx/html/theme.json` | White-label config (runtime) |

---

## 13. Adding New Compliance Frameworks

1. **Define rules** in `backend/src/core/compliance_rules.json`:
   ```json
   {
     "MY_FRAMEWORK": {
       "control_1": { "title": "...", "description": "...", "severity": "high" }
     }
   }
   ```

2. **Extend** `backend/src/agents/compliance.py` to load and apply the new framework rules.

3. **Update** `backend/src/agents/cross_mapping_analyzer.py` to include cross-references.

4. **Add** a PDF template in `backend/src/utils/pdf_exporter.py`.

5. **Add** the framework option to the scan type selector in `frontend/src/components/Dashboard.tsx`.

---

## 14. Adding New Scan Agents

All scan agents inherit from `backend/src/skills/base.py`:

```python
# backend/src/skills/my_scanner.py
from src.skills.base import BaseSkill
from src.models.contracts import ScanResult

class MyScannerSkill(BaseSkill):
    """Custom scanner skill."""

    async def execute(self, target: str, intensity: int) -> ScanResult:
        # Implement scanning logic here
        findings = []
        # ... populate findings ...
        return ScanResult(target=target, findings=findings)
```

Register the agent in `backend/src/api/main.py` `on_startup()`:

```python
from src.skills.my_scanner import MyScannerSkill
ai_hub.register_agent("my_scanner", MyScannerSkill())
```

---

## 15. API Reference

Interactive API documentation is available at runtime:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Core Endpoints Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Authenticate and receive JWT |
| `GET` | `/auth/me` | Any | Get current user info |
| `POST` | `/auth/change-password` | Any | Change password; clears force-reset flag |
| `POST` | `/auth/register` | admin | Create a new user account |
| `POST` | `/scan` | admin, analyst | Initiate a compliance scan |
| `GET` | `/scans` | viewer+ | List recent scans (paginated) |
| `GET` | `/scan/{job_id}` | Any | Get scan status and results |
| `GET` | `/stats` | Any | Dashboard aggregate statistics |
| `GET` | `/reports/pdf/{job_id}/{framework}` | Any | Download PDF report |
| `GET` | `/audit/logs` | admin | View audit trail |
| `POST` | `/command` | Any | Execute AI natural-language command |
| `GET` | `/health` | Public | Service health check |

---

*CyberSurX GRC Developer Guide v2.0.0*  
*Internal Engineering Documentation — Not for Distribution*
