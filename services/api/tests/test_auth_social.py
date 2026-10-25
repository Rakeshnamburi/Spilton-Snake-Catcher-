"""Tests for email-OTP and social (Google / Microsoft) sign-in."""

import urllib.parse

import pytest

from app.api import auth_social
from app.core.config import get_settings

pytestmark = pytest.mark.anyio


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


async def test_otp_login_creates_and_reuses_account(client):
    requested = await client.post(
        "/api/v1/auth/otp/request", json={"email": "otp@example.com"}
    )
    assert requested.status_code == 200
    code = requested.json()["dev_code"]

    verified = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "otp@example.com", "code": code, "name": "Otp Person"},
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["email"] == "otp@example.com"
    assert verified.json()["user"]["phone"] is None

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200


async def test_otp_wrong_code_is_rejected(client):
    await client.post("/api/v1/auth/otp/request", json={"email": "wrong@example.com"})
    response = await client.post(
        "/api/v1/auth/otp/verify", json={"email": "wrong@example.com", "code": "000000"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_INVALID"


async def test_logout_revokes_session(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Logout User",
            "email": "logout@example.com",
            "phone": "9876500000",
            "password": "StrongPass123!",
        },
    )
    csrf = client.cookies.get("spilton_csrf")
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    out = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert out.status_code == 204
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_google_web_oauth_creates_account(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "google_client_id", "cid")
    monkeypatch.setattr(settings, "google_client_secret", "secret")

    start = await client.get("/api/v1/auth/oauth/google/start?mode=web")
    assert start.status_code == 302
    state = urllib.parse.parse_qs(
        urllib.parse.urlparse(start.headers["location"]).query
    )["state"][0]

    monkeypatch.setattr(
        auth_social.httpx, "post", lambda url, **kw: _FakeResponse({"access_token": "t"})
    )
    monkeypatch.setattr(
        auth_social.httpx,
        "get",
        lambda url, **kw: _FakeResponse(
            {"sub": "uid-1", "email": "g@example.com", "name": "G User"}
        ),
    )
    callback = await client.get(
        f"/api/v1/auth/oauth/google/callback?code=abc&state={state}"
    )
    assert callback.status_code == 302
    assert "/auth/callback" in callback.headers["location"]

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "g@example.com"


async def test_microsoft_mobile_oauth_exchange(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "microsoft_client_id", "cid")
    monkeypatch.setattr(settings, "microsoft_client_secret", "secret")

    start = await client.get("/api/v1/auth/oauth/microsoft/start?mode=mobile")
    state = urllib.parse.parse_qs(
        urllib.parse.urlparse(start.headers["location"]).query
    )["state"][0]
    monkeypatch.setattr(
        auth_social.httpx, "post", lambda url, **kw: _FakeResponse({"access_token": "t"})
    )
    monkeypatch.setattr(
        auth_social.httpx,
        "get",
        lambda url, **kw: _FakeResponse(
            {"sub": "ms-1", "email": "ms@outlook.com", "name": "MS User"}
        ),
    )
    callback = await client.get(
        f"/api/v1/auth/oauth/microsoft/callback?code=abc&state={state}"
    )
    deep_link = callback.headers["location"]
    assert deep_link.startswith("spilton://auth-callback")
    exchange_code = urllib.parse.parse_qs(urllib.parse.urlparse(deep_link).query)["code"][0]

    exchanged = await client.post(
        "/api/v1/auth/oauth/exchange", json={"code": exchange_code}
    )
    assert exchanged.status_code == 200
    assert exchanged.json()["user"]["email"] == "ms@outlook.com"
    assert exchanged.json()["access_token"]


async def test_unconfigured_provider_redirects_with_error(client):
    response = await client.get("/api/v1/auth/oauth/google/start?mode=web")
    assert response.status_code == 302
    assert "error" in response.headers["location"]
