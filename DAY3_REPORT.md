# Day 3 Implementation Report

Date: 14 October 2026  
Sprint: SPILTON Snake Rescue, Day 3 of 7  
Status: **Day 3 marketplace foundations are implemented in DEMO MODE. This build is not authorized for emergency operation, live rescue dispatch, real rescuer availability, or payment collection.**

## Safety and operational posture

- `DEMO_MODE=true` remains the only supported Day 3 marketplace mode.
- `AUTHORIZED_OPERATION_ENABLED`, `PRICING_AUTHORIZED`, and `PAYMENTS_ENABLED` are fail-closed server settings and remain `false`. They cannot be enabled by an ordinary admin-dashboard toggle.
- All discoverable profiles and bookings are explicitly labelled simulated. No real dispatch message or external notification is sent.
- Injury/snakebite booking guidance tells the user to call **112** and seek immediate medical care without waiting for the form.
- Photo/evidence flows never tell a customer to approach a snake. Snake classification is not present.
- No helpline, rescuer authorization, rating, completed-rescue count, or official location row was invented.

## Implemented features

### Official location-directory foundation

- Added normalized `states`, `districts`, `subdistricts`, `villages`, `urban_local_bodies`, `wards`, and `location_import_jobs` tables with official-code uniqueness, parent foreign keys, active status, alternate/local names, source version, and import timestamps.
- Added a transactional CSV/XLSX importer for administrator-provided official LGD exports. It validates headers/codes/parents, detects conflicting duplicates, performs idempotent upserts, hashes the source, records counts and sanitized failures, and rolls back directory changes on error.
- Added paginated hierarchy and bounded search APIs plus API-backed cascading selectors on web and mobile.
- GPS remains a coordinate observation, never proof of an exact village. Users must confirm/correct the hierarchy or enter a manual address.
- Added [docs/LGD_IMPORT.md](docs/LGD_IMPORT.md) with the official source, import order, update process, and recovery rules.

**Coverage truth:** no official LGD export was imported on this development host because the government download flow requires a current administrator-selected report/CAPTCHA. Automated tests use clearly synthetic, official-shaped rows only. The application therefore shows an import-required empty state until official files are supplied; complete India coverage is not claimed.

### Rescuer onboarding, verification, profiles, and availability

- Expanded rescuer profiles with public display name, private photo key, directory codes, organization, experience, languages, training, authorization authority/reference/dates, service-area description/radius, private coordinates, operating hours, availability, last seen, public aggregate fields, and demo flag.
- Added private authorization-document metadata, verification history, and availability history.
- Public onboarding always starts at `PENDING_VERIFICATION`; it never changes the account role or self-grants verification.
- Admin verification requires an approved organization and stored private evidence before `VERIFIED`; approval changes the user to `RESCUER`. Reject, suspend, review, and expiry states are supported and audited.
- Expired/suspended/unverified profiles are excluded from public discovery and booking.
- Public profile responses omit authorization documents, personal address, phone/email, and exact coordinates. Fictional profile metrics are labelled demo data and default to zero rather than fabricated history.
- Verified rescuers can select `AVAILABLE`, `BUSY`, or `OFFLINE`; updates record history and last seen, and stale availability is forced offline during eligibility checks.

### Nearby discovery

- Discovery requires verification, active approved organization, unexpired authorization, enabled demo profile, matching state/district coverage, current availability, and distance within both requested and configured service radii.
- PostgreSQL uses a PostGIS `ST_DWithin`/distance branch and migration-created GiST expression index. SQLite tests use the same eligibility rules with a Haversine fallback.
- Search validates coordinates, bounds radius/pagination, supports experience/language/availability filters, and returns approximate distance without exposing rescuer coordinates.
- Web offers list and privacy-safe customer-location map views. Mobile offers GPS/manual-coordinate discovery without adding an incompatible native map dependency.

### Demo booking marketplace

