# SPILTON Snake Rescue — Day 5 Report

Date completed: 16 October 2026

## Safety and operational status

Day 5 remains a development simulation. The server requires demo mode for the financial workflow, forces rescue/payment/review data to demo records, and does not expose a production payment credential form. No real rescuer was dispatched, no real payment, refund, commission, settlement, or payout was made, and no public evidence repository was created. Existing snakebite guidance continues to direct users to immediate medical care and India's emergency number 112.

## Implemented features

### Arrival and rescue completion

- Added the compatible `POST /api/v1/bookings/{id}/arrive` route while preserving `/arrived`.
- Arrival records a timestamp and may include an explicitly consented coordinate/accuracy sample. Exact arrival coordinates stay private; a large destination discrepancy creates a review warning rather than claiming precise arrival.
- Assigned rescuers can start one demo rescue session after arrival, read its current state, select a controlled outcome, submit observations and an authorized-action summary, and complete the booking.
- Completion is protected by booking state, rescuer assignment, verification, idempotency, row locking, and audit/event records. Species text is stored only as an unverified observation and is never an AI safety classification.
- Customers can confirm a completed simulation or open a restricted dispute. Administrators can review and resolve disputes with an audit trail.
- The workflow supports `ARRIVED → IN_PROGRESS → COMPLETED` and the existing eligible unable-to-assist/cancellation branches. `DISPUTED` is an explicit review state.

### Private rescue evidence

- Added optional JPEG, PNG, and WebP rescue evidence with a 5 MB per-file limit and at most 8 evidence images per booking.
- Uploads require the assigned rescuer, use random private storage keys, verify the file signature and decoded image, re-encode the image to remove EXIF/embedded GPS, and never execute or publicly serve uploaded content.
- Optional evidence GPS metadata is stored in a separate table only after explicit consent. It is not included in ordinary evidence responses or admin list responses.
- Customer, assigned rescuer, coordinator, and administrator access is checked server-side for private retrieval. Access and deletion events are audited.
- Evidence rows include a configurable retention expiry. `python -m app.workers.evidence_cleanup` deletes expired private objects and leaves a sanitized tombstone audit event.
- Video upload deliberately returns `VIDEO_PIPELINE_NOT_CONFIGURED`; no unsafe raw-video fallback was added.

### Demo payments, commission, and ledger

- Added `DEMO_ONLINE`, `DEMO_CASH`, and `NO_CHARGE` records. The UI and API collect no card, UPI, bank, or wallet credentials.
- Payment creation requires an idempotency key. Online success/failure is produced by a local demo gateway; cash remains pending until the assigned rescuer explicitly confirms the simulated receipt.
- Successful non-zero demo payments create a Decimal-based 10% commission snapshot and rescuer-share calculation with explicit two-decimal, half-up rounding.
- Added payment attempts, events, refunds, signed-provider webhook records, commission entries, settlement foundations, and balanced ledger entries. Refunds create proportional commission reversals.
- Customer receipt/history, rescuer illustrative earnings/transactions, assigned cash confirmation, admin payment/refund, and ledger inspection are connected to real API responses.
- `PAYMENTS_ENABLED=false` remains required for the simulation. Earnings are non-withdrawable; real settlement and payout have no executable path.

### Ratings and reviews

- A customer can create one demo-labelled review only for their eligible completed booking.
- Owners can edit a review. Authenticated users can report abuse through a rate-limited endpoint, and coordinator/admin moderation can hide or remove content.
- Public review responses omit customer and booking identifiers. Rating summaries return count, average, and a 1–5 distribution without fabricating historical performance.

### Notification integration

- Added demo templates/events for rescue-session start, rescue-report submission, booking completion, completion dispute, payment success/failure, and review submission; arrival continues to use the Day 4 event.
- In-app records are private to the recipient. If a user has explicitly enabled email, SMS, WhatsApp, or push, demo mode records a sanitized `DEMO_RECORDED` delivery attempt through the existing adapter and does not contact a provider.

### Website

- Customer booking details now include the protected completion report, authorized private evidence retrieval, completion confirmation, dispute, no-charge/online/cash demo choice, receipt, and review controls.
- `/payments` lists the signed-in customer's demo financial records.
- The rescuer journey includes session start, structured outcome/report fields, optional private image evidence, and completion.
- `/rescuer/earnings` shows non-withdrawable illustrative totals, assigned transactions, and assigned-rescuer cash confirmation.
- Added restricted administrator routes: `/admin/rescue-reports`, `/admin/evidence`, `/admin/payments`, `/admin/ledger`, `/admin/reviews`, and `/admin/disputes`.

