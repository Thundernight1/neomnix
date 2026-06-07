# Neomnix — Project Scope

## Healthcare Cybersecurity Compliance Automation

Automated compliance mapping and continuous monitoring for **HIPAA-2026** and **WA-MHMDA (RCW 19.373.030)**, tailored to grant-funded healthcare cybersecurity vendors.

**Target customer:** Mid-to-large enterprises holding federal/state grants (SBIR, HRSA, CDC, state health IT) that must maintain continuous evidence of compliance without manual audit prep.

## Core Deliverables

1. **Rule engine** mapping every technical control → HIPAA-2026 / WA-MHMDA citation.
2. **Real-time gap analysis** with evidence packaging.
3. **Critical-data-leak WebSocket alerts** (SharkTap integration).
4. **Admin-only VIP audit PDF** ("Healthcare Sector VIP Audit Report" / Turkish: *"Sağlık Sektörü VIP Denetim Raporu"*) with per-violation penalty schedule and grant-loss risk banner.
5. **Minimal dashboard** with three modules:
   - Active Data Leak Status
   - Grant Loss Risk Indicator
   - HIPAA Violation Summary

## Out of Scope (explicit)

- **SOC2, NIST-800-53, FedRAMP, PCI-DSS, CCM-4.0, SEC-2023** — framework support is permanently removed.
- **Public pricing, self-serve checkout, Stripe integration** — billing surface is admin/internal only.
- **Multi-framework N×N crosswalk** — removed in Chunk 2.
- **AI terminal, charting, scan history UI** — removed in Chunk 5.

## Risk Labels (used in finding output)

Each finding carries two business-language risk labels alongside its regulatory citations:

- `"HIPAA Ceza Riski"` — HIPAA penalty risk
- `"Devlet Hibesi (Grant) İptal Riski"` — grant cancellation risk

## Chunk Plan

| #  | Title                          | Status      | Branch                              | Tests verified |
|----|--------------------------------|-------------|-------------------------------------|----------------|
| 1  | Healthcare framework trim      | **Done**    | `refactor/chunk1-healthcare-frameworks` | 55 passed / 1 skipped |
| 2  | Rule engine integration        | Pending     | `refactor/chunk2-rule-engine`       | —              |
| 3  | Critical-alert WebSocket + admin-only PDF endpoint + Crossmap stub | Pending | `refactor/chunk3-alerts-and-pdf-role` | — |
| 4  | VIP PDF template               | Pending     | `refactor/chunk4-vip-pdf`           | —              |
| 5  | Dashboard rewrite              | Pending     | `refactor/chunk5-dashboard`         | —              |

### Chunk 1 — Healthcare framework trim (DONE)

Files changed:
- `backend/src/core/compliance_rules.json` — `metadata.frameworks` trimmed to `["HIPAA-2026", "WA-MHMDA"]`; `tcpwrapped` entry's controls gained `WA-MHMDA-RCW-19.373.030` (replaced removed SOC2/CCM controls).
- `backend/src/agents/compliance.py` — `_extract_frameworks()` default fallback set changed from `{HIPAA-2026, WA-MHMDA, NIST-800-53, SOC2}` to `{HIPAA-2026, WA-MHMDA}`.
- `backend/tests/test_compliance_agent_mapping.py` — replaced SOC2 input/assertion with HIPAA-2026 in `test_extract_frameworks_includes_wa_when_mixed_controls`; added `test_extract_frameworks_default_set_is_healthcare_only` asserting the new default set.
- `.gitignore` — added `.venv/`, `venv/`, `env/`.

### Chunk 2 — Rule engine integration (PENDING)

Files to touch:
- `backend/src/agents/cross_mapping_analyzer.py` — drop N×N multi-framework logic, map detected vulnerabilities to HIPAA-2026 + WA-MHMDA only, attach `risk_type` field per finding with the two risk labels.
- `backend/src/services/crossmap_engine.py` — `get_framework_matrix()` and `compute_all_control_mappings()` defaults: change from `["soc2", "hipaa", "nist", "mhmda"]` to `["hipaa", "mhmda"]`.
- `backend/src/services/gap_analyzer.py` — `SUPPORTED_FRAMEWORKS`: same trim.
- `backend/tests/test_crossmap.py` — matrix tests currently assert 4-framework default. Update to expect 2-framework matrix. Cosine/keyword tests are framework-agnostic and remain untouched.

