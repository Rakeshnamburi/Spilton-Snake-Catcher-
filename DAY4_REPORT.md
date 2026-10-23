# SPILTON Snake Rescue — Day 4 Report

Date completed: 15 October 2026

## Safety status

Day 4 remains a development simulation. The server enforces demo incidents, bookings, notifications, tracking points, and journeys. No real rescuer was contacted, no payment was processed, and no real email, SMS, WhatsApp, or push notification was sent. All new customer and rescuer tracking screens display a demo warning. Suspected snakebite guidance continues to direct users to immediate medical care and India's emergency number 112.

## Implemented features

### Booking and notifications

- Customer booking creation now records `REQUESTED` and `PENDING_RESCUER_RESPONSE`, creates an in-app receipt for the customer, and creates an idempotent assigned-booking notification for the fictional demo rescuer.
- Accept, reject, expire, cancel, journey-start, and arrival paths create booking events and recipient notifications without exposing coordinates.
- Notification events include private deep links and unique deduplication keys. Delivery attempts support channel uniqueness, attempt counts, retry timestamps, provider message IDs, and sanitized results.
- Database-backed templates cover booking received, assigned, accepted, rejected, expired, cancelled, journey started, and arrival events across in-app, email, SMS, WhatsApp, and push channels.
- Demo adapters record `DEMO_RECORDED`; the notification worker has capped exponential retry handling. SMTP and generic authorized-provider adapters fail closed behind server configuration.
- Notification preferences require explicit opt-in for SMS, WhatsApp, and push. Device registration supports multiple devices, hashed token lookup, owner-only deactivation, token hints instead of raw-token API output, and no token logging.
- WhatsApp delivery-status webhook requests require an HMAC signature when configured.
- A one-shot booking-expiration worker processes unanswered demo requests.

### Real-time events and tracking

- Booking events have per-booking sequence numbers and a uniqueness constraint.
- The API exposes ownership-checked event polling and SSE with heartbeats, `Last-Event-ID`/sequence reconnection, bounded batches, and disconnect cleanup. PostgreSQL remains the source of truth; the web client falls back to polling.
- Tracking sessions record the booking, assigned rescuer, consent version/timestamp, active state, start/pause/stop/expiry times, and last-location time.
- Tracking locations validate latitude, longitude, accuracy, active consent, assignment, booking state, update frequency, session expiry, and simulated-data flag.
- Start, pause, resume, stop, location, read-current-tracking, and arrival endpoints are implemented. Arrival and eligible cancellation stop sharing. Expired sessions reject new points.
- A cleanup worker deletes location points older than `TRACKING_RETENTION_HOURS`; the default is 24 hours.
- The OSRM-compatible routing adapter caches successful routes. When no provider is configured or a request fails, road distance and ETA remain unavailable; separately labelled Haversine distance may still be shown.

### Website

- `/bookings/[id]/tracking` provides protected booking status, connection state, stale-location warnings, MapLibre markers/route, last update, ETA state, refresh, and timeline navigation.
- `/rescuer/bookings/[id]` provides explicit tracking consent, user-triggered browser foreground GPS, synthetic manual fallback, throttled points, pause/resume/stop, and simulated arrival.
- Leaving the page or hiding the tab stops the browser watcher and clearly reports that continuous foreground updates stopped.
- `/admin/notifications` shows privacy-reduced delivery attempts and failures.
- `/admin/tracking` shows demo session state without exact coordinates.

### Mobile

- `bookings/[id]/tracking` displays the protected current simulated point, destination, route where available, ETA state, connection/polling state, stale warnings, refresh, and timeline access.
- `rescuer-journey` implements explicit consent, foreground-only Expo Location permission, throttled updates, manual fictional coordinates, pause/resume/stop, arrival, watcher cleanup, and permission-denied fallback.
- Expo Notifications supports explicit permission request, native token registration, foreground display handling, notification-response deep links, and safe failure when a native token is unavailable.
- `expo-notifications` and `react-native-maps` were added using Expo-compatible versions. No background-location permission is configured.

### Administration and privacy

