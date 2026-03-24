# CyberSurX GRC - Deployment Pipeline Guide

## Overview

The deployment pipeline automates testing, building, and deploying the CyberSurX GRC application across multiple environments. It supports:

- **Development**: Local testing via `docker compose up`
- **Staging**: Pre-production environment via `docker-compose.staging.yml`
- **Production**: Main deployment via `docker-compose.prod.yml` or Kubernetes
- **CI/CD**: Automated workflows triggered on push events

## Deployment Strategies

### 1. Docker Compose (Staging/Production)

Best for single-host deployments with simplified orchestration.

#### Staging Deployment
```bash
# Automatic via GitHub Actions on develop branch
# Or manual:
export BACKEND_IMAGE=ghcr.io/your-org/cybersurx/backend:staging-abc123
export FRONTEND_IMAGE=ghcr.io/your-org/cybersurx/frontend:staging-abc123
docker compose -f docker-compose.staging.yml up -d
```

#### Production Deployment
```bash
# Requires environment variables
export DATABASE_URL="postgresql://user:pass@host/db"
export JWT_SECRET_KEY="your-secret-key"
export OLLAMA_API_KEY="your-ollama-key"
export REDIS_PASSWORD="your-redis-password"
export BACKEND_IMAGE=ghcr.io/your-org/cybersurx/backend:v1.2.3
export FRONTEND_IMAGE=ghcr.io/your-org/cybersurx/frontend:v1.2.3

docker compose -f docker-compose.prod.yml up -d
```

### 2. Kubernetes (Recommended for Production Scale)

Use for multi-node clusters with advanced orchestration.

#### Prerequisites
```bash
kubectl config use-context your-cluster
kubectl create namespace cybersurx-prod
```

#### Deploy via GitHub Actions
```bash
# Trigger manually
gh workflow run deploy-k8s.yml \
  -f environment=production \
  -f image_tag=v1.2.3
```

#### Manual Deployment
```bash
# Create secrets
kubectl create secret generic cybersurx-secrets \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=JWT_SECRET_KEY="..." \
  -n cybersurx-prod

# Deploy
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
```

## Environment Secrets

Set these as GitHub secrets for CI/CD:

### Required for All Environments
```
OLLAMA_API_KEY        # LLM API key
ZAP_API_KEY           # OWASP ZAP security scanner key
JWT_SECRET_KEY        # JWT signing key (min 32 chars)
```

### Production Only
```
PROD_HOST             # Production server hostname/IP
PROD_USER             # SSH username
PROD_SSH_KEY          # SSH private key (base64 encoded)
ADMIN_EMAIL           # Admin account email
ADMIN_DEFAULT_PASSWORD # Admin initial password
DATABASE_URL          # PostgreSQL connection string
REDIS_PASSWORD        # Redis authentication password
SENTRY_DSN_PRODUCTION # Error tracking DSN
SLACK_WEBHOOK         # Slack notifications
AWS_ACCESS_KEY_ID     # For ECS deployments (optional)
AWS_SECRET_ACCESS_KEY # For ECS deployments (optional)
AWS_REGION            # For ECS deployments (optional)
```

### Staging Only
```
STAGING_HOST          # Staging server hostname/IP
STAGING_USER          # SSH username
STAGING_SSH_KEY       # SSH private key
SENTRY_DSN_STAGING    # Staging error tracking
```

## GitHub Workflows

### 1. CI Pipeline (`ci.yml`)
**Triggers:** Push to main/develop, PRs

**Jobs:**
- Backend tests (pytest, mypy, flake8)
- Frontend build (npm, ESLint, TypeScript)
- Docker image build (with layer caching)
- Security scanning (Trivy, Bandit)
- Integration tests (docker compose health checks)

**Status:** Check GitHub Actions tab

### 2. Staging Deploy (`deploy-staging.yml`)
**Triggers:** Push to develop branch

**Flow:**
```
develop push 
  → Build images (staging tags)
  → SSH to staging host
  → Update docker-compose.staging.yml
  → Run smoke tests
  → Notify Slack
```

**Monitor:** GitHub Actions Workflow Runs

### 3. Production Deploy (`deploy-production.yml`)
**Triggers:** Push to main branch, after CI passes

**Flow:**
```
main push 
  → Pre-deployment checks
  → Build production images
  → Backup current state
  → Deploy via SSH
  → Run health checks
  → Post-deployment verification
  → Auto-rollback on failure
```

**Deployment strategies:**
- `rolling`: Sequential container replacement (default)
- `blue-green`: Full cutover between versions
- `canary`: Gradual traffic shifting

**Trigger manually:**
```bash
gh workflow run deploy-production.yml \
  --ref main \
  -f deployment_strategy=blue-green
```

### 4. Kubernetes Deploy (`deploy-k8s.yml`)
**Triggers:** Manual workflow dispatch

**Options:**
- Target environment: `staging` or `production`
- Image tag: `latest`, `v1.2.3`, or commit SHA

```bash
gh workflow run deploy-k8s.yml \
  -f environment=production \
  -f image_tag=v1.2.3
```

### 5. Security Audit (`security-audit.yml`)
**Triggers:** Weekly (Sundays 2 AM UTC), manual

**Scans:**
- Trivy: Container vulnerability
- Bandit: Python security issues
- Safety: Dependency CVEs
- npm audit: Frontend dependencies

