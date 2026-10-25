"""Email OTP and social (Google / Microsoft) sign-in endpoints.

These extend the password flow in ``app.api.routes``. They are intentionally
self-contained and reuse the shared session-cookie and rate-limit helpers so
web (cookie) and mobile (bearer token) clients behave identically.
"""

from __future__ import annotations

import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
import jwt
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes import api_error, enforce_rate_limit, set_session_cookie
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, keyed_digest
from app.db.session import get_db
from app.models.entities import AuditLog, AuthOtp, OAuthIdentity, Role, User
from app.schemas.api import (
    AuthProvidersResponse,
    LoginResponse,
    OAuthExchangeBody,
    OtpRequestBody,
    OtpVerifyBody,
    PasswordForgotBody,
    PasswordResetBody,
)
from app.services.auth_email import AuthEmailError, send_otp_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "microsoft": {
        "authorize": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "userinfo": "https://graph.microsoft.com/oidc/userinfo",
        "scope": "openid email profile User.Read",
    },
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _as_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo; treat stored timestamps as UTC for comparisons."""

    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _provider_credentials(provider: str) -> tuple[str, str]:
    settings = get_settings()
    if provider == "google":
        return settings.google_client_id or "", settings.google_client_secret or ""
    if provider == "microsoft":
        return settings.microsoft_client_id or "", settings.microsoft_client_secret or ""
    raise api_error(404, "UNKNOWN_PROVIDER", "Unknown sign-in provider")


def _callback_url(provider: str) -> str:
    base = get_settings().api_public_url.rstrip("/")
    return f"{base}/api/v1/auth/oauth/{provider}/callback"


def _sign_state(provider: str, mode: str, return_to: str | None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "type": "oauth_state",
        "provider": provider,
        "mode": mode,
        "return_to": return_to or "",
        "nonce": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=settings.oauth_state_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _verify_state(state: str, provider: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise api_error(400, "INVALID_OAUTH_STATE", "Sign-in link expired or invalid") from None
    if payload.get("type") != "oauth_state" or payload.get("provider") != provider:
        raise api_error(400, "INVALID_OAUTH_STATE", "Sign-in link expired or invalid")
    return payload


def _issue_session(db: Session, response: Response | None, user: User) -> LoginResponse:
    token = create_access_token(user.id, user.token_version)
    csrf = set_session_cookie(response, token) if response is not None else None
    return LoginResponse(user=user, access_token=token, csrf_token=csrf)


def _redirect_after_auth(
    mode: str, payload: dict, *, status: str, reason: str = ""
) -> RedirectResponse:
    settings = get_settings()
    if mode == "mobile":
        query = urlencode({"status": status, **({"reason": reason} if reason else {})})
        target = f"{settings.mobile_app_scheme}://auth-callback?{query}"
        return RedirectResponse(target, status_code=302)
    target = f"{settings.web_app_url.rstrip('/')}/auth/callback"
    query = urlencode({"status": status, **({"reason": reason} if reason else {})})
    return RedirectResponse(f"{target}?{query}", status_code=302)


def _exchange_jwt(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "type": "oauth_exchange",
            "sub": str(user.id),
            "ver": user.token_version,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def _generate_otp(length: int) -> str:
    upper = 10**length
    return str(secrets.randbelow(upper)).zfill(length)


def _find_or_create_user(
    db: Session, *, email: str, name: str | None, phone: str | None, password: str | None
) -> tuple[User, bool]:
    """Return (user, created). Never overwrites an existing account's details."""

    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user, False
    user = User(
        name=(name or email.split("@")[0])[:120],
        email=email,
        phone=phone,
        password_hash=hash_password(password) if password else None,
        role=Role.CITIZEN,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(User).where(User.email == email))
        if existing is None:
            raise
        return existing, False
    db.refresh(user)
    return user, True


