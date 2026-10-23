# Day 6 deployment and recovery runbook

This runbook deploys the **DEMO platform only**. `DEMO_MODE=true`, `AUTHORIZED_OPERATION_ENABLED=false`, `PRICING_AUTHORIZED=false`, and `PAYMENTS_ENABLED=false` are enforced by the API settings model. Real rescue dispatch and real payment processing are not release options in this sprint.

## Services

- `web`: production Next.js server.
- `api`: FastAPI with `/health` liveness and `/ready` database readiness.
- `worker`: notification retries, booking expiry, tracking retention, and evidence retention.
- `migrate`: one-shot Alembic migration job that must complete before API/worker startup.
- `postgres`: PostGIS-enabled PostgreSQL source of truth.
- `redis`: integration foundation; PostgreSQL remains authoritative.
- `private_media`: local-development-only private volume. Use a private S3-compatible bucket for a real hosted environment.

## Local container smoke environment

1. Copy `.env.example` to `.env`.
2. Generate a unique JWT secret of at least 32 random characters.
3. Keep every operational/payment feature gate false.
4. Run `docker compose config`, then `docker compose up --build`.
5. Verify `http://localhost:8000/health`, `http://localhost:8000/ready`, `http://localhost:8000/docs`, and `http://localhost:3000`.

Docker was not available in the Day 6 workstation, so the compose runtime remains a Day 7 verification gate even though the manifest and images are present.

## Hosted environment requirements

- Set `ENVIRONMENT=staging` or `production`, `COOKIE_SECURE=true`, a rotated `JWT_SECRET`, and explicit HTTPS-only `WEB_ORIGINS`. Startup fails closed when these requirements are violated.
- Put database, object-storage, provider, and monitoring credentials in the hosting platform secret store. Do not commit `.env`.
- Use TLS at the ingress and forward `X-Request-ID`; the API returns the accepted/generated identifier.
- Configure private object storage with public access blocked, server-side encryption, short-lived signed access, lifecycle rules matching evidence retention, and access logging.
- Configure `ERROR_MONITORING_DSN` only after an approved monitoring provider and data-processing policy exist. Do not send contact details, coordinates, tokens, evidence, or message bodies to monitoring.
- Import official LGD exports separately. Deployment does not imply complete location coverage.

## Database migration

Run `alembic upgrade head` as a release job before new API/worker instances. Record the previous revision with `alembic current`. Do not automatically downgrade a production database. Roll back application instances first; use a reviewed forward-fix migration when stored data could be lost.

## Backup and restore baseline

Before migration:

1. Create an encrypted PostgreSQL custom-format backup with `pg_dump --format=custom`.
2. Record database version, Alembic revision, application commit, backup checksum, and object-storage snapshot/version marker.
3. Snapshot the private media bucket/volume and preserve encryption keys separately.

Restore rehearsal:

1. Restore into an isolated empty database with `pg_restore --clean --if-exists` only in that isolated target.
2. Point a disposable API instance at the restored database.
3. Run `alembic current`, `/ready`, the LGD integrity audit, ownership tests, and a synthetic DEMO booking smoke test.
4. Verify evidence remains private and notification adapters remain in demo mode.
5. Record elapsed time and any manual repair steps. A backup is not release-ready until a restore rehearsal succeeds.

## Mobile release preparation

`apps/mobile/eas.json` contains internal Android APK and production Android App Bundle profiles. Replace the placeholder HTTPS API URL and configure the EAS project/credentials before building. Validate iOS signing separately. Never place backend credentials in Expo public environment variables.

## Post-deploy smoke tests

- Register/login/logout; confirm a logged-out bearer token is rejected.
- Create an incident and a DEMO booking with unique idempotency keys.
- Accept using only the assigned fictional rescuer.
- Start consented simulated tracking, publish one valid update, stop tracking.
- Complete the synthetic workflow and create a demo payment/review record.
- Confirm another customer cannot read the booking, media, tracking, or payment.
- Confirm admin operation health and privacy request queues require `ADMIN`.
- Confirm no real email, SMS, WhatsApp, push dispatch, payment, or settlement occurred.

## Rollback and incident response

- Disable ingress to unsafe endpoints before changing data when privacy or authorization is suspected.
- Rotate JWT/provider credentials and restart API/worker instances after credential exposure.
- Preserve audit logs and correlation IDs; never copy sensitive payloads into tickets.
- Stop the worker if retry storms occur, investigate sanitized delivery metadata, then resume.
- Keep DEMO feature gates false throughout rollback.
