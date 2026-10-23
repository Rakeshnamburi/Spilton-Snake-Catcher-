# SPILTON Snake Rescue

**Saving Lives. Protecting Wildlife.**

SPILTON is a shared web, Android/iOS, and API platform for reporting snake sightings and preparing legally controlled wildlife-assistance coordination. The repository currently represents the Day 6 integrated DEMO MVP.

> **Demo Platform — Not an Active Emergency Rescue Service.** No workflow in this repository dispatches a real rescuer, promises availability, or sends a live emergency notification. For a suspected snakebite or other medical emergency in India, call **112** and seek immediate medical care. Never approach, touch, trap, provoke, catch, or relocate a snake, including to take a photograph.

## What works through Day 6

- A responsive Next.js website with a six-step, validated report flow; user-requested browser GPS; manual location fallback; a draggable MapLibre marker; optional private photos; review; submission; and clear snakebite triage.
- Authenticated report tracking through `/track`, `/my-reports`, and `/reports/[id]`. A reference code alone never grants access.
- An Expo Router mobile application with the same six reporting stages, foreground-only location permission, manual fallback, optional photo selection/upload, confirmation, report history, incident details, timeline, and eligible cancellation.
- A FastAPI v1 API with citizen authentication, incident ownership checks, pagination and filters, idempotent incident creation, private media access, cancellation, audit events, and coordinator/administrator status controls.
- SQLAlchemy models and Alembic migrations targeting PostgreSQL/PostGIS, with SQLite retained only as a convenient local/test fallback.
- English, Telugu, Tamil, Kannada, and Malayalam UI foundations. English is the fallback, and non-English critical safety translations are explicitly marked for human review.
- An import-only India location directory for official LGD CSV/XLSX exports, with hierarchy validation, idempotent upserts, source hashes/versions, rollback, import history, paginated APIs, and cascading web/mobile selectors.
- Citizen rescuer applications, private authorization evidence, admin-controlled organization/profile verification, expiry checks, public-safe simulated profiles, and availability history.
- Eligible nearby demo-rescuer discovery that checks verification, approved organization, authorization expiry, service area, availability, and distance without publishing a rescuer's exact coordinates.
- Idempotent simulated bookings with ownership controls, row locks, status history, rescuer accept/reject, customer cancellation, expiry, in-app notification events, and sanitized local delivery logs.
- Decimal-based illustrative 10% commission snapshots. Pricing authorization, real payment processing, authorized operation, external notifications, and live dispatch are all server-disabled.
- Idempotent customer and assigned-rescuer notifications, persistent delivery attempts, explicit channel preferences, multiple device registrations, sanitized retry records, and a one-shot notification worker. Email, SMS, WhatsApp Business, and push use local `DEMO_RECORDED` delivery only while demo mode is active.
- Authenticated booking event feeds with ordered sequence numbers, SSE heartbeats and reconnection cursors on the website, plus protected polling fallback for web and mobile.
- Explicit-consent simulated journey tracking with start, pause, resume, stop, arrival, expiration, server throttling, coordinate validation, foreground browser/Expo location updates, and short-retention cleanup tooling.
- Customer tracking screens on web and mobile with protected current location, stale-location warnings, a map, honest connection state, and an OSRM-compatible routing abstraction. Without a configured routing provider, ETA stays unavailable and only clearly labelled geographic distance is shown.
- Privacy-reduced admin notification-delivery and tracking-session views. Exact live coordinates, device tokens, phone numbers, and message bodies are not included in these admin lists.
- Assigned demo rescuers can record arrival, explicitly start a rescue session, select a controlled outcome, submit a structured rescue report, attach optional private evidence, and complete an eligible booking. Customers can confirm completion or open a restricted demo dispute.
- Optional rescue evidence reuses private storage, authorization checks, randomized keys, image signature/decode validation, metadata-stripping re-encoding, access/deletion audit events, and a configurable retention cleanup worker. Video fails closed until a safe validation/transcoding pipeline exists.
- Demo-only `NO_CHARGE`, `DEMO_ONLINE`, and `DEMO_CASH` records support idempotent creation, assigned-rescuer cash confirmation, success/failure simulation, receipts, partial/full refund records, 10% commission snapshots, reversal accounting, and a balanced double-entry-style ledger. No financial credentials or real money are accepted.
- One verified customer review is allowed per eligible completed booking. Public demo reviews expose no customer identity, rating summaries include a 1–5 distribution, and reporting/moderation is protected and rate-limited.
- Customer payment history, rescuer illustrative earnings/transactions, and privacy-reduced administrator rescue-report, evidence, payment, ledger, review, and dispute views are available on web. The mobile app includes completion, dispute, demo receipt/payment, review, evidence upload, and assigned cash-confirmation flows.
- Web and mobile profile management now require the current password for contact changes. Token-version rotation invalidates earlier JWTs on refresh/logout, and tracked export/deletion requests have authenticated citizen and administrator workflows.
- Five-language primary account and marketplace navigation extends the earlier report/safety localization. Preferences persist locally, English remains the fallback, and development builds warn about missing localized keys. Critical non-English medical text remains explicitly pending human safety review.
- API correlation IDs, privacy-safe structured access logs, security headers, liveness/readiness endpoints, and privacy-reduced administrator operations health metrics are implemented.
- Release foundations include a migration-gated API, restart-safe maintenance worker, web container, PostGIS/Redis/private-media Compose services, Expo EAS profiles, locale/secret CI gates, dependency scans, backup/restore guidance, and a fail-closed staging/production configuration validator.

