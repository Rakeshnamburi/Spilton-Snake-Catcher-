"""Privacy-safe notification templates, adapters, queuing, and retry processing."""

from __future__ import annotations

import hashlib
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.entities import (
    DeviceRegistration,
    NotificationDeliveryAttempt,
    NotificationEvent,
    NotificationPreference,
    NotificationTemplate,
    User,
)
from app.services.integrations import IntegrationNotConfigured

logger = logging.getLogger(__name__)
CHANNELS = ("IN_APP", "EMAIL", "SMS", "WHATSAPP", "PUSH")
EXTERNAL_CHANNELS = ("EMAIL", "SMS", "WHATSAPP", "PUSH")

TEMPLATES: dict[str, tuple[str, str]] = {
    "BOOKING_REQUESTED": (
        "Demo booking request received",
        "Demo booking {booking_reference} is pending a simulated rescuer response.",
    ),
    "BOOKING_ASSIGNED": (
        "New simulated booking assigned",
        "Demo booking {booking_reference} is ready for your simulated response.",
    ),
    "BOOKING_ACCEPTED": (
        "Demo booking accepted",
        "Demo booking {booking_reference} was accepted in simulation.",
    ),
    "BOOKING_REJECTED": (
        "Demo booking rejected",
        "Demo booking {booking_reference} was rejected in simulation. Use verified "
        "public alternatives if assistance is needed.",
    ),
    "BOOKING_EXPIRED": (
        "Demo booking expired",
        "Demo booking {booking_reference} expired without a simulated response.",
    ),
    "TRACKING_STARTED": (
        "Simulated journey started",
        "Foreground demo tracking started for booking {booking_reference} with explicit consent.",
    ),
    "RESCUER_ARRIVED": (
        "Simulated rescuer arrived",
        "The simulated journey for booking {booking_reference} was marked arrived.",
    ),
    "RESCUE_SESSION_STARTED": (
        "Simulated rescue session started",
        "Demo rescue documentation started for booking {booking_reference}.",
    ),
    "RESCUE_REPORT_SUBMITTED": (
        "Simulated rescue report submitted",
        "A demo rescue report was submitted for booking {booking_reference}.",
    ),
    "BOOKING_COMPLETED": (
        "Demo booking completed",
        "Demo booking {booking_reference} has a simulated completion report.",
    ),
    "COMPLETION_DISPUTED": (
        "Simulated completion disputed",
        "Demo booking {booking_reference} was sent for restricted coordinator review.",
    ),
    "DEMO_PAYMENT_SUCCEEDED": (
        "Demo payment recorded",
        "An illustrative payment was recorded for booking {booking_reference}; no money moved.",
    ),
    "DEMO_PAYMENT_FAILED": (
        "Demo payment simulation failed",
        "The payment simulation for booking {booking_reference} failed; no money moved.",
    ),
    "REVIEW_SUBMITTED": (
        "Demo review submitted",
        "A demo review was submitted for booking {booking_reference}.",
    ),
    "BOOKING_CANCELLED": (
        "Demo booking cancelled",
        "Demo booking {booking_reference} was cancelled.",
    ),
}


@dataclass(frozen=True)
class NotificationMessage:
    template_key: str
    recipient_reference: str
    subject: str = ""
    body: str = ""
    deep_link: str | None = None
    variables: dict[str, str] | None = None


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    status: str
    message_id: str | None
    sanitized_result: str


class ExternalNotificationAdapter:
    channel = "UNCONFIGURED"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _require_live_authorization(self) -> None:
        if self.settings.demo_mode or not self.settings.authorized_operation_enabled:
            raise IntegrationNotConfigured(
                f"{self.channel} live delivery is blocked by the server-side demo gate"
            )

    def send(self, message: NotificationMessage) -> DeliveryResult:
        del message
        raise IntegrationNotConfigured(f"{self.channel} provider is not configured")


class DemoNotificationAdapter(ExternalNotificationAdapter):
    channel = "DEMO"

    def __init__(self, channel: str, settings: Settings | None = None):
        super().__init__(settings)
        self.channel = channel

    def send(self, message: NotificationMessage) -> DeliveryResult:
        digest = hashlib.sha256(
            f"{self.channel}:{message.template_key}:{message.recipient_reference}".encode()
        ).hexdigest()[:16]
        logger.info(
            "demo_notification_recorded channel=%s template=%s",
            self.channel,
            message.template_key,
        )
        return DeliveryResult(
            provider="LOCAL_DEMO",
            status="DEMO_RECORDED",
            message_id=f"demo-{digest}",
            sanitized_result="Recorded locally; no external message was sent.",
        )


