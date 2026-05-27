# Neomnix — Multi-Framework Compliance Scanning Platform

Neomnix, bir şirketin sistemini tarayarak bulunan güvenlik açıklarını otomatik olarak **HIPAA, SOC2, WA-MHMDA, NIST-800-53, CCM-4.0 ve SEC-2023** gibi birden fazla uyumluluk çerçevesine eş zamanlı olarak eşleyen, yapay zeka destekli bir GRC (Governance, Risk & Compliance) platformudur.

Tek bir tarama sonucunda şu soruyu yanıtlar: _"Bu güvenlik açığı hangi yasaları ihlal ediyor ve nasıl düzeltilir?"_

---

## Özellikler

### Çok Çerçeveli Uyumluluk Eşleme (Cross-Mapping)
- Bulunan her güvenlik açığı otomatik olarak HIPAA, SOC2, NIST-800-53, WA-MHMDA, CCM-4.0 ve SEC-2023 kontrollerine eşlenir
- TF-IDF cosine similarity + Jaccard keyword algoritmasıyla N×N framework overlap matrisi hesaplanır
- `compliance_rules.json` üzerinden kural tabanlı + semantik eşleme birlikte çalışır

### SharkTap — Pasif Ağ Analizi
- `.pcap`, `.pcapng`, `.cap` dosyaları yüklenip analiz edilir (`POST /scan/pcap`)
- DNS tunneling, şifresiz DB trafiği, FTP/Telnet oturumları, büyük veri çıkışı otomatik tespit edilir
- Tüm bulgular doğrudan compliance kontrollerine beslenir

### Gap Analysis
- `POST /api/gap/analyze` → Celery worker üzerinde async gap analizi başlatır
- Eksik UCL kontrolleri tespit edilir, AI önerileri eklenir
- `GET /api/gap/report/{org_id}` ile framework filtrelemeli tam rapor alınır

### Cloud Security Posture Management (CSPM)
- Prowler entegrasyonu ile AWS, Azure ve GCP taraması
- `"scan aws"` gibi doğal dil komutlarıyla AI Hub üzerinden tetiklenir

### AI Hub — Doğal Dil Komut Yönlendirme
- `POST /command` endpointine doğal dil gönderilir
- Anahtar kelime tespiti ile scanner, cross_mapper, cloud_scanner veya LLM ajanına yönlendirilir
- Ollama LLM entegrasyonu desteklenir

### PDF & Markdown Rapor Üretimi
- Her tarama sonunda framework başına ayrı Markdown + PDF raporu otomatik oluşturulur
- `GET /reports/pdf/{job_id}/{framework}` ile indirilir
- Desteklenen: `HIPAA-2026`, `WA-MHMDA`, `NIST-800-53`, `SOC2`

### Güvenlik & Yetkilendirme
- JWT tabanlı kimlik doğrulama (admin / analyst / viewer rol hiyerarşisi)
- Multi-tenancy: her kullanıcı yalnızca kendi kiracısının verilerini görür
- Rate limiting (200 req/dk, login 10 req/dk)
- Production CORS koruması (`ALLOWED_ORIGINS` zorunlu, `*` reddedilir)
- Tüm işlemler audit log'a yazılır

### Billing (Stripe)
- `STRIPE_ENABLED=true` ile aktif edilir
- Webhook imza doğrulaması dahil
- `GET /billing/status` ile durum sorgulanır

---

## Hızlı Başlangıç

```bash
# Tüm servisleri başlat
docker compose up -d

# Logları izle
docker logs -f neomnix-api
docker logs -f neomnix-worker

# Durdur
docker compose down
```

---

## Servisler

| Servis    | Port | Görev                        |
|-----------|------|------------------------------|
| API       | 8000 | FastAPI backend              |
| Frontend  | 3000 | React + Vite web arayüzü     |
| Redis     | 6379 | Celery mesaj kuyruğu         |
| ZAP       | 8080 | OWASP ZAP güvenlik tarayıcı  |
| Worker    | —    | Celery async görev işleyici  |

---

## Ortam Değişkenleri

```bash
cp secrets.env.example .env
```

