# Neomnix: Git teslim ve main birleştirme komutları

Bu komutlar kullanıcı tarafından çalıştırılacak yönergelerdir; bu denetimde uzak
GitHub deposuna push veya merge yapılmadı. `release/production-audit-20260917`
dalında PR #6 ve #7'nin commit geçmişi birleştirilmiştir. Giriş ekranı ve paket
dosyası çakışmalarında denetlenmiş release sürümü korunmuştur.

## Paketi içeri alma

Önce ekli `neomnix-release.bundle` dosyasını indirin. Aşağıdaki akış yeni bir
klasör oluşturur; mevcut çalışma ağacınıza reset/clean uygulamaz. Aynı adlı
`neomnix-release-review` klasörü varsa farklı bir klasör seçin.

```bash
set -euo pipefail
read -r -p "İndirdiğiniz neomnix-release.bundle dosyasının tam yolu: " BUNDLE
test -f "$BUNDLE"
git clone https://github.com/Thundernight1/neomnix.git neomnix-release-review
cd neomnix-release-review
git bundle verify "$BUNDLE"
git fetch "$BUNDLE" release/production-audit-20260917:release/production-audit-20260917
git switch release/production-audit-20260917
git fetch origin --prune
git status --short
git log --oneline --graph -12
git diff --stat origin/main...HEAD
git diff --check
```

Göreli bundle yolu kullanmayın: clone klasörüne girildikten sonra da geçerli
olması için tam dosya yolu girin. Main bu denetimden sonra ilerlediyse release
dalına yeni main değişikliklerini alın; hiçbir çakışmayı topluca `--ours` veya
`--theirs` ile körlemesine kapatmayın.

```bash
git merge --no-edit origin/main
```

Merge çakışırsa durun, ilgili dosyaları inceleyip düzenleyin ve testlerden sonra
`git add` / `git commit` ile tamamlayın. Aşağıdaki yayın komutlarına çakışma
çözülmeden geçmeyin.

## Yerel doğrulama

Python 3.12, Node 22 ve Docker/Compose kurulu olmalıdır. Gerçek sır üretmeden
önce environment/deployment yönergesi için README'yi okuyun.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
(cd backend && ../.venv/bin/pytest -q && ../.venv/bin/bandit -r src -q)
.venv/bin/pip install pip-audit
.venv/bin/pip-audit -r backend/requirements.lock
(cd frontend && npm ci && npm run lint && npm test && npm run build)
(cd frontend && npm audit --audit-level=high)
docker build -f backend/Dockerfile.prod backend
docker build frontend
git diff --check
test -z "$(git status --porcelain)"
```

## Onaydan sonra GitHub'a gönderme

Bu bölüm dış sisteme yazar. Denetim bulgularını ve dosya değişikliklerini
onayladıktan sonra çalıştırın. Önce yalnızca release dalı ve PR oluşturulur;
main doğrudan güncellenmez.

```bash
git push -u origin release/production-audit-20260917
gh pr create --repo Thundernight1/neomnix \
  --base main --head release/production-audit-20260917 \
  --title "Release candidate: real scan workflows and security hardening" \
  --body "Implements real PCAP/Celery/report workflows, tenant/session hardening, migrations and release CI. Integrates the histories and intent of PRs #6 and #7. Local verification: 193 backend tests, 2 frontend tests, lint/build and real PCAP-to-PDF flow passed. Container/staging, TLS, backup restore, retention and regulatory acceptance remain required gates. See AUDIT-REPORT.md. Do not merge until CI and release-owner review pass."
gh pr checks release/production-audit-20260917 \
  --repo Thundernight1/neomnix --watch
```

## Main'i güncelleme

Yalnızca CI, kod incelemesi ve AUDIT-REPORT.md içindeki üretim kabul koşulları
tamamlandıktan sonra çalıştırın. İncelenen HEAD SHA, merge sırasında değişmiş
commit'in yanlışlıkla onaylanmasını önler. Otomatik/koşulsuz merge kullanılmaz.

```bash
REVIEWED_SHA="$(git rev-parse HEAD)"
gh pr merge release/production-audit-20260917 \
  --repo Thundernight1/neomnix --merge \
  --match-head-commit "$REVIEWED_SHA"
git switch main
git pull --ff-only origin main
git log -1 --oneline
git status --short
```

Merge commit yöntemi PR #6/#7 geçmişlerini korur; squash/rebase merge kullanmayın
eğer bu PR ancestry'sinin main'de korunmasını istiyorsanız. Uzak açık PR'ların
durumunu sonradan kontrol edin; gerekirse superseded açıklamasıyla kapatma ayrı
bir kullanıcı onayı gerektirir. Force push ve üretim verisi silme bu akışta yoktur.
