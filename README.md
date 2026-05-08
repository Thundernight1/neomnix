# Neomnix - HIPAA SEC SOC2 Compliance Platform

A Docker-based security scanning and compliance reporting system.

## Quick Start

```bash
# Start all services
docker compose up -d

# View logs
docker logs -f aegis-api
docker logs -f aegis-worker

# Stop all services
docker compose down
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| API | 8000 | FastAPI backend |
| Frontend | 3000 | React web UI |
| Redis | 6379 | Message broker |
| ZAP | 8080 | Security scanner |

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key variables:
- `JWT_SECRET_KEY` - Authentication token secret
- `OLLAMA_API_KEY` - LLM API key
- `ZAP_API_KEY` - Security scanner API key

## Local Development

**Backend (FastAPI)**
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
uvicorn src.api.main:app --reload --port 8000
```

**Frontend (React)**
```bash
cd frontend
npm run dev
```

**Worker (Celery)**
```bash
celery -A src.worker.tasks worker --loglevel=info
```

## GitHub Actions

CI/CD pipelines run on every push to `main`:
- Validate docker-compose syntax
- Build Dockerfiles
- Run checks

View status: https://github.com/Thundernight1/HIPAA-SEC-SOC2/actions

## Admin Access

Default admin account:
- Email: `admin@neomnix.io`
- Password: Set in `.env` as `ADMIN_DEFAULT_PASSWORD`

Change on first login.

## Database

SQLite by default at `./neomnix.db`

Reset:
```bash
docker compose down -v
docker compose up -d
```

## Support

For issues, check container logs:
```bash
docker compose logs
```
