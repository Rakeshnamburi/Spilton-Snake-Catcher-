"""Issue and check email-verification codes.

Shared by the signup flow (``routes.py``) and the resend/verify endpoints
(``auth_social.py``) so both use the same hashing, expiry and attempt rules as
the login OTP.
"""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import keyed_digest
from app.models.entities import AuthOtp, User
from app.services.auth_email import AuthEmailError, send_otp_email

PURPOSE = "EMAIL_VERIFY"
SUBJECT = "Confirm your SPILTON email address"


def _generate(length: int) -> str:
    return f"{secrets.randbelow(10**length):0{length}d}"


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def issue_code(db: Session, email: str) -> tuple[str, str]:
    """Create a fresh verification code and email it. Returns (transport, code)."""

    settings = get_settings()
    address = email.strip().lower()
    code = _generate(settings.otp_length)
    now = datetime.now(timezone.utc)
    db.add(
        AuthOtp(
            email=address,
            code_hash=keyed_digest(f"verify:{address}:{code}"),
            purpose=PURPOSE,
            expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
        )
    )
    db.commit()
    try:
        transport = send_otp_email(
            recipient=address,
            code=code,
            ttl_minutes=settings.otp_ttl_minutes,
            subject=SUBJECT,
        )
    except AuthEmailError:
        raise
    return transport, code


def check_code(db: Session, email: str, code: str) -> str:
    """Validate a verification code.

    Returns ``OK``, ``NOT_FOUND``, ``EXPIRED``, ``TOO_MANY`` or ``INVALID``.
    """

    settings = get_settings()
    address = email.strip().lower()
    record = db.scalar(
        select(AuthOtp)
        .where(
            AuthOtp.email == address,
            AuthOtp.purpose == PURPOSE,
            AuthOtp.consumed_at.is_(None),
        )
        .order_by(AuthOtp.created_at.desc())
        .limit(1)
    )
    if record is None:
        return "NOT_FOUND"
    now = datetime.now(timezone.utc)
    if _as_utc(record.expires_at) < now:
        return "EXPIRED"
    if record.attempts >= settings.otp_max_attempts:
        return "TOO_MANY"
    expected = keyed_digest(f"verify:{address}:{code.strip()}")
    if not hmac.compare_digest(expected, record.code_hash):
        record.attempts += 1
        db.commit()
        return "INVALID"
    record.consumed_at = now
    db.commit()
    return "OK"


def mark_verified(db: Session, user: User) -> None:
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        db.refresh(user)
