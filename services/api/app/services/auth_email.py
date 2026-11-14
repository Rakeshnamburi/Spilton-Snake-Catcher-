"""Transactional email for authentication codes (OTP / email verification).

Transport order:

1. **Brevo** — when ``BREVO_API_KEY`` is set the code is delivered through
   Brevo's HTTP API. This works on hosts that block outbound SMTP (Render's free
   plan blocks it), so it is the recommended production path.
2. **SMTP** — when the ``SMTP_*`` values are set.
3. **Console** — development fallback: the code is written to the API log and
   (in development only) returned as ``dev_code`` so local testing is possible.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


class AuthEmailError(RuntimeError):
    """Raised when an authentication email could not be handed to a provider."""


def _body(code: str, ttl_minutes: int) -> str:
    return (
        f"Your SPILTON one-time code is: {code}\n\n"
        f"This code expires in {ttl_minutes} minutes. "
        "If you did not request it, you can safely ignore this email.\n\n"
        "Never share this code with anyone. SPILTON staff will never ask you for it."
    )


def _send_brevo(
    *, recipient: str, subject: str, text: str, reply_to: str | None = None
) -> None:
    settings = get_settings()
    payload: dict = {
        "sender": {
            "email": settings.brevo_sender_email,
            "name": settings.brevo_sender_name,
        },
        "to": [{"email": recipient}],
        "subject": subject,
        "textContent": text,
        "htmlContent": "<p>" + text.replace("\n\n", "</p><p>").replace("\n", "<br/>") + "</p>",
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    try:
        response = httpx.post(
            BREVO_ENDPOINT,
            headers={
                "api-key": settings.brevo_api_key or "",
                "content-type": "application/json",
                "accept": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:200] if error.response is not None else ""
        logger.error("auth_email_brevo_rejected status=%s %s", error.response.status_code, detail)
        raise AuthEmailError("Could not send the email. Try again shortly.") from error
    except httpx.HTTPError as error:
        logger.error("auth_email_brevo_failure error=%s", type(error).__name__)
        raise AuthEmailError("Could not send the email. Try again shortly.") from error


def _send_smtp(
    *, recipient: str, subject: str, text: str, reply_to: str | None = None
) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from_address
    message["To"] = recipient
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(text)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
            client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        logger.error(
            "auth_email_smtp_failure recipient=%s error=%s", recipient, type(error).__name__
        )
        raise AuthEmailError("Could not send the email. Try again shortly.") from error


def send_otp_email(
    *, recipient: str, code: str, ttl_minutes: int, subject: str | None = None
) -> str:
    """Send a one-time passcode. Returns the transport used."""

    settings = get_settings()
    subject = subject or "Your SPILTON sign-in code"
    text = _body(code, ttl_minutes)

    if settings.brevo_configured:
        _send_brevo(recipient=recipient, subject=subject, text=text)
        logger.info("auth_email_sent transport=brevo recipient=%s", recipient)
        return "brevo"

    if settings.smtp_configured:
        _send_smtp(recipient=recipient, subject=subject, text=text)
        logger.info("auth_email_sent transport=smtp recipient=%s", recipient)
        return "smtp"

    logger.warning(
        "auth_otp_console_delivery email=%s code=%s ttl_minutes=%s "
        "(set BREVO_API_KEY or SMTP_* in .env to send real email)",
        recipient,
        code,
        ttl_minutes,
    )
    return "console"


def send_system_email(
    *, recipient: str, subject: str, text: str, reply_to: str | None = None
) -> str:
    """Send a non-authentication email (for example a website enquiry).

    Returns the transport used. With nothing configured the message is logged and
    "console" is returned, so a development machine still shows what was sent.
    """

    settings = get_settings()
    if settings.brevo_configured:
        _send_brevo(recipient=recipient, subject=subject, text=text, reply_to=reply_to)
        logger.info("system_email_sent transport=brevo recipient=%s", recipient)
        return "brevo"
    if settings.smtp_configured:
        _send_smtp(recipient=recipient, subject=subject, text=text, reply_to=reply_to)
        logger.info("system_email_sent transport=smtp recipient=%s", recipient)
        return "smtp"
    logger.warning(
        "system_email_console_delivery recipient=%s subject=%s body=%s "
        "(set BREVO_API_KEY or SMTP_* in .env to send real email)",
        recipient,
        subject,
        text,
    )
    return "console"