- Added bookings, booking events, status history, and financial snapshots.
- Implemented and validated `REQUESTED → PENDING_RESCUER_RESPONSE → ACCEPTED | REJECTED | EXPIRED`, plus eligible customer cancellation.
- Booking creation requires authentication, an eligible assigned profile, a valid imported location hierarchy, an `Idempotency-Key`, and explicit demo/safety acknowledgement.
- Database row locks and guarded transitions prevent duplicate/conflicting acceptance. Only the assigned verified rescuer can accept/reject; only the customer/assigned rescuer/privileged staff can retrieve the record.
- Customer location/address is hidden from public APIs. Assigned rescuers receive only rounded coordinates and no manual address/landmark in Day 3.
- Acceptance/rejection/cancellation records status history, booking events, audit logs, and an in-app demo notification.

### Notifications and financial foundation

- Added notification templates, events, delivery attempts, and preferences.
- Working in-app notification creation and read-state APIs are implemented. The local adapter logs only sanitized IDs/event types.
- Email, SMS, WhatsApp Business, and FCM adapters are configuration-ready and fail closed without provider configuration. They are not used for rescue dispatch in demo mode.
- Financial calculations use `Decimal`. Every Day 3 booking stores a ₹0.00 snapshot with the configured illustrative 10% commission percentage; real pricing and payment remain disabled.

### Website

Implemented functional routes backed by the API:

- `/rescuers` and `/rescuers/[id]`
- `/book/[rescuerId]`, `/bookings`, and `/bookings/[id]`
- `/rescuer/register`, `/rescuer/dashboard`, and `/rescuer/bookings`
- `/admin/rescuers`, `/admin/bookings`, and `/admin/locations`
- `/admin/incidents` as a direct route to the existing Day 2 incident administration view

The booking flow includes directory/GPS/manual location, safety triage, final review, single-submit idempotency, session errors, and visible no-dispatch/no-payment warnings. Admin marketplace screens use real API responses rather than hardcoded metrics.

### Mobile

Implemented Expo Router screens for:

- location selection and nearby demo rescuers;
- rescuer profile and booking request/review/confirmation;
- customer booking list and detail/status history;
- rescuer onboarding and dashboard;
- incoming assigned demo bookings with conflict refresh and accept/reject.

The mobile flow reuses Expo Secure Store authentication, foreground-only Expo Location, manual fallback, shared contracts, structured API errors, duplicate protection, and expiry/network handling. Authorization evidence upload is currently completed through the private web onboarding flow; the mobile application screen does not yet select/upload the evidence file.

## Database migration

`services/api/alembic/versions/0003_day3_marketplace.py`

The migration extends rescuer profiles and creates all Day 3 location, verification, availability, booking, notification, pricing, commission, and financial-snapshot tables with indexes, checks, foreign keys, and uniqueness constraints. PostgreSQL receives the new enum values and a PostGIS GiST expression index for rescuer coordinates. SQLite remains a development/test fallback.

The isolated SQLite round trip completed successfully:

```text
upgrade base → 0001 → 0002 → 0003
downgrade 0003 → 0002 → 0001 → base
upgrade base → 0001 → 0002 → 0003
current: 0003_day3_marketplace (head)
```

PostgreSQL/PostGIS runtime execution remains unverified because Docker/PostgreSQL is unavailable on this host.

## New API endpoints

### Locations

- `GET /api/v1/locations/states`
- `GET /api/v1/locations/districts?state_code=`
- `GET /api/v1/locations/subdistricts?district_code=`
- `GET /api/v1/locations/villages?subdistrict_code=`
- `GET /api/v1/locations/search?q=`

### Rescuers

- `POST /api/v1/rescuers/onboarding`
- `GET /api/v1/rescuers/me`
- `PATCH /api/v1/rescuers/me/availability`
- `POST /api/v1/rescuers/onboarding/documents`
- `GET /api/v1/rescuers/me/documents/{document_id}`
- `GET /api/v1/rescuers/nearby`
- `GET /api/v1/rescuers/{rescuer_id}`

### Bookings and notifications

- `POST /api/v1/bookings`
- `GET /api/v1/bookings/mine`
- `GET /api/v1/bookings/assigned`
- `GET /api/v1/bookings/{booking_id}`
- `POST /api/v1/bookings/{booking_id}/accept`
- `POST /api/v1/bookings/{booking_id}/reject`
- `POST /api/v1/bookings/{booking_id}/cancel`
- `GET /api/v1/notifications/mine`
- `POST /api/v1/notifications/{notification_id}/read`

