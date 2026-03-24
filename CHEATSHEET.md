# 🚀 DEPLOYMENT - Ultra Hızlı Cheatsheet

## HEMEN BAŞLA (2 dakika)

```bash
# 1. Ultra-basit kurulum
./scripts/quick-setup.sh

# 2. GitHub'da environments oluştur
# Settings → Environments → New: "staging", "production"

# 3. Test
git push origin develop
gh run watch
```

## SECRETS NELERDİR?

| Secret | Değer | Komut |
|--------|-------|-------|
| **JWT_SECRET_KEY** | 32 char random | `openssl rand -hex 32` |
| **OLLAMA_API_KEY** | LLM key | `grep OLLAMA docker-compose.yml` |
| **ZAP_API_KEY** | Security key | `grep ZAP docker-compose.yml` |
| **PROD_HOST** | Server IP/domain | IP'yi sor admin'e |
| **PROD_USER** | SSH user | Genelde: `deploy` |
| **PROD_SSH_KEY** | SSH private key | `base64 < ~/.ssh/id_rsa` |
| **ADMIN_EMAIL** | Email | `admin@cybersurx.io` |
| **ADMIN_DEFAULT_PASSWORD** | Password | Güçlü şifre oluştur |
| **DATABASE_URL** | DB connection | `postgresql://user:pass@host/db` |

## NASIL UPLOAD EDERIM?

### Seçenek 1: Otomatik (Tavsiye Edilen)
```bash
./scripts/quick-setup.sh
# Secrets'ı sor → GitHub'a yükle
```

### Seçenek 2: Manuel
```bash
cp secrets.env.example secrets.env
nano secrets.env          # Değerleri doldur
./scripts/setup-deployment-env.sh --org ORG --repo REPO --file secrets.env
rm secrets.env            # Sil
```

### Seçenek 3: Tek tek
```bash
echo "my-secret-value" | gh secret set MY_SECRET -a owner/repo
```

## DEPLOYMENT FLOW

```
develop push
  ↓
CI tests (backend, frontend, security)
  ↓
Build Docker images
  ↓
Deploy to Staging (auto)
  ↓
Health checks + Slack notify

main push (merged PR)
  ↓
CI tests
  ↓
Build Docker images
  ↓
Deploy to Production (auto)
  ↓
Health checks + auto-rollback if fail
```

## KOMUTLAR

### Workflows
```bash
gh workflow list                           # Tüm workflows
gh workflow run deploy-staging.yml         # Staging deploy
gh workflow run deploy-production.yml      # Production deploy (need approval)
gh run watch                               # Monitoring
gh run list --workflow=deploy-staging.yml  # History
```

### Secrets
```bash
gh secret list                      # Secrets listele
gh secret set MY_SECRET -a org/repo # Secret ekle
gh secret remove MY_SECRET          # Secret sil
```

### Git
```bash
git checkout develop
git push origin develop              # Staging deploy trigger
git push origin main                 # Production deploy trigger (after PR)
```

### SSH Tests
```bash
ssh -i ~/.ssh/id_rsa user@host echo "test"           # SSH kontrol
ssh deploy@prod.example.com "docker compose ps"      # Remote docker
ssh deploy@prod.example.com "docker compose logs api" # Remote logs
```

## SSH KEY ENCODING

### macOS/Linux
```bash
base64 < ~/.ssh/id_rsa
# Tamamını kopyala
```

### Windows PowerShell
```powershell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("C:\Users\YOU\.ssh\id_rsa"))
```

## ERRORS & FIXES

| Error | Fix |
|-------|-----|
| "Not authenticated" | `gh auth login` |
| "SSH key invalid" | `ssh -i ~/.ssh/id_rsa user@host` test et |
| "Workflow won't trigger" | Settings → Actions → Enable |
| "Deploy fails" | `ssh deploy@host` → `docker compose logs` |
| "Database connection refused" | `psql postgresql://...` test et |

## GITHUB AYARLARI

### Environments (Settings → Environments)
```
staging:
  No protection needed
  
production:
  ✓ Add required reviewers
  ✓ Deployment branches: main
```

### Branch Protection (Settings → Branches)
```
Pattern: main
✓ Require a pull request
✓ Require status checks to pass
✓ Require approval from 1+ collaborators
```

## PRODUCTION CHECKLIST

- [ ] Secrets uploaded (`gh secret list`)
- [ ] Environments created
- [ ] Branch protection rules set
- [ ] SSH key working (`ssh user@host echo ok`)
- [ ] Database accessible
- [ ] Redis password set
- [ ] Admin email and password ready
- [ ] Staging deployment tested
- [ ] Production domain configured
- [ ] SSL certificate ready

## ROLLBACK

### Automatic
Deploy başarısız → otomatik önceki sürüme döner

### Manual
```bash
ssh deploy@prod.example.com
cd /opt/cybersurx
./scripts/rollback.sh
```

## MONITORING

```bash
# Logs
./scripts/verify_deployment.sh
docker compose logs -f api

# Remote
ssh deploy@prod.example.com "docker compose logs -f api"

# GitHub Actions
Settings → Actions → Recent runs
```

## GITHUB UI SHORTCUTS

```
Repository Home
  ↓
Settings
  ↓
Environments → Create staging + production
  ↓
Branches → Add protection rule for main
  ↓
Secrets → Review uploaded secrets
  ↓
Actions → Monitor workflows
```

## İLK DEPLOYMENT

1. **Setup:** `./scripts/quick-setup.sh`
2. **Environments:** Settings → Environments → Create
3. **Branch Protection:** Settings → Branches → main → Add rules
4. **Test:** `git push origin develop`
5. **Monitor:** `gh run watch`
6. **Verify:** Staging health check
7. **Production:** Merge to main → auto deploy

---

**Daha fazla:** [TURKCE_BASLA.md](TURKCE_BASLA.md) | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
