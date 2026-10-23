# SPILTON Snake Rescue — Day 6 Checklist

Started: 16 October 2026

Day 6 integrates and hardens the existing demo MVP. Live rescue dispatch, real notifications, real payments, settlement, and payout remain disabled.

## P0 — Safety, security, and data integrity

- [x] Re-audit server-side demo, authorization, payment, notification, tracking-consent, and privacy gates.
- [x] Add request correlation IDs, secure response headers, privacy-safe structured request logs, readiness and operations-health checks.
- [x] Implement authenticated profile edit plus account export/deletion-request foundations without immediate destructive deletion.
- [x] Improve logout/session invalidation and document the deliberate absence of long-lived refresh tokens.
- [x] Verify evidence, financial, booking, tracking, admin, and cross-user authorization with automated tests.
- [x] Verify Decimal commission/refund ledger consistency and duplicate-operation protection.

## P1 — Connected end-to-end workflows

- [x] Verify the existing full API integration path from booking creation through acceptance, tracking, arrival, completion, demo payment, ledger, and review.
- [x] Run rejection, no-rescuer, expired-authorization, payment-failure/retry, tracking-expiry, and cross-owner regression coverage.
- [x] Audit customer, rescuer, and admin navigation and connect profile/privacy actions.
- [x] Add authenticated account/profile controls to web and mobile.
- [x] Verify OpenAPI contracts and shared web/mobile payload compatibility.

## P2 — Localization, reliability, performance, and accessibility

- [x] Maintain centralized per-client translation catalogs for English, Telugu, Tamil, Kannada, and Malayalam with English fallback and a cross-client quality gate.
- [x] Persist language preferences and add missing-key diagnostics in development.
- [ ] Complete human-reviewed translation of all detailed admin/finance/completion copy; primary account/marketplace navigation is translated and critical medical fallback remains labelled.
- [x] Add index/query integrity review and a measured 40-request in-process read smoke without presenting it as production capacity.
- [x] Improve profile/privacy loading, retry, error, and status states.
- [x] Verify SSE/event ordering, notification retry, stale tracking behavior through regression tests and add a restart-safe worker scheduler.

## P3 — Release preparation

- [x] Add CI security/secret/dependency scanning and final quality gates without unsafe automatic dependency upgrades.
- [x] Document Docker services, worker processes, backup/restore, rollback, HTTPS, storage, and external credential requirements.
- [x] Create `DAY6_REPORT.md` and `DAY7_RELEASE_CHECKLIST.md`; update README.
- [x] Run backend tests, migration checks, Python format/lint, web lint/type/build, mobile typecheck, Expo dependency/bundle checks, dependency audit, and secret scan.
- [x] Explicitly document skipped PostgreSQL, physical-device, provider-delivery, authoritative LGD, Docker-daemon, and external load validations.