All created incidents are forced to `is_demo=true`. Guest reporting is not enabled; a citizen account is required.

## Repository map

```text
apps/web                 Next.js App Router website and protected admin interface
apps/mobile              Expo Router Android/iOS application
services/api             FastAPI, SQLAlchemy, Alembic, tests, and demo seed
packages/shared-types    shared TypeScript API/domain contracts
packages/config          shared design tokens and regional scope
infrastructure/docker    API and web container definitions
docs                     architecture notes
```

## Prerequisites

- Node.js 20.19 or newer and npm 10+
- Python 3.12 or newer
- Docker Desktop for the intended PostgreSQL/PostGIS and Redis local stack
- An Android/iOS simulator or Expo Go-compatible device for mobile testing

## First-time setup

From the repository root:

```powershell
Copy-Item .env.example .env
Copy-Item .env.example services/api/.env
npm ci
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r services/api/requirements.txt
```

Replace `JWT_SECRET` in both local environment files with the same random value of at least 32 characters. Never commit either `.env` file. The root file is used by Docker Compose; `services/api/.env` is used when Alembic and Uvicorn run directly from that directory.

Start the database services:

```powershell
docker compose up -d postgres redis
```

Apply the schema and optionally create explicitly fictional demo accounts:

```powershell
Set-Location services/api
alembic upgrade head
python -m app.db.seed
Set-Location ../..
```

The optional seed creates only reserved `.example` demo users and a fictional incident; it does not add wildlife helpline numbers or pretend to provide an official LGD directory. The local-only seeded credentials are:

- Administrator: `admin.demo@spilton-demo.example` / `ChangeThisDemo123!`
- Citizen: `citizen.demo@spilton-demo.example` / `ChangeThisDemo123!`

Do not use these credentials outside a disposable development environment.

### Import official LGD location data

The repository intentionally contains no hardcoded production location list. After downloading the current official CSV/XLSX reports from <https://lgdirectory.gov.in/demo/downloadDirectory.do>, import them in parent-to-child order from `services/api`:

```powershell
python -m app.db.import_lgd states C:\imports\states.xlsx --source-version 2026-10-13
python -m app.db.import_lgd districts C:\imports\districts.xlsx --source-version 2026-10-13
python -m app.db.import_lgd subdistricts C:\imports\subdistricts.xlsx --source-version 2026-10-13
python -m app.db.import_lgd villages C:\imports\villages.xlsx --source-version 2026-10-13
```

