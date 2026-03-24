# 🚀 CyberSurX Deployment Pipeline - Başlangıç Sayfası

**Türkçe Kurulum Rehberi - EN KOLAY YOLDAN BAŞLA**

---

## ⚡ 2 Dakikalık Hızlı Kurulum

```bash
./scripts/quick-setup.sh
```

Bu script'i çalıştırırsan:
- ✅ Senden gerekli secrets'ı soracak
- ✅ GitHub'a otomatik yükleyecek
- ✅ Hiçbir dosya bırakmayacak

**İşte bu kadar!** 🎉

---

## 📚 Dokümantasyon Rehberi

### 👉 Başlangıç İçin (Beni Oku!)
**Dosya:** `TURKCE_BASLA.md`
- Türkçe dilinde tam rehber
- 5 dakikalık setup
- Hata çözme talimatları
- **Okuma süresi:** 5 dakika

### 👉 Referans Için
**Dosya:** `CHEATSHEET.md`
- 1 sayfalık hızlı komut listesi
- Secrets referansı
- Deployment flow
- **Okuma süresi:** 2 dakika

### 👉 Secrets Hakkında Soruların Varsa
**Dosya:** `SECRETS_FILLED_GUIDE.md`
- Her secret'ın detaylı açıklaması
- Nereden bulacağınız gösterilir
- Hangi değerleri kullanacağınız
- **Okuma süresi:** 10 dakika

### 👉 Tüm Detaylar İçin
**Dosya:** `DEPLOYMENT_GUIDE.md`
- Tam deployment kılavuzu
- Her workflow'un detayı
- Troubleshooting section
- **Okuma süresi:** 30 dakika

### 👉 Yenileri Gören İçin
**Dosya:** `FILES_CREATED.md`
- Neler eklendiğinin listesi
- Dosya ağacı
- Her dosya ne için
- **Okuma süresi:** 5 dakika

---

## 🎯 Senin Durum Hangisi?

### "Hemen başlamak istiyorum"
```bash
./scripts/quick-setup.sh
# Bitti! GitHub Environments oluştur + branch protection ekle
```

### "Adım adım gitmek istiyorum"
1. `cat TURKCE_BASLA.md` - Oku (5 min)
2. `./scripts/quick-setup.sh` - Çalıştır (2 min)
3. GitHub Environments & Branch Protection (2 min)
4. `git push origin develop` - Test et (5 min)

### "Secrets'ı nasıl dolduracağımı bilmiyorum"
```bash
cat SECRETS_FILLED_GUIDE.md
# Bölüm: "Secrets NELERDİR?" ve "Gerekli Değerleri Nereden Bulacağım?"
```

### "Komutları merak ediyorum"
```bash
cat CHEATSHEET.md
# Tüm komutları 1 sayfada bulabilirsin
```

### "Detaylı bilgi istiyorum"
```bash
cat DEPLOYMENT_GUIDE.md
# 10KB tam kılavuz - tüm soruların cevapı var
```

---

## 🔑 Secrets: Ne Soracak Sistem?

### 3 Zorunlu Secret
1. **JWT_SECRET_KEY** - Oluştur: `openssl rand -hex 32`
2. **OLLAMA_API_KEY** - docker-compose.yml'de bak
3. **ZAP_API_KEY** - docker-compose.yml'de bak (genelde: aegis-zap-secret)

### Optional: Production Secrets
- PROD_HOST, PROD_USER, PROD_SSH_KEY
- ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD
- DATABASE_URL
- REDIS_PASSWORD

İlk 3'ünü vermezsen setup çalışmaz. Ötekiler geç de ekleyebilirsin.

---

## 📋 Adım Adım Talimatlar

### 1. Ultra-Basit Setup (2 dakika)
```bash
./scripts/quick-setup.sh

# Sorular:
# - GitHub org
# - GitHub repo
# - JWT_SECRET_KEY (generate: openssl rand -hex 32)
# - OLLAMA_API_KEY (find: grep OLLAMA docker-compose.yml)
# - ZAP_API_KEY (find: grep ZAP docker-compose.yml)
# - Optional: PROD_HOST, PROD_USER, etc.
```

