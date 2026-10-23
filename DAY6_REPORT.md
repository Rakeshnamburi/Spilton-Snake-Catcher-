# SPILTON Snake Rescue — Day 6 Report

Date: 19 October 2026  
Release posture: **integrated DEMO MVP; not approved for live rescue operations**

## Outcome

Day 6 connected and hardened the Day 1–5 customer, rescuer, administrator, notification, tracking, completion, evidence, demo-finance, and review modules without enabling real dispatch, real provider delivery, or real payments. The API, website, and Android Expo bundle compile; the backend regression snapshot and final focused security tests pass. Several external release gates remain for Day 7 and are explicitly listed below.

## Implemented

### Authentication, account, and privacy

- Added JWT `jti` and per-user token versions. Session refresh rotates the token version; logout revokes every earlier JWT for that account.
- Added password-confirmed name/email/phone profile updates.
- Added idempotent open export/deletion requests and owner-only request history.
- Added administrator request listing and audited `UNDER_REVIEW`, `COMPLETED`, and `REJECTED` transitions.
- Added web `/profile`, mobile profile editing/privacy actions, safe server logout, and web `/admin/account-requests`.
- Public registration remains `CITIZEN` only; existing RBAC and ownership gates remain enforced.

### Reliability and observability

- Added safe `X-Request-ID` correlation, JSON request completion logs with no query/body/contact/location data, security headers, and request IDs in structured errors.
- Kept `/health` as the stable liveness contract and added `/ready` with a database check.
- Added protected `/api/v1/admin/operations/health` with low-cardinality booking, tracking, and notification queue counts.
- Added a restart-safe scheduler process for notification retries, booking expiry, tracking retention, and evidence retention. Jobs remain idempotent and PostgreSQL remains the source of truth.
- Added fail-closed staging/production configuration checks: non-default JWT secret, secure cookies, and explicit HTTPS origins are required. Demo, authorized-operation, pricing, and real-payment gates cannot be enabled by environment values in this sprint.

### Location integrity

- Added `python -m app.db.audit_lgd`, a read-only hierarchy/source/count audit that never claims complete official coverage.
- The local audit reported zero official LGD records, zero orphans, and `complete_official_coverage_claimed=false`. No locations were fabricated.

### Localization and clients

- Retained centralized web/mobile catalogs for English, Telugu, Tamil, Kannada, and Malayalam with persisted preference and English fallback.
- Added translated primary authentication, profile/privacy, marketplace navigation, rescuer-search actions, and booking-list actions.
- Added development-only missing-translation diagnostics and `npm run check:locales`, which requires all five entries for the primary Day 6 key set.
- Critical non-English medical translations remain labelled as requiring human safety review; English remains authoritative.
- Some detailed admin, finance, and completion copy is still English and is a Day 7 content-review gate.

### CI and deployment preparation

- Added repository secret scanning, locale completeness, critical-level npm audit, Python `pip-audit`, Ruff format, Expo SDK compatibility, and Android export gates to CI.
- Added migration-gated Compose services for PostGIS, Redis, FastAPI, the recurring worker, private media, and Next.js.
- Added production-oriented API/web Dockerfiles, health dependencies, `.dockerignore`, and Expo EAS preview/production profiles.
- Added [deployment and restore guidance](docs/DEPLOYMENT.md) and [security/privacy baseline](docs/SECURITY_PRIVACY.md).

## Database migration

`0006_day6_release_readiness.py`:

- adds `users.token_version` with a non-null default;
- creates `account_data_requests` with user/processor foreign keys, request/status constraints, timestamps, and lookup indexes.

A fresh SQLite migration from `0001_initial` through `0006_day6_release_readiness` passed. PostgreSQL/PostGIS migration execution is still required on the Day 7 staging environment.

