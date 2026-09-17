# Neomnix teknik denetim ve sürüm adayı

Denetlenen başlangıç: `12b715e89daef738ee41b45e1c807ae9bb592f0d`.
Kod deposu: https://github.com/Thundernight1/neomnix

## Sonuç ve kapsam

Bu teslim, uygulanmış düzeltmeler ve çalıştırılmış kontroller içeren bir sürüm
adayıdır. “Tüm güvenlik açıkları kapandı” veya “doğrudan müşteri kullanımına hazır”
iddiası değildir. Aşağıdaki dağıtım, operasyon ve mevzuat kabul koşulları
tamamlanmadan üretime alınmamalıdır. Uzak `main` dalına yazılmadı.

Kullanıcı onayıyla release dalı gönderildi ve
[PR #8](https://github.com/Thundernight1/neomnix/pull/8) açıldı.
`0862f26` kod commit'i için backend, frontend ve Docker image build işleri
[GitHub Actions'ta başarılı tamamlandı](https://github.com/Thundernight1/neomnix/actions/runs/35178923611).
Netlify preview da başarılı; yardımcı header/page/redirect kontrolleri skipped
durumundadır. Bu sonuçlar tam Compose staging veya üretim onayı değildir.

## Düzeltilen önemli sorunlar

- Frontend temiz kurulumundaki ESLint peer dependency çakışması, TypeScript
  hataları, kullanılmayan importlar ve oturum/hata mesajları düzeltildi.
- localStorage oturum kanıtı kaldırıldı; sunucu doğrulaması, zorunlu parola
  değişimi, tenant/rol sınırları ve aktif kullanıcı/kurum kontrolleri eklendi.
- JWT için zorunlu süre/kimlik alanları, parola değişiminde token geçersizleştirme,
  üretimde Redis iptal listesi ve HttpOnly cookie kullanımı güçlendirildi.
- Eksik tarama listeleme/detay, PCAP yükleme ve audit API akışları gerçek
  SQLAlchemy/Celery/tshark işlemleriyle tamamlandı.
- Yabancı tenant tarama/gap/task erişimleri kapatıldı. Aktif taramalar açık
  CIDR izin listesine bağlandı; varsayılan davranış erişimi reddeder.
- Geçersiz veya büyük capture doğrulaması, güvenli dosya yolu, görev başarısızlığı
  ve ham yükleme temizliği eklendi. Worker hatası artık başarı gibi sunulmuyor.
- PDF Unicode/font hatası giderildi. PDF üretimi başarısızsa görev de başarısız
  oluyor; eksik raporla sessiz “completed” sonucu üretilmiyor.
- Gap kontrol-citation ilişkisi düzeltildi. Kullanılamayan AI servisi artık sahte
  tavsiye üretmiyor. Dev/test mockları gerçek üretim mantığıyla karıştırılmadı.
- Uygulamadaki kullanılmayan Crossmap ve karşılığı olmayan command API istemcisi
  kaldırıldı. UI input placeholder'ları ve test mockları yerinde bırakıldı.
- Yanıltıcı canlı/uyumluluk/hibe göstergeleri azaltıldı; veri yokluğu başarı değil
  değerlendirilmemiş durum olarak gösteriliyor.
- Üretim Compose, kilitli bağımlılıklar, fail-fast migration/startup, güvenli env
  üretimi ve CI kontrolleri eklendi.

## Çalıştırılan doğrulamalar

| Kontrol | Sonuç ve sınır |
|---|---|
| Python 3.12 backend testleri | 193 geçti; 252 uyarı mevcut |
| Frontend temiz kurulum | `npm ci` başarılı |
| Frontend lint | Başarılı |
| Frontend testleri | 2 geçti; kapsam sınırlı |
| TypeScript + Vite production build | Başarılı |
| GitHub Actions | Backend/frontend/image işleri başarılı; PostgreSQL 17 migration kontrolü dahil |
| Python bağımlılık taraması | `pip-audit` bilinen açık bulmadı |
| npm bağımlılık taraması | Audit sırasında bilinen açık bulunmadı |
| Statik Python güvenlik kontrolü | Bandit bulgu üretmedi |
| Git whitespace kontrolü | `git diff --check` başarılı |
| Migration | Yeni SQLite ve gerçek PostgreSQL 18 üzerinde head ve tekrar çalıştırma başarılı |
| Gerçek servis akışı | PostgreSQL + Redis + Celery + tshark ile sentetik PCAP işlendi |
| PDF | HIPAA-2026 ve WA-MHMDA raporları HTTP 200 ve geçerli PDF imzasıyla indirildi |
| Yetki ve veri kontrolü | Tenant izolasyonu/rol/izin listesi regresyon testleri geçti |
| Parola döndürme | Yeni cookie çalıştı, eski token HTTP 401 aldı |
| Hatalı capture | HTTP 422 ile reddedildi |
| Audit ve çıkış | Rapor indirme audit kaydı ve logout sonrası HTTP 401 doğrulandı |
| Tarayıcı | Login, zorunlu reset, dashboard, PCAP, detay, audit, CSV; masaüstü/mobil kontrol edildi |
| Mobil düzen | Scan ve audit başlık taşmaları düzeltildi; 390px görünümde sayfa taşması yok |

Gerçek analiz için yalnızca dokümantasyon IP adresleri içeren üretilmiş test
capture'ı kullanıldı. Üçüncü taraf sistemlere aktif tarama yapılmadı. Backend
testlerindeki uyarılar, frontend ESLint sürümünün destek uyarısı ve sınırlı frontend
test kapsamı teknik borçtur; “sıfır uyarı” iddiası yoktur.

## Dosya bazlı değişiklik amacı

| Dosya | Amaç |
|---|---|
| `.gitignore` | Güvenli örnek env dosyalarının izlenmesi |
| `.github/workflows/ci.yml` | Test, audit, migration ve image build kapıları |
| `README.md` | Gerçek kurulum, operasyon ve kapsam sınırları |
| `AUDIT-REPORT.md` | Denetim sonuçları ve dosya bazlı açıklamalar |
| `GIT-RELEASE.md` | Bundle import, kontrollü PR/CI/main komutları |
| `QA-INVENTORY.md` | Kontrol matrisi ve üretim kabul başlıkları |
| `secrets.env.example` | Zorunlu ve opsiyonel ayarların sır içermeyen şablonu |
| `scripts/init-env.sh` | Rastgele bağımsız sırlar ve mode-600 env oluşturma |
| `docker-compose.production.yml` | PostgreSQL/Redis/API/worker/ZAP/frontend üretim topolojisi |
| `docker-compose.yml` | Ortak üretim Compose yapılandırmasına yönlendirme |
| `docker-compose.beta.yml` | Güvensiz ayrı beta varsayımlarını kaldırma |
| `backend/.dockerignore` | Yerel sırları/verileri build context dışında tutma |
| `backend/Dockerfile.prod` | Python 3.12, lock, migration ve tshark/font runtime |
| `backend/start.sh` | Yapılandırma/DB/migration hata durumunda başlangıcı durdurma |
| `backend/requirements.txt` | PyJWT geçişi, gereksiz Stripe bağımlılığının kaldırılması |
| `backend/requirements.lock` | Tekrarlanabilir Python 3.12 bağımlılık sürümleri |
| `backend/alembic/env.py` | Ortam DATABASE_URL kullanımını düzeltme |
| `backend/alembic/versions/0000_baseline.py` | Sıfırdan migration zincirini çalıştırma |
| `backend/alembic/versions/1e518a1fd67f_remove_stripe_billing_and_legacy_scan_.py` | Baseline migration bağımlılığı |
| `backend/alembic/versions/0002_unique_user_email.py` | Veri silmeden duplicate kontrolü ve email unique index |
| `backend/src/api/auth.py` | JWT, parola, rol, tenant ve üretim oturum iptali |
| `backend/src/api/main.py` | Cookie/CSRF origin, reset, readiness, istatistik ve WebSocket |
| `backend/src/api/scans.py` | Gerçek tenant-scope tarama/PCAP/audit API uçları |
| `backend/src/api/gap.py` | Tenant/task ownership, framework doğrulama ve hata yönetimi |
| `backend/src/agents/compliance.py` | PDF hatasını görev sonucuna yansıtma |
| `backend/src/agents/scanner.py` | Gerçek scanner hataları ve ZAP istemci düzeltmesi |
| `backend/src/orchestrator.py` | Tarama yoğunluk sınırı |
| `backend/src/services/alerts.py` | Tenant bazlı Redis publish/subscribe |
| `backend/src/services/gap_analyzer.py` | Framework kapsamı ve citation ilişki düzeltmesi |
| `backend/src/services/remediation_ai.py` | Sahte AI fallback yerine açık unavailable sonucu |
| `backend/src/skills/sharktap_skill.py` | Tshark hata/timeout durumunu sessiz başarıdan ayırma |
| `backend/src/skills/base.py` | UUID dosya adı, mode-600 kanıt kaydı ve yazma hatasını görünür kılma |
| `backend/src/skills/zap_skill.py` | API anahtarı ve bounded polling |
| `backend/src/utils/pdf_exporter.py` | Unicode fallback ve her PDF nesnesinde font kaydı |
| `backend/src/worker/tasks.py` | Gerçek PCAP işi, başarısızlık, kaynak temizliği, task ayarları |
| `backend/tests/test_auth.py` | Geçerli süreli JWT test fixture'ları |
| `backend/tests/test_gap.py` | Yeni güvenli task ownership davranışına uyum |
| `backend/tests/test_ws_alerts.py` | Tenant içeren alert fixture'ı |
| `backend/tests/test_release_security.py` | Tenant/rol/scope/veri yokluğu regresyonları |
| `backend/tests/test_pdf_release.py` | Unicode ve ardışık PDF regresyonları |
| `frontend/.dockerignore` | Yerel bağımlılık/sır/build artığını dışlama |
| `frontend/.env.example` | Aynı origin API prefix ayarı |
| `frontend/Dockerfile` | Node 22 ve temiz lock tabanlı build |
| `frontend/nginx.conf` | PCAP yükleme boyut desteği |
| `frontend/package.json` | Uyumlu bağımlılıklar ve lint/test/typecheck/build |
| `frontend/package-lock.json` | Çözümlenmiş ve audit edilmiş frontend sürümleri |
| `frontend/eslint.config.js` | Paylaşılan UI exportları için dar kapsamlı kurallar |
| `frontend/vite.config.ts` | ESM alias ve geliştirme WebSocket proxy |
| `frontend/src/App.tsx` | Sunucu doğrulamalı korumalı route ve reset kapısı |
| `frontend/src/App.test.tsx` | Gerçek render/hata davranışı testleri |
| `frontend/src/components/LoginScreen.tsx` | Görünür hata/expiry, validation, cookie tabanlı giriş |
| `frontend/src/components/ForcePasswordChangeModal.tsx` | Token localStorage bağımlılığını kaldırma |
| `frontend/src/components/Dashboard.tsx` | Gerçek PCAP/scan akışı ve dürüst boş/offline durumları |
| `frontend/src/components/ScanDetail.tsx` | Gerçek status, framework, tip güvenliği ve mobil düzen |
| `frontend/src/components/AuditLog.tsx` | CSV injection önlemi, tipler, mobil düzen, yanlış iddiaların kaldırılması |
| `frontend/src/components/Crossmap.tsx` | Silindi: kullanılmayan eksik UI |
| `frontend/src/components/ui/GlassCard.tsx` | Motion props/children TypeScript uyumu |
| `frontend/src/components/ui/input.tsx` | ESLint uyumlu prop tipi |
| `frontend/src/lib/api.ts` | API_BASE, desteklenen scan tipleri, çalışmayan command istemcisinin silinmesi |
| `frontend/src/lib/useTheme.ts` | Güvenli tip dönüşümleri ve effect davranışı |

## Git ve pull request durumu

Denetim sırasında açık iki PR vardı:
[PR #7](https://github.com/Thundernight1/neomnix/pull/7) giriş ekranı düzeltmesi ve
[PR #6](https://github.com/Thundernight1/neomnix/pull/6) frontend bağımlılık güncellemesi.
GitHub ikisini de MERGEABLE olarak bildirdi; bu CI veya üretim onayı değildir.
İki PR yerel release dalına gerçek merge commit'leriyle birleştirildi. Release
düzeltmeleriyle oluşan LoginScreen/package/lock çakışmaları, PR amaçlarını kapsayan
test edilmiş release dosyaları korunarak çözüldü.
Kullanıcı push/PR açılmasını onayladı; PR #8 açık ve mergeable durumdadır.
Main birleştirmesi onaylanmadı ve uygulanmadı.
Teslim edilen Git yönergesi önce release branch/PR, sonra kontrollü main merge
akışını kullanır; force push veya branch silme içermez.

## Üretim öncesinde tamamlanması gerekenler

- Docker image build ve PostgreSQL 17 migration GitHub Actions'ta geçti.
  Tam Compose staging boot ve Redis 7 hedefinde entegrasyon hâlâ doğrulanmalıdır;
  yerel entegrasyon PostgreSQL 18/Redis 8 kullandı.
- HTTPS domain, TLS ingress, WebSocket proxy, gerçek secret dağıtımı ve ağ
  izolasyonu deployment sahibi tarafından yapılandırılmalıdır.
- PostgreSQL restore provası, migration öncesi yedek, duplicate-email incelemesi
  ve eski veritabanı snapshot'ı üzerinde yükseltme testi zorunludur.
- PCAP, `data/raw`, PDF ve audit verileri için PHI/gizlilik değerlendirmesi,
  depolama şifreleme, retention/deletion ve yedek erişim politikası gereklidir.
  Audit log append-only veya kriptografik olarak değiştirilemez değildir.
- Onaylı mevzuat kontrol kataloğu, rapor metinleri ve heuristic skor yorumları
  hukuk/uyumluluk uzmanı tarafından incelenmelidir. Eksik katalog veri uydurularak
  tamamlanmadı; mevcut mevzuat etiketleri hukuki doğruluk garantisi değildir.
- Yetkili staging kapsamındaki Nmap/ZAP uçtan uca taraması, kuyruk/worker çökme
  senaryoları, yük/DoS kontrolleri, üretim Redis revocation/WebSocket entegrasyon
  testi, yedekleme ve alarm/sorumluluk planı tamamlanmalıdır.
- Yerel statik ve bağımlılık kontrolleri kapsamlı penetrasyon testi, tüm Git
  geçmişi secret taraması veya bağımsız güvenlik onayının yerine geçmez.
- Migration baseline canlı model metadata'sını kullanır; sonraki şema değişiklikleri
  immutable migration disiplinine taşınmalıdır. Dev `create_all` davranışı
  migration ile uygulanan tüm üretim index kurallarını birebir temsil etmez.

## Teslim biçimi

Kaynak ZIP'i tam repo dosyalarını; tam-dosya Markdown paketi değişen/eklenen her
metin dosyasının eksiksiz içeriğini içerir. Silinen dosya ayrıca işaretlidir.
Lock dosyaları dahil içerikler kısaltılmadı. Gerçek sırlar, test capture'ları,
veritabanları, node_modules ve sanal ortamlar teslim edilmez.