### Chunk 3 — Critical-alert WebSocket + admin-only PDF endpoint + Crossmap stub (PENDING)

Files to touch:
- `backend/src/api/main.py` —
  - Add module-level `asyncio.Queue` (single instance, owned by the app).
  - Add `GET /ws/alerts?token=…` WebSocket route that authenticates via the existing JWT, then drains the queue until the client disconnects.
  - Trim `get_pdf_report` allowlist from `{"HIPAA-2026", "WA-MHMDA", "NIST-800-53", "SOC2"}` to `{"HIPAA-2026", "WA-MHMDA"}`.
  - Change PDF route auth from `Depends(get_current_user)` to `Depends(require_role("admin"))`.
- `backend/src/skills/sharktap_skill.py` — when a critical data leak threat is detected (UNENCRYPTED_DATABASE, DNS_TUNNELING_SUSPECTED, CLEARTEXT_TELNET_SESSION), push a structured alert object to a queue passed in via a constructor argument (no global). Default to a no-op queue so the skill remains testable in isolation.
- `backend/src/api/main.py` — pass the alert queue into `SharkTapSkill()` instantiation.
- `frontend/src/components/Crossmap.tsx` — replace with a stub component explaining the N×N logic has been removed and the system is now strictly HIPAA-2026 + WA-MHMDA.

### Chunk 4 — VIP PDF template (PENDING)

Files to touch:
- `backend/src/utils/pdf_exporter.py` —
  - Rename template string in the cover header to `"Sağlık Sektörü VIP Denetim Raporu"`.
  - For every critical finding, prominently display: estimated penalty amount (starting at $5,000+) and a large-font "Hibe İptal Riski (Grant Loss)" warning.
  - Add a comment block at the top of `generate_report()` explaining that role enforcement happens at the FastAPI route via `require_role("admin")` in `main.py` — the exporter itself is not the authorization boundary.

### Chunk 5 — Dashboard rewrite (PENDING)

Files to touch:
- `frontend/src/components/Dashboard.tsx` — gut down to:
  1. Active Data Leak Status (driven by WebSocket connection to `/ws/alerts`).
  2. Grant Loss Risk Indicator (Red/Green).
  3. HIPAA Violation Summary.
  4. Critical-alert overlay using existing `frontend/src/components/ui/alert.tsx`, flashing red when a critical alert arrives.
  5. WebSocket lifecycle (connect on mount, disconnect on unmount, simple reconnect-on-error).
  Delete: KPI row, charts, scan form, PCAP upload, history table, AI terminal. (~734 lines → ~150-200 lines.)
- `frontend/src/App.tsx` — remove the now-unused `import Crossmap from './components/Crossmap';` (currently imported but never routed).

## Hard Constraints (apply to every chunk)

1. **No new dependencies** unless strictly necessary. If a new dep is required, it must be called out in a code comment with justification.
2. **No fabricated test results** — every chunk must be verified by actually running `pytest` and reporting the real output, including any failures.
3. **User authorization before destructive operations** — any `rm -rf`, `git push`, `git reset --hard`, etc. requires explicit "go" from the user, not a confirmation of a previous plan.
4. **Narrative copy in `compliance_rules.json` is left untouched** — only structural `controls` lists and the `frameworks` metadata array are edited.
5. **Turkish + English labels are both preserved** in customer-facing surfaces.
6. **Auth pattern stays consistent** — JWT in `Authorization: Bearer …` for REST, JWT in `?token=…` query string for WebSocket (matching how the existing app handles bearer tokens in fetch headers; WebSockets in browsers cannot set custom headers easily).

## Branch & Commit Convention

- One feature branch per chunk: `refactor/chunk<N>-<short-slug>`.
- No pushes without explicit user approval.
- Each chunk's commit message: `refactor(chunk<N>): <one-line summary>`.
