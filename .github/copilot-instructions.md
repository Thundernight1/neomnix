# CyberSurX GRC — Copilot Instructions

## Overview

Neomnix (codename: CyberSurX GRC) is a multi-tenant compliance scanning and reporting platform. It orchestrates security scanners (nmap, OWASP ZAP), AI agents, and compliance mapping engines to produce HIPAA / SOC2 / NIST assessments.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10, FastAPI, SQLAlchemy, Alembic, Celery |
| AI/Orchestration | LangGraph, custom agent framework |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui |
| Data | PostgreSQL (production), SQLite (dev fallback), Redis (Celery broker) |
| Security | OWASP ZAP, nmap, python-jose JWT, bcrypt |
| Infrastructure | Docker Compose (6 services) |

---

## Build, Test, and Lint

### Backend (`/backend`)

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
cd backend && pytest

# Run a single test file
pytest tests/test_auth.py

# Run a single test class
pytest tests/test_auth.py::TestLogin

# Run a single test method
pytest tests/test_auth.py::TestLogin::test_login_success

# Run only unit tests (fast, no external deps)
pytest -m unit

# Run with coverage
pytest --cov=src

# Type checking
mypy src/
```

**Test markers** (defined in `pytest.ini`):
- `unit` — fast, no external dependencies
- `integration` — requires services (Redis, DB, ZAP)
- `slow` — long-running tests
- `asyncio` — async/await tests
- `security` — security-specific tests
- `requires_zap` — needs OWASP ZAP running
- `requires_llm` — needs LLM API access

### Frontend (`/frontend`)

```bash
cd frontend

# Dev server (proxies /api to localhost:8000)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Lint TypeScript/React
npm run lint

# Lint CSS
npx stylelint "src/**/*.{css,scss}"
```

### End-to-End Tests (`/frontend/e2e`)

```bash
cd frontend/e2e
npx cypress open    # interactive mode
npx cypress run     # headless mode
```

### Docker (Full Stack)

```bash
# Start all services
docker compose up -d

# View logs
docker logs -f aegis-api
docker logs -f aegis-worker

# Restart frontend after theme.json changes
docker compose restart frontend

# Tear down completely (including DB volumes)
docker compose down -v
```

---

## High-Level Architecture

### Service Topology

The application runs as 6 Docker Compose services:

| Service | Container Name | Port | Purpose |
|---------|----------------|------|---------|
| API | `aegis-api` | 8000 | FastAPI + Uvicorn (4 workers in prod) |
| Worker | `aegis-worker` | — | Celery worker (concurrency=2) running LangGraph scans |
| Redis | `aegis-redis` | 6379 | Celery broker/backend |
| ZAP | `aegis-zap` | 9080 | OWASP ZAP daemon for web app scanning |
| Frontend | `aegis-frontend` | 3000 | Nginx serving React SPA |
| PostgreSQL | `aegis-postgres` | 5432 | Primary database |

### Backend Architecture

```
src/
├── api/
│   ├── main.py          # FastAPI app, routes, startup logic
│   └── auth.py          # JWT auth, OAuth2, role-based access, audit logging
├── agents/
│   ├── ai_hub.py        # Intent router — maps natural language commands to agents
│   ├── scanner.py       # ScannerAgent — orchestrates nmap + ZAP skills
│   ├── compliance.py    # ComplianceAgent — maps findings to controls
│   ├── dispatch.py      # ScannerDispatcher — bridges API → Celery tasks
│   ├── cross_mapping_analyzer.py
│   ├── cloud_scanner.py
│   └── llm_agent.py
├── core/
│   ├── compliance_rules.json
│   └── recommended_settings.json
├── db/
│   └── models.py        # SQLAlchemy ORM: Tenant, User, ScanJob, AuditLog, etc.
├── models/
│   └── contracts.py     # Pydantic models: VulnerabilityArtifact, ComplianceVerdict, NeomnixState
├── services/
│   └── crossmap_engine.py
├── skills/
│   ├── base.py          # BaseSkill abstract class (all skills extend this)
│   ├── nmap_skill.py
│   ├── zap_skill.py
│   └── sharktap_skill.py
├── utils/
│   └── pdf_exporter.py
└── worker/
    └── tasks.py         # Celery tasks — run_neomnix_scan invokes the LangGraph orchestrator
