# ========================================
# ZORUNLU SECRETS (REQUIRED) - HEPSİNİ DOLDUR
# ========================================

# 1. JWT SECRET KEY
# ================
# Ne işe yarar: Kullanıcı login token'larını imzalamak için kullanılır
# Nasıl oluşturulur: Random 32+ karakterlik string
# 
# Hızlı oluştur:
#   macOS/Linux: openssl rand -hex 16
#   Windows: [System.Convert]::ToBase64String((1..32 | % {[byte]$_})) | ForEach-Object {[char]([int]$_)} | Join-Object
#
# İçinde olması gerekenler: Harfler, rakamlar, özel karakterler (_-!@#$%^&*)
# ÖRNEK: a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z
JWT_SECRET_KEY=a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z

# 2. OLLAMA API KEY
# =================
# Ne işe yarar: LLM (Yapay Zeka) API'sine erişim için
# Nasıl alınır: Ollama dashboard'undan veya .env file'ından
# Eğer bilmiyorsan: dummy value kullan (test için)
OLLAMA_API_KEY=your-actual-ollama-key-here

# 3. OWASP ZAP API KEY
# ====================
# Ne işe yarar: Security scanning tool'a erişim için
# Varsayılan: Eğer değiştirmediysen kullan: aegis-zap-secret
# Veya docker-compose.yml'den oku
ZAP_API_KEY=aegis-zap-secret


# ========================================
# STAGING (TEST) ORTAMI SECRETS
# Staging sunucusu varsa doldur, yoksa boş bırak
# ========================================

# Staging sunucusunun adresi
# ÖRNEK: staging.example.com veya 192.168.1.100
STAGING_HOST=staging.example.com

# Staging sunucusuna SSH ile bağlanacak kullanıcı adı
# Genelde: deploy veya ubuntu
STAGING_USER=deploy

# Staging sunucusuna SSH'yle bağlanmak için kullanılan private key
# 
# NASIL HAZIRLANIR:
# 1. SSH key'i base64'e encode et:
#    macOS/Linux:
#      cat ~/.ssh/id_rsa | base64
#    Tamamını kopyala (başından sonuna kadar)
#
# 2. Veya direkt dosyadan:
#    macOS/Linux:
#      base64 < ~/.ssh/id_rsa
#    Windows PowerShell:
#      [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("C:\Users\YourUser\.ssh\id_rsa"))
#
# Output: LS0tLS1CRUdJTi... (çok uzun olacak, hepsi bu şekilde)
STAGING_SSH_KEY=LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0K...


# ========================================
# PRODUCTION (CANLILIĞI) ORTAMI SECRETS
# Üretim sunucusu için zorunlu
# ========================================

# Production sunucusunun adresi (IP veya domain)
# ÖRNEK: prod.example.com veya 203.0.113.42
PROD_HOST=prod.example.com

# Production sunucusuna SSH ile bağlanacak kullanıcı adı
PROD_USER=deploy

# Production sunucusuna SSH'yle bağlanmak için private key (base64 encoded)
# Staging key'i ile aynı şekilde hazırla
PROD_SSH_KEY=LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0K...

# Admin kullanıcı email'i
# Bu email ile ilk kez login yapabileceksin
ADMIN_EMAIL=admin@cybersurx.io

# Admin şifresi (ilk login'de kullanılacak)
# En az 12 karakter, büyük harf, küçük harf, rakam, özel karakter
# ÖRNEK: SecurePass2024!@#
ADMIN_DEFAULT_PASSWORD=SecurePass2024!@#

# PostgreSQL Database bağlantı URL'i
# Format: postgresql://username:password@host:port/database_name
# 
# ÖRNEK:
#   postgresql://cybersurx_user:MyP@ssw0rd@db.internal:5432/cybersurx
#   postgresql://admin:Pass123!@203.0.113.50:5432/prod_db
#
# Açıklaması:
#   - cybersurx_user: veritabanı kullanıcı adı
#   - MyP@ssw0rd: veritabanı şifresi
#   - db.internal: veritabanı sunucusu adresi
#   - 5432: PostgreSQL port (genelde 5432)
#   - cybersurx: veritabanı adı
DATABASE_URL=postgresql://cybersurx_user:MyP@ssw0rd@db.internal:5432/cybersurx

# Redis cache sunucusu şifresi
# Redis'e bağlanırken kullanılacak
# Güçlü bir şifre olmalı (12+ karakter)
REDIS_PASSWORD=RedisPass2024!@#


# ========================================
# OPSİYONEL: ERROR TRACKING (Sentry)
# Hata takibi yapmak istiyorsan doldur
# ========================================

# Sentry staging DSN
# Sentry'den kopyala: Settings → Client Keys → DSN
# Format: https://xxxxx@sentry.io/projectid
SENTRY_DSN_STAGING=https://abc123def456@sentry.io/123456

# Sentry production DSN
SENTRY_DSN_PRODUCTION=https://xyz789uvw012@sentry.io/654321


# ========================================
# OPSİYONEL: SLACK NOTIFICATIONS
# Deployment sonuçlarını Slack'e göndermek istiyorsan
# ========================================

# Slack Webhook URL
# 
# NASIL ALIRIM:
# 1. Slack workspace'ine git
# 2. api.slack.com/apps → Create New App
# 3. "From scratch" seç
# 4. App name: "CyberSurX Deploy" yaz
# 5. Workspace seç
# 6. Sol menüden "Incoming Webhooks" tıkla
# 7. "Activate Incoming Webhooks" aç
# 8. "Add New Webhook to Workspace" tıkla
# 9. Webhook URL kopyala
#
# Şöyle görünecek: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXX
SLACK_WEBHOOK=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXX


# ========================================
# OPSİYONEL: KUBERNETES DEPLOYMENT
# Kubernetes kullanıyorsan doldur
# ========================================

# Kubeconfig dosyası (base64 encoded)
#
# NASIL HAZIRLANIR:
# 1. Kubeconfig dosyasını base64'e encode et:
#    macOS/Linux:
#      base64 < ~/.kube/config
#    Tamamını kopyala
#
# 2. Veya:
#    cat ~/.kube/config | base64
K8S_KUBECONFIG=LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUQwVENDQXJtZ0F3SUJBZ0lRRWllWllTN3dYcm5l...


# ========================================
# OPSİYONEL: AWS DEPLOYMENT (ECS)
# AWS'de deploy etmek istiyorsan doldur
# ========================================

# AWS Access Key ID
# AWS IAM console'dan al
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE

# AWS Secret Access Key
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# AWS Region
# ÖRNEK: us-east-1, eu-west-1, ap-southeast-1
AWS_REGION=us-east-1