class EmailNotificationAdapter(ExternalNotificationAdapter):
    channel = "EMAIL"

    def send(self, message: NotificationMessage) -> DeliveryResult:
        self._require_live_authorization()
        settings = self.settings
        if not all(
            [
                settings.smtp_host,
                settings.smtp_username,
                settings.smtp_password,
                settings.smtp_from_address,
            ]
        ):
            raise IntegrationNotConfigured("SMTP credentials are incomplete")
        email = EmailMessage()
        email["From"] = settings.smtp_from_address
        email["To"] = message.recipient_reference
        email["Subject"] = message.subject
        email.set_content(message.body + (f"\n\n{message.deep_link}" if message.deep_link else ""))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(email)
        return DeliveryResult("SMTP", "DELIVERED", None, "Provider accepted the email.")


class _HttpTemplateAdapter(ExternalNotificationAdapter):
    provider_url_setting = ""
    token_setting = ""

    def send(self, message: NotificationMessage) -> DeliveryResult:
        self._require_live_authorization()
        url = getattr(self.settings, self.provider_url_setting)
        token = getattr(self.settings, self.token_setting)
        if not url or not token:
            raise IntegrationNotConfigured(f"{self.channel} provider credentials are incomplete")
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "recipient": message.recipient_reference,
                "template": message.template_key,
                "variables": {"safe_summary": message.body, "deep_link": message.deep_link},
            },
            timeout=10,
        )
        response.raise_for_status()
        return DeliveryResult(
            self.channel,
            "PROVIDER_ACCEPTED",
            response.headers.get("X-Message-Id"),
            "Provider accepted request.",
        )


class SmsNotificationAdapter(_HttpTemplateAdapter):
    channel = "SMS"
    provider_url_setting = "sms_provider_url"
    token_setting = "sms_provider_api_key"


class WhatsAppNotificationAdapter(_HttpTemplateAdapter):
    channel = "WHATSAPP"
    provider_url_setting = "whatsapp_provider_url"
    token_setting = "whatsapp_access_token"


class FirebaseNotificationAdapter(ExternalNotificationAdapter):
    channel = "PUSH"

    def send(self, message: NotificationMessage) -> DeliveryResult:
        self._require_live_authorization()
        if not self.settings.fcm_project_id or not self.settings.fcm_service_account_json:
            raise IntegrationNotConfigured("Firebase credentials are incomplete")
        raise IntegrationNotConfigured(
            "FCM OAuth transport requires the documented service-account worker integration"
        )


def _enabled(db: Session, user_id, channel: str) -> bool:
    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
        )
    )
    if channel == "EMAIL" and preference is None:
        return True
    return bool(preference and preference.is_enabled and preference.opted_in_at)


def ensure_templates(db: Session) -> None:
    for key, (subject, body) in TEMPLATES.items():
        for channel in CHANNELS:
            exists = db.scalar(
                select(NotificationTemplate.id).where(
                    NotificationTemplate.template_key == key,
                    NotificationTemplate.channel == channel,
                )
            )
            if exists is None:
                db.add(
                    NotificationTemplate(
                        template_key=key,
                        channel=channel,
                        subject_template=subject if channel == "EMAIL" else None,
                        body_template=body,
                        is_active=True,
                    )
                )
    # SessionLocal disables autoflush, so make lazily-created templates visible to
    # subsequent notification events in the same transaction.
    db.flush()