# --------------------------------------------------------------------------- #
# provider discovery
# --------------------------------------------------------------------------- #
@router.get("/providers", response_model=AuthProvidersResponse)
def auth_providers() -> AuthProvidersResponse:
    settings = get_settings()
    return AuthProvidersResponse(
        password=True,
        email_otp=True,
        google=bool(settings.google_client_id and settings.google_client_secret),
        microsoft=bool(settings.microsoft_client_id and settings.microsoft_client_secret),
    )


# --------------------------------------------------------------------------- #
# email OTP
# --------------------------------------------------------------------------- #
@router.post("/otp/request")
def otp_request(payload: OtpRequestBody, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    email = payload.email.strip().lower()
    enforce_rate_limit(f"otp-email:{email}", limit=5, window_seconds=300)
    enforce_rate_limit(f"otp-ip:{_client_ip(request)}", limit=20, window_seconds=300)

    now = datetime.now(timezone.utc)
    recent = db.scalar(
        select(AuthOtp)
        .where(AuthOtp.email == email)
        .order_by(AuthOtp.created_at.desc())
        .limit(1)
    )
    if (
        recent is not None
        and (now - _as_utc(recent.created_at)).total_seconds()
        < settings.otp_resend_cooldown_seconds
    ):
        raise api_error(429, "OTP_COOLDOWN", "Please wait before requesting another code.")

    code = _generate_otp(settings.otp_length)
    db.add(
        AuthOtp(
            email=email,
            code_hash=keyed_digest(f"{email}:{code}"),
            purpose="LOGIN",
            expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
        )
    )
    db.commit()

    try:
        transport = send_otp_email(
            recipient=email, code=code, ttl_minutes=settings.otp_ttl_minutes
        )
    except AuthEmailError as error:
        raise api_error(502, "EMAIL_SEND_FAILED", str(error)) from error

    body = {
        "sent": True,
        "transport": transport,
        "expires_in_seconds": settings.otp_ttl_minutes * 60,
    }
    # In development with no SMTP, surface the code so local testing is possible.
    if transport == "console" and settings.environment.lower() == "development":
        body["dev_code"] = code
    return body


@router.post("/otp/verify", response_model=LoginResponse)
def otp_verify(
    payload: OtpVerifyBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    email = payload.email.strip().lower()
    enforce_rate_limit(f"otp-verify:{email}", limit=10, window_seconds=300)

    record = db.scalar(
        select(AuthOtp)
        .where(AuthOtp.email == email, AuthOtp.consumed_at.is_(None))
        .order_by(AuthOtp.created_at.desc())
        .limit(1)
    )
    if record is None:
        raise api_error(400, "OTP_NOT_FOUND", "Request a new code to continue.")
    now = datetime.now(timezone.utc)
    if _as_utc(record.expires_at) < now:
        raise api_error(400, "OTP_EXPIRED", "That code has expired. Request a new one.")
    if record.attempts >= settings.otp_max_attempts:
        raise api_error(429, "OTP_TOO_MANY_ATTEMPTS", "Too many attempts. Request a new code.")

    expected = keyed_digest(f"{email}:{payload.code.strip()}")
    if not hmac.compare_digest(expected, record.code_hash):
        record.attempts += 1
        db.commit()
        raise api_error(400, "OTP_INVALID", "That code is incorrect.")

    record.consumed_at = now
    user, _created = _find_or_create_user(
        db, email=email, name=payload.name, phone=payload.phone, password=None
    )
    db.commit()
    db.refresh(user)
    if not user.is_active:
        raise api_error(403, "ACCOUNT_DISABLED", "This account is disabled.")
    return _issue_session(db, response, user)


# --------------------------------------------------------------------------- #
# Password reset (forgot password)
# --------------------------------------------------------------------------- #
@router.post("/password/forgot")
def password_forgot(
    payload: PasswordForgotBody, request: Request, db: Session = Depends(get_db)
):
    """Email a password-reset code.

    Always answers the same way so the endpoint cannot be used to discover which
    addresses have accounts.
    """

    settings = get_settings()
    email = payload.email.strip().lower()
    enforce_rate_limit(f"pw-forgot-email:{email}", limit=5, window_seconds=900)
    enforce_rate_limit(f"pw-forgot-ip:{_client_ip(request)}", limit=20, window_seconds=900)

    result: dict = {"sent": True, "expires_in_seconds": settings.otp_ttl_minutes * 60}
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        return result

    now = datetime.now(timezone.utc)
    code = _generate_otp(settings.otp_length)
    db.add(
        AuthOtp(
            email=email,
            code_hash=keyed_digest(f"reset:{email}:{code}"),
            purpose="PASSWORD_RESET",
            expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
        )
    )
    db.commit()

    try:
        transport = send_otp_email(
            recipient=email,
            code=code,
            ttl_minutes=settings.otp_ttl_minutes,
            subject="Reset your SPILTON password",
        )
    except AuthEmailError as error:
        raise api_error(502, "EMAIL_SEND_FAILED", str(error)) from error

    if transport == "console" and settings.environment.lower() == "development":
        result["dev_code"] = code
    return result


@router.post("/password/reset")
def password_reset(
    payload: PasswordResetBody, request: Request, db: Session = Depends(get_db)
):
    settings = get_settings()
    email = payload.email.strip().lower()
    enforce_rate_limit(f"pw-reset:{email}", limit=10, window_seconds=900)

    record = db.scalar(
        select(AuthOtp)
        .where(
            AuthOtp.email == email,
            AuthOtp.purpose == "PASSWORD_RESET",
            AuthOtp.consumed_at.is_(None),
        )
        .order_by(AuthOtp.created_at.desc())
        .limit(1)
    )
    if record is None:
        raise api_error(400, "RESET_CODE_NOT_FOUND", "Request a new reset code to continue.")
    now = datetime.now(timezone.utc)
    if _as_utc(record.expires_at) < now:
        raise api_error(400, "RESET_CODE_EXPIRED", "That code has expired. Request a new one.")
    if record.attempts >= settings.otp_max_attempts:
        raise api_error(429, "RESET_TOO_MANY_ATTEMPTS", "Too many attempts. Request a new code.")

    expected = keyed_digest(f"reset:{email}:{payload.code.strip()}")
    if not hmac.compare_digest(expected, record.code_hash):
        record.attempts += 1
        db.commit()
        raise api_error(400, "RESET_CODE_INVALID", "That code is incorrect.")

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise api_error(400, "RESET_CODE_INVALID", "That code is incorrect.")

    record.consumed_at = now
    user.password_hash = hash_password(payload.new_password)
    # Changing the password signs the account out everywhere.
    user.token_version += 1
    db.add(
        AuditLog(
            actor_id=user.id,
            action="AUTH_PASSWORD_RESET",
            entity_type="user",
            entity_id=str(user.id),
        )
    )
    db.commit()
    return {"reset": True}


# --------------------------------------------------------------------------- #
# OAuth (Google / Microsoft)
# --------------------------------------------------------------------------- #
@router.get("/oauth/{provider}/start")
def oauth_start(
    provider: str,
    mode: str = Query(default="web", pattern="^(web|mobile)$"),
    return_to: str | None = Query(default=None),
):
    settings = get_settings()
    client_id, _secret = _provider_credentials(provider)
    if not client_id:
        return _redirect_after_auth(mode, {}, status="error", reason="provider_not_configured")

    config = PROVIDERS[provider]
    tenant = settings.microsoft_tenant or "common"
    authorize = config["authorize"].format(tenant=tenant)
    params = {
        "client_id": client_id,
        "redirect_uri": _callback_url(provider),
        "response_type": "code",
        "scope": config["scope"],
        "state": _sign_state(provider, mode, return_to),
    }
    if provider == "google":
        params["access_type"] = "online"
        params["prompt"] = "select_account"
    return RedirectResponse(f"{authorize}?{urlencode(params)}", status_code=302)


@router.get("/oauth/{provider}/callback")
def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if provider not in PROVIDERS:
        raise api_error(404, "UNKNOWN_PROVIDER", "Unknown sign-in provider")
    if not state:
        raise api_error(400, "INVALID_OAUTH_STATE", "Missing sign-in state")

    payload = _verify_state(state, provider)
    mode = payload.get("mode", "web")
    if error or not code:
        return _redirect_after_auth(mode, payload, status="error", reason=error or "cancelled")

    client_id, client_secret = _provider_credentials(provider)
    if not client_id or not client_secret:
        return _redirect_after_auth(mode, payload, status="error", reason="provider_not_configured")

    config = PROVIDERS[provider]
    tenant = settings.microsoft_tenant or "common"
    token_url = config["token"].format(tenant=tenant)
    try:
        token_response = httpx.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _callback_url(provider),
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        token_response.raise_for_status()
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("missing access_token")
        userinfo_response = httpx.get(
            config["userinfo"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        userinfo_response.raise_for_status()
        profile = userinfo_response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "oauth_profile_fetch_failed provider=%s error=%s", provider, type(exc).__name__
        )
        return _redirect_after_auth(mode, payload, status="error", reason="provider_error")

    provider_user_id = str(
        profile.get("sub") or profile.get("id") or profile.get("oid") or ""
    ).strip()
    email = (profile.get("email") or profile.get("preferred_username") or "").strip().lower()
    name = profile.get("name") or profile.get("given_name")
    if not provider_user_id or not email:
        return _redirect_after_auth(mode, payload, status="error", reason="email_unavailable")

    identity = db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == provider,
            OAuthIdentity.provider_user_id == provider_user_id,
        )
    )
    if identity is not None:
        user = db.get(User, identity.user_id)
    else:
        user, _created = _find_or_create_user(db, email=email, name=name, phone=None, password=None)
        db.add(
            OAuthIdentity(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                email=email,
                display_name=name,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            identity = db.scalar(
                select(OAuthIdentity).where(
                    OAuthIdentity.provider == provider,
                    OAuthIdentity.provider_user_id == provider_user_id,
                )
            )
            user = db.get(User, identity.user_id) if identity else user

    if user is None or not user.is_active:
        return _redirect_after_auth(mode, payload, status="error", reason="account_disabled")

    if mode == "mobile":
        return RedirectResponse(
            f"{settings.mobile_app_scheme}://auth-callback?"
            f"{urlencode({'status': 'ok', 'code': _exchange_jwt(user)})}",
            status_code=302,
        )

    # Web: set the session cookie on the redirect itself so it is not lost.
    return_to = payload.get("return_to") or "/track"
    target = f"{settings.web_app_url.rstrip('/')}/auth/callback"
    redirect = RedirectResponse(
        f"{target}?{urlencode({'status': 'ok', 'return_to': return_to})}", status_code=302
    )
    set_session_cookie(redirect, create_access_token(user.id, user.token_version))
    return redirect


@router.post("/oauth/exchange", response_model=LoginResponse)
def oauth_exchange(payload: OAuthExchangeBody, db: Session = Depends(get_db)):
    """Mobile clients swap the one-time deep-link code for a bearer session."""

    settings = get_settings()
    try:
        claims = jwt.decode(payload.code, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise api_error(400, "INVALID_EXCHANGE_CODE", "Sign-in code expired or invalid") from None
    if claims.get("type") != "oauth_exchange":
        raise api_error(400, "INVALID_EXCHANGE_CODE", "Sign-in code expired or invalid")
    user = db.get(User, UUID(claims["sub"]))
    if user is None or not user.is_active or claims.get("ver") != user.token_version:
        raise api_error(401, "SESSION_EXPIRED", "Sign-in session is no longer valid")
    return _issue_session(db, None, user)
