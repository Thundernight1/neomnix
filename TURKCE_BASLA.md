# 🚀 CyberSurX Deployment - Türkçe Başlangıç Rehberi

Deployment pipeline'ı kurmanın en kolay yolu. **5 dakika içinde tamamlanır.**

## 📋 Ne Yapacağız?

1. ✅ GitHub Secrets'a deployment anahtarlarını ekleyeceğiz
2. ✅ GitHub Environments oluşturacağız
3. ✅ Branch protection rules kuracağız
4. ✅ İlk deployment'ı test edeceğiz

## 🎯 En Hızlı Yol (Recommended)

### Adım 1: Ultra-basit setup script'i çalıştır

```bash
./scripts/quick-setup.sh
```

Bu script:
- ✅ Senden gerekli secrets'ı soracak
- ✅ Otomatik olarak GitHub'a yükleyecek
- ✅ Hiçbir dosya bırakmayacak (güvenli)

### Adım 2: GitHub ortamlarını oluştur

1. GitHub repository'ye git
2. **Settings → Environments**
3. **New environment** → `staging` oluştur
4. **New environment** → `production` oluştur
5. Production'da: **Add deployment protection rule** → require reviews

### Adım 3: Branch protection kurulumu

1. **Settings → Branches**
2. **Add rule** → Branch name pattern: `main`
3. Seçenekler:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass (select CI workflow)
   - ✅ Require approval from collaborators

### Adım 4: Test et

```bash
# Develop branch'e push et
git checkout develop
echo "test" >> test.txt
git add .
git commit -m "test deployment"
git push origin develop

# Deployment'ı izle
gh run watch

# Veya GitHub UI'de:
# Settings → Actions → Workflows → deploy-staging.yml
```

**Bitir!** 🎉

---

## 🔑 Sorulan Secrets Nelerdir?

### 🔐 Zorunlu (Hepsi sorulacak)

#### 1. JWT_SECRET_KEY
**Ne?** Kullanıcı token'larını imzalamak için gizli anahtar

**Nasıl oluşturabilirim?**
```bash
openssl rand -hex 32
```

**Çıktı örneği:**
```
a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z
```

Bunu direkt copy-paste et.

#### 2. OLLAMA_API_KEY
**Ne?** Yapay zeka (LLM) servisi API key'i

**Nerede bulabilirim?**
```bash
cat docker-compose.yml | grep OLLAMA_API_KEY
```

Veya Ollama dashboard'undan. Eğer bilmiyorsan boş bırakabilirsin (dummy value).

#### 3. ZAP_API_KEY
**Ne?** Security scanning tool'u API key'i

**Nerede bulabilirim?**
```bash
cat docker-compose.yml | grep ZAP_API_KEY
```

Genelde default'u: `aegis-zap-secret`

### 🏢 Production Ortamı (Veya geç kurulabilir)

#### PROD_HOST
**Örnek:** `prod.example.com` veya `203.0.113.42`

#### PROD_USER
**Örnek:** `deploy` veya `ubuntu`

Normalde SSH ile şöyle bağlanıyorsan:
```bash
ssh deploy@prod.example.com
```

Kullanıcı adı: `deploy`

#### PROD_SSH_KEY
**Terminalde çalıştır:**
```bash
base64 < ~/.ssh/id_rsa
```

Tamamını kopyala ve yapıştır.

#### ADMIN_EMAIL & PASSWORD
```
Email: admin@cybersurx.io
Şifre: SecurePass2024!@# (güçlü olmalı)
```

#### DATABASE_URL
**PostgreSQL örneği:**
```
postgresql://db_user:db_pass@192.168.1.100:5432/cybersurx
```

**SQLite örneği (test için):**
```
sqlite:///./cybersurx.db
```

---

## 🛠️ Alternatif: Manuel Doldurma

Eğer quick-setup.sh script'ini kullanmak istemezsen:

### 1. secrets.env oluştur

```bash
cp secrets.env.example secrets.env
nano secrets.env
```

### 2. Değerleri doldur

```bash
JWT_SECRET_KEY=a7f9e3k2j1m9n8p0q3r5s7t9u2v4w6x8y0z
OLLAMA_API_KEY=sk-proj-xxxxx
ZAP_API_KEY=aegis-zap-secret
PROD_HOST=prod.example.com
PROD_USER=deploy
PROD_SSH_KEY=LS0tLS1CRUdJTi... (base64 encoded)
ADMIN_EMAIL=admin@cybersurx.io
ADMIN_DEFAULT_PASSWORD=SecurePass2024!@#
DATABASE_URL=postgresql://...
```

### 3. GitHub'a yükle

```bash
./scripts/setup-deployment-env.sh \
  --org your-github-org \
  --repo cybersurx \
  --file secrets.env
```

### 4. Temizle

```bash
rm secrets.env
```

---

## 🔍 Yararlı Komutlar

### Secrets'ı kontrol et
```bash
gh secret list
```

### Deployment'ı tetikle
```bash
gh workflow run deploy-staging.yml
gh workflow run deploy-production.yml
```

### Çalışan deployment'ı izle
```bash
gh run watch
```

### SSH key'i kontrol et
```bash
ssh -i ~/.ssh/id_rsa deploy@prod.example.com echo "test"
```

### Database bağlantısını test et
```bash
psql postgresql://user:pass@host:5432/db
```

---

## ❌ Hata Bulma

### "Not authenticated"
```bash
gh auth login
```

### "SSH key invalid"
```bash
# Key kontrol et
ssh -i ~/.ssh/id_rsa user@host echo "test"

# Base64 encoding kontrol et
base64 < ~/.ssh/id_rsa | head -c 50
```

### "Workflow doesn't trigger"
- Settings → Actions → Enable workflows
- Branch protection rules kontrol et
- git push develop ile test et

### "Deploy fails"
```bash
# SSH'ye bağlan
ssh deploy@prod.example.com
cd /opt/cybersurx

# Logs'u göster
docker compose logs -f api

# Container'ları kontrol et
docker compose ps
```

---

## 📚 Detaylı Rehberler

- **[SECRETS_FILLED_GUIDE.md](SECRETS_FILLED_GUIDE.md)** - Her secret hakkında detay
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Tam deployment kılavuzu
- **[DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md)** - Komut referansı

---

## ✅ Kontrol Listesi

Setup'tan sonra kontrol et:

- [ ] `gh secret list` - Tüm secrets var mı?
- [ ] GitHub Environments oluşturdun mu (staging, production)?
- [ ] Branch protection rules var mı (main branch)?
- [ ] Test push: `git push origin develop`
- [ ] Deployment triggered mi?
- [ ] Health check geçti mi?

---

## 🎉 Başarılı!

Deploy edildiğinde:

1. ✅ Staging'e: develop branch push → auto deploy
2. ✅ Production'a: main branch push (PR approved) → auto deploy
3. ✅ Rollback: Otomatik (hata varsa) veya manuel

**Hepsi bitti!** 🚀
