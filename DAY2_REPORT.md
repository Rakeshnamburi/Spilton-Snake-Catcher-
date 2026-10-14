# Day 2 Implementation Report

Date: 12 October 2026  
Sprint: SPILTON Snake Rescue, Day 2 of 7  
Status: **Day 2 implementation and local verification are complete within the explicitly documented infrastructure limitations. Production or emergency use is not authorized.**

## Safety posture

The platform remains fully in **DEMO MODE**.

- No real rescuer is dispatched, assigned, notified, or represented as available.
- No live emergency notification is sent.
- Snakebite/injury screens prioritize immediate medical care and India's emergency number **112**; report submission is explicitly not a substitute for medical care.
- Photos are optional, and every upload flow warns users never to approach a snake for a picture.
- No snake-species or venom-risk classification is present.
- The wildlife contact directory contains no invented numbers; the demo seed adds none.

## Implemented features

### Website

- Replaced the single-page report form with a responsive six-step flow: incident, safety triage, location, optional media, reporter, and review/submit.
- Added browser geolocation only after a user action, with loading, success, denial, timeout, unavailable, and retry states.
- Added manual coordinates and locality entry, five-state/district configuration, coordinate/state bounds validation, and location review confirmation.
- Added a MapLibre map with pan/zoom, a draggable marker, configurable style URL, accuracy text, and a manual-entry fallback if tiles fail.
- Added image preview/removal and client-side JPEG/PNG/WebP, signature, 5 MB, and three-image checks before the server performs authoritative validation.
- Added authenticated `/my-reports`, `/reports/[id]`, owner-only reference tracking, status timeline, private-media links, and eligible cancellation.
- Expanded `/admin` with API-backed counts, a privacy-reduced paginated incident queue, search/state/district/status filters, and validated demo status controls.
- Added centralized English/Telugu/Tamil/Kannada/Malayalam navigation, reporting, status, error, and safety-message foundations with English fallback and human-review notices for non-English critical guidance.
- Browser QA found and fixed an internal enum validation message and an accidental submission edge case when moving from reporter details to review. The wizard now requires an explicit final submit action.

### Mobile

- Implemented Expo Router screens for all six report stages plus submission confirmation.
- Added foreground-only Expo Location permission, coordinate capture, accuracy display, refresh, denial/timeout/network recovery, and manual locality/coordinate fallback.
- Added Expo Image Picker selection for up to three optional JPEG/PNG/WebP images of 5 MB each, removal, sequential upload, partial-failure messaging, retry, and continue-without-photos behavior.
- Added authenticated My Reports, Incident Details, Status Timeline, and eligible cancellation flows.
- Added network timeouts, structured API errors, session-expiry handling, empty states, idempotent submission, and token storage in Expo Secure Store.
- Kept native map integration out of this Expo build because it would add native configuration risk; the mobile location flow remains functional through GPS coordinates and manual entry.

### Backend and database

