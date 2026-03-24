# 📟 Command Reference & Operations Guide

This document lists all the essential commands needed to manage, develop, and maintain the CyberSurX GRC system.

## 🐳 Docker Operations (Recommended)

### Start System
```bash
docker-compose up -d --build
```

### Stop System
```bash
docker-compose down
```

### View Logs
```bash
docker logs -f aegis-api    # API logs
docker logs -f aegis-worker # Scanner logs
```

### Reset Database
```bash
docker-compose down -v
docker-compose up -d
```

---

## 🛠️ Local Development (Manual)

### Backend (FastAPI)
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
uvicorn src.api.main:app --reload --port 8000
```

### Worker (Celery)
```bash
celery -A src.worker.tasks worker --loglevel=info
```

### Frontend (Vite)
```bash
cd frontend
npm run dev
```

---

## 🔐 Administrative Commands

### Reset Admin Password
Environmental variables in `.env` control the seed admin:
- `ADMIN_EMAIL`
- `ADMIN_DEFAULT_PASSWORD`

### Access Audit Logs via CLI
```bash
# Get last 50 audit entries from SQLite directly
sqlite3 data/cybersurx.db "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50;"
```

### Export PDF Reports
Reports are stored in the container at `/app/reports/pdf/`. To copy them to your local machine:
```bash
docker cp hipaasecsoc2-api-1:/app/reports/pdf/. ./exported_reports/
```

---

## 🧪 Testing

### Backend Unit Tests
```bash
PYTHONPATH=. pytest tests/
```

### Deployment Verification
```bash
./scripts/verify_deployment.sh
```
