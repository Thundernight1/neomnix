# Deployment Secrets Setup Guide

Deployment pipeline'ı çalıştırmak için GitHub Secrets'a bilgileri eklemeniz gerekiyor.

## 3 Yöntem

### Metod 1: Interactive Setup (En Kolay)

```bash
./scripts/setup-deployment-interactive.sh
```

Aşağıdaki soruları soracak:
- GitHub Organization
- GitHub Repository
- Tüm secrets'ı interaktif olarak girmeniz istenecek

### Metod 2: Environment File (Tavsiye Edilen)

1. **Template'i kopyala:**
   ```bash
   cp secrets.env.example secrets.env
   ```

2. **Secrets'ı doldur:**
   ```bash
   # secrets.env dosyasını açıp değerleri doldur
   nano secrets.env
   ```

3. **Upload et:**
   ```bash
   ./scripts/setup-deployment-env.sh \
     --org yourorg \
     --repo yourrepo \
     --file secrets.env
   ```

4. **Sil (ÖNEMLI - Secret'ları korumak için):**
   ```bash
   rm secrets.env
   ```

### Metod 3: GitHub Web UI (Manuel)

1. Repository'yi aç
2. Settings → Secrets and variables → Actions
3. Her secret'ı manuel olarak ekle
4. Organization-level secrets için: Settings → Secrets and variables → Actions

## Required Secrets (Zorunlu)

| Secret | Açıklama | Örnek |
|--------|----------|--------|
| `JWT_SECRET_KEY` | JWT signing key (min 32 chars) | `abc123def456...` (32+ random chars) |
| `OLLAMA_API_KEY` | LLM API key | From Ollama config |
| `ZAP_API_KEY` | Security scanner key | From OWASP ZAP |

## Staging Secrets

| Secret | Açıklama |
|--------|----------|
| `STAGING_HOST` | staging.example.com |
| `STAGING_USER` | SSH user (e.g., deploy) |
| `STAGING_SSH_KEY` | SSH private key (base64 encoded) |

## Production Secrets

| Secret | Açıklama |
|--------|----------|
| `PROD_HOST` | prod.example.com |
| `PROD_USER` | SSH user |
| `PROD_SSH_KEY` | SSH private key (base64 encoded) |
| `ADMIN_EMAIL` | Admin email |
| `ADMIN_DEFAULT_PASSWORD` | Initial password |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_PASSWORD` | Redis auth password |

## SSH Key Encoding

SSH private key'ı base64 encode etmek için:

```bash
# macOS/Linux
base64 -i ~/.ssh/id_rsa

# Windows (PowerShell)
certutil -encode input.key output.b64
```

Output'u kopyala ve secret'a yapıştır.

## Environment Setup (GitHub)

GitHub'da environment'lar oluştur:

1. Settings → Environments
2. "New environment" → "staging"
3. "New environment" → "production"
4. Production için:
   - Required reviewers ekle
   - Deployment branches kuralı set et

## Test

Setup'tan sonra secrets'in çalıştığını test et:

```bash
# List secrets (check they exist)
gh secret list

# Trigger staging deploy
gh workflow run deploy-staging.yml

# Watch progress
gh run watch
```

## Güvenlik Notları

⚠️ **ÖNEMLI:**

1. **Never commit secrets.env** - `.gitignore`'a ekle
2. **Use organization secrets** for shared values (Staging, API keys)
3. **Use environment secrets** for prod-only values
4. **Rotate JWT_SECRET_KEY** quarterly
5. **Never share secrets** - use GitHub UI for setup
6. **Audit secret access** - check GitHub security logs regularly

## Troubleshooting

### "Not authenticated"
```bash
gh auth login
```

### "Could not determine repository"
```bash
./scripts/setup-deployment-env.sh --org myorg --repo myrepo
```

### Secret not found in workflow
1. Check secret exists: `gh secret list`
2. Verify organization vs repository secrets
3. Workflows use repository secrets by default

### SSH key not working
```bash
# Verify key is valid
ssh -i ~/.ssh/id_rsa user@host echo "test"

# Re-encode if needed
base64 -i ~/.ssh/id_rsa | pbcopy
```

## Next Steps

1. ✅ Setup secrets using one of the methods above
2. ✅ Create GitHub environments (staging, production)
3. ✅ Setup branch protection rules
4. ✅ Configure production domain SSL
5. ✅ Test: `gh workflow run deploy-staging.yml`
6. ✅ Read: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