def create_notification_event(
    db: Session,
    *,
    recipient_id,
    booking_id,
    event_type: str,
    title: str,
    body: str,
    deduplication_key: str | None = None,
) -> NotificationEvent:
    ensure_templates(db)
    if deduplication_key:
        existing = db.scalar(
            select(NotificationEvent).where(
                NotificationEvent.deduplication_key == deduplication_key
            )
        )
        if existing:
            return existing
    settings = get_settings()
    deep_link = (
        f"{settings.public_web_url.rstrip('/')}/bookings/{booking_id}" if booking_id else None
    )
    event = NotificationEvent(
        recipient_id=recipient_id,
        booking_id=booking_id,
        event_type=event_type,
        title=title,
        body=body,
        deep_link=deep_link,
        deduplication_key=deduplication_key,
        is_demo=True,
    )
    db.add(event)
    db.flush()
    now = datetime.now(timezone.utc)
    db.add(
        NotificationDeliveryAttempt(
            notification_event_id=event.id,
            channel="IN_APP",
            provider="LOCAL_DEMO",
            status="DELIVERED",
            attempt_count=1,
            max_attempts=1,
            last_attempt_at=now,
            delivered_at=now,
            sanitized_result="Stored as a private in-app demo notification.",
        )
    )
    user = db.get(User, recipient_id)
    channel_targets: dict[str, str] = {}
    if user and _enabled(db, recipient_id, "EMAIL"):
        channel_targets["EMAIL"] = settings.demo_email_recipient or user.email
    if user and _enabled(db, recipient_id, "SMS"):
        channel_targets["SMS"] = user.phone
    if user and _enabled(db, recipient_id, "WHATSAPP"):
        channel_targets["WHATSAPP"] = user.phone
    if _enabled(db, recipient_id, "PUSH"):
        device = db.scalar(
            select(DeviceRegistration)
            .where(
                DeviceRegistration.user_id == recipient_id,
                DeviceRegistration.is_active.is_(True),
            )
            .order_by(DeviceRegistration.last_seen_at.desc())
        )
        if device:
            channel_targets["PUSH"] = device.token_value
    for channel in channel_targets:
        attempt = NotificationDeliveryAttempt(
            notification_event_id=event.id,
            channel=channel,
            provider="LOCAL_DEMO" if settings.demo_mode else "CONFIGURED_PROVIDER",
            status="PENDING",
            attempt_count=0,
            max_attempts=settings.notification_max_attempts,
            next_attempt_at=now,
            sanitized_result="Queued without storing message content in delivery logs.",
        )
        db.add(attempt)
        db.flush()
        if settings.demo_mode:
            result = DemoNotificationAdapter(channel, settings).send(
                NotificationMessage(
                    template_key=event_type,
                    recipient_reference=str(recipient_id),
                    subject=title,
                    body=body,
                    deep_link=deep_link,
                )
            )
            attempt.status = result.status
            attempt.provider = result.provider
            attempt.provider_message_id = result.message_id
            attempt.sanitized_result = result.sanitized_result
            attempt.attempt_count = 1
            attempt.last_attempt_at = now
            attempt.delivered_at = now
            attempt.next_attempt_at = None
    logger.info("notification_created event=%s booking_id=%s", event_type, booking_id)
    return event


def _adapter(channel: str, settings: Settings) -> ExternalNotificationAdapter:
    if settings.demo_mode:
        return DemoNotificationAdapter(channel, settings)
    adapter_type = {
        "EMAIL": EmailNotificationAdapter,
        "SMS": SmsNotificationAdapter,
        "WHATSAPP": WhatsAppNotificationAdapter,
        "PUSH": FirebaseNotificationAdapter,
    }[channel]
    return adapter_type(settings)


def process_due_deliveries(db: Session, *, limit: int = 100) -> int:
    now = datetime.now(timezone.utc)
    attempts = db.scalars(
        select(NotificationDeliveryAttempt)
        .where(
            NotificationDeliveryAttempt.channel.in_(EXTERNAL_CHANNELS),
            NotificationDeliveryAttempt.status.in_(("PENDING", "RETRY")),
            NotificationDeliveryAttempt.next_attempt_at <= now,
        )
        .order_by(NotificationDeliveryAttempt.next_attempt_at)
        .limit(limit)
    ).all()
    processed = 0
    for attempt in attempts:
        event = db.get(NotificationEvent, attempt.notification_event_id)
        user = db.get(User, event.recipient_id) if event else None
        if event is None or user is None:
            attempt.status = "FAILED"
            attempt.error_code = "RECIPIENT_MISSING"
            continue
        recipient = user.email if attempt.channel == "EMAIL" else user.phone
        if attempt.channel == "PUSH":
            device = db.scalar(
                select(DeviceRegistration).where(
                    DeviceRegistration.user_id == user.id,
                    DeviceRegistration.is_active.is_(True),
                )
            )
            if device is None:
                attempt.status = "FAILED"
                attempt.error_code = "DEVICE_MISSING"
                continue
            recipient = device.token_value
        attempt.attempt_count += 1
        attempt.last_attempt_at = now
        try:
            result = _adapter(attempt.channel, get_settings()).send(
                NotificationMessage(
                    template_key=event.event_type,
                    recipient_reference=recipient,
                    subject=event.title,
                    body=event.body,
                    deep_link=event.deep_link,
                )
            )
            attempt.status = result.status
            attempt.provider = result.provider
            attempt.provider_message_id = result.message_id
            attempt.sanitized_result = result.sanitized_result
            attempt.delivered_at = now
            attempt.next_attempt_at = None
        except (IntegrationNotConfigured, httpx.HTTPError, OSError, smtplib.SMTPException) as error:
            retry = attempt.attempt_count < attempt.max_attempts
            attempt.status = "RETRY" if retry else "FAILED"
            attempt.error_code = type(error).__name__[:80]
            attempt.sanitized_result = (
                "Delivery failed without logging credentials or message body."
            )
            attempt.next_attempt_at = (
                now + timedelta(minutes=2**attempt.attempt_count) if retry else None
            )
        processed += 1
    db.commit()
    return processed
