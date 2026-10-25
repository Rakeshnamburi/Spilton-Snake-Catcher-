"""Transactional email for authentication codes (OTP).

Unlike the demo-gated notification adapters, authentication email is expected to
work in this build: if SMTP is configured the code is delivered for real;
otherwise it is written to the API log so local development still works.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AuthEmailError(RuntimeError):
    """Raised when an authentication email could not be handed to SMTP."""


def send_otp_email(
    *, recipient: str, code: str, ttl_minutes: int, subject: str | None = None
) -> str:
    """Send a one-time passcode. Returns the transport used ("smtp" or "console")."""

    settings = get_settings()
    subject = subject or "Your SPILTON sign-in code"
    body = (
        f"Your SPILTON one-time code is: {code}\n\n"
        f"This code expires in {ttl_minutes} minutes. "
        "If you did not request it, you can safely ignore this email.\n\n"
        "Never share this code with anyone. SPILTON staff will never ask you for it."
    )

    if not settings.smtp_configured:
        # Development fallback: no SMTP configured, surface the code in the log.
        logger.warning(
            "auth_otp_console_delivery email=%s code=%s ttl_minutes=%s "
            "(set SMTP_* in .env to send real email)",
            recipient,
            code,
            ttl_minutes,
        )
        return "console"

    message = EmailMessage()
    message["From"] = settings.smtp_from_address
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
            client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        logger.error("auth_otp_smtp_failure recipient=%s error=%s", recipient, type(error).__name__)
        raise AuthEmailError("Could not send the sign-in email. Try again shortly.") from error
    logger.info("auth_otp_email_sent recipient=%s", recipient)
    return "smtp"
