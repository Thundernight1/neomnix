# 🚀 CyberSurX GRC - CI/CD Pipeline Quick Reference

## Workflow Özeti

| Workflow | Tetikleyici | Amacı |
|----------|-----------|-------|
| **CI** | Push to main/develop, PR | Tests, Build, Security scan |
| **Deploy** | CI success on main | Production deployment |
| **Security Audit** | Haftalık (Pazar 02:00 UTC) | Deep vulnerability scan |

---

## Otomatik Workflow Tetikleyicileri

### 1️⃣ **Kod Push → CI Pipeline Çalışır**
```bash
git push origin feature-branch
# ↓
# GitHub Actions tetiklenir
# ✅ Backend tests
# ✅ Frontend build
# ✅ Docker images
# ✅ Security scan
```

### 2️⃣ **CI Başarı → Deploy Pipeline Çalışır** (main only)
```bash
# CI tamamlandı ✅
# ↓
# Deploy workflow otomatik tetiklenir
# ✅ Production images pushed to registry
# ✅ Deployment manifest created
```

### 3️⃣ **Her Pazar 02:00 UTC → Security Audit**
```bash
# Scheduled trigger
# ↓
# Deep vulnerability scan
# ✅ Trivy file scan
# ✅ Python security (bandit, safety)
# ✅ npm audit
# 📋 Issues created if vulnerabilities found
```

---

## Test Kategorileri

### Unit Tests (Hızlı, bağımlılık yok)
```python
@pytest.mark.unit
def test_data_validation():
    assert validate(good_data) == True
```
**Çalışma süresi:** < 1s per test

### Integration Tests (Harici servisler)
```python
@pytest.mark.integration
async def test_with_redis():
    result = await redis_operation()
    assert result is not None
```
**Çalışma süresi:** 5-30s

### Slow Tests
```python
@pytest.mark.slow
async def test_long_scan():
    results = await full_scan()
```
**Çalışma süresi:** > 30s

---

## Yerel Test Komutları

### Backend Tests
```bash
# Tüm testler
cd backend
pytest tests/ -v

# Sadece unit testler (hızlı)
pytest tests/ -v -m unit

# Sadece integration testler
pytest tests/ -v -m integration

# Coverage raporu
pytest tests/ --cov=src --cov-report=html
```

### Frontend Build & Lint
```bash
cd frontend

# Linting
npm run lint

# Build
npm run build

# Development mode
npm run dev
```

### Docker Compose Test
```bash
# Test ortamında başlat
docker compose -f docker-compose.test.yml up --build

# Logları izle
docker compose -f docker-compose.test.yml logs -f api

# Health check
curl http://localhost:8000/docs
curl http://localhost:3000
```

---

## GitHub Actions Artifacts

### Test Results
- **Path:** `Actions → Run → Artifacts → backend-test-results`
- **Format:** JUnit XML (CI tools tarafından parse edilebilir)
- **Retention:** 30 gün

### Coverage Report
- **Path:** `Actions → Run → Artifacts → backend-coverage`
- **Format:** Cobertura XML
- **Açılması:** `open coverage/index.html` (yerel)

### Security Reports
- **Path:** `Actions → Run → Artifacts → security-audit-results`
- **Dosyalar:**
  - `trivy-fs-results.json` - Filesystem scan
  - `bandit-results.json` - Python security
  - `safety-results.json` - Dependency vulnerabilities

### Deployment Config
- **Path:** `Actions → Run → Artifacts → deployment-manifest`
- **İçerik:** Image tags, deployment time, commit info

---

## Debug Commands

### Test Başarısızlığını Yerel Olarak Repro Et
```bash
cd backend

# Hata mesajı ile detaylı output
pytest tests/test_name.py -vvs

# Stop on first failure
pytest tests/ -x

# Last failed tests
pytest --lf

# Specific test
pytest tests/test_cybersurx.py::test_vulnerability_artifact_valid -v
```

### Docker Debug
```bash
# Container'ları kontrol et
docker ps -a

# Service logs
docker compose logs -f api
docker compose logs -f redis

# Container'a gir
docker compose exec api bash

# Network kontrol
docker network ls
docker network inspect aegis-test-network
```

### Environment Variables
```bash
# .env file check
cat .env

# Container'da env kontrol
docker compose exec api env

# Test sırasında env set et
DATABASE_URL=sqlite:///test.db pytest tests/
```

---

## Troubleshooting

### ❌ "redis connection refused"
```bash
# Redis çalışıyor mu?
docker compose ps redis

# Redis başlat
docker compose up redis -d

# Health check
redis-cli ping  # Should return PONG
```

### ❌ "pytest: command not found"
```bash
# Pip dependencies install et
cd backend
pip install -r requirements.txt
```

### ❌ "Docker build fails on rate limit"
```bash
# Cache'i temizle
docker builder prune -a

# Retry manual
docker build ./backend -t aegis-api:test
```

### ❌ "Port already in use"
```bash
# Port'u bulup kill et
lsof -i :8000
kill -9 <PID>

# Veya docker compose'u tamamen down et
docker compose down -v
```

---

## PR Workflow

1. **Feature branch oluştur**
   ```bash
   git checkout -b feat/new-compliance-check
   ```

2. **Code yaz & commit**
   ```bash
   git commit -m "Add NIST 800-53 mapping"
   ```

3. **Push → CI tetiklenir**
   ```bash
   git push origin feat/new-compliance-check
   ```

4. **GitHub'da PR aç**
   - Tüm checks geçmesini bekle ✅
   - Code review iste
   - Approve oldu mu → Merge

5. **Main'e merge → Deploy tetiklenir**
   - Images built & pushed
   - Deployment manifest created
   - Production ready

---

## Status Check

### GitHub Actions Dashboard
```
GitHub.com → Your Repo → Actions
```

**Görebileceklerin:**
- ✅ Workflow runs (successful/failed)
- 🔄 In-progress jobs
- 📊 Test results
- 🔒 Security scans
- 📦 Artifacts

### Status Badges (README'ye eklenebilir)
```markdown
![CI Pipeline](https://github.com/yourorg/repo/workflows/CyberSurX%20GRC%20-%20Full%20CI%2FCD%20Pipeline/badge.svg)
```

---

## Performance Tips

### Build Cache Optimization
```yaml
# .github/workflows/ci.yml içinde zaten yapılı
cache-from: type=gha
cache-to: type=gha,mode=max
```
**Sonuç:** 2-3x faster builds (ilk build'den sonra)

### Parallel Job Execution
```yaml
strategy:
  matrix:
    service: [backend, frontend]
```
**Sonuç:** Backend + Frontend tests paralel çalışır

### Test Matrix (opsiyonel)
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```
**Sonuç:** Multiple Python versions test edilir

---

## Contacts & Support

- 📚 Full docs: `CI_CD_SETUP.md`
- 🔧 Workflow config: `.github/workflows/`
- 🧪 Test config: `backend/pytest.ini`
- 📝 Project docs: `docs/`

---

**Son Update:** 2024-01-15  
**Pipeline Status:** ✅ Ready for production