Urban local body and ward imports are also supported. Use the actual LGD export version/date, not the example above. See [docs/LGD_IMPORT.md](docs/LGD_IMPORT.md) for validation, recovery, and update procedures.

## Run locally

Open three terminals at the repository root.

```powershell
# Terminal 1 — API
Set-Location services/api
uvicorn app.main:app --reload --port 8000

# Terminal 2 — website
npm run dev:web

# Terminal 3 — Expo
npm run dev:mobile
```

Optional Day 4/5 maintenance commands, run from `services/api`, are:

```powershell
# Process pending notification attempts once
python -m app.workers.notifications --once

# Expire unanswered demo booking requests
python -m app.workers.booking_expiration

# Remove location points older than TRACKING_RETENTION_HOURS
python -m app.workers.tracking_cleanup

# Delete expired Day 5 private evidence and record tombstone audit events
python -m app.workers.evidence_cleanup

# Run the restart-safe recurring scheduler used by the worker container
python -m app.workers.scheduler

# Audit imported LGD hierarchy counts, sources, and orphan relationships
python -m app.db.audit_lgd
```

Local addresses:

- Website: <http://localhost:3000>
- API health: <http://localhost:8000/health>
- API readiness: <http://localhost:8000/ready>
- OpenAPI documentation: <http://localhost:8000/docs>
- Expo development server: <http://localhost:8081> (the terminal prints the device URL)

For a physical device, set `EXPO_PUBLIC_API_URL` to the computer's reachable LAN URL, such as `http://192.168.1.20:8000`; `localhost` points to the phone itself. The website defaults to `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` when the API is elsewhere.

### Optional containerized stack

With the root `.env` configured, Compose runs the one-shot migration job before starting the API and worker:

```powershell
docker compose config
docker compose up --build
```

Private local media is kept outside public application directories. Docker uses the `private_media` volume; direct local execution uses `PRIVATE_MEDIA_DIR`.

## Core API through Day 3

All application endpoints except `/health` use the `/api/v1` prefix.