- Extended incidents with reporter email, landmark, address description, sighting time, injury, visibility, immediate-danger, and idempotency hashes.
- Added the `incident_media` table, indexes, foreign keys, file-size constraint, coordinate constraints, and owner/idempotency uniqueness.
- Migrated the workflow to `CREATED`, `UNDER_REVIEW`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`, `CANCELLED`, and `UNABLE_TO_ASSIST`.
- Added validated transitions, citizen cancellation restrictions, timeline events, and audit records.
- Added owner-scoped, paginated incident listing and protected incident detail/timeline/media operations.
- Added coordinator/admin incident filtering and demo-only status updates. The server independently escalates injury reports to `SNAKEBITE` and immediate-danger reports to `HIGH` urgency.
- Added optional `Idempotency-Key` support with hashed keys/payloads, safe replay, and conflict detection.
- Added structured API errors, request validation, media request-size protection, CSRF protection for cookie sessions, and in-process limits for authentication, creation, and uploads.
- Added private local and S3-compatible media adapters. Images are signature-checked, decoded, restricted to one frame and safe dimensions, re-encoded without EXIF/ancillary metadata, assigned random keys, and retrieved only after authorization.
- Corrected the fictional seed accounts to use reserved, non-deliverable `.example` addresses that pass API email validation, and added a seeded incident-created timeline event.

## Database migration

`services/api/alembic/versions/0002_day2_incident_tracking.py`

The migration:

- adds the Day 2 incident and idempotency fields;
- backfills `sighting_at` from `created_at`;
- maps legacy `RECEIVED` to `CREATED` and `REVIEWING` to `UNDER_REVIEW`;
- expands the incident status enum;
- adds coordinate and owner/idempotency constraints; and
- creates `incident_media` with its incident index and cascading foreign key.

PostgreSQL and SQLite migration branches are both defined. SQLite is a development/test convenience, not the production database target.

## API endpoints

New or expanded Day 2 endpoints:

- `POST /api/v1/incidents`
- `GET /api/v1/incidents/mine`
- `GET /api/v1/incidents/{incident_id}`
- `GET /api/v1/incidents/{incident_id}/events`
- `GET /api/v1/incidents/{incident_id}/media`
- `POST /api/v1/incidents/{incident_id}/media`
- `GET /api/v1/incidents/{incident_id}/media/{media_id}`
- `POST /api/v1/incidents/{incident_id}/cancel`
- `GET /api/v1/admin/incidents`
- `PATCH /api/v1/admin/incidents/{incident_id}/status`

Day 1 system, authentication, emergency-contact, and admin-overview routes remain available. OpenAPI remains generated at `/docs`.

## Principal files added or modified

### Root and shared configuration

- `.env.example`
- `.gitignore`
- `docker-compose.yml`
- `package.json`
- `package-lock.json`
- `packages/shared-types/index.ts`
- `README.md`
- `DAY2_REPORT.md`

### API

- `services/api/app/main.py`
- `services/api/app/api/routes.py`
- `services/api/app/core/config.py`
- `services/api/app/models/entities.py`
- `services/api/app/schemas/api.py`
- `services/api/app/services/incident_workflow.py`
- `services/api/app/services/media_storage.py`
- `services/api/app/services/request_limits.py`
- `services/api/alembic/versions/0002_day2_incident_tracking.py`
- `services/api/requirements.txt`
- `services/api/tests/conftest.py`
- `services/api/tests/test_api.py`
- `services/api/tests/test_day2_incidents.py`

### Web

- `apps/web/app/my-reports/page.tsx`
- `apps/web/app/reports/[id]/page.tsx`
- `apps/web/app/report/page.tsx`
- `apps/web/app/track/page.tsx`
- `apps/web/app/admin/page.tsx`
- `apps/web/components/incident-status.tsx`
- `apps/web/components/location-map.tsx`
- `apps/web/components/site-shell.tsx`
- `apps/web/features/incidents/report-form.tsx`
- `apps/web/features/incidents/my-reports.tsx`
- `apps/web/features/incidents/report-detail.tsx`
- `apps/web/features/incidents/track-form.tsx`
- `apps/web/features/admin/dashboard.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/i18n.tsx`
- `apps/web/lib/incidents.ts`
- `apps/web/lib/regions.ts`
- `apps/web/package.json`
- `apps/web/eslint.config.mjs`

### Mobile

- `apps/mobile/app/report.tsx`
- `apps/mobile/app/report-triage.tsx`
- `apps/mobile/app/report-location.tsx`
- `apps/mobile/app/report-media.tsx`
- `apps/mobile/app/report-reporter.tsx`
- `apps/mobile/app/report-review.tsx`
- `apps/mobile/app/report-confirmation.tsx`
- `apps/mobile/app/my-reports.tsx`
- `apps/mobile/app/incidents/[id]/index.tsx`
- `apps/mobile/app/incidents/[id]/timeline.tsx`
- `apps/mobile/features/report/*`
- `apps/mobile/features/incidents/*`
- `apps/mobile/services/api.ts`
- `apps/mobile/services/errors.ts`
- `apps/mobile/services/i18n.tsx`
- `apps/mobile/services/regions.ts`
- `apps/mobile/package.json`
- `apps/mobile/app.json`
- `apps/mobile/tsconfig.json`

## Automated test coverage added

The API suite now covers:

1. authenticated manual-location incident creation and snakebite escalation;
2. server-side immediate-danger escalation;
3. whitespace/control and coordinate-pair/bounds validation;
4. owner access and cross-user denial;
5. idempotent replay without duplicate records;
6. paginated/status-filtered report listing;
7. eligible citizen cancellation and its timeline event;
8. valid/invalid workflow transitions and administrator updates;
9. protected, filtered, privacy-reduced admin listing;
10. valid private image storage, EXIF removal, and authorized retrieval;
11. unauthenticated and non-owner media denial;
12. unsupported, oversized, corrupt, and content-type-mismatched image rejection;
13. the three-image incident limit; and
14. double-submit CSRF protection for cookie sessions.

The original authentication, role-safety, profile, health, and private incident tests remain.

## Verification record

### Results observed during implementation

- Web ESLint: passed after the Next.js 16 flat-config migration.
- Web TypeScript: passed.
- Mobile TypeScript: passed.
- Web production build: passed with Webpack; all 13 application routes compiled. Turbopack was replaced for this build because its PostCSS worker crashed on this Windows host.
- Expo dependency compatibility: `npx expo install --check` passed.
- Expo startup: Metro started on `http://localhost:8081`, and its status endpoint returned HTTP 200.
- API formatting and lint: `ruff format --check .` and `ruff check .` passed.
- Backend regression suite: **28 passed in 146.09 seconds** in the final run. An earlier restricted-sandbox attempt stalled on Windows temp/Argon2 operations; the documented workspace-local pytest base directory and normal host permissions completed cleanly.
- Dependency audit after framework upgrades: 28 npm advisories remained (10 moderate, 18 high, 0 critical). They are concentrated in Expo/Metro/React Native transitive dependencies; the suggested automatic remediations require incompatible downgrades or another major-version change.
- PostgreSQL/PostGIS and Redis containers could not be started because the local Docker engine was unavailable. No PostgreSQL runtime result is claimed.

### Final verification

| Check | Command | Final result |
| --- | --- | --- |
| Web lint | `npm run lint:web` | **PASS** |
| Web + mobile types | `npm run typecheck` and workspace-specific checks | **PASS** |
| Web production build | `npm run build:web` | **PASS** — 13 routes generated with Next.js 16.4/Webpack |
| Expo dependency check | `npx expo install --check` | **PASS** — dependencies are up to date |
| API formatting | `ruff format --check .` | **PASS** — 28 files already formatted |
| API lint | `ruff check .` | **PASS** |
| API tests | `python -m pytest -q --basetemp=.pytest-tmp/final-after-browser` | **PASS** — 28 passed in 146.09s |
| Day 2 migration | isolated SQLite `alembic upgrade head` and `alembic current` | **PASS** — `0002_day2_incident_tracking (head)` |
| API runtime smoke | `GET /health`, `/api/v1/status`, `/openapi.json` | **PASS** — healthy, DEMO, dispatch false, 17 OpenAPI paths |
| Browser visual/interaction QA | Home, report wizard, triage, manual location, media, tracking, owner list/detail, emergency, and admin protection | **PASS** — fictional login/report data only |
| PostgreSQL/PostGIS integration | Docker Compose services + migration | **BLOCKED: local Docker engine unavailable** |

## Acceptance status

| Day 2 criterion | Status |
| --- | --- |
| Website report flow | Implemented and browser-verified through explicit review and demo submission |
| Mobile report flow | Implemented; TypeScript and Expo startup pass, physical-device QA pending |
| User-triggered GPS and manual fallback | Implemented on web and mobile |
| Web interactive map | Implemented; production tile provider not configured |
| Mobile native map | Not implemented; functional coordinate/manual alternative provided |
| Optional private image upload | Implemented; server validation, privacy, and authorization tests pass |
| PostgreSQL persistence | Model/migration implemented; local PostgreSQL runtime unverified |
| Owner-only tracking/detail/timeline | Implemented |
| Admin list/filter/pagination/status changes | Implemented |
| Status events and audit writes | Implemented |
| Demo-mode enforcement/no live dispatch | Implemented |
| Full security and release readiness | Not complete; see limitations |

## Known limitations and remaining risks

- This is not an operational emergency or wildlife rescue service.
- Docker Desktop's engine was unavailable on the verification host, so PostgreSQL/PostGIS and Redis integration could not be exercised. SQLite-only success must not be treated as proof of PostgreSQL readiness.
- Mobile uses coordinates and manual entry but has no native map. Physical Android and iOS device testing remains outstanding.
- The web map defaults to MapLibre demo tiles. A licensed, monitored production tile provider and privacy review are required.
- Guest reporting/tracking is not implemented. All incident creation and tracking require an authenticated citizen account.
- The administrator UI has a protected privacy-reduced queue and status controls, but no dedicated incident-detail drawer or per-incident audit-history panel yet.
- Local and S3-compatible private storage are implemented, but malware scanning, retention/deletion automation, quotas, backups, and production lifecycle policy are not.
- Rate limiting is process-local; Redis-backed distributed limits are still required.
- Access tokens are short-lived, but refresh rotation, server-side bearer revocation, password reset, and verified email/phone flows remain.
- Firebase Cloud Messaging is configuration-only. No notification is sent.
- Non-English translations have not been reviewed by qualified human translators. English safety/medical guidance remains the authoritative fallback.
- The verified wildlife directory remains empty until real, source-backed contacts are approved. No invented numbers may be added.
- The remaining npm audit advisories are a release blocker until the Expo/Metro/React Native dependency chain provides compatible fixes or the stack is safely upgraded and revalidated.
- No automated browser end-to-end or React Native component test suite exists yet.
- No screenshots were captured in this implementation report at the time of writing.

## Day 3 readiness and handoff

1. Re-run the schema and API tests against PostgreSQL/PostGIS once Docker is available; add that integration to CI.
2. Add automated browser end-to-end tests for GPS denial/manual entry, bite triage, explicit review, idempotent submission, owner isolation, uploads, cancellation, and admin transitions.
3. Add React Native component/integration tests and run the application on physical Android and iOS devices.
4. Add an administrator incident-detail/audit view and verified emergency-contact management workflow.
5. Implement Redis-backed rate limits/session revocation and token refresh rotation.
6. Add media malware scanning, retention/deletion, production S3 lifecycle controls, and access logging.
7. Arrange human review for Telugu, Tamil, Kannada, and Malayalam critical safety text.
8. Replace demo map tiles, complete privacy/accessibility reviews, and obtain legal/operational authorization before any live-response capability is considered.
