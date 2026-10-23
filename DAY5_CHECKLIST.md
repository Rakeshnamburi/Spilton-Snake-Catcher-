# SPILTON Snake Rescue — Day 5 Implementation Checklist

Started: 15 October 2026

All rescue completion, evidence, payment, commission, settlement, earnings, and review activity remains fictional and simulated. No live dispatch, real charge, payout, or public evidence is permitted.

## 1. Preserve and verify Day 1–4

- [x] Re-run the combined backend baseline.
- [x] Verify current web/mobile TypeScript and production build baselines.
- [x] Preserve authentication, RBAC, ownership, notification, tracking, media privacy, emergency guidance, and fail-closed operational gates.

## 2. Rescue completion domain

- [x] Extend booking states for `IN_PROGRESS`, `COMPLETED`, `UNABLE_TO_ASSIST`, and `DISPUTED` with validated transitions.
- [x] Extend arrival with a compatible `/arrive` endpoint, arrival timestamp, optional consented accuracy, and distance warning.
- [x] Add rescue outcomes, sessions, reports, report events, and completion disputes.
- [x] Implement assigned-rescuer start/report/complete and customer confirm/dispute workflows with audit events and idempotency.
- [x] Stop tracking on completion, cancellation, unable-to-assist, and dispute where required.

## 3. Private evidence

- [x] Add rescue media, optional GPS evidence metadata, and evidence audit events.
- [x] Reuse private storage with authorization, randomized keys, image signature/decode validation, EXIF removal, limits, and private retrieval.
- [x] Add safe evidence list/upload/download/delete APIs and retention metadata.
- [x] Fail closed for video when a validated metadata-removal/duration pipeline is unavailable.

## 4. Demo payments and accounting

- [x] Add payments, attempts, events, refunds, provider webhooks, commission entries, settlement accounts/entries, and balanced financial ledger entries.
- [x] Implement `DEMO_ONLINE`, `DEMO_CASH`, and `NO_CHARGE` without collecting card or UPI credentials.
- [x] Add idempotent create/confirm/fail/cash-confirm/status/refund simulation APIs.
- [x] Use `Decimal`/`Numeric`, explicit rounding, 10% snapshot, commission reversal, and ledger reconciliation.
- [x] Keep real gateway, money collection, settlement, and payout impossible through server configuration.

## 5. Ratings and reviews

- [x] Add one verified-booking review per eligible completed booking.
- [x] Add edit, report, moderation, pagination, abuse protection, rating distribution, and aggregate updates.
- [x] Clearly label demo reviews and avoid fabricated production history.

## 6. Website and mobile

- [x] Add customer completion, dispute, demo checkout, receipt, payment history, and review flows.
- [x] Add rescuer rescue-session, evidence, completion report, earnings, and transaction flows.
- [x] Add admin rescue reports, evidence, disputes, payments, commissions/ledger, and review moderation.
- [x] Keep the existing design, responsive behavior, accessible controls, and visible demo/snakebite warnings.

## 7. Verification and documentation

- [x] Add Day 5 workflow, evidence, payment, commission, ledger, ownership, notification, and review tests.
- [x] Run backend format/lint/tests and a fresh migration.
- [x] Run web lint/type/build, mobile TypeScript, and Expo bundle validation.
- [x] Update README and create `DAY5_REPORT.md` with actual results and Day 6 handoff.
