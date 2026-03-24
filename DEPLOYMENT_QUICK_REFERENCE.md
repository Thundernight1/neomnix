# CyberSurX GRC - Deployment Pipeline Reference

Quick reference for common deployment tasks.

## Automated Deployments

### Staging (develop branch)
```bash
# Auto-triggered on push to develop
# Manual trigger:
gh workflow run deploy-staging.yml
```

### Production (main branch)
```bash
# Auto-triggered on push to main (after CI passes)
# Manual trigger with strategy:
gh workflow run deploy-production.yml \
  -f deployment_strategy=rolling
```

### Kubernetes (manual)
```bash
# Deploy to staging
gh workflow run deploy-k8s.yml \
  -f environment=staging \
  -f image_tag=latest

# Deploy to production
gh workflow run deploy-k8s.yml \
  -f environment=production \
  -f image_tag=v1.2.3
```

## Manual Docker Compose Deployment

### Staging
```bash
export BACKEND_IMAGE=ghcr.io/your-org/cybersurx/backend:staging-abc123
export FRONTEND_IMAGE=ghcr.io/your-org/cybersurx/frontend:staging-abc123
docker compose -f docker-compose.staging.yml up -d
./scripts/verify_deployment.sh
```

### Production
```bash
export DATABASE_URL="postgresql://user:pass@host/db"
export JWT_SECRET_KEY="secret"
export OLLAMA_API_KEY="key"
export BACKEND_IMAGE=ghcr.io/your-org/cybersurx/backend:v1.2.3
export FRONTEND_IMAGE=ghcr.io/your-org/cybersurx/frontend:v1.2.3

docker compose -f docker-compose.prod.yml up -d
./scripts/verify_deployment.sh
```

## Verification

```bash
# Run verification script
./scripts/verify_deployment.sh

# Manual checks
curl http://localhost:8000/health      # API
curl http://localhost:3000             # Frontend
docker compose exec -T redis redis-cli ping  # Redis
docker compose logs -f api             # View logs
```

## Rollback

### Automatic
- Triggered if health checks fail post-deploy
- Uses backed-up compose file

### Manual
```bash
./scripts/rollback.sh

# Or specific version
docker compose -f backup-compose-TIMESTAMP.yml up -d
```

## Status Checks

```bash
# GitHub Actions
gh workflow list
gh run list --workflow=deploy-production.yml

# Container status
docker compose ps
docker compose logs -f

# Kubernetes
kubectl get deployments -n cybersurx-prod
kubectl get pods -n cybersurx-prod
```

## Environment Setup

### GitHub Secrets (Required)
```
PROD_HOST           # Server address
PROD_USER           # SSH user
PROD_SSH_KEY        # SSH key
STAGING_HOST        # Staging server
STAGING_USER        # Staging user
STAGING_SSH_KEY     # Staging key
OLLAMA_API_KEY      # API key
JWT_SECRET_KEY      # Secret
```

### Environment Files
```bash
# Production
.env.prod (never commit)
  DATABASE_URL=postgresql://...
  JWT_SECRET_KEY=...
  OLLAMA_API_KEY=...

# Staging
.env.staging
  DATABASE_URL=sqlite:///./staging.db
```

## Common Issues

### Deployment timeout
- Increase `TIMEOUT` in `deploy-production.yml`
- Check `start_period` in healthchecks

### Memory errors
- Increase docker memory limits
- Check `docker stats` for usage

### Connection refused
- Ensure services are started: `docker compose ps`
- Check logs: `docker compose logs api`

### Rollback needed
- Run: `./scripts/rollback.sh`
- Or SSH and restore from backup

## Monitoring

```bash
# Real-time stats
docker compose stats --no-stream

# Logs with search
docker compose logs api | grep ERROR

# Export logs
docker compose logs > debug-$(date +%s).log

# Kubernetes
kubectl top pods -n cybersurx-prod
kubectl logs -n cybersurx-prod -l app=backend -f
```

## See Also

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Full documentation
- [CI/CD Setup](CI_CD_SETUP.md) - Pipeline configuration
- [README](README.md) - Quick start
