"""End-to-end test of the multi-step rescuer approval flow.

A new catcher stays invisible until ALL of these happen, in this order:
  1. organization verified by an admin
  2. at least one private authorization document uploaded
  3. rescuer moved PENDING_VERIFICATION -> UNDER_REVIEW
  4. rescuer moved UNDER_REVIEW -> VERIFIED (this also grants the RESCUER role)
  5. the catcher sets themselves AVAILABLE
"""

import io
from datetime import date, timedelta

import pytest
from PIL import Image

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.entities import RescuerProfile, User
from tests.test_day3_marketplace import _directory, _user

pytestmark = pytest.mark.anyio

PASSWORD = "StrongPass123!"


def _token(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _application() -> dict:
    return {
        "public_display_name": "Approval Flow Catcher",
        "state_code": "TEST-S",
        "district_code": "TEST-D",
        "organization_name": "Approval Flow Org",
        "years_experience": 3,
        "languages": ["English"],
        "training_details": "Synthetic training record for the approval flow test.",
        "authorization_reference": "APPROVAL-TEST",
        "issuing_authority": "Synthetic Test Authority",
        "authorization_issue_date": str(date.today() - timedelta(days=30)),
        "authorization_expiry": str(date.today() + timedelta(days=365)),
        "service_area_description": "Synthetic approval-flow coverage area",
        "service_radius_km": 30,
        "latitude": 17.42,
        "longitude": 78.49,
        "operating_hours": {},
        "acknowledgement": True,
    }


async def test_catcher_is_invisible_until_fully_approved(client):
    with SessionLocal() as db:
        _directory(db)
        applicant = _user(db, email="approval.catcher@example.com")
        admin = _user(db, email="approval.admin@example.com")
        admin.role = admin.role.__class__.ADMIN
        db.commit()
        applicant_id = applicant.id
        admin_id = admin.id

    applicant_headers = _token(applicant_id)
    admin_headers = _token(admin_id)

    created = await client.post(
        "/api/v1/rescuers/onboarding", headers=applicant_headers, json=_application()
    )
    assert created.status_code == 201
    assert created.json()["verification_status"] == "PENDING_VERIFICATION"

    # Not visible yet.
    nearby = await client.get(
        "/api/v1/rescuers/nearby?latitude=17.42&longitude=78.49&radius_km=20&state_code=TEST-S"
    )
    assert nearby.json()["total"] == 0

    with SessionLocal() as db:
        profile = db.query(RescuerProfile).filter_by(user_id=applicant_id).one()
        profile_id = str(profile.id)
        organization_id = str(profile.organization_id)

    # Organization must be verified first.
    org = await client.patch(
        f"/api/v1/admin/organizations/{organization_id}/verification",
        headers=admin_headers,
        json={"status": "VERIFIED", "note": "Synthetic organization check"},
    )
    assert org.status_code == 200

    # Evidence is required before VERIFIED.
    review = await client.patch(
        f"/api/v1/admin/rescuers/{profile_id}/verification",
        headers=admin_headers,
        json={"status": "UNDER_REVIEW", "note": "Documents received"},
    )
    assert review.status_code == 200

    blocked = await client.patch(
        f"/api/v1/admin/rescuers/{profile_id}/verification",
        headers=admin_headers,
        json={"status": "VERIFIED", "note": "Trying without evidence"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "EVIDENCE_REQUIRED"

    buffer = io.BytesIO()
    Image.new("RGB", (60, 60), "green").save(buffer, format="PNG")
    upload = await client.post(
        "/api/v1/rescuers/onboarding/documents",
        headers=applicant_headers,
        files={"file": ("authorization.png", buffer.getvalue(), "image/png")},
    )
    assert upload.status_code == 201

    verified = await client.patch(
        f"/api/v1/admin/rescuers/{profile_id}/verification",
        headers=admin_headers,
        json={"status": "VERIFIED", "note": "Approved after review"},
    )
    assert verified.status_code == 200
    assert verified.json()["verification_status"] == "VERIFIED"

    # The RESCUER role is granted by the approval itself.
    with SessionLocal() as db:
        assert db.get(User, applicant_id).role.value == "RESCUER"

    # Still offline until the catcher goes available.
    await client.patch(
        "/api/v1/rescuers/me/availability", headers=applicant_headers, json={"status": "AVAILABLE"}
    )
    nearby = await client.get(
        "/api/v1/rescuers/nearby?latitude=17.42&longitude=78.49&radius_km=20&state_code=TEST-S"
    )
    assert nearby.json()["total"] == 1
    assert nearby.json()["items"][0]["display_name"] == "Approval Flow Catcher"