### Mobile

- `booking-completion` provides completion confirmation, private evidence metadata, dispute, demo payment/receipt, and review flows.
- `rescuer-completion` provides rescue-session start, controlled outcome/report creation, optional private image evidence, and completion.
- `payments` and `rescuer-earnings` provide demo history, non-withdrawable summaries, assigned transactions, and cash confirmation.
- Booking and profile/navigation screens link to the new workflows. All screens retain visible demo/no-real-payment notices.

## Database migration

Migration `0005_day5_completion_finance_reviews`:

- extends bookings with arrival/completion/customer-confirmation metadata and adds the `DISPUTED` state;
- creates rescue outcomes, rescue sessions, rescue reports/events, rescue media, evidence location metadata/audit events, and completion disputes;
- creates payments, attempts, events, refunds, signed webhook records, commission entries, settlement accounts/entries, and financial ledger entries;
- creates reviews and review abuse reports with booking/customer/rescuer constraints and useful indexes;
- seeds seven generic controlled rescue outcomes with deterministic identifiers, all explicitly usable only in the simulated workflow.

A fresh SQLite database migrated successfully through `0001_initial`, `0002_day2_incident_tracking`, `0003_day3_marketplace`, `0004_day4_realtime_tracking`, and `0005_day5_completion_finance_reviews (head)`.

## New API endpoints

### Completion and evidence

- `GET /api/v1/rescue-outcomes`
- `POST|GET /api/v1/bookings/{booking_id}/rescue/start|rescue`
- `POST /api/v1/bookings/{booking_id}/complete`
- `GET /api/v1/bookings/{booking_id}/rescue/report`
- `POST /api/v1/bookings/{booking_id}/confirm-completion`
- `POST /api/v1/bookings/{booking_id}/dispute`
- `POST|GET /api/v1/bookings/{booking_id}/rescue/evidence`
- `GET|DELETE /api/v1/bookings/{booking_id}/rescue/evidence/{media_id}`
- `GET /api/v1/admin/rescue-reports`
- `GET /api/v1/admin/evidence`
- `GET /api/v1/admin/disputes`
- `PATCH /api/v1/admin/disputes/{dispute_id}`

### Demo finance

- `POST /api/v1/bookings/{booking_id}/payments`
- `POST /api/v1/payments/{payment_id}/confirm`
- `POST /api/v1/payments/{payment_id}/cash-confirm`
- `GET /api/v1/payments`
- `GET /api/v1/payments/{payment_id}`
- `GET /api/v1/rescuer/earnings`
- `GET /api/v1/rescuer/transactions`
- `GET /api/v1/admin/payments`
- `POST /api/v1/admin/payments/{payment_id}/refund`
- `GET /api/v1/admin/ledger`
- `POST /api/v1/webhooks/payments/{provider}`

### Reviews

- `POST /api/v1/bookings/{booking_id}/review`
- `PATCH /api/v1/reviews/{review_id}`
- `GET /api/v1/rescuers/{rescuer_id}/reviews`
- `GET /api/v1/rescuers/{rescuer_id}/rating-summary`
- `POST /api/v1/reviews/{review_id}/report`
- `GET /api/v1/admin/reviews`
- `PATCH /api/v1/admin/reviews/{review_id}`

OpenAPI generation completed with 94 registered paths; the required Day 5 paths were present.

## Main files created

- `DAY5_CHECKLIST.md`, `DAY5_REPORT.md`
- `services/api/alembic/versions/0005_day5_completion_finance_reviews.py`
- `services/api/app/api/day5_rescue.py`, `day5_payments.py`, `day5_reviews.py`
- `services/api/app/schemas/day5.py`
- `services/api/app/services/day5_finance.py`, `evidence_retention.py`, `payment_gateway.py`
- `services/api/app/workers/evidence_cleanup.py`
- `services/api/tests/test_day5_completion_finance.py`
- `apps/web/features/marketplace/day5-customer.tsx`, `day5-rescuer.tsx`, `day5-finance.tsx`
- `apps/web/features/admin/day5.tsx` and the six Day 5 admin route pages
- `apps/mobile/app/booking-completion.tsx`, `rescuer-completion.tsx`, `payments.tsx`, `rescuer-earnings.tsx`

Existing models, routing, tracking, booking status logic, shared TypeScript contracts, navigation, dashboard links, environment template, and README were extended without removing Day 1–4 behavior.

## Verification results