- Admin lists provide notification delivery state and tracking-session metadata but omit exact coordinates, raw device tokens, recipients, phone numbers, and full provider message bodies.
- Booking ownership, assigned-rescuer checks, coordinator/admin authorization, explicit consent, expiry, and demo-mode gates are enforced server-side.
- Logging uses event types, booking IDs, template keys, and sanitized status rather than recipient or location data.

## Database migration

Migration `0004_day4_realtime_tracking`:

- adds ordered `booking_events.sequence` with unique/indexed booking sequence;
- extends notification events, preferences, and delivery attempts for deduplication, deep links, opt-in, retries, delivery timestamps, and sanitized provider state;
- creates `device_registrations`;
- creates `tracking_sessions`;
- creates `tracking_locations` with coordinate/accuracy constraints and session-time indexes.

A fresh SQLite migration ran successfully from `0001_initial` through `0004_day4_realtime_tracking (head)`. Docker Desktop was not running, so the same migration was not executed against the local PostgreSQL/PostGIS container in this environment.

## New API endpoints

- `POST /api/v1/devices/register`
- `DELETE /api/v1/devices/{device_id}`
- `GET /api/v1/notifications`
- `GET /api/v1/notifications/mine`
- `PATCH|POST /api/v1/notifications/{notification_id}/read`
- `GET|PUT /api/v1/notifications/preferences`
- `GET /api/v1/bookings/{booking_id}/events`
- `GET /api/v1/bookings/{booking_id}/events/stream`
- `POST /api/v1/bookings/{booking_id}/tracking/start`
- `POST /api/v1/bookings/{booking_id}/tracking/pause`
- `POST /api/v1/bookings/{booking_id}/tracking/resume`
- `POST /api/v1/bookings/{booking_id}/tracking/stop`
- `POST /api/v1/bookings/{booking_id}/tracking/location`
- `GET /api/v1/bookings/{booking_id}/tracking`
- `POST /api/v1/bookings/{booking_id}/arrived`
- `POST /api/v1/webhooks/whatsapp`
- `GET /api/v1/admin/notifications`
- `GET /api/v1/admin/tracking`

## Files created

- `DAY4_CHECKLIST.md`, `DAY4_REPORT.md`, `docs/DAY4_NOTIFICATIONS.md`
- `services/api/alembic/versions/0004_day4_realtime_tracking.py`
- `services/api/app/api/devices.py`, `realtime.py`, `tracking.py`, `webhooks.py`
- `services/api/app/schemas/day4.py`
- `services/api/app/services/routing.py`, `tracking.py`
- `services/api/app/workers/booking_expiration.py`, `notifications.py`, `tracking_cleanup.py`
- `services/api/tests/test_day4_realtime_tracking.py`
- `apps/web/features/tracking/*` and Day 4 route pages under `apps/web/app`
- `apps/mobile/app/bookings/[id]/tracking.tsx`, `apps/mobile/app/rescuer-journey.tsx`
- `apps/mobile/components/tracking-map.tsx`, `apps/mobile/services/notifications.ts`

Existing marketplace, admin, API router/model/schema, shared type, environment, dependency, and navigation files were extended without removing Day 1–3 functionality.

## Main files modified

- `.env.example`, `README.md`, `package-lock.json`, `packages/shared-types/index.ts`
- `services/api/app/main.py`, `models/entities.py`, `core/config.py`, `db/seed.py`
- `services/api/app/api/routes.py`, `bookings.py`, `notifications.py`, `admin_marketplace.py`, `marketplace_helpers.py`
- `services/api/app/services/marketplace.py`, `notifications.py`
- `services/api/app/schemas/marketplace.py`
- `services/api/tests/test_day3_marketplace.py`
- `apps/web/features/admin/*`, `apps/web/features/marketplace/*`, `apps/web/lib/marketplace.ts`
- `apps/mobile/app.json`, navigation/profile/booking routes, marketplace types, and `apps/mobile/package.json`

## Verification results