### Administration

- `GET /api/v1/admin/rescuers`
- `PATCH /api/v1/admin/organizations/{organization_id}/verification`
- `PATCH /api/v1/admin/rescuers/{profile_id}/verification`
- `GET /api/v1/admin/rescuers/{profile_id}/documents`
- `GET /api/v1/admin/rescuers/{profile_id}/documents/{document_id}`
- `GET /api/v1/admin/bookings`
- `GET /api/v1/admin/locations`
- `GET /api/v1/admin/marketplace/overview`

OpenAPI remains generated at `/docs` and `/openapi.json`.

## Principal files added or modified

### Backend and database

- `services/api/app/models/entities.py`
- `services/api/app/schemas/marketplace.py`
- `services/api/app/api/locations.py`
- `services/api/app/api/rescuers.py`
- `services/api/app/api/bookings.py`
- `services/api/app/api/marketplace_helpers.py`
- `services/api/app/api/admin_marketplace.py`
- `services/api/app/api/notifications.py`
- `services/api/app/services/lgd_import.py`
- `services/api/app/services/marketplace.py`
- `services/api/app/services/notifications.py`
- `services/api/app/db/import_lgd.py`
- `services/api/alembic/versions/0003_day3_marketplace.py`
- `services/api/tests/test_day3_marketplace.py`

### Web and shared contracts

- `packages/shared-types/index.ts`
- `apps/web/features/marketplace/*`
- `apps/web/features/admin/marketplace.tsx`
- `apps/web/app/rescuers/*`
- `apps/web/app/book/*`
- `apps/web/app/bookings/*`
- `apps/web/app/rescuer/*`
- `apps/web/app/admin/{rescuers,bookings,locations,incidents}/*`
- `apps/web/components/site-shell.tsx`
- `apps/web/lib/marketplace.ts`
- `apps/web/next.config.ts`

### Mobile, configuration, and documentation

- `apps/mobile/features/marketplace/*`
- `apps/mobile/components/location-directory.tsx`
- `apps/mobile/app/marketplace-location.tsx`
- `apps/mobile/app/nearby-rescuers.tsx`
- `apps/mobile/app/rescuers/[id].tsx`
- `apps/mobile/app/book/[rescuerId].tsx`
- `apps/mobile/app/booking-confirmation.tsx`
- `apps/mobile/app/bookings*`
- `apps/mobile/app/rescuer-{register,dashboard,bookings}.tsx`
- `.env.example`, `package.json`, `package-lock.json`
- `README.md`, `DAY3_CHECKLIST.md`, `docs/LGD_IMPORT.md`, `DAY3_REPORT.md`

## Automated coverage

Day 3 tests cover:

1. official-shaped CSV hierarchy import and idempotent replay;
2. invalid/missing parent rejection and transactional recovery;
3. location hierarchy APIs;
4. no self-verification and evidence-required admin approval;
5. unverified and expired rescuer exclusion;
6. eligible authorized simulated rescuer discovery;
7. manual-location demo booking creation;
8. idempotent replay and conflicting-key protection;
9. assigned-rescuer acceptance and other-rescuer denial;
10. rejection, cancellation, and invalid transition denial;
11. privacy-reduced rescuer views;
12. booking status/event persistence and in-app notifications;
13. Decimal commission calculations; and
14. disabled real operation, external delivery, pricing, and payments.

The complete suite also retains Day 1 authentication/RBAC and Day 2 incident/media/privacy coverage.

## Verification record

