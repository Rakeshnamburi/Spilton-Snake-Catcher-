"""Notification provider contracts.

Day 3 sends only local in-app demo events. External adapters deliberately fail closed
until credentials, templates, opt-in, and delivery verification exist.
"""

from dataclasses import dataclass

from app.services.integrations import IntegrationNotConfigured


@dataclass(frozen=True)
class NotificationMessage:
    template_key: str
    recipient_reference: str
    variables: dict[str, str]


class ExternalNotificationAdapter:
    channel = "UNCONFIGURED"

    def send(self, message: NotificationMessage) -> None:
        del message
        raise IntegrationNotConfigured(
            f"{self.channel} delivery is disabled; Day 3 permits local in-app "
            "demo notifications only"
        )


class EmailNotificationAdapter(ExternalNotificationAdapter):
    channel = "EMAIL"


class SmsNotificationAdapter(ExternalNotificationAdapter):
    channel = "SMS"


class WhatsAppNotificationAdapter(ExternalNotificationAdapter):
    channel = "WHATSAPP"


class FirebaseNotificationAdapter(ExternalNotificationAdapter):
    channel = "PUSH"
