import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_spilton.db")
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, engine
from app.main import app
from app.models.entities import Role, User
from app.services.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def database(tmp_path):
    settings = get_settings()
    previous_media_dir = settings.private_media_dir
    settings.private_media_dir = str(tmp_path / "private-media")
    rate_limiter.clear()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    settings.private_media_dir = previous_media_dir
    rate_limiter.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest.fixture
async def citizen(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test Citizen",
            "email": "citizen@example.com",
            "phone": "9876543210",
            "password": "StrongPass123!",
        },
    )
    return response.json()


@pytest.fixture
async def other_citizen(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Other Citizen",
            "email": "other@example.com",
            "phone": "9876543211",
            "password": "StrongPass123!",
        },
    )
    return response.json()


@pytest.fixture
async def admin(client):
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        user = User(
            name="Demo Admin",
            email="admin@example.com",
            phone="9876543212",
            password_hash=hash_password("StrongPass123!"),
            role=Role.ADMIN,
        )
        db.add(user)
        db.commit()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "StrongPass123!"},
    )
    return response.json()