| Check | Command | Result |
| --- | --- | --- |
| Web TypeScript | `npm run typecheck --workspace @spilton/web` | **PASS** |
| Mobile TypeScript | `npm run typecheck --workspace @spilton/mobile` | **PASS** after regenerating Expo typed-route metadata |
| Web lint | `npm run lint --workspace @spilton/web` | **PASS** |
| Web production build | `npm run build --workspace @spilton/web` | **PASS** — Next.js 16.4/Webpack generated all 24 application routes |
| Expo dependency compatibility | `npx expo install --check` | **PASS against the installed SDK 57 local dependency map**; network version lookup was unavailable, so the tool warned that offline validation is less authoritative |
| API format/lint | `ruff format --check app tests` and `ruff check app tests` | **PASS** — 38 files formatted; lint clean |
| API regression | `DATABASE_URL=sqlite:// python -m pytest -q --basetemp=.pytest-tmp-day3-final-memory` | **PASS — 36 passed in 9.03s** |
| Migration round trip | isolated SQLite upgrade/downgrade/upgrade/current | **PASS** — `0003_day3_marketplace (head)` |
| Local runtime smoke | API health/status/OpenAPI plus `/`, `/rescuers`, `/rescuer/register`, `/admin/locations` | **PASS** — every request returned HTTP 200; OpenAPI contains 46 paths; status reports DEMO with dispatch/payments/external notifications false |
| PostgreSQL/PostGIS migration/runtime | Docker Compose | **NOT RUN** — database service unavailable on this host |

On this Windows host, the restricted process sandbox blocks Python asyncio while creating its local self-pipe socket and blocks child Webpack writes to generated `.next` folders. The same test/build commands were rerun with normal host process permissions. The source remained inside the workspace. These were environment restrictions, not ignored failures.

## Acceptance status

| Day 3 criterion | Status |
| --- | --- |
| Day 1/2 behavior preserved | **PASS** in the 36-test combined regression |
| Hierarchical location directory/import | Implemented; no official dataset imported on this host |
| GPS/manual confirmation | Implemented on web/mobile; GPS is not treated as verified address |
| Rescuer onboarding/verification | Implemented; mobile evidence upload remains web-assisted |
| Eligible nearby discovery | Implemented; PostgreSQL/PostGIS branch not runtime-tested here |
| Public simulated profiles | Implemented with privacy and demo labels |
| Customer demo booking | Implemented with idempotency and disabled payments |
| Assigned rescuer accept/reject | Implemented with ownership and transition controls |
| Customer status/history | Implemented |
| In-app demo notifications | Implemented |
| Admin rescuer/booking/location views | Implemented with API data |
| Financial snapshot | Implemented using Decimal; collection disabled |
| Real dispatch/payment | Server-disabled |

## Known limitations and blockers

- This is not an active emergency or wildlife rescue service.
- No official LGD file was supplied/imported, so directory completeness cannot be demonstrated and customer booking waits for an official hierarchy import.
- Docker/PostgreSQL/PostGIS/Redis were unavailable. PostgreSQL-specific enum and spatial-index paths require integration verification.
- Mobile uses GPS/manual coordinates without a native map and defers private evidence file selection/upload to the web flow.
- No real provider credentials are configured or exercised. Email/SMS/WhatsApp/FCM delivery is not complete.
- Real pricing, payment collection, transfers, and dispatch are intentionally absent.
- Rate limits and stale-session handling are process-local; Redis-backed distributed enforcement is still required.
- Consent-based live tracking, ETA, tracking expiry, and journey-state processing are only represented by reserved future booking states/contracts.
- Full official authorization policy, state-specific permissions, partner approval, document malware scanning, retention rules, and legal review are outstanding.
- Non-English critical medical text still requires qualified human review.
- Physical Android/iOS testing and automated browser/component end-to-end suites remain outstanding.
- No screenshots were captured. The production build and representative local routes were HTTP-smoke-tested, and the local preview was opened in the app for manual inspection.

## Day 4 readiness

1. Run migrations and geospatial discovery tests against PostgreSQL/PostGIS and connect Redis-backed rate limits/session freshness.
2. Import administrator-verified official LGD exports and validate real hierarchy counts without publishing a completeness claim until reviewed.
3. Add consent records and short-lived tracking-session contracts, journey start/stop, location minimization, ETA abstraction, and automatic shutdown.
4. Connect notification outbox processing while preserving demo-only local delivery; test real providers only in an approved non-dispatch sandbox.
5. Add mobile evidence upload and evaluate an Expo-SDK-compatible native map through device builds.
6. Add browser/mobile integration tests, concurrency tests against PostgreSQL, and physical accessibility/device QA.
7. Complete legal, partner, authorization, privacy, retention, and security reviews before any consideration of authorized operation.
