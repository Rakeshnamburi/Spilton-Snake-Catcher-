# SPILTON Snake Rescue — Day 3 Implementation Checklist

Completed: 14 October 2026

All marketplace behavior remains simulated. Authorized operation, live dispatch, live provider notifications, pricing collection, and payments stay server-disabled.

## 1. Preserve and verify the Day 1/2 baseline

- [x] Inspect the monorepo, reports, applications, API, models, migrations, authentication, RBAC, incident workflow, and existing tests.
- [x] Re-run the Day 1/2 regression suite after Day 3 changes.
- [x] Preserve incident privacy, private media, GPS/manual fallback, demo disclaimers, and snakebite guidance.

## 2. India location directory foundation

- [x] Add state/UT, district, subdistrict, village, urban-local-body, ward, and import-job models and migration.
- [x] Add an idempotent LGD CSV/XLSX import command with hierarchy validation, duplicate detection, source metadata, and transaction rollback.
- [x] Add paginated state, district, subdistrict, village, and search APIs.
- [x] Add web/mobile cascading selectors backed by the API with GPS/manual confirmation.
- [x] Do not claim full India coverage until an official LGD export is imported.

## 3. Rescuer onboarding and verification

- [x] Extend rescuer profiles with public/private onboarding fields, authorization dates, service coverage, languages, experience, and availability.
- [x] Add private authorization-document metadata and verification-history models.
- [x] Add citizen-to-rescuer application APIs that never self-grant a privileged role or VERIFIED status.
- [x] Add admin review/approve/reject/suspend actions with audit history and expiry checks.
- [x] Add public demo profile and eligible nearby-search APIs without exposing private coordinates or documents.

## 4. Availability and demo discovery

- [x] Add AVAILABLE/BUSY/OFFLINE controls, operating-hours data, last-seen handling, and availability history.
- [x] Filter discovery by verification, active organization, authorization expiry, service coverage, availability, and radius.
- [x] Use PostGIS distance/indexing when PostgreSQL is available and a safe distance calculation fallback in SQLite tests.

## 5. Demo booking workflow

- [x] Add bookings, booking events, booking status history, and financial snapshot tables.
- [x] Implement REQUESTED → PENDING_RESCUER_RESPONSE → ACCEPTED/REJECTED/EXPIRED plus eligible cancellation.
- [x] Add authenticated create/list/detail/accept/reject/cancel APIs with ownership, row locking, idempotency, and transition validation.
- [x] Force every booking to demo mode; keep real dispatch and payment gates disabled server-side.

## 6. Notifications and pricing foundation

- [x] Add notification templates, events, delivery attempts, and preferences.
- [x] Implement in-app notifications and sanitized local demo delivery logging.
- [x] Add configuration-only email/SMS/WhatsApp/FCM adapters without sending real messages.
- [x] Add Decimal-based 10% illustrative commission snapshots and keep pricing/payment authorization disabled.

## 7. Website

- [x] Implement `/rescuers`, `/rescuers/[id]`, `/book/[rescuerId]`, `/bookings`, and `/bookings/[id]`.
- [x] Implement `/rescuer/register`, `/rescuer/dashboard`, and `/rescuer/bookings`.
- [x] Implement `/admin/rescuers`, `/admin/bookings`, and `/admin/locations`.
- [x] Use live API data, accessible loading/error/empty states, and visible demo warnings.

## 8. Mobile

- [x] Implement nearby rescuers, rescuer profile, location selection, booking request/confirmation, bookings/detail, onboarding, dashboard, and incoming requests.
- [x] Reuse Secure Store authentication and handle expiry, denial, network errors, duplicates, and acceptance conflicts.

## 9. Verification and documentation

- [x] Add tests for import hierarchy, eligibility, ownership, booking races/transitions, notifications, Decimal calculations, and disabled operational gates.
- [x] Run backend formatting/lint/tests, Alembic upgrade checks, web lint/type/build, mobile typecheck, and Expo compatibility checks.
- [x] Update README and create `DAY3_REPORT.md` with actual results, LGD coverage truth, blockers, and Day 4 handoff.

