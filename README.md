# SPILTON Snake Rescue

**Saving Lives. Protecting Wildlife.**

SPILTON is a shared web, Android/iOS, and API platform for reporting snake sightings and preparing legally controlled wildlife-assistance coordination. The repository currently represents the Day 3 development prototype.

> **Demo Platform — Not an Active Emergency Rescue Service.** No workflow in this repository dispatches a real rescuer, promises availability, or sends a live emergency notification. For a suspected snakebite or other medical emergency in India, call **112** and seek immediate medical care. Never approach, touch, trap, provoke, catch, or relocate a snake, including to take a photograph.

## What works through Day 3

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

All created incidents are forced to `is_demo=true`. Guest reporting is not enabled; a citizen account is required.

## Repository map

```text
apps/web                 Next.js App Router website and protected admin interface
apps/mobile              Expo Router Android/iOS application
services/api             FastAPI, SQLAlchemy, Alembic, tests, and demo seed
packages/shared-types    shared TypeScript API/domain contracts
packages/config          shared design tokens and regional scope
infrastructure/docker    API container definition
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

Local addresses:

- Website: <http://localhost:3000>
- API health: <http://localhost:8000/health>
- OpenAPI documentation: <http://localhost:8000/docs>
- Expo development server: <http://localhost:8081> (the terminal prints the device URL)

For a physical device, set `EXPO_PUBLIC_API_URL` to the computer's reachable LAN URL, such as `http://192.168.1.20:8000`; `localhost` points to the phone itself. The website defaults to `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` when the API is elsewhere.

### Optional containerized API

The API image does not run migrations automatically. With the root `.env` configured:

```powershell
docker compose build api
docker compose run --rm api alembic upgrade head
docker compose up api
```

Private local media is kept outside public application directories. Docker uses the `private_media` volume; direct local execution uses `PRIVATE_MEDIA_DIR`.

## Day 3 API additions

All application endpoints except `/health` use the `/api/v1` prefix.

| Method | Path | Access |
| --- | --- | --- |
| `GET` | `/health` | Public health check |
| `GET` | `/api/v1/status` | Public demo-mode status |
| `POST` | `/api/v1/auth/register` | Public; always creates `CITIZEN` |
| `POST` | `/api/v1/auth/login` | Public, rate-limited |
| `POST` | `/api/v1/auth/logout` | Authenticated cookie session |
| `GET` | `/api/v1/auth/me` | Authenticated |
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

Malware scanning, retention/deletion policy automation, and production object-store lifecycle controls are not yet implemented.

## Quality checks

Run JavaScript checks from the repository root:

```powershell
npm run lint:web
npm run typecheck
npm run build:web
npx expo install --check
```

Run API checks from `services/api`:

```powershell
ruff format --check .
ruff check .
alembic upgrade head
alembic current
python -m pytest -q --basetemp=.pytest-tmp
```

The explicit pytest base directory avoids a Windows host issue where the global temporary directory may be inaccessible. CI executes the same lint, type, build, migration, and backend test categories on clean Linux runners.

## Security and privacy boundaries

- Web authentication uses a short-lived JWT in an `HttpOnly`, `SameSite=Lax` cookie plus a double-submit CSRF token for unsafe cookie-authenticated requests. Set `COOKIE_SECURE=true` behind production HTTPS.
- Mobile authentication uses a bearer token held in Expo Secure Store with device-only accessibility; it is not stored in AsyncStorage.
- Public registration cannot self-assign `RESCUER`, `COORDINATOR`, or `ADMIN`.
- Citizen incident access is ownership-checked. The admin list deliberately omits phone numbers, exact coordinates, address descriptions, and narrative text.
- Reference codes are random and are never accepted as authorization.
- Login, registration, incident creation, and media upload have process-local rate limits. Redis-backed distributed limiting remains required before horizontal scaling.
- Booking creation and rescuer evidence upload are also limited and ownership-checked. Customer contact/address data is withheld from public discovery and reduced in rescuer/admin views.
- `AUTHORIZED_OPERATION_ENABLED`, `PRICING_AUTHORIZED`, and `PAYMENTS_ENABLED` are typed fail-closed settings and remain `false`; no ordinary admin action can enable them.
- Logout clears the web cookie, but server-side bearer-token revocation and refresh-token rotation are not yet implemented.
- Logs and audit rows store action metadata rather than report contact details.

## Configuration notes

- Browser map style: `NEXT_PUBLIC_MAP_STYLE_URL`; the development fallback uses MapLibre demo tiles and must be replaced with an appropriately licensed production provider.
- Media: `MEDIA_STORAGE_BACKEND=local` with `PRIVATE_MEDIA_DIR`, or `MEDIA_STORAGE_BACKEND=s3` plus the `S3_*` settings.
- Email, SMS, WhatsApp Business, Firebase, and Redis configuration foundations exist, but external adapters fail closed without credentials and DEMO MODE sends no real dispatch message.
- The emergency directory is empty until source-backed, independently verified contacts are configured. Do not add invented phone numbers.

See [DAY3_REPORT.md](DAY3_REPORT.md) for the implementation inventory, verification record, limitations, and Day 4 handoff. Day 2 details remain in [DAY2_REPORT.md](DAY2_REPORT.md).