| Değişken                   | Açıklama                                      |
|----------------------------|-----------------------------------------------|
| `JWT_SECRET_KEY`           | JWT imzalama anahtarı (zorunlu)               |
| `ADMIN_DEFAULT_PASSWORD`   | İlk admin şifresi (zorunlu, SEED_ADMIN=true)  |
| `ADMIN_EMAIL`              | Admin e-posta adresi                          |
| `DATABASE_URL`             | PostgreSQL bağlantı URL'i                     |
| `REDIS_URL`                | Redis bağlantı URL'i                          |
| `OLLAMA_API_KEY`           | LLM API anahtarı                              |
| `ZAP_API_KEY`              | OWASP ZAP API anahtarı                        |
| `STRIPE_ENABLED`           | `true` ile Stripe billing aktif edilir        |
| `STRIPE_API_KEY`           | Stripe gizli anahtarı                         |
| `STRIPE_WEBHOOK_SECRET`    | Stripe webhook imza anahtarı                  |
| `ALLOWED_ORIGINS`          | Production CORS origin listesi (zorunlu)      |
| `APP_ENV`                  | `development` / `production` / `test`         |

---

## Yerel Geliştirme

**Backend (FastAPI)**
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
uvicorn src.api.main:app --reload --port 8000
```

**Frontend (React + Vite)**
```bash
cd frontend
npm install
npm run dev
```

**Celery Worker**
```bash
celery -A src.worker.tasks worker --loglevel=info
```

---

## API Endpointleri

| Method | Endpoint                              | Yetki              | Açıklama                              |
|--------|---------------------------------------|--------------------|---------------------------------------|
| POST   | `/auth/login`                         | Herkese açık       | JWT token al                          |
| POST   | `/auth/register`                      | Admin              | Yeni kullanıcı oluştur                |
| GET    | `/auth/me`                            | Giriş yapmış       | Mevcut kullanıcı bilgisi              |
| POST   | `/auth/change-password`               | Giriş yapmış       | Şifre güncelle                        |
| POST   | `/scan`                               | Admin / Analyst    | Tarama başlat (quick/deep/full)       |
| GET    | `/scan/{job_id}`                      | Giriş yapmış       | Tarama durumu ve sonucu               |
| GET    | `/scans`                              | Viewer+            | Tarama geçmişi (sayfalı)              |
| POST   | `/scan/pcap`                          | Admin / Analyst    | PCAP dosyası yükle ve analiz et       |
| POST   | `/command`                            | Giriş yapmış       | Doğal dil AI komutu çalıştır          |
| GET    | `/reports/pdf/{job_id}/{framework}`   | Giriş yapmış       | PDF rapor indir                       |
| POST   | `/api/gap/analyze`                    | Giriş yapmış       | Gap analizi başlat                    |
| GET    | `/api/gap/results/{task_id}`          | Giriş yapmış       | Gap analizi sonucu                    |
| GET    | `/api/gap/report/{org_id}`            | Giriş yapmış       | Tam gap raporu                        |
| GET    | `/stats`                              | Giriş yapmış       | Dashboard istatistikleri              |
| GET    | `/audit/logs`                         | Admin              | Audit log kayıtları                   |
| GET    | `/billing/status`                     | Herkese açık       | Stripe billing durumu                 |
| POST   | `/billing/webhook`                    | Stripe imzalı      | Stripe webhook işle                   |
| GET    | `/health`                             | Herkese açık       | Sistem sağlık kontrolü                |

---

## Uyumluluk Çerçeveleri

| Framework    | Kapsam                                              |
|--------------|-----------------------------------------------------|
| HIPAA-2026   | Sağlık verisi gizliliği ve güvenliği (ABD)          |
| WA-MHMDA     | Washington eyaleti mental health veri yasası        |
| NIST-800-53  | Federal güvenlik kontrol standardı / hibe uyumu     |
| SOC2         | Servis organizasyonu güvenlik denetimi              |
| CCM-4.0      | Cloud Controls Matrix (CSA)                         |
| SEC-2023     | SEC siber güvenlik ifşaat kuralları                 |

---

## Testler

```bash
# Tüm testleri çalıştır
cd backend
pytest

# Coverage raporu
pytest --cov=src --cov-report=html
```

Test dosyaları: auth, crossmap, compliance agent mapping, production readiness, PDF export, billing flag, artifact serialization, LLM disabled mode, E2E (Playwright).

---

## Admin Erişimi

```
E-posta: admin@neomnix.io  (veya ADMIN_EMAIL env değişkeni)
Şifre:   ADMIN_DEFAULT_PASSWORD env değişkeni
```

İlk girişte şifre değiştirme zorunludur.

---

## Veritabanı Sıfırlama

```bash
docker compose down -v
docker compose up -d
```

---

## CI/CD

Her `main` push'unda GitHub Actions çalışır:
- Docker Compose syntax doğrulama
- Dockerfile build kontrolü
- Test suite

Durum: https://github.com/Thundernight1/neomnix/actions
