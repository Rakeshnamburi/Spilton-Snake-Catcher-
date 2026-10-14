import pytest

from app.core.security import hash_password
from app.db.seed import DEMO_ADMIN_EMAIL, DEMO_CITIZEN_EMAIL
from app.db.session import SessionLocal
from app.models.entities import Role, User
from app.schemas.api import LoginRequest

pytestmark = pytest.mark.anyio


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


async def test_documented_demo_seed_emails_pass_login_validation():
    for email in (DEMO_ADMIN_EMAIL, DEMO_CITIZEN_EMAIL):
        assert LoginRequest(email=email, password="ChangeThisDemo123!").email == email


async def test_registration_cannot_self_assign_role(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "User",
            "email": "user@example.com",
            "phone": "9876543211",
            "password": "StrongPass123!",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "CITIZEN"


async def test_registration_rejects_whitespace_only_name(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "  ",
            "email": "blank-name@example.com",
            "phone": "9876543299",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_login_and_profile(client, citizen):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "citizen@example.com", "password": "StrongPass123!"}
    )
    token = response.json()["access_token"]
    assert (
        await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 200


async def test_demo_incident_requires_auth_and_is_private(client, citizen):
    payload = {
        "reporter_name": "Test Citizen",
        "contact_phone": "9876543210",
        "state": "Kerala",
        "district": "Ernakulam",
        "city": "Kochi",
        "description": "Snake observed from a safe distance near the gate.",
        "urgency": "STANDARD",
        "consent": True,
    }
    client.cookies.clear()
    assert (await client.post("/api/v1/incidents", json=payload)).status_code == 401
    token = citizen["access_token"]
    created = await client.post(
        "/api/v1/incidents", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert created.status_code == 201 and created.json()["is_demo"] is True


async def test_admin_role_protection(client, citizen):
    assert (
        await client.get(
            "/api/v1/admin/overview", headers={"Authorization": f"Bearer {citizen['access_token']}"}
        )
    ).status_code == 403
    with SessionLocal() as db:
        admin = User(
            name="Admin",
            email="admin@example.com",
            phone="9876543212",
            password_hash=hash_password("StrongPass123!"),
            role=Role.ADMIN,
        )
        db.add(admin)
        db.commit()
    login = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "StrongPass123!"}
    )
    assert (
        await client.get(
            "/api/v1/admin/overview",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
    ).status_code == 200