### 2. GitHub Environments Oluştur (2 dakika)
**Git:** Settings → Environments
```
Create: "staging"
Create: "production"
  - Add required reviewers
  - Deployment branches: main
```

### 3. Branch Protection Ekle (1 dakika)
**Git:** Settings → Branches → Add rule
```
Pattern: main
✓ Require a pull request
✓ Require status checks to pass
✓ Require approval from collaborators
```

### 4. Test Deploy (5 dakika)
```bash
git checkout develop
echo "test" >> README.md
git add .
git commit -m "test deployment"
git push origin develop

# Deployment otomatik başlayacak
# Bunu izle: gh run watch
```

### ✅ TAMAMLANDI!
Production'a deploy etmek artık çok basit:
```bash
# 1. PR aç, approve et
git checkout -b feature/something
git push origin feature/something
# GitHub'da PR aç, merge et

# 2. Production'a otomatik deploy olur
# Hepsi bitti!
```

---

## 🆘 Hızlı Problem Çözme

| Problem | Çözüm |
|---------|-------|
| "Secrets nedir?" | `cat SECRETS_FILLED_GUIDE.md` |
| "Komutlar?" | `cat CHEATSHEET.md` |
| "SSH key nasıl?" | `base64 < ~/.ssh/id_rsa` (hepsini kopyala) |
| "Setup takıldı?" | GitHub CLI ile: `gh auth login` |
| "Deploy başarısız?" | `ssh deploy@host` → `docker compose logs` |

---

## 📂 Dosyalar Neler?

### Workflows (Otomatik)
- `deploy-staging.yml` - develop → staging
- `deploy-production.yml` - main → production
- `deploy-k8s.yml` - Manual Kubernetes

### Docker Compose
- `docker-compose.staging.yml` - Test ortamı
- `docker-compose.prod.yml` - Üretim ortamı

### Scripts (Manuel)
- `quick-setup.sh` - Setup (Recommended)
- `verify_deployment.sh` - Health check
- `rollback.sh` - Emergency rollback

### Dokümantasyon
- **`TURKCE_BASLA.md`** ← Beni oku! (5 min)
- `CHEATSHEET.md` - 1-page referans (2 min)
- `SECRETS_FILLED_GUIDE.md` - Secrets detayı (10 min)
- `DEPLOYMENT_GUIDE.md` - Tam kılavuz (30 min)

---

## ✅ Tamamlama Kontrol Listesi

Setup'tan sonra bu soruları sor kendine:

- [ ] `./scripts/quick-setup.sh` çalıştırdın mı?
- [ ] GitHub Environments oluşturdun mu (staging + production)?
- [ ] Branch protection rules ekledin mi (main)?
- [ ] `gh secret list` ile secrets'ı gördün mü?
- [ ] `git push origin develop` ile test deployment yaptın mı?
- [ ] Deployment başarılı mı (`gh run watch`)?
- [ ] Health check geçti mi (`./scripts/verify_deployment.sh`)?

Hepsi evet ise: **TAMAMLANDI!** 🎉

---

## 📞 İhtiyacın Olan Şey Ne?

- **"Hızlı başla"** → `./scripts/quick-setup.sh`
- **"Türkçe rehber"** → `cat TURKCE_BASLA.md`
- **"Komut listesi"** → `cat CHEATSHEET.md`
- **"Secrets sorular"** → `cat SECRETS_FILLED_GUIDE.md`
- **"Detaylı bilgi"** → `cat DEPLOYMENT_GUIDE.md`
- **"Tüm dosyalar"** → `cat FILES_CREATED.md`

---

## 🚀 HEMEN BAŞLA

```bash
# Bu komutu çalıştır
./scripts/quick-setup.sh

# Veya bu dosyayı oku
cat TURKCE_BASLA.md
```

**Başarılar!** 🎊

---

**Sorular?** Bak:
- `SECRETS_FILLED_GUIDE.md` - Secrets soruları
- `CHEATSHEET.md` - Komut soruları  
- `TURKCE_BASLA.md` - Genel sorular
- `DEPLOYMENT_GUIDE.md` - Tüm detaylar

**Daha da hızlı:** `./scripts/quick-setup.sh` ⚡