| Check | Actual result |
| --- | --- |
| Day 1–4 backend baseline before final Day 5 UI additions | 42 passed in 1234.92s |
| Focused Day 5 backend suite after final notification integration | 4 passed in 107.92s |
| Final combined backend suite | 46 passed in 1862.04s (31m02s) |
| Ruff format and lint | Passed; 59 Python files formatted and checked |
| Web ESLint | Passed |
| Web and mobile TypeScript | Passed |
| Next.js production build | Passed; 32/32 static pages generated and dynamic Day 5 routes compiled |
| Expo dependency compatibility | Initially found four patch mismatches; updated to SDK 57-compatible versions and recheck passed |
| Android Expo production bundle | Passed after dependency update; 1,591 modules and a 3.7 MB Hermes bundle exported |
| Fresh Alembic migration | Passed through `0005_day5_completion_finance_reviews (head)` on SQLite |
| PostgreSQL/PostGIS migration | Not run in this environment; the local Docker service was not available during the sprint validation |
| Real payment/provider test | Intentionally not run; the implementation must not move real money in demo mode |

`npm install` continued to report 29 production-tree advisories (19 high and 10 moderate) in the Expo/React Native dependency tree. No forced breaking downgrade/upgrade was applied; this remains a release blocker.

The focused tests exercise assigned-rescuer enforcement, unrelated-user denial, arrival, rescue-session start, structured/idempotent completion, customer confirmation, image signature/decode checks, EXIF removal, randomized private storage, unauthorized evidence denial, invalid image rejection, online simulation, exact 10% Decimal commission, non-withdrawable earnings, partial refund/reversal, balanced ledger groups, review uniqueness, and assigned-rescuer-only cash confirmation.

## Commands executed for final validation

```powershell
npm run lint:web
npm run typecheck
npm run build:web
npx expo export --platform android --output-dir ../../.expo-export-day5-sdk-final
npx expo install --check
npm audit --omit=dev

python -m ruff check app tests
python -m pytest tests/test_day5_completion_finance.py -q --basetemp=.pytest-day5-final-20261016
python -m pytest tests -q --basetemp=.pytest-day5-full-final-20261016
python -m alembic upgrade head
python -m alembic current
```

The first focused pytest attempt could not create its default Windows global temporary directory (`PermissionError: WinError 5`). It was rerun with a repository-local `--basetemp`; the test code then passed. A later parallel pytest experiment was discarded because both processes shared `test_spilton.db` and caused SQLite lock/table races; the recorded focused and final results use one sequential process.

## Known limitations and release blockers

- Video evidence is intentionally unavailable until content inspection, codec validation, duration/size limits, safe metadata removal, malware scanning, and transcoding are implemented.
- Images are decoded and sanitized, but a production malware-scanning service is not integrated.
- The retention worker is one-shot; deployment still needs a scheduler, monitoring, object-store lifecycle controls, and legal hold/deletion policy review.
- Mobile currently lists authorized evidence metadata but does not render/download the private binary; the website provides authorized image viewing. Admin evidence is intentionally metadata-only.
- No real gateway, payment method tokenization, tax invoice, settlement, reconciliation provider, payout, or withdrawal exists. Provider webhooks only validate HMAC and store sanitized demo status.
- The financial ledger is an application-level demo ledger, not a regulated accounting or banking system. PostgreSQL concurrency tests and an independent reconciliation audit remain required.
- A physical Android/iOS launch, camera/gallery upload, GPS arrival, and accessibility review were not available in this environment.
- No official LGD production dataset, verified wildlife contact directory, real rescuer authorization, legal pricing approval, or external provider credential was added.
- Previously reported Expo/React Native production-tree dependency advisories remain a release blocker until an SDK-compatible upgrade and device regression pass are completed.

## Day 6 readiness

1. Run the complete stack against PostgreSQL/PostGIS and Redis, including concurrent completion/payment/refund/idempotency tests.
2. Add malware scanning and a safe video evidence pipeline before enabling video.
3. Add scheduled retention, legal-hold controls, reconciliation reports, and tamper-evident evidence/ledger audit exports.
4. Add private evidence rendering to mobile with cache prevention and lifecycle cleanup.
5. Perform Android/iOS device tests for gallery permission, large/invalid images, network interruption, and session expiry.
6. Resolve the Expo/React Native dependency advisories through a coordinated SDK-compatible upgrade.
7. Keep live dispatch, real payment, settlement, payout, and authorized operation fail-closed until wildlife, contractual, financial, and operational approvals are documented outside the ordinary admin interface.
