# Architecture

All clients use the versioned FastAPI service. The web client authenticates with an HttpOnly cookie; mobile uses the same short-lived JWT in Expo Secure Store. PostgreSQL is the production database target, with PostGIS available in Docker for future proximity queries. SQLite exists only as a frictionless local/test fallback.

Incident access is deny-by-default: citizens can create and list their own records, and detail access requires ownership. Coordinator and administrator access is explicit. Dashboard summaries deliberately exclude direct personal and precise-location fields.

## Deployment boundary

The API exposes demo incident coordination only. It does not implement responder matching, automatic dispatch, snake classification, public reference-code lookup, or live availability. Those features must not be enabled until authorization, verified partnerships, operating procedures, and readiness reviews are complete.

## Planned adapters

- Redis: distributed rate limits, revocation/session state, and queues.
- S3-compatible storage: private media with signed URLs, scanning, and retention controls.
- Firebase Cloud Messaging: opt-in device notifications after credential setup.
- MapLibre: consent-aware maps without using map results as rescue guarantees.