| Method | Path | Access |
| --- | --- | --- |
| `GET` | `/health` | Public health check |
| `GET` | `/api/v1/status` | Public demo-mode status |
| `POST` | `/api/v1/auth/register` | Public; always creates `CITIZEN` |
| `POST` | `/api/v1/auth/login` | Public, rate-limited |
| `POST` | `/api/v1/auth/logout` | Authenticated; revokes earlier account tokens |
| `POST` | `/api/v1/auth/refresh` | Authenticated short-session rotation |
| `GET/PATCH` | `/api/v1/auth/me` | Authenticated profile read/update; update requires password |
| `GET/POST` | `/api/v1/auth/account-requests` | Owner-only export/deletion request workflow |
| `POST` | `/api/v1/incidents` | Authenticated citizen; accepts `Idempotency-Key` |
| `GET` | `/api/v1/incidents/mine` | Authenticated owner; paginated/status-filtered |
| `GET` | `/api/v1/incidents/{incident_id}` | Owner, coordinator, or admin |
| `GET` | `/api/v1/incidents/{incident_id}/events` | Owner, coordinator, or admin |
| `GET` | `/api/v1/incidents/{incident_id}/media` | Owner, coordinator, or admin |
| `POST` | `/api/v1/incidents/{incident_id}/media` | Owner, coordinator, or admin |
| `GET` | `/api/v1/incidents/{incident_id}/media/{media_id}` | Owner, coordinator, or admin |
| `POST` | `/api/v1/incidents/{incident_id}/cancel` | Owner while status is cancellable |
| `GET` | `/api/v1/emergency-contacts` | Public, active verified directory records only |
| `GET` | `/api/v1/admin/incidents` | Coordinator or admin; paginated and filtered |
| `PATCH` | `/api/v1/admin/incidents/{incident_id}/status` | Coordinator or admin; validated demo transition |
| `GET` | `/api/v1/admin/overview` | Admin |
| `GET` | `/api/v1/locations/states` | Public; imported active LGD rows only |
| `GET` | `/api/v1/locations/districts?state_code=` | Public; paginated hierarchy |
| `GET` | `/api/v1/locations/subdistricts?district_code=` | Public; paginated hierarchy |
| `GET` | `/api/v1/locations/villages?subdistrict_code=` | Public; paginated hierarchy |
| `GET` | `/api/v1/locations/search?q=` | Public; bounded search |
| `POST` | `/api/v1/rescuers/onboarding` | Authenticated citizen; pending only |
| `GET` | `/api/v1/rescuers/me` | Applicant/rescuer owner |
| `PATCH` | `/api/v1/rescuers/me/availability` | Verified rescuer owner |
| `POST` | `/api/v1/rescuers/onboarding/documents` | Applicant owner; private evidence |
| `GET` | `/api/v1/rescuers/nearby` | Public; eligible simulated profiles only |
| `GET` | `/api/v1/rescuers/{rescuer_id}` | Public-safe simulated profile |
| `POST` | `/api/v1/bookings` | Authenticated customer; idempotent demo request |
| `GET` | `/api/v1/bookings/mine` | Customer owner |
| `GET` | `/api/v1/bookings/assigned` | Assigned verified rescuer |
| `GET` | `/api/v1/bookings/{booking_id}` | Customer, assigned rescuer, coordinator, or admin |
| `POST` | `/api/v1/bookings/{booking_id}/accept` | Assigned verified rescuer only |
| `POST` | `/api/v1/bookings/{booking_id}/reject` | Assigned verified rescuer only |
| `POST` | `/api/v1/bookings/{booking_id}/cancel` | Eligible customer owner |
| `GET` | `/api/v1/notifications/mine` | Authenticated recipient |
| `POST` | `/api/v1/notifications/{notification_id}/read` | Notification owner |
| `GET/PATCH` | `/api/v1/admin/rescuers...` | Admin verification and private evidence review |
| `GET` | `/api/v1/admin/bookings` | Admin; privacy-reduced demo queue |
| `GET` | `/api/v1/admin/locations` | Admin; import status and counts |
| `GET` | `/api/v1/admin/marketplace/overview` | Admin; demo-only analytics |
| `GET` | `/api/v1/admin/operations/health` | Admin; privacy-reduced queue/session metrics |
| `GET/PATCH` | `/api/v1/admin/account-requests...` | Admin privacy request review |

## Day 4 API additions

| Method | Path | Access |
| --- | --- | --- |
| `POST` | `/api/v1/devices/register` | Authenticated user; raw token is never returned |
| `DELETE` | `/api/v1/devices/{device_id}` | Device owner only |
| `GET` | `/api/v1/notifications` | Authenticated recipient only |
| `PATCH` | `/api/v1/notifications/{notification_id}/read` | Notification owner only |
| `GET/PUT` | `/api/v1/notifications/preferences` | Authenticated user; external channels require explicit opt-in |
| `GET` | `/api/v1/bookings/{booking_id}/events` | Booking participant/admin; sequence cursor |
| `GET` | `/api/v1/bookings/{booking_id}/events/stream` | Cookie-authenticated booking participant/admin; SSE |
| `POST` | `/api/v1/bookings/{booking_id}/tracking/start` | Assigned verified rescuer; explicit consent required |
| `POST` | `/api/v1/bookings/{booking_id}/tracking/pause` | Assigned rescuer only |
| `POST` | `/api/v1/bookings/{booking_id}/tracking/resume` | Assigned rescuer only |
| `POST` | `/api/v1/bookings/{booking_id}/tracking/stop` | Assigned rescuer only |
| `POST` | `/api/v1/bookings/{booking_id}/tracking/location` | Assigned rescuer with active, unexpired session |
| `GET` | `/api/v1/bookings/{booking_id}/tracking` | Customer, assigned rescuer, coordinator, or admin |
| `POST` | `/api/v1/bookings/{booking_id}/arrived` | Assigned rescuer with active tracking |
| `POST` | `/api/v1/webhooks/whatsapp` | Configured provider; HMAC signature required |
| `GET` | `/api/v1/admin/notifications` | Admin; privacy-reduced delivery state |
| `GET` | `/api/v1/admin/tracking` | Admin; no exact coordinates |

