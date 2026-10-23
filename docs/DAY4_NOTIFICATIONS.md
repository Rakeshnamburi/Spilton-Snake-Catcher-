# Day 4 notification provider setup

This repository is intentionally locked to demo behavior. `DEMO_MODE=true` and the typed `AUTHORIZED_OPERATION_ENABLED=false` gate cause email, SMS, WhatsApp Business, and FCM attempts to use the local `DEMO_RECORDED` adapter. No external rescue message is sent.

## Local behavior

Booking and tracking transitions create private `notification_events` plus one `notification_delivery_attempts` row per enabled channel. In-app delivery is immediately available to the recipient. External-channel attempts store only status, provider name, attempt timestamps, a provider message identifier when one exists, and a sanitized diagnostic. Credentials, device tokens, phone numbers, and full message bodies are not written to delivery logs.

Run one retry batch from `services/api`:

```powershell
python -m app.workers.notifications --once
```

The worker uses capped exponential retry metadata. Schedule the one-shot command with the deployment platform rather than running an unmanaged infinite loop.

## SMTP

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_ADDRESS`. In a future authorized test environment, use a local mailbox emulator or an explicitly approved test recipient through `DEMO_EMAIL_RECIPIENT`. Templates deliberately omit exact coordinates and unnecessary contact data.

## SMS in India

Configure `SMS_PROVIDER_URL` and `SMS_PROVIDER_API_KEY` only for an authorized provider. Before any non-demo use, complete sender/entity registration and applicable Indian DLT template approval, map each event to the exact approved template, record consent, enforce provider rate limits, and test delivery receipts. The current generic HTTP adapter is a configuration foundation, not a certified DLT integration.

## WhatsApp Business Platform

Configure `WHATSAPP_PROVIDER_URL`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_WEBHOOK_SECRET`, and approved template identifiers. Production activation also requires a WhatsApp Business account, approved templates, recipient opt-in, provider-specific payload mapping, and delivery-status reconciliation.

The webhook endpoint is `POST /api/v1/webhooks/whatsapp`. It validates the `X-Webhook-Signature` HMAC before accepting status updates. Never replace this with browser automation, scraping, or a personal WhatsApp account.

## Firebase Cloud Messaging

The mobile client can request notification permission after user action, register a native push token, receive foreground notifications, and deep-link to a booking. Configure `FCM_PROJECT_ID` and `FCM_SERVICE_ACCOUNT_JSON` only in a secrets manager. The server adapter intentionally fails closed because the production OAuth/service-account transport and delivery receipt handling have not been completed or tested.

Expo Go may not provide the native notification behavior required for final testing. Use a development build for platform push validation.

## Activation requirements

External delivery must remain disabled until all of the following are complete:

- state-specific wildlife operating approval and partner procedures;
- explicit, server-reviewed authorized-operation configuration outside the normal admin UI;
- provider contracts, approved templates, opt-in records, safe recipients, and credentials in a secrets manager;
- device-token encryption at rest and rotation/revocation procedures;
- provider-specific webhook verification, delivery receipt reconciliation, and failure drills;
- end-to-end tests proving no private coordinates or unnecessary personal data leave the platform.

Changing an environment variable alone is not approval to perform real rescue dispatch.