## Deployment Runbook

### Staging Deployment (Manual)

1. **Build images locally:**
   ```bash
   docker build -t cybersurx/backend:test ./backend
   docker build -t cybersurx/frontend:test ./frontend
   ```

2. **Deploy to staging:**
   ```bash
   ssh staging-user@staging.example.com
   cd /opt/cybersurx
   export BACKEND_IMAGE=cybersurx/backend:test
   export FRONTEND_IMAGE=cybersurx/frontend:test
   docker compose -f docker-compose.staging.yml up -d
   ```

3. **Verify:**
   ```bash
   curl https://staging.cybersurx.io/api/health
   curl https://staging.cybersurx.io
   ```

### Production Deployment (Manual)

1. **Ensure CI passes on main branch:**
   ```bash
   git push origin main
   # Wait for GitHub Actions workflow to complete
   ```

2. **Tag release:**
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```

3. **Trigger deployment:**
   ```bash
   gh workflow run deploy-production.yml
   ```

4. **Monitor:**
   ```bash
   # Watch workflow progress
   gh run watch $(gh run list --workflow=deploy-production.yml -L1 --json databaseId -q '.[0].databaseId')
   
   # Or check GitHub Actions tab
   ```

5. **Verify production:**
   ```bash
   curl https://cybersurx.io/api/health
   curl https://cybersurx.io/api/docs
   ```

### Rollback (Emergency)

**Automatic:**
- Triggered if health checks fail post-deployment
- Uses latest backup compose file
- Restores previous version

**Manual Rollback:**
```bash
ssh prod-user@prod.example.com
cd /opt/cybersurx
ls -la backup-compose-*.yml
docker compose -f backup-compose-TIMESTAMP.yml pull
docker compose -f backup-compose-TIMESTAMP.yml up -d
```

## Health Checks

### API Health
```bash
curl -f http://localhost:8000/health
# Returns: {"status": "healthy"}
```

### Frontend Health
```bash
curl -f http://localhost:3000
# Returns: HTML (HTTP 200)
```

### Database Connection
```bash
docker compose exec -T api python -c "from src.db import engine; print('DB OK')"
```

### Redis Connection
```bash
docker compose exec -T redis redis-cli ping
# Returns: PONG
```

### Worker Status
```bash
docker compose exec -T worker celery -A src.worker.tasks inspect active
```

## Logging & Debugging

### View Container Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker

# Last N lines
docker compose logs -f api --tail=100

# With timestamps
docker compose logs -f api --timestamps
```

### Production Logs (SSH)
```bash
ssh prod-user@prod.example.com
cd /opt/cybersurx

# View API logs
docker compose logs -f api --tail=50

# View errors
docker compose logs api | grep ERROR

# Export logs
docker compose logs api > api-$(date +%s).log
```

### Kubernetes Logs
```bash
kubectl logs -n cybersurx-prod -l app=backend -f
kubectl logs -n cybersurx-prod deployment/backend -c backend --tail=100
kubectl logs -n cybersurx-prod deployment/worker -c worker -f
```

## Performance Monitoring

### Container Resource Usage
```bash
docker compose stats --no-stream
docker stats --no-stream
```

### Kubernetes Pod Metrics
```bash
kubectl top nodes
kubectl top pods -n cybersurx-prod
```

### Database Performance
```bash
# Connect to database
docker compose exec -T api psql $DATABASE_URL

# Query slow queries
SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC;
```

## Troubleshooting

### Deployment Fails with "Connection refused"
**Cause:** Service not ready yet
**Fix:**
```bash
# Wait for service to be healthy
docker compose ps
docker compose logs api
# Try again
docker compose up -d api
```

### Health Check Timeouts
**Cause:** Service takes too long to start
**Fix:**
```yaml
# Increase start_period in docker-compose
healthcheck:
  start_period: 60s  # Instead of 20-30s
```

### Out of Memory
**Cause:** Container memory limit exceeded
**Fix:**
```bash
# Check current usage
docker stats

# Increase limit in docker-compose
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G  # Instead of 512M
```

### Rollback Failed
**Cause:** No backup file available
**Fix:**
```bash
# Use specific previous image tag
docker compose -f docker-compose.prod.yml pull v1.2.2
docker compose up -d
```

## Best Practices

1. **Always tag releases:**
   ```bash
   git tag -a v1.2.3 -m "Release notes"
   ```

2. **Test staging first:**
   ```bash
   # Develop → Staging → Main
   ```

3. **Monitor deployment:**
   ```bash
   # Watch logs in real-time
   docker compose logs -f --tail=100
   ```

4. **Use environment files:**
   ```bash
   # Instead of exporting variables
   echo "DATABASE_URL=postgresql://..." > .env.prod
   docker compose --env-file .env.prod up -d
   ```

5. **Keep backups:**
   ```bash
   # Automatic backup created before deploy
   ls -la backup-compose-*.yml
   ```

6. **Secure secrets:**
   ```bash
   # Never commit .env files
   echo ".env*" >> .gitignore
   
   # Use GitHub Secrets for CI/CD
   # Use AWS Secrets Manager for production
   ```

## Related Documentation

- [CI/CD Setup Guide](CI_CD_SETUP.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