| Check | Actual result |
| --- | --- |
| Pre-Day 4 backend regression | 36 passed |
| Final backend suite | 42 passed in 6.99s |
| Ruff format and lint | Passed; 55 Python files checked after formatting one changed file |
| Web ESLint | Passed |
| Web TypeScript | Passed |
| Mobile TypeScript | Passed |
| Next.js production build | Passed; 24/24 static pages generated and all dynamic Day 4 routes compiled |
| Expo dependency check | Reported dependencies up to date using the local SDK 57 dependency map; network validation was unavailable in the restricted run |
| Expo public configuration | Passed; foreground location and notifications plugins present, no background-location permission |
| Android Expo production bundle | Passed; 1,586 modules bundled and the Android Hermes bundle exported successfully |
| Fresh Alembic migration | Passed through `0004_day4_realtime_tracking (head)` on SQLite |
| Docker Compose/PostgreSQL run | Not run: `.env` was absent and Docker Desktop daemon was not running |
| Real provider delivery | Intentionally not run; demo mode must not send external rescue notifications |

The backend test suite validates assigned-recipient notifications, customer receipts, demo delivery attempts for email/SMS/WhatsApp/push, private device responses, unauthorized rescuer rejection, duplicate transition rejection, explicit consent, valid/invalid coordinates, customer ownership, unrelated-customer denial, pause/resume/arrival/cancellation/completion stopping, expiry rejection, event sequence order, routing-provider failure behavior, and unauthenticated/unauthorized SSE rejection.

## Dependency security result

`npm audit --omit=dev` reported 29 production-tree advisories: 19 high and 10 moderate, predominantly inside the Expo/React Native/Metro toolchain. npm's suggested automatic resolutions would downgrade Expo/React Native or move Expo Router to a different SDK generation, so no unsafe forced upgrade/downgrade was applied. This is an open release blocker that requires a coordinated Expo SDK dependency review and device regression testing.

## External credentials and approvals still required

- SMTP or transactional email credentials plus a safe mailbox/test-recipient policy.
- Authorized SMS provider, Indian DLT entity/sender/template approvals, and delivery receipts.
- WhatsApp Business account, approved templates, recipient opt-in, provider payload mapping, and webhook reconciliation.
- Firebase project/service account and completed FCM OAuth transport; real push delivery was not tested.
- Approved/licensed map tiles and routing provider with documented usage/rate limits.
- PostgreSQL/Redis deployment, TLS, secrets manager, monitoring, and scheduler/worker runtime.
- Wildlife authorization, verified operating partners, policies, and emergency procedures. These cannot be enabled from the normal admin dashboard.

## Known limitations

- SSE currently polls PostgreSQL every 15 seconds. Redis pub/sub fan-out and bearer-authenticated mobile streaming are not implemented; mobile uses protected polling.
- Web and mobile tracking are foreground-only. Background tracking is intentionally absent.
- Route-provider success was not integration-tested because no approved routing endpoint was configured.
- FCM provider transport deliberately fails closed; only client/device registration and local demo delivery foundations are present.
- SMS/WhatsApp HTTP adapters require provider-specific approved payload mapping before any authorized test.
- Device tokens are private, hashed for lookup, and never returned/logged, but production KMS/database encryption at rest is still required.
- Notification processing, booking expiration, and retention cleanup are one-shot workers that require an external scheduler in deployment.
- A device/simulator launch and real GPS/push test were not available in this environment.
- No official LGD production dataset, verified wildlife contacts, real rescuer authorizations, or provider credentials were added.

## Day 5 handoff

1. Resolve the Expo/React Native dependency advisories through a coordinated SDK-compatible upgrade and run Android/iOS device regression tests.
2. Run migration and concurrency tests against PostgreSQL/PostGIS, then add Redis-backed distributed rate limiting and event fan-out.
3. Complete FCM OAuth transport and provider-specific receipt handling in an isolated test project without enabling real dispatch.
4. Add encrypted-at-rest device tokens using the deployment KMS/secrets architecture.
5. Add scheduled worker execution, dead-letter review, retention monitoring, and operational dashboards.
6. Add route-provider contract tests and approved tile/routing configuration.
7. Continue to keep authorized operation, real payment, and live dispatch fail-closed until external legal and operational approvals exist.
