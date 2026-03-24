# CyberSurX GRC - CI/CD Pipeline Setup

## Overview

Bu CI/CD pipeline sistemi, CyberSurX GRC projesinin otomatik test edilmesini, güvenlik kontrol edilmesini ve production'a deployment yapılmasını sağlar.

## Pipeline Workflows

### 1. **CI Pipeline** (`ci.yml`)
Ana branch'e ve PR'lara push yapıldığında tetiklenir.

**Aşamalar:**

#### Backend Tests & Quality
- ✅ Python 3.12 setup
- ✅ Unit tests (pytest)
- ✅ Type checking (mypy)
- ✅ Code linting (flake8)
- ✅ Coverage reporting
- ✅ Redis health check

**Test Komutu:**
```bash
pytest tests/ -v --cov=src --cov-report=xml
```

**Marker Kategorileri:**
```python
@pytest.mark.unit          # Hızlı unit testler
@pytest.mark.integration   # Harici bağımlılıklar gerektiren
@pytest.mark.slow          # Yavaş testler
@pytest.mark.asyncio       # Async/await testleri
@pytest.mark.security      # Güvenlik testleri
@pytest.mark.requires_zap  # OWASP ZAP gerektiren
```

#### Frontend Build & Linting
- ✅ Node 20 setup
- ✅ npm ci (clean install)
- ✅ ESLint kontrolü
- ✅ TypeScript build
- ✅ Dist artifact upload

**Build Komutu:**
```bash
npm run build
```

#### Docker Build & Push
- ✅ Buildx setup (multi-platform support)
- ✅ Registry login
- ✅ Backend image build & push
- ✅ Frontend image build & push
- ✅ Cache optimization (GHA cache)

#### Security Scanning
- ✅ Trivy filesystem scan
- ✅ SARIF report upload
- ✅ GitHub Security tab integration

#### Integration Test
- ✅ Docker Compose up
- ✅ Health checks
- ✅ Service connectivity verification
- ✅ Log collection on failure

**Çalışan Kontroller:**
```bash
curl http://localhost:8000/docs  # API health
curl http://localhost:3000       # Frontend health
redis-cli ping                   # Redis health
```

---

### 2. **Deploy Pipeline** (`deploy.yml`)
CI başarılı olduğunda production'a deployment yapar.

**Koşullar:**
- Main branch'e push
- CI workflow başarı ile tamamlandı

**Adımlar:**
1. Backend image build & push (tag: commit SHA + latest)
2. Frontend image build & push (tag: commit SHA + latest)
3. Deployment manifest oluştur
4. Artifacts upload (30 gün retention)

**Manifest Format:**
```bash
BACKEND_IMAGE=ghcr.io/org/repo/backend:abc123def456
FRONTEND_IMAGE=ghcr.io/org/repo/frontend:abc123def456
DEPLOYMENT_TIME=2024-01-15T10:30:00Z
COMMIT_SHA=abc123def456
COMMITTED_BY=username
```

---

### 3. **Security Audit Pipeline** (`security-audit.yml`)
Haftalık (Pazar 02:00 UTC) otomatik güvenlik denetimi yapar.

**Taramalar:**

#### Trivy
- Filesystem scan (tüm dosyalar)
- Config audit (Docker, K8s, vb.)
- JSON output (detailed)

#### Bandit (Python)
- Güvenlik açıkları taraması
- İlişkilendirme sırasında algılanan sorunlar

#### Safety (Python Dependencies)
- pip bağımlılıklarında CVE kontrolü

#### npm audit
- Frontend bağımlılıklarında CVE kontrolü

**Otomatic Issue Oluşturma:**
Güvenlik açıkları bulunursa GitHub issue oluşturur.

---

## Local Kullanım

### 1. Test Çalıştırma

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend build & lint
cd frontend
npm run lint
npm run build
```

### 2. Docker Compose ile Test

```bash
# Test ortamında çalıştır
docker compose -f docker-compose.test.yml up --build

# Logları göster
docker compose -f docker-compose.test.yml logs -f api
```

### 3. CI Pipeline Yerel Emülasyonu

```bash
# GitHub Actions local runner (act)
act -j backend-test

# Tüm jobs
act
```

---

## Secret Management

### GitHub Secrets (Gerekli)

GitHub Actions secrets olarak ekle:
- `GITHUB_TOKEN` - Otomatik sağlanır

### Environment Variables (CI'da)

```yaml
DATABASE_URL: sqlite:///./test.db
JWT_SECRET_KEY: test-secret-key
REDIS_URL: redis://localhost:6379/0
OLLAMA_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
```

---

## Artifacts & Reports

### Backend
- `backend-test-results.xml` - JUnit format test results
- `backend-coverage.xml` - Code coverage (Cobertura)
- Retention: 30 gün

### Frontend
- `frontend-dist/` - Built production files
- Retention: 7 gün

### Security
- `trivy-fs-results.json` - Filesystem vulnerabilities
- `trivy-config-results.json` - Configuration audit
- `bandit-results.json` - Python security issues
- `safety-results.json` - Dependency vulnerabilities
- Retention: 90 gün

### Deployment
- `deployment-config.env` - Image tags & metadata
- Retention: 90 gün

---

## Troubleshooting

### Test Başarısızlığı

```bash
# Yerel debug
cd backend
pytest tests/test_name.py -vvs

# Redis bağlantısı kontrol et
redis-cli ping

# System dependencies kontrol et
nmap --version
```

### Docker Build Başarısızlığı

```bash
# Cache temizle
docker builder prune -a

# Manual build
docker build ./backend -t aegis-api:test
```

### Integration Test Timeout

```bash
# Services health kontrol et
docker compose -f docker-compose.test.yml ps

# Logs kontrol et
docker compose -f docker-compose.test.yml logs api
```

---

## Best Practices

### 1. Test Yazarken
```python
import pytest

class TestMyFeature:
    @pytest.mark.unit
    async def test_fast_operation(self):
        """Hızlı unit test"""
        result = await my_function()
        assert result == expected

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_with_external_service(self):
        """Harici servisi kullanıysa mark et"""
        result = await external_call()
        assert result is not None
```

### 2. PR Workflow
1. Feature branch oluştur
2. Push et → CI workflow otomatik çalışır
3. Tüm checks geçmesi bekle ✅
4. Code review ve approve
5. Merge → Deploy workflow tetiklenir

### 3. Deployment Stratejisi
- **Main branch** → Production deployment
- **Develop branch** → Staging/Test
- **Feature branches** → CI only (no deploy)

### 4. Monitoring
- GitHub Actions tab → Workflows
- Security → Code scanning alerts
- Artifacts → Test reports & logs

---

## Performance Tips

### Cache Optimization
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

### Parallel Execution
```yaml
strategy:
  matrix:
    service: [backend, frontend]
```

### Timeout Configuration
```ini
[pytest]
timeout = 300  # 5 minutes per test
```

---

## Maintenance

### Güncellemeler
- Python packages: `pip list --outdated`
- npm packages: `npm outdated`
- GitHub Actions actions: `@v3 → @v4`

### Logs Temizleme
```bash
# 30 günden eski artifacts sil
# GitHub otomatik yapıyor (retention-days ayarı)
```

---

## İletişim & Support

Pipeline hataları için:
1. Logs kontrol et (GitHub Actions tab)
2. Yerel repro et (`pytest`, `npm run build`)
3. Issue aç detaylı error mesajı ile