## Day 5 API additions

| Method | Path | Access |
| --- | --- | --- |
| `GET` | `/api/v1/rescue-outcomes` | Authenticated workflow clients; controlled outcome directory |
| `POST/GET` | `/api/v1/bookings/{booking_id}/rescue/start`, `/rescue` | Assigned rescuer starts; booking participants read |
| `POST` | `/api/v1/bookings/{booking_id}/complete` | Assigned rescuer; idempotent structured completion |
| `GET` | `/api/v1/bookings/{booking_id}/rescue/report` | Booking participant, coordinator, or admin |
| `POST` | `/api/v1/bookings/{booking_id}/confirm-completion` | Customer owner only |
| `POST` | `/api/v1/bookings/{booking_id}/dispute` | Customer owner only |
| `POST/GET` | `/api/v1/bookings/{booking_id}/rescue/evidence` | Assigned rescuer uploads; authorized participants list |
| `GET/DELETE` | `/api/v1/bookings/{booking_id}/rescue/evidence/{media_id}` | Authorized private retrieval/deletion |
| `POST` | `/api/v1/bookings/{booking_id}/payments` | Customer; idempotent demo record only |
| `POST` | `/api/v1/payments/{payment_id}/confirm` | Customer online-payment simulation |
| `POST` | `/api/v1/payments/{payment_id}/cash-confirm` | Assigned rescuer only |
| `GET` | `/api/v1/payments`, `/api/v1/payments/{payment_id}` | Authorized customer/participant |
| `GET` | `/api/v1/rescuer/earnings`, `/api/v1/rescuer/transactions` | Assigned rescuer; illustrative only |
| `POST/PATCH` | `/api/v1/bookings/{booking_id}/review`, `/api/v1/reviews/{review_id}` | Eligible customer owner |
| `GET` | `/api/v1/rescuers/{rescuer_id}/reviews`, `/rating-summary` | Public-safe, demo-labelled results |
| `POST` | `/api/v1/reviews/{review_id}/report` | Authenticated, rate-limited abuse report |
| `GET/PATCH` | `/api/v1/admin/rescue-reports`, `/evidence`, `/disputes...`, `/payments...`, `/ledger`, `/reviews...` | Coordinator/admin according to endpoint |
| `POST` | `/api/v1/webhooks/payments/{provider}` | Disabled unless an HMAC secret is configured |

The demo status workflow is:

```text
CREATED → UNDER_REVIEW → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
             ↘ CANCELLED                 ↘ UNABLE_TO_ASSIST → CLOSED
```

The API validates every transition and records it in incident events and audit logs. `ASSIGNED` and `IN_PROGRESS` are simulated labels only.

## Media rules

- JPEG, PNG, and WebP only
- Maximum 5 MB per image and 3 images per incident
- File signature and decoded image validation on the server
- Re-encoding removes EXIF and other metadata, including embedded GPS data
- Random private storage keys; media is never served from a public directory
- Authorized API retrieval with `private, no-store`, `nosniff`, and restrictive content security headers
- Local private-storage adapter by default; S3-compatible private adapter when configured

Incident uploads remain limited to 3 images. Day 5 rescue evidence permits at most 8 optional images per booking and applies the same 5 MB validation/sanitization boundary. Evidence retention cleanup is implemented as a one-shot worker; production malware scanning, safe video transcoding/metadata removal, an external scheduler, and object-store lifecycle enforcement are not yet configured.

## Quality checks

Run JavaScript checks from the repository root:

```powershell
npm run lint:web
npm run typecheck
npm run build:web
npm run check:locales
npm run scan:secrets
npx expo install --check
npx expo export --platform android --output-dir .expo-export
```

Run API checks from `services/api`:

```powershell
ruff format --check .
ruff check .
alembic upgrade head
alembic current
python -m pytest -q --basetemp=.pytest-tmp
python -m pip_audit -r requirements.txt  # when pip-audit is installed
```

