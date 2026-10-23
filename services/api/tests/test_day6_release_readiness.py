import asyncio
import time

import pytest
from pydantic import ValidationError

from app.core.config import Settings

pytestmark = pytest.mark.anyio


def bearer(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def test_production_configuration_fails_closed():
    with pytest.raises(ValidationError):
        Settings(environment="production")
    secure = Settings(
        environment="production",
        jwt_secret="a-production-secret-that-is-longer-than-32-characters",
        cookie_secure=True,
        web_origins="https://demo.spilton.example",
    )
    assert secure.demo_mode is True
    assert secure.authorized_operation_enabled is False
    assert secure.payments_enabled is False


async def test_health_readiness_and_request_security_headers(client):
    request_id = "day6-test-request-001"
    health = await client.get("/health", headers={"X-Request-ID": request_id})
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert health.headers["x-request-id"] == request_id
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"

    ready = await client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "database": "ok", "mode": "DEMO"}


async def test_profile_privacy_requests_and_session_rotation(client, citizen):
    original_headers = bearer(citizen)
    updated = await client.patch(
        "/api/v1/auth/me",
        headers=original_headers,
        json={
            "name": "Updated Citizen",
            "email": "updated-citizen@example.com",
            "phone": "9876543299",
            "current_password": "StrongPass123!",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Citizen"

    created = await client.post(
        "/api/v1/auth/account-requests",
        headers=original_headers,
        json={"request_type": "EXPORT", "reason": "Portability test"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "REQUESTED"
    replay = await client.post(
        "/api/v1/auth/account-requests",
        headers=original_headers,
        json={"request_type": "EXPORT", "reason": "Duplicate request"},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == created.json()["id"]
    listed = await client.get("/api/v1/auth/account-requests", headers=original_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    rotated = await client.post("/api/v1/auth/refresh", headers=original_headers)
    assert rotated.status_code == 200
    rotated_session = rotated.json()
    assert rotated_session["access_token"] != citizen["access_token"]
    assert (await client.get("/api/v1/auth/me", headers=original_headers)).status_code == 401
    rotated_headers = bearer(rotated_session)
    assert (await client.get("/api/v1/auth/me", headers=rotated_headers)).status_code == 200

    logged_out = await client.post("/api/v1/auth/logout", headers=rotated_headers)
    assert logged_out.status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=rotated_headers)).status_code == 401


async def test_admin_operations_health_is_protected(client, citizen, admin):
    denied = await client.get("/api/v1/admin/operations/health", headers=bearer(citizen))
    assert denied.status_code == 403
    response = await client.get("/api/v1/admin/operations/health", headers=bearer(admin))
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "DEMO"
    assert data["live_dispatch_enabled"] is False
    assert data["real_payments_enabled"] is False

    created = await client.post(
        "/api/v1/auth/account-requests",
        headers=bearer(citizen),
        json={"request_type": "DELETION", "reason": "Day 6 admin workflow test"},
    )
    assert created.status_code == 201
    listing = await client.get("/api/v1/admin/account-requests", headers=bearer(admin))
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    updated = await client.patch(
        f"/api/v1/admin/account-requests/{created.json()['id']}",
        headers=bearer(admin),
        json={"status": "UNDER_REVIEW", "note": "Identity review started."},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "UNDER_REVIEW"


async def test_moderate_authenticated_read_smoke(client, citizen):
    """Catch obvious read-path regressions; this is not a production capacity benchmark."""

    paths = [
        "/health",
        "/api/v1/status",
        "/api/v1/locations/states",
        "/api/v1/bookings/mine",
        "/api/v1/notifications",
    ]
    started = time.perf_counter()
    responses = await asyncio.gather(
        *(client.get(path, headers=bearer(citizen)) for _ in range(8) for path in paths)
    )
    elapsed = time.perf_counter() - started
    assert all(response.status_code == 200 for response in responses)
    assert elapsed < 60
    print(f"day6_read_smoke requests={len(responses)} elapsed_seconds={elapsed:.3f}")
