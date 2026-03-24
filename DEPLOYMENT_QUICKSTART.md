# 🚀 Deployment Pipeline - Quick Start

5 dakikalık setup:

## 1. Secrets Setup (2 min)

```bash
# Copy template
cp secrets.env.example secrets.env

# Edit with your values
nano secrets.env

# Upload to GitHub
./scripts/setup-deployment-env.sh \
  --org your-github-org \
  --repo your-repo-name \
  --file secrets.env

# Delete local copy
rm secrets.env
```

## 2. GitHub Environments (1 min)

Go to: **Settings → Environments**

Create two environments:
- `staging` (no protection needed)
- `production` (add required reviewers)

## 3. Branch Protection (1 min)

Settings → Branches → Add Rule

For `main` branch:
- ✅ Require status checks (CI workflow)
- ✅ Require review from 1+ person
- ✅ Require approval before merge

## 4. Test Deployment (1 min)

```bash
# Push to develop branch
git checkout develop
git commit -am "test"
git push origin develop

# Watch staging deploy
gh run watch

# Or: Settings → Actions → Workflows → View workflow runs
```

## 5. Verify (Manual)

```bash
# SSH to staging
ssh deploy@staging.example.com
docker compose ps

# Check logs
docker compose logs -f api
```

## Automatic Flow After Setup

```
develop branch push
  ↓ (auto trigger)
  → CI tests + build images
  ↓ (if passes)
  → Deploy to Staging
  ↓ (health checks)
  → Slack notification
  
main branch push (after PR merge)
  ↓ (auto trigger)
  → CI tests + build images
  ↓ (if passes)
  → Deploy to Production
  ↓ (health checks + auto-rollback)
  → Slack notification
```

## Common Commands

```bash
# View all workflows
gh workflow list

# Trigger staging deploy
gh workflow run deploy-staging.yml

# Trigger production deploy (requires approval)
gh workflow run deploy-production.yml

# Watch current run
gh run watch

# View logs of specific workflow
gh run list --workflow=deploy-staging.yml

# Check recent deployments
git log --oneline -20
```

## Emergency Procedures

### Rollback Production

```bash
# SSH to production
ssh deploy@prod.example.com
cd /opt/cybersurx

# Interactive rollback
./scripts/rollback.sh

# Or manual
ls backup-compose-*.yml
docker compose -f backup-compose-TIMESTAMP.yml up -d
```

### Health Check

```bash
./scripts/verify_deployment.sh
```

### View Logs

```bash
# Staging
ssh deploy@staging.example.com
docker compose logs -f api

# Production
ssh deploy@prod.example.com
docker compose logs -f api
```

## Documentation

- 📖 [Full Deployment Guide](DEPLOYMENT_GUIDE.md)
- 📖 [Secrets Setup Guide](SECRETS_SETUP.md)
- 📖 [Quick Reference](DEPLOYMENT_QUICK_REFERENCE.md)

## Troubleshooting

**Workflow won't start:**
- Check: Settings → Actions → General (enable workflows)
- Check: Branch protection rules (not blocking)

**Deploy fails:**
- View logs: Settings → Actions → Click workflow → View logs
- SSH to server and check: `docker compose logs api`

**Secrets not found:**
```bash
gh secret list  # Verify secrets exist
```

**Can't SSH to server:**
```bash
# Test SSH key
ssh -i ~/.ssh/id_rsa -T user@host

# Re-encode key
base64 -i ~/.ssh/id_rsa
```

## Next Steps

1. ✅ Complete setup above
2. 📝 Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. 🧪 Deploy to staging first
4. 📊 Monitor: Settings → Actions
5. 🔒 Setup monitoring/alerts (Sentry, Slack)
