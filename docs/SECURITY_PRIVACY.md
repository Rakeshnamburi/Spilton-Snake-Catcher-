# Security and privacy baseline

## Data minimization

- Public rescuer responses omit private coordinates, identity documents, home addresses, email, and phone.
- Booking, incident, tracking, payment, evidence, and notification records require authenticated ownership or an authorized role.
- Admin list endpoints use reduced fields where operational detail is unnecessary.
- Exact movement history is retained only for the configured short tracking period; evidence has a separate retention cleanup job.
- Application logs contain method, path, status, duration, and correlation ID—not query strings, payloads, contact data, coordinates, tokens, or evidence.

## Account controls

- Public registration always creates `CITIZEN`; privileged roles require administrator-controlled workflows.
- Web sessions use HttpOnly cookies plus double-submit CSRF protection; mobile bearer tokens use device secure storage.
- JWTs contain a unique ID and token version. Refresh rotates the version; logout invalidates all earlier tokens for that account.
- Profile contact changes require the current password.
- Export/deletion requests are recorded, idempotent while open, auditable, and processed only by administrators. A request does not silently delete safety, legal, financial, or audit records.

## Upload and notification controls

- Evidence/media is private, randomized, signature-validated, size-limited, and sanitized of EXIF metadata.
- Real provider sends are disabled in demo mode. Logs store sanitized delivery results only.
- Device tokens are protected records and are never returned through public or unrelated-user APIs.

## Remaining external review

- Human safety review of Telugu, Tamil, Kannada, and Malayalam critical medical translations.
- Formal privacy notice, retention schedule, data-processing agreements, and legal review.
- Hosted WAF/rate-limit policy, centralized monitoring/redaction validation, and penetration testing.
- Real authorization/partner verification. Application verification never substitutes for wildlife authorization.
