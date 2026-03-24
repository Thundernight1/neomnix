# Secrets Doldurma Rehberi - Hızlı Referans

## 3 Zorunlu Secret (MUTLAKA DOLDUR)

### 1️⃣ JWT_SECRET_KEY
```bash
# Oluştur (terminalde çalıştır):
openssl rand -hex 32

# Çıktı örneği:
# a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z

# secrets.env'ye yapıştır:
JWT_SECRET_KEY=a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z
```

### 2️⃣ OLLAMA_API_KEY
```bash
# Docker-compose.yml'de bak:
cat docker-compose.yml | grep OLLAMA_API_KEY

# Veya .env dosyasında varsa:
cat .env | grep OLLAMA_API_KEY

# Örnek:
OLLAMA_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3️⃣ ZAP_API_KEY
```bash
# Docker-compose.yml'den kopyala:
cat docker-compose.yml | grep ZAP_API_KEY

# Genelde şu şekilde:
ZAP_API_KEY=aegis-zap-secret
```

---

## Staging Ortamı (Varsa Doldur)

### STAGING_HOST & STAGING_USER
```bash
# SSH bağlantısı nasıl yapıyor normalde?
ssh deploy@staging.example.com

# Yukarıdaki 'deploy' username, 'staging.example.com' hostname
STAGING_HOST=staging.example.com
STAGING_USER=deploy
```

### STAGING_SSH_KEY (Base64 Encode)
```bash
# Terminalde:
cat ~/.ssh/id_rsa | base64

# Veya eğer id_rsa yoksa, başka key kullan:
cat ~/.ssh/other_key | base64

# Tüm output'u kopyala ve yapıştır
STAGING_SSH_KEY=LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0K...
```

---

## Production Ortamı (Mutlaka Doldur)

### PROD_HOST & PROD_USER
```bash
# Senin production sunucun:
PROD_HOST=203.0.113.42        # veya prod.example.com
PROD_USER=deploy              # SSH username
```

### PROD_SSH_KEY
```bash
# SSH key'i base64'e encode et:
base64 < ~/.ssh/id_rsa

# Sonucun tamamını kopyala
PROD_SSH_KEY=LS0tLS1CRUdJTi...
```

### ADMIN_EMAIL & PASSWORD
```bash
# Kimle login etmek istiyorsun?
ADMIN_EMAIL=your-email@example.com
ADMIN_DEFAULT_PASSWORD=SecurePass123!@#
```

### DATABASE_URL
```bash
# Eğer PostgreSQL kullanıyorsan:
DATABASE_URL=postgresql://db_user:db_pass@192.168.1.100:5432/cybersurx

# Açıklaması:
# postgresql:// = protokol
# db_user = veritabanı kullanıcı adı
# db_pass = veritabanı şifresi
# 192.168.1.100 = veritabanı sunucusu IP'si
# 5432 = PostgreSQL port (sabit)
# cybersurx = veritabanı adı

# Eğer SQLite kullanıyorsan (test için):
DATABASE_URL=sqlite:///./cybersurx.db
```

### REDIS_PASSWORD
```bash
# Redis'e bağlanırken kullanılacak şifre:
REDIS_PASSWORD=MyRedisPass123!@#
```

---

## Optional Secrets (İsteğe Bağlı)

### Sentry (Hata Takibi)
```bash
# sentry.io'dan project oluştur
# Settings → Client Keys → DSN'yi kopyala

SENTRY_DSN_STAGING=https://xxxxx@sentry.io/123456
SENTRY_DSN_PRODUCTION=https://yyyyy@sentry.io/789012
```

### Slack Webhook
```bash
# api.slack.com/apps'tan webhook al
# Şöyle görünecek:
SLACK_WEBHOOK=https://hooks.slack.com/services/T123/B456/ABC123
```

---

## Dolu Örnek secrets.env

```bash
# ZORUNLU
JWT_SECRET_KEY=a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z
OLLAMA_API_KEY=sk-proj-xxxxxxxxxxxxx
ZAP_API_KEY=aegis-zap-secret

# STAGING (varsa)
STAGING_HOST=staging.example.com
STAGING_USER=deploy
STAGING_SSH_KEY=LS0tLS1CRUdJTi...

# PRODUCTION
PROD_HOST=prod.example.com
PROD_USER=deploy
PROD_SSH_KEY=LS0tLS1CRUdJTi...
ADMIN_EMAIL=admin@cybersurx.io
ADMIN_DEFAULT_PASSWORD=SecurePass2024!@#
DATABASE_URL=postgresql://user:pass@db.internal:5432/cybersurx
REDIS_PASSWORD=RedisPass2024!@#

# OPTIONAL
SLACK_WEBHOOK=https://hooks.slack.com/services/T/B/X
```

---

## Step by Step

1. **secrets.env.example'i kopyala:**
   ```bash
   cp secrets.env.example secrets.env
   ```

2. **Değerleri bul:**
   ```bash
   # Bu dosyalarda ara:
   cat docker-compose.yml
   cat .env
   cat .github/workflows/ci.yml
   ```

3. **Doldur:**
   ```bash
   nano secrets.env
   # Ya da:
   code secrets.env
   ```

4. **Upload et:**
   ```bash
   ./scripts/setup-deployment-env.sh \
     --org your-org \
     --repo cybersurx \
     --file secrets.env
   ```

5. **Sil:**
   ```bash
   rm secrets.env
   ```

---

## Gerekli Değerleri Nereden Bulacağım?

| Secret | Nereden? | Komut |
|--------|---------|-------|
| JWT_SECRET_KEY | Oluştur | `openssl rand -hex 32` |
| OLLAMA_API_KEY | .env veya docker-compose | `grep OLLAMA docker-compose.yml` |
| ZAP_API_KEY | docker-compose.yml | `grep ZAP docker-compose.yml` |
| STAGING_HOST | Sunucunun IP/domain | `nslookup staging.example.com` |
| STAGING_USER | SSH kullanıcı | `ssh -l ? staging.example.com` |
| STAGING_SSH_KEY | ~/.ssh/id_rsa | `base64 < ~/.ssh/id_rsa` |
| PROD_HOST | Prod sunucusu | IP'ni sor yöneticiye |
| PROD_USER | SSH kullanıcı | IP'ni sor yöneticiye |
| PROD_SSH_KEY | ~/.ssh/id_rsa | `base64 < ~/.ssh/id_rsa` |
| DATABASE_URL | Veritabanı admin | Bağlantı string'i sor |
| REDIS_PASSWORD | Redis yapılandırması | Yapılandırmada bak |

---

## Hata Ayıklama

### "SSH key invalid"
```bash
# Key'i kontrol et
ssh -i ~/.ssh/id_rsa user@host echo "test"

# Hata verirse, key'i base64'e düzgün encode et
base64 < ~/.ssh/id_rsa > key.b64
cat key.b64
```

### "Database connection refused"
```bash
# Database'i test et
psql postgresql://user:pass@host:5432/dbname

# SSH tunnel kullan
ssh -L 5432:localhost:5432 user@prod-server
```

### "API key invalid"
```bash
# Ollama'yı test et
curl -H "Authorization: Bearer YOUR_KEY" https://api.ollama.com/v1/models
```
