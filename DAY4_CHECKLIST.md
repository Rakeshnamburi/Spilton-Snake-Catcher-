# SPILTON Snake Rescue — Day 4 Implementation Checklist

Started: 14 October 2026
Completed review: 15 October 2026

All Day 4 notification, journey, and tracking behavior is simulated. No real rescue dispatch, external message, payment, or unconsented location sharing is permitted.

## 1. Preserve and verify Day 1–3

- [x] Re-run the combined backend regression before Day 4 changes.
- [x] Verify web and mobile TypeScript baselines.
- [x] Preserve authentication, RBAC, incident privacy, booking ownership, demo gates, and emergency guidance.

## 2. Notification delivery foundation

- [x] Extend notification templates, events, attempts, preferences, idempotency, retries, and sanitized errors.
- [x] Add safe demo adapters for email, SMS, WhatsApp Business, and push.
- [x] Add provider configuration contracts, consent checks, recipient validation, and webhook signature verification.
- [x] Add device registration, removal, multi-device support, token protection, and invalidation.
- [x] Add a notification worker command with retry/backoff and no real delivery in DEMO MODE.

## 3. Real-time booking events

- [x] Add ordered booking event sequence numbers and event deduplication support.
- [x] Add authenticated SSE subscriptions with ownership checks, heartbeat, reconnection cursor, and polling fallback.
- [x] Publish booking, notification, and tracking changes without exposing unrelated bookings.
- [ ] Redis pub/sub fan-out is deferred; Day 4 uses PostgreSQL source-of-truth polling and documents the horizontal-scaling limitation.

## 4. Consent-based tracking

- [x] Add tracking sessions and tracking locations with indexes, constraints, expiry, and retention metadata.
- [x] Implement explicit start/pause/resume/stop/location/arrived endpoints.
- [x] Enforce assigned-rescuer identity, accepted/en-route state, consent, rate limits, coordinate validation, and expiry.
- [x] Stop tracking on cancellation, arrival, completion, expiration, or explicit stop.
- [x] Add customer-authorized current tracking view without public history exposure.

## 5. Routing and ETA

- [x] Add routing-provider abstraction with configured OSRM-compatible adapter.
- [x] Add safe demo/unavailable fallback: geographic distance labelled approximate and ETA unavailable.
- [x] Prevent straight-line distance from being presented as road distance or precise ETA.

## 6. Website

- [x] Add `/bookings/[id]/tracking` customer tracking experience.
- [x] Extend booking detail and rescuer journey dashboard with real actions and connection states.
- [x] Add foreground browser geolocation controls and explicit sharing disclosure.
- [x] Extend admin marketplace view with tracking and delivery status, failures, events, and audit summaries.

## 7. Mobile

- [x] Add foreground-only live booking tracking screen.
- [x] Add rescuer journey controls, explicit permission/consent, throttled updates, pause/resume/stop, and arrival.
- [x] Add device registration foundation, notification deep links, and foreground refresh behavior.
- [x] Handle denied permission, stale/unavailable tracking, network recovery, and session expiry.

## 8. Verification and documentation

- [x] Add Day 4 authorization, tracking, delivery, realtime, and ETA tests.
- [x] Run backend format/lint/tests and fresh migration verification.
- [x] Run web lint/type/build, mobile typecheck, Expo dependency validation, and an Android production bundle export.
- [x] Run representative API regression and production route compilation checks; physical-device smoke testing remains unavailable and is documented.
- [x] Update README and create `DAY4_REPORT.md` with actual results and Day 5 handoff.
