import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: UUID, token_version: int = 0) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "type": "access",
        "ver": token_version,
        "jti": secrets.token_urlsafe(18),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> UUID:
    return UUID(decode_access_token_claims(token)["sub"])


def decode_access_token_claims(token: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"require": ["sub", "exp", "type", "ver", "jti"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    UUID(payload["sub"])
    if not isinstance(payload.get("ver"), int) or payload["ver"] < 0:
        raise jwt.InvalidTokenError("Invalid token version")
    return payload


def keyed_digest(value: str) -> str:
    """Return a non-reversible digest suitable for persisted idempotency metadata."""

    return hmac.new(
        get_settings().jwt_secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()