```

**Agent Orchestration Flow:**
1. API receives scan request → `ScannerDispatcher` creates a `ScanJob` record and queues a Celery task
2. Celery worker (`run_neomnix_scan`) invokes `NeomnixOrchestrator`
3. Orchestrator runs a LangGraph state machine:
   - `scanner_node` → `quality_check_node` → (conditional) → `regulatory_mapper_node`
   - Low confidence triggers a recursive rescan with boosted intensity
4. Results are serialized to the DB and compliance report generated

### Frontend Architecture

```
src/
├── components/
│   ├── Dashboard.tsx
│   ├── CommandCenter.tsx      # Main authenticated landing page
│   ├── LoginScreen.tsx
│   ├── ScanDetail.tsx
│   ├── AuditLog.tsx
│   ├── AICommandTerminal.tsx  # Natural-language command interface
│   ├── ErrorBoundary.tsx
│   └── ui/                    # shadcn/ui components (Button, Card, Input, etc.)
│       ├── GlassCard.tsx      # Custom: glassmorphism card primitive
│       └── NeonButton.tsx     # Custom: glowing button primitive
├── lib/
│   ├── api.ts                 # Fetch wrapper for backend API
│   ├── useTheme.ts            # Runtime white-label theme loader
│   └── utils.ts               # cn() helper for Tailwind class merging
├── App.tsx                    # Router + auth guards + theme init
└── main.tsx
```

---

## Key Conventions

### Backend

**Pydantic Contracts**
All inter-agent data transfer uses strict Pydantic models in `src/models/contracts.py`:
- `VulnerabilityArtifact` — immutable finding with severity, description, evidence
- `ComplianceVerdict` — final assessment with confidence score and mapped controls
- `NeomnixState` — LangGraph `TypedDict` carrying artifacts, context, verdict, confidence

Fields have validators. `VulnerabilityArtifact` rejects ambiguous values like `"unknown"`, `"n/a"`, `"tbd"`.

**Skills Pattern**
Every security tool is a `BaseSkill` subclass implementing `async execute(target, **kwargs)`.
Skills auto-persist raw output to `backend/data/raw/` via `save_data()`.

**Database Access**
- Use `get_db()` FastAPI dependency for request-scoped sessions
- Override in tests via `app.dependency_overrides[get_db] = override_get_db`
- Multi-tenancy: every model has `tenant_id` (except unified control framework tables)

**Authentication**
- JWT bearer tokens via `/auth/login` (OAuth2 password form)
- `get_current_user` dependency extracts user from token
- `require_role("admin", "analyst")` factory restricts endpoints by role
- `force_password_change` flag triggers a modal on first login
- All actions are audit-logged via `log_audit()`

**Environment Variables**
Critical vars for local dev (from `secrets.env.example` or `.env`):
- `JWT_SECRET_KEY` — token signing
- `DATABASE_URL` — defaults to SQLite if unset
- `REDIS_URL` — Celery broker
- `OLLAMA_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` — LLM integration
- `ZAP_API_KEY` — ZAP daemon auth
- `STRIPE_API_KEY` — billing (required in production startup)

### Frontend

**shadcn/ui Setup**
- Config in `components.json` (style: new-york, baseColor: slate)
- Components live in `src/components/ui/`
- Custom primitives (`GlassCard`, `NeonButton`) extend the design system

**Tailwind & Styling**
- Tailwind v4 with `tailwindcss-animate` plugin
- Custom `cyber.*` colors in `tailwind.config.js` (navy, cyan, purple, blue, slate)
- Glassmorphism effects via `bg-glass-gradient` and `backdrop-blur`
- Global CSS variables are applied at runtime by `useTheme()`

**White-Label Theming**
- `theme.json` at repo root configures branding without code changes
- Volume-mounted into the Nginx container at runtime
- Edit `theme.json` → `docker compose restart frontend` to apply
- `useTheme.ts` performs a deep merge of `theme.json` over `DEFAULT_THEME`
- CSS custom properties (`--brand-*`) are injected into `:root`

**Path Aliases**
- `@/` maps to `src/` (configured in `vite.config.ts` and `tsconfig.json`)
- Examples: `import { Button } from "@/components/ui/button"`

**API Client**
- `src/lib/api.ts` wraps `fetch`
- Base URL from `VITE_API_URL` env var; defaults to `/api` (proxied to localhost:8000 in dev)
- Auth token is NOT included in the api client — each component reads `localStorage.getItem('token')` and passes it in headers

**Auth & Routing**
- Auth state stored in `localStorage` (`token`, `force_password_change`)
- Route guards check `isAuthenticated()` inline in `<Route>` elements
- `/` redirects authenticated users to `CommandCenter`, unauthenticated to `/login`

### Testing

**Backend Test Patterns**
- Use in-memory SQLite for test DB fixtures
- Override `get_db` dependency to inject test sessions
- Group related tests in classes (e.g., `TestLogin`, `TestGetMe`)

**Frontend**
- E2E tests in `frontend/e2e/` using Cypress
- No unit test runner configured (no Jest/Vitest in devDependencies)

### Docker & Deployment

**Production Startup**
`backend/start.sh` performs ordered initialization:
1. Verify required env vars (`STRIPE_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`)
2. Test DB connectivity
3. Run Alembic migrations (`alembic upgrade head`)
4. Seed compliance framework data (`scripts/migrate_ucl_data.py`)
5. Start Uvicorn with 4 workers, uvloop, httptools

**Backend Dockerfile**
Based on `python:3.10` (full, not slim) to include GCC/headers for native builds.
System dependencies: `nmap`, `libpq-dev`.

**Frontend Dockerfile**
Builds with Vite, then serves via Nginx.
`theme.json` is volume-mounted so branding changes don't require rebuild.
