# SPILTON Snake Rescue — Day 7 Release Checklist

Release decision: **NO-GO until every blocking item is checked and evidenced.** The only current release candidate is a controlled DEMO/staging build.

## Safety, legal, and operations — blocking

- [ ] Wildlife/legal counsel approves each intended state workflow and partner authorization process.
- [ ] Verified organizations, authorization evidence, service areas, escalation procedures, and human operating team are documented.
- [ ] Critical medical and safety copy is human-reviewed in English, Telugu, Tamil, Kannada, and Malayalam.
- [ ] Emergency contact directory contains only source-backed contacts with verification dates and owner/review process.
- [ ] Demo banners, no-live-availability wording, 112 guidance, and no-handling/photo-pressure language pass final content review.
- [ ] Real dispatch, authorized-operation, pricing, real payments, settlement, and payout remain disabled. Any future enablement requires a separate reviewed release—not an admin toggle.

## Data and infrastructure — blocking

- [ ] Import current official LGD state/district/subdistrict/village/ULB/ward exports and preserve source version/hash metadata.
- [ ] Run `python -m app.db.audit_lgd`; investigate every orphan/error and do not claim coverage beyond imported official records.
- [ ] Run `alembic upgrade head` and the full test suite against PostgreSQL/PostGIS; verify spatial indexes/query plans.
- [ ] Validate Redis-backed deployment behavior and decide/implement distributed rate limiting before horizontal scale.
- [ ] Build API/web/worker containers with Docker daemon running; execute migration-gated Compose smoke test.
- [ ] Configure private S3-compatible storage, blocked public access, encryption, signed access, access logs, and lifecycle rules.
- [ ] Complete encrypted PostgreSQL plus private-media backup and isolated restore rehearsal; record RPO/RTO evidence.
- [ ] Configure HTTPS, secure cookies, explicit CORS origins, secret manager, credential rotation, WAF/rate limits, and DNS.
- [ ] Configure redaction-tested error monitoring/metrics/alerts for readiness, worker failures, notification backlog, tracking expiry, and provider errors.

## Security and privacy — blocking

- [ ] Clean CI passes secret scan, npm critical gate, `pip-audit`, Ruff, migrations, backend tests, web build, Expo checks/export.
- [ ] Resolve or formally accept each remaining Expo/Metro transitive advisory with owner, impact, compensating control, and review date.
- [ ] Independent authorization/privacy review covers cross-user access, IDOR, CSRF, XSS, upload/evidence, webhooks, SSE, device tokens, tracking, finance, and admin roles.
- [ ] Penetration test and dependency/SBOM review complete; no unresolved critical/high issue accepted without sign-off.
- [ ] Privacy notice, consent records, retention schedule, account export/deletion procedure, dispute handling, and processor agreements are approved.
- [ ] Database/object-store encryption and access-control review complete; logs/monitoring contain no phone, email, exact location, tokens, evidence, or sensitive message bodies.
- [ ] Session expiry/rotation/logout behavior verified in two browsers and physical devices.

## Functional regression — blocking

- [ ] Customer: signup/login → GPS/manual location → eligible rescuer discovery → demo booking → updates/tracking → completion → demo receipt/review.
- [ ] Rescuer: onboarding → admin verification → availability → assigned request accept/reject → consented journey → arrival → completion/evidence → illustrative earnings.
- [ ] Admin: rescuer/organization review → incident/booking/tracking/notification monitoring → evidence/payment/ledger/review/dispute/privacy request workflows.
- [ ] Negative paths: no eligible rescuer, expired/suspended rescuer, rejection, expiry, cancellation, duplicate idempotency, offline/retry, tracking expiry, provider failure, payment simulation failure, cross-owner denial.
- [ ] No real provider message, payment, settlement, payout, or rescue dispatch occurs during any DEMO test.
- [ ] Staging load test meets agreed latency/error targets for login, locations, nearby search, bookings, notifications, tracking reads/writes, completion, and admin queues.

## Web and accessibility — blocking

- [ ] Production build and route smoke test pass on supported desktop/mobile browsers.
- [ ] Keyboard-only navigation, focus order, labels, error announcements, contrast, zoom/reflow, large touch targets, and reduced-motion behavior pass WCAG review.
- [ ] Map/tile/routing provider licensing, failure states, attribution, and no-false-ETA behavior are approved.
- [ ] Every primary action works; no placeholder or dead-end button remains.

## Mobile release — blocking

- [ ] Replace EAS placeholder API URL; configure EAS project, signing, app icons/splash, privacy manifests, store metadata, and support/privacy URLs.
- [ ] Signed Android APK/AAB and iOS archive build successfully.
- [ ] Physical Android/iOS tests cover foreground location deny/allow, manual fallback, gallery/camera denial, evidence upload, network loss/retry, session expiry, deep links, foreground/background notification behavior, and battery impact.
- [ ] Background tracking remains disabled unless a separately reviewed permission/disclosure implementation is approved.
- [ ] Store disclosures accurately say DEMO/not an emergency service and explain location/media usage.

## Go/no-go record

- [ ] Product owner sign-off
- [ ] Engineering sign-off
- [ ] Security/privacy sign-off
- [ ] Legal/wildlife authorization sign-off
- [ ] Operations/on-call sign-off
- [ ] Backup/restore evidence attached
- [ ] CI/build/test evidence attached
- [ ] Rollback owner and communication plan assigned

If any blocking item is unchecked, release only to a restricted synthetic-data DEMO environment.
