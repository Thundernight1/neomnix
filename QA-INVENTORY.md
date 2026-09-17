# Release QA inventory

This is a release-candidate audit, not a legal compliance certification.

| Requirement | Check |
|---|---|
| Login | Wrong password is visible; valid login uses HttpOnly cookie |
| Session | Server-side session check; forced password change blocks protected endpoints |
| Capture upload | Valid capture accepted; invalid/oversize file rejected; worker failure visible |
| Findings | Real tshark result persisted; no synthetic successful fallback |
| Isolation | Foreign scan, gap organization and task denied |
| Roles | Viewer cannot submit jobs or export administrator reports |
| Reports | Completed scan details and both supported PDF downloads |
| Live alerts | Tenant-separated Redis channel; no raw packet data in notifications |
| Database | Fresh SQLite and PostgreSQL migrations; application startup |
| Tooling | npm ci, lint, typecheck/build, frontend tests, backend tests, dependency audit |
| UI | Login, password reset, dashboard, detail and audit at desktop/mobile; overflow and console errors |
| Failure modes | Invalid credentials, invalid capture, unavailable worker, unauthorized target |

Production-only gates: TLS ingress, deployed container image builds, backup restore,
retention policy, authorized regulatory control catalog, vulnerability-management
review, and load/availability testing require deployment-owner signoff.