## New or changed API surface

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/refresh` | Rotate the short-lived session and revoke the previous JWT |
| `PATCH` | `/api/v1/auth/me` | Password-confirmed profile update |
| `GET/POST` | `/api/v1/auth/account-requests` | Owner-only privacy request history/create |
| `GET` | `/api/v1/admin/account-requests` | Administrator privacy queue |
| `PATCH` | `/api/v1/admin/account-requests/{id}` | Audited administrator status transition |
| `GET` | `/api/v1/admin/operations/health` | Privacy-reduced operations metrics |
| `GET` | `/ready` | Database readiness check |

Final generated OpenAPI: **100 paths**, with all required Day 6 paths present.

## Verification record

| Check | Actual result |
| --- | --- |
| Backend full regression snapshot | **49 passed** in 1800.86 seconds |
| Final Day 6 security/privacy/config/load file | **5 passed** in 148.84 seconds |
| Moderate authenticated read smoke | **40/40 HTTP 200** in 0.501 seconds using in-process ASGI; not a production capacity benchmark |
| Ruff format | **62 files formatted; pass** |
| Ruff lint | **pass** |
| Fresh migrations | **0001 → 0006 pass**, head confirmed |
| LGD integrity audit | **pass**, zero imported official records and zero orphans; completeness not claimed |
| Web ESLint | **pass** |
| Web/mobile TypeScript | **pass** |
| Next.js production build | **pass**, 34 routes |
| Locale quality gate | **pass** for five primary Day 6 locale sets |
| Secret scan | **pass**, no high-confidence tracked/unignored credentials found |
| Expo dependency compatibility | **dependencies up to date** |
| Android Expo export | **pass**, 1,591 modules and 3.7 MB Hermes bundle |
| Compose manifest | **valid** using `.env.example` |
| Docker image build | **not run**: Docker Desktop Linux daemon was not running |
| npm production audit | **no critical advisory gate failure**; 29 transitive advisories remain (19 high, 10 moderate) in Expo/Metro tooling. Suggested forced fix is breaking and was not applied. |
| Python vulnerability audit | **not available locally** (`pip_audit` not installed); added as a clean-CI gate |

The 49-test snapshot started before the last two focused Day 6 tests were added. The final five-test focused run executed all current Day 6 tests, so every current test case was exercised across the two recorded runs; a single final 51-test invocation was not repeated to avoid another 30-minute duplicate run.

## Security findings and fixes

- Fixed: logout previously cleared cookies without invalidating bearer tokens.
- Fixed: account contact updates and tracked privacy requests were missing.
- Fixed: no correlation identifier or privacy-safe access log envelope.
- Fixed: staging/production could start with an insecure cookie/default JWT configuration.
- Preserved: owner/RBAC checks, CSRF for cookie sessions, mobile SecureStore bearer storage, upload validation, private evidence, demo-only provider adapters, tracking consent/expiry, idempotency, Decimal accounting, balanced ledger tests, and public data minimization.
- Remaining: distributed Redis rate limiting, database/KMS field encryption, centralized redaction-tested monitoring, WAF policy, independent penetration test, formal privacy/legal review, and dependency remediation compatible with the active Expo SDK.

## Key modified areas

- Backend: `core/security.py`, `core/config.py`, `main.py`, account/admin routes and schemas, entities, migration `0006`, worker scheduler, LGD audit, Day 6 tests.
- Web: profile/privacy UI, admin privacy queue, five-language account/marketplace copy, translated booking actions, navigation.
- Mobile: profile/privacy controls, server logout, localized marketplace titles/actions, EAS build profiles.
- Platform: Compose migration/worker/web services, web Dockerfile, CI, locale/secret scripts, environment template, README and operational docs.

## Remaining blockers / Day 7 handoff

1. Import and validate a current official Government LGD dataset; the repository intentionally ships no fake complete directory.
2. Run migrations and integration tests against PostgreSQL/PostGIS and Redis, not only SQLite.
3. Start Docker Desktop and build/smoke the API, worker, and web images.
4. Resolve or formally risk-accept Expo/Metro transitive advisories without forced SDK downgrade.
5. Run `pip-audit` in clean CI and remediate any finding.
6. Human-review all critical Telugu/Tamil/Kannada/Malayalam medical text and review remaining English-only detailed workflow copy.
7. Configure only approved test credentials/recipients for email, SMS/DLT, WhatsApp templates/opt-in, FCM, routing, S3, and monitoring; then test delivery in a safe staging tenant.
8. Run signed Android/iOS builds and real-device permission, offline, deep-link, foreground notification, camera/gallery, and accessibility checks.
9. Run staging load tests, backup/restore rehearsal, security review/penetration test, and legal/operational authorization review.

Day 6 is complete as an integrated, tested **DEMO development MVP**. It is not cleared for live wildlife emergency operations, production provider messaging, or real money.