The explicit pytest base directory avoids a Windows host issue where the global temporary directory may be inaccessible. CI executes the same lint, type, build, migration, and backend test categories on clean Linux runners.

## Security and privacy boundaries

- Web authentication uses a short-lived JWT in an `HttpOnly`, `SameSite=Lax` cookie plus a double-submit CSRF token for unsafe cookie-authenticated requests. Set `COOKIE_SECURE=true` behind production HTTPS.
- Mobile authentication uses a bearer token held in Expo Secure Store with device-only accessibility; it is not stored in AsyncStorage.
- Public registration cannot self-assign `RESCUER`, `COORDINATOR`, or `ADMIN`.
- Citizen incident access is ownership-checked. The admin list deliberately omits phone numbers, exact coordinates, address descriptions, and narrative text.
- Reference codes are random and are never accepted as authorization.
- Login, registration, incident creation, and media upload have process-local rate limits. Redis-backed distributed limiting remains required before horizontal scaling.
- Tracking updates are server-throttled, require the assigned rescuer and an active consent record, expire automatically, and stop on cancellation or arrival. Location history is private and a cleanup worker enforces the configured retention window.
- Push tokens are hashed for lookup, omitted from API responses and logs, and private to the server database. Production deployment still needs database/KMS-backed encryption at rest.
- Booking creation and rescuer evidence upload are also limited and ownership-checked. Customer contact/address data is withheld from public discovery and reduced in rescuer/admin views.
- `AUTHORIZED_OPERATION_ENABLED`, `PRICING_AUTHORIZED`, and `PAYMENTS_ENABLED` are typed fail-closed settings and remain `false`; no ordinary admin action can enable them.
- Logout increments an account token version and rejects all previously issued JWTs; refresh rotates the same short-lived session. Long-lived refresh tokens are intentionally not implemented yet.
- Logs and audit rows store action metadata rather than report contact details.

## Configuration notes

- Browser map style: `NEXT_PUBLIC_MAP_STYLE_URL`; the development fallback uses MapLibre demo tiles and must be replaced with an appropriately licensed production provider.
- Media: `MEDIA_STORAGE_BACKEND=local` with `PRIVATE_MEDIA_DIR`, or `MEDIA_STORAGE_BACKEND=s3` plus the `S3_*` settings.
- Email, SMS, WhatsApp Business, Firebase, and Redis configuration foundations exist. Demo mode records sanitized local delivery attempts only and never calls providers. Provider approval, Indian SMS DLT registration, WhatsApp templates/opt-in, FCM service-account transport, safe test recipients, and end-to-end delivery testing remain deployment prerequisites.
- Routing: set `ROUTING_PROVIDER_URL` to an approved OSRM-compatible endpoint and optional `ROUTING_API_KEY`. If it is absent or fails, the API does not invent an ETA.
- Evidence: `EVIDENCE_RETENTION_DAYS` defaults to 30. Evidence coordinates require explicit per-upload consent, are stored separately, and are never returned by public or ordinary admin list APIs.
- Demo finance: `PAYMENTS_ENABLED` must remain `false`. `PAYMENT_WEBHOOK_SECRET` enables only signature validation and safe event recording; the local gateway never accepts card, UPI, bank, or wallet credentials and cannot transfer money.
- The emergency directory is empty until source-backed, independently verified contacts are configured. Do not add invented phone numbers.

See [DAY6_REPORT.md](DAY6_REPORT.md) for the implementation inventory and verification record, [DAY7_RELEASE_CHECKLIST.md](DAY7_RELEASE_CHECKLIST.md) for the release gate, [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment/restore operations, and [docs/SECURITY_PRIVACY.md](docs/SECURITY_PRIVACY.md) for the security baseline. Provider setup is documented in [docs/DAY4_NOTIFICATIONS.md](docs/DAY4_NOTIFICATIONS.md). Earlier sprint reports remain available from Day 1 through Day 5.
