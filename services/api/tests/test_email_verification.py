"""Signup confirmation: a new account cannot sign in until the email is confirmed."""

import pytest

from app.core.config import get_settings

pytestmark = pytest.mark.anyio

PASSWORD = "strongpass123"


@pytest.fixture
def verification_on():
    settings = get_settings()
    previous = settings.require_email_verification
    settings.require_email_verification = True
    yield
    settings.require_email_verification = previous


async def test_signup_requires_email_confirmation(client, verification_on):
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Confirm Person",
            "email": "confirm@example.com",
            "phone": "9812340001",
            "password": PASSWORD,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["email_verification_sent"] is True
    assert "access_token" not in body  # signing up does not sign you in
    code = body["dev_code"]

    blocked = await client.post(
        "/api/v1/auth/login", json={"email": "confirm@example.com", "password": PASSWORD}
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"

    wrong = await client.post(
        "/api/v1/auth/email/verify", json={"email": "confirm@example.com", "code": "000000"}
    )
    assert wrong.status_code == 400

    verified = await client.post(
        "/api/v1/auth/email/verify", json={"email": "confirm@example.com", "code": code}
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["email_verified"] is True
    assert verified.json()["access_token"]

    client.cookies.clear()
    allowed = await client.post(
        "/api/v1/auth/login", json={"email": "confirm@example.com", "password": PASSWORD}
    )
    assert allowed.status_code == 200
    assert allowed.json()["user"]["email_verified"] is True


async def test_resend_does_not_reveal_accounts(client, verification_on):
    unknown = await client.post(
        "/api/v1/auth/email/resend", json={"email": "nobody-here@example.com"}
    )
    assert unknown.status_code == 200
    assert unknown.json()["sent"] is True
    assert "dev_code" not in unknown.json()


async def test_email_otp_login_confirms_the_address(client, verification_on):
    await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Otp Confirm",
            "email": "otpconfirm@example.com",
            "phone": "9812340002",
            "password": PASSWORD,
        },
    )
    # Receiving a sign-in code proves ownership, so it also confirms the address.
    requested = await client.post(
        "/api/v1/auth/otp/request", json={"email": "otpconfirm@example.com"}
    )
    assert requested.status_code == 200
    code = requested.json()["dev_code"]
    verified = await client.post(
        "/api/v1/auth/otp/verify", json={"email": "otpconfirm@example.com", "code": code}
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["email_verified"] is True
