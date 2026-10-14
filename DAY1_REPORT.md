# Day 1 Report

Date: 9 October 2026

## Completed

- npm workspace monorepo for Next.js, Expo, shared packages, and FastAPI.
- Responsive public website with home, report, track, safety, emergency, about, contact, login, and registration routes.
- Protected, API-driven administration overview with safe aggregate metrics, incident rows, empty states, and audit activity.
- Expo Router mobile application with splash, onboarding, home, report, tracking, safety, emergency, authentication, and profile screens.
- Explicit location permission with manual fallback on web and mobile.
- FastAPI versioned endpoints for status, citizen auth, profile, logout, incidents, emergency contacts, and admin overview.
- Argon2 passwords; JWT validation; HttpOnly web cookie; Expo Secure Store; citizen-only public registration; role and ownership checks.
- SQLAlchemy models and initial Alembic migration for all requested entities, constraints, indexes, and timestamps.
- PostgreSQL/PostGIS and Redis development services, API Dockerfile, environment template, fictional-only seed, and CI workflow.
- Tests for health, registration role safety, login/profile, authenticated demo incident creation, and admin authorization.

## Verification results

- `npm run lint:web` — passed with no errors or warnings.
- `npm run typecheck` — passed for both Expo mobile and Next.js web.
- `npm run build:web` — passed; all 13 routes/static pages generated successfully.
- `npx expo install --check` — passed using Expo's bundled offline compatibility map; the command warned that offline validation is less reliable than the remote version endpoint.
- Expo startup — passed in offline CI mode; Metro started and waited successfully on `http://localhost:8081`.
- `ruff format .` and `ruff check .` — passed for the API and migration source.
- `pytest` — 5 passed, covering health, registration privilege safety, login/profile, authenticated demo incident creation, and administrator role protection.
- `alembic upgrade head` plus `alembic current` — passed on the local SQLite fallback at `0001_initial (head)`.
- FastAPI runtime health check — Uvicorn started and `GET /health` returned HTTP 200 with `{"status":"ok"}`.
- Docker Compose services were not started because the local Docker engine was not running; PostgreSQL runtime integration therefore remains unverified locally.
- `npm audit --omit=dev` — failed with 57 transitive advisories (20 moderate, 36 high, 1 critical), concentrated in the Expo/React Native build toolchain plus PostCSS. The available automated fixes require breaking upgrades to Expo 57, React Native 0.86, Next 16, and Tailwind 4, so they were not forced during final verification.

## Known Day 1 limitations

- The service is demo-only and does not dispatch or claim rescuer availability.
- The public wildlife contact directory is intentionally empty until administrators add independently verified, source-backed records.
- Photo upload is disabled pending private-object storage policy, scanning, and retention implementation.
- Redis, S3, Firebase, PostGIS proximity queries, MapLibre rendering, localization, password reset, refresh-token rotation, CSRF tokens, and email/phone verification remain integration foundations.
- Rate limiting is in-process and must move to Redis before horizontal scaling.
- The contact page is non-sending until an approved communications channel exists.
- Admin filters are a basic Day 1 table foundation; expanded server-side filtering is planned.
- The npm audit findings above are a release blocker. Upgrade and revalidate the mobile/web major-version stack before any production release.

## Day 2 handoff

1. Add refresh-token rotation, revocation, CSRF defense-in-depth, password reset, and verified email/phone flows.
2. Add administrator workflows for role grants, organization/rescuer verification, and verified emergency-contact CRUD with audit records.
3. Implement private media upload using signed URLs, validation, malware scanning, access logging, and retention/deletion.
4. Add Redis-backed rate limiting and sessions, FCM device registration, and notification preferences.
5. Add English/Telugu/Tamil/Kannada/Malayalam localization and accessibility testing.
6. Add MapLibre with explicit privacy controls and optional PostGIS proximity search.
7. Add Playwright/browser accessibility tests, mobile component tests, and PostgreSQL integration tests.
8. Conduct a legal, operational, privacy, and security readiness review before any live dispatch work.
