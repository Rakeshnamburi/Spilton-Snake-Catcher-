from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.entities import (
    AvailabilityStatus,
    Booking,
    BookingFinancialSnapshot,
    District,
    LocationImportJob,
    NotificationEvent,
    Organization,
    RescuerDocument,
    RescuerProfile,
    Role,
    State,
    User,
    VerificationStatus,
)
from app.services.integrations import IntegrationNotConfigured
from app.services.lgd_import import LGDImportError, import_lgd_file
from app.services.marketplace import financial_values
from app.services.notifications import EmailNotificationAdapter, NotificationMessage

pytestmark = pytest.mark.anyio


def _token(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _directory(db):
    state = State(
        lgd_code="TEST-S",
        name="Synthetic Test State",
        is_union_territory=False,
        is_active=True,
        source_version="synthetic-test-only",
    )
    district = District(
        lgd_code="TEST-D",
        state_code="TEST-S",
        name="Synthetic Test District",
        is_active=True,
        source_version="synthetic-test-only",
    )
    db.add(state)
    db.flush()
    db.add(district)


def _user(db, *, email: str, role: Role = Role.CITIZEN) -> User:
    user = User(
        name=email.split("@", 1)[0].replace(".", " ").title(),
        email=email,
        phone=f"90000{abs(hash(email)) % 100000:05d}",
        password_hash="not-used-by-token-tests",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _rescuer(
    db,
    *,
    email: str,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    expiry: date | None = None,
    latitude: float = 17.41,
    longitude: float = 78.48,
) -> tuple[User, RescuerProfile]:
    user = _user(db, email=email, role=Role.RESCUER)
    organization = Organization(
        name=f"Fictional Demo Organization {email}",
        state="Synthetic Test State",
        district="Synthetic Test District",
        organization_type="SYNTHETIC_TEST",
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(organization)
    db.flush()
    profile = RescuerProfile(
        user_id=user.id,
        organization_id=organization.id,
        verification_status=status,
        public_display_name="Fictional Demo Rescuer",
        state_code="TEST-S",
        district_code="TEST-D",
        organization_name=organization.name,
        years_experience=7,
        languages=["English", "Telugu"],
        training_details="Synthetic training record used only by the automated test suite.",
        authorization_reference="SYNTHETIC-TEST-ONLY",
        issuing_authority="Synthetic Test Authority",
        authorization_issue_date=date.today() - timedelta(days=30),
        authorization_expiry=expiry or date.today() + timedelta(days=365),
        service_area_description="Synthetic test district only",
        service_radius_km=50,
        latitude=latitude,
        longitude=longitude,
        availability=AvailabilityStatus.AVAILABLE,
        last_seen_at=datetime.now(timezone.utc),
        availability_updated_at=datetime.now(timezone.utc),
        average_rating=Decimal("0.00"),
        review_count=0,
        completed_service_count=0,
        is_demo=True,
    )
    db.add(profile)
    db.flush()
    return user, profile


def _booking_payload(rescuer_id, *, manual: bool = False) -> dict:
    payload = {
        "rescuer_id": str(rescuer_id),
        "state_code": "TEST-S",
        "district_code": "TEST-D",
        "customer_notes": "Snake visible from a safe distance near the outside gate.",
        "confirm_demo_and_safety": True,
    }
    if manual:
        payload["manual_address"] = "Synthetic manual address for automated testing"
    else:
        payload.update({"latitude": 17.42, "longitude": 78.49, "location_accuracy": 18})
    return payload


def test_official_style_lgd_import_is_idempotent_and_rejects_invalid_hierarchy(tmp_path):
    state_file = tmp_path / "states.csv"
    state_file.write_text(
        "State Code,State Name (In English),State or UT,Is Active\n"
        "TEST-S,Synthetic Test State,State,Yes\n",
        encoding="utf-8",
    )
    district_file = tmp_path / "districts.csv"
    district_file.write_text(
        "District Code,District Name (In English),State Code,Is Active\n"
        "TEST-D,Synthetic Test District,TEST-S,Yes\n",
        encoding="utf-8",
    )
    invalid_file = tmp_path / "invalid-districts.csv"
    invalid_file.write_text(
        "District Code,District Name (In English),State Code\n"
        "BROKEN-D,Broken Synthetic District,UNKNOWN-S\n",
        encoding="utf-8",
    )
    with SessionLocal() as db:
        first = import_lgd_file(
            db,
            entity_type="states",
            path=state_file,
            source_version="synthetic-test-2026-10-13",
        )
        second = import_lgd_file(
            db,
            entity_type="states",
            path=state_file,
            source_version="synthetic-test-2026-10-13",
        )
        district = import_lgd_file(
            db,
            entity_type="districts",
            path=district_file,
            source_version="synthetic-test-2026-10-13",
        )
        assert first.rows_inserted == 1
        assert second.rows_skipped == 1
        assert district.rows_inserted == 1
        with pytest.raises(LGDImportError, match="Unknown parent"):
            import_lgd_file(
                db,
                entity_type="districts",
                path=invalid_file,
                source_version="synthetic-test-2026-10-13",
            )
        assert db.scalar(select(func.count()).select_from(District)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(LocationImportJob)
                .where(LocationImportJob.status == "FAILED")
            )
            == 1
        )


async def test_location_apis_return_only_imported_hierarchy(client):
    with SessionLocal() as db:
        _directory(db)
        db.commit()
    states = await client.get("/api/v1/locations/states")
    districts = await client.get("/api/v1/locations/districts?state_code=TEST-S")
    assert states.status_code == 200 and states.json()["items"][0]["lgd_code"] == "TEST-S"
    assert districts.status_code == 200
    assert districts.json()["items"][0]["lgd_code"] == "TEST-D"
    assert (await client.get("/api/v1/locations/districts?state_code=UNKNOWN")).json()["total"] == 0


async def test_rescuer_onboarding_never_self_verifies_and_admin_requires_evidence(client):
    with SessionLocal() as db:
        _directory(db)
        applicant = _user(db, email="applicant@example.com")
        admin = _user(db, email="marketplace.admin@example.com", role=Role.ADMIN)
        db.commit()
        applicant_id, admin_id = applicant.id, admin.id
    payload = {
        "public_display_name": "Fictional Applicant",
        "state_code": "TEST-S",
        "district_code": "TEST-D",
        "organization_name": "Fictional Applicant Organization",
        "years_experience": 3,
        "languages": ["English"],
        "training_details": "Synthetic training details for test validation only.",
        "authorization_reference": "SYNTHETIC-REFERENCE",
        "issuing_authority": "Synthetic Authority",
        "authorization_issue_date": str(date.today() - timedelta(days=30)),
        "authorization_expiry": str(date.today() + timedelta(days=365)),
        "service_area_description": "Synthetic test district",
        "service_radius_km": 25,
        "acknowledgement": True,
    }
    created = await client.post(
        "/api/v1/rescuers/onboarding", json=payload, headers=_token(applicant_id)
    )
    assert created.status_code == 201
    assert created.json()["verification_status"] == "PENDING_VERIFICATION"
    with SessionLocal() as db:
        assert db.get(User, applicant_id).role == Role.CITIZEN
    listing = await client.get("/api/v1/admin/rescuers", headers=_token(admin_id))
    row = listing.json()["items"][0]
    organization_id = row["organization_id"]
    profile_id = row["id"]
    assert (
        await client.patch(
            f"/api/v1/admin/organizations/{organization_id}/verification",
            json={"status": "VERIFIED", "note": "Synthetic organization evidence reviewed."},
            headers=_token(admin_id),
        )
    ).status_code == 200
    assert (
        await client.patch(
            f"/api/v1/admin/rescuers/{profile_id}/verification",
            json={"status": "UNDER_REVIEW", "note": "Synthetic evidence review started."},
            headers=_token(admin_id),
        )
    ).status_code == 200
    no_evidence = await client.patch(
        f"/api/v1/admin/rescuers/{profile_id}/verification",
        json={"status": "VERIFIED", "note": "Attempt without private evidence."},
        headers=_token(admin_id),
    )
    assert (
        no_evidence.status_code == 409
        and no_evidence.json()["error"]["code"] == "EVIDENCE_REQUIRED"
    )
    with SessionLocal() as db:
        db.add(
            RescuerDocument(
                rescuer_profile_id=UUID(profile_id),
                storage_key=f"synthetic-tests/{profile_id}/evidence.pdf",
                original_filename="synthetic-evidence.pdf",
                content_type="application/pdf",
                file_size=128,
            )
        )
        db.commit()
    approved = await client.patch(
        f"/api/v1/admin/rescuers/{profile_id}/verification",
        json={"status": "VERIFIED", "note": "Synthetic evidence accepted for demo testing."},
        headers=_token(admin_id),
    )
    assert approved.status_code == 200
    with SessionLocal() as db:
        assert db.get(User, applicant_id).role == Role.RESCUER


async def test_discovery_excludes_unverified_and_expired_rescuers(client):
    with SessionLocal() as db:
        _directory(db)
        _, eligible = _rescuer(db, email="eligible.rescuer@example.com")
        _rescuer(
            db,
            email="pending.rescuer@example.com",
            status=VerificationStatus.PENDING_VERIFICATION,
        )
        _rescuer(
            db,
            email="expired.rescuer@example.com",
            expiry=date.today() - timedelta(days=1),
        )
        db.commit()
        eligible_id = str(eligible.id)
    response = await client.get(
        "/api/v1/rescuers/nearby?latitude=17.42&longitude=78.49&radius_km=20&state_code=TEST-S"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == eligible_id
    assert response.json()["items"][0]["is_demo"] is True
    assert response.json()["items"][0]["service_charge"] is None


async def test_demo_booking_is_idempotent_supports_manual_location_and_disables_money(client):
    with SessionLocal() as db:
        _directory(db)
        customer = _user(db, email="booking.customer@example.com")
        _, rescuer = _rescuer(db, email="booking.rescuer@example.com")
        db.commit()
        customer_id, rescuer_id = customer.id, rescuer.id
    headers = {**_token(customer_id), "Idempotency-Key": "booking-test-key-0001"}
    payload = _booking_payload(rescuer_id, manual=True)
    first = await client.post("/api/v1/bookings", json=payload, headers=headers)
    replay = await client.post("/api/v1/bookings", json=payload, headers=headers)
    assert first.status_code == 201 and replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert replay.headers["x-idempotent-replay"] == "true"
    assert first.json()["status"] == "PENDING_RESCUER_RESPONSE"
    assert first.json()["is_demo"] is True
    assert first.json()["quoted_amount"] is None
    assert first.json()["payment_status"] == "DISABLED"
    assert first.json()["live_dispatch_enabled"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 1
        snapshot = db.scalar(select(BookingFinancialSnapshot))
        assert snapshot.pricing_authorized is False
        assert snapshot.service_amount == Decimal("0.00")


async def test_assigned_rescuer_accepts_other_rescuer_is_denied_and_privacy_is_reduced(client):
    with SessionLocal() as db:
        _directory(db)
        customer = _user(db, email="accept.customer@example.com")
        assigned_user, assigned = _rescuer(db, email="assigned.rescuer@example.com")
        other_user, _ = _rescuer(
            db,
            email="other.rescuer@example.com",
            latitude=17.45,
            longitude=78.50,
        )
        db.commit()
        customer_id = customer.id
        assigned_user_id = assigned_user.id
        other_user_id = other_user.id
        assigned_id = assigned.id
    created = await client.post(
        "/api/v1/bookings",
        json=_booking_payload(assigned_id),
        headers={**_token(customer_id), "Idempotency-Key": "booking-accept-key-0001"},
    )
    booking_id = created.json()["id"]
    denied = await client.post(
        f"/api/v1/bookings/{booking_id}/accept",
        json={"note": "Not assigned."},
        headers=_token(other_user_id),
    )
    assert denied.status_code == 403
    rescuer_view = await client.get(
        f"/api/v1/bookings/{booking_id}", headers=_token(assigned_user_id)
    )
    assert rescuer_view.json()["location_precision"] == "APPROXIMATE_RESCUER_VIEW"
    assert rescuer_view.json()["latitude"] == 17.42
    accepted = await client.post(
        f"/api/v1/bookings/{booking_id}/accept",
        json={"note": "Synthetic demo acceptance."},
        headers=_token(assigned_user_id),
    )
    assert accepted.status_code == 200 and accepted.json()["status"] == "ACCEPTED"
    duplicate = await client.post(
        f"/api/v1/bookings/{booking_id}/accept",
        json={},
        headers=_token(assigned_user_id),
    )
    assert duplicate.status_code == 409
    customer_view = await client.get(f"/api/v1/bookings/{booking_id}", headers=_token(customer_id))
    assert [item["status"] for item in customer_view.json()["history"]] == [
        "REQUESTED",
        "PENDING_RESCUER_RESPONSE",
        "ACCEPTED",
    ]
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(NotificationEvent)
                .where(NotificationEvent.recipient_id == customer_id)
            )
            == 1
        )


async def test_reject_invalid_transition_and_customer_cancellation(client):
    with SessionLocal() as db:
        _directory(db)
        customer = _user(db, email="reject.customer@example.com")
        rescuer_user, rescuer = _rescuer(db, email="reject.rescuer@example.com")
        db.commit()
        customer_id, rescuer_user_id, rescuer_id = customer.id, rescuer_user.id, rescuer.id
    rejected_booking = await client.post(
        "/api/v1/bookings",
        json=_booking_payload(rescuer_id),
        headers={**_token(customer_id), "Idempotency-Key": "booking-reject-key-0001"},
    )
    rejected_id = rejected_booking.json()["id"]
    rejected = await client.post(
        f"/api/v1/bookings/{rejected_id}/reject",
        json={"note": "Synthetic rejection."},
        headers=_token(rescuer_user_id),
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"
    invalid = await client.post(
        f"/api/v1/bookings/{rejected_id}/reject", json={}, headers=_token(rescuer_user_id)
    )
    assert invalid.status_code == 409

    cancelled_booking = await client.post(
        "/api/v1/bookings",
        json=_booking_payload(rescuer_id, manual=True),
        headers={**_token(customer_id), "Idempotency-Key": "booking-cancel-key-0001"},
    )
    cancelled = await client.post(
        f"/api/v1/bookings/{cancelled_booking.json()['id']}/cancel",
        json={"note": "Customer cancelled synthetic test."},
        headers=_token(customer_id),
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"


async def test_decimal_finance_external_delivery_and_operational_gates_are_safe(client):
    amount, commission, share = financial_values(Decimal("1000.00"), Decimal("10.00"))
    assert (amount, commission, share) == (
        Decimal("1000.00"),
        Decimal("100.00"),
        Decimal("900.00"),
    )
    with pytest.raises(IntegrationNotConfigured):
        EmailNotificationAdapter().send(
            NotificationMessage(
                template_key="booking_requested",
                recipient_reference="synthetic-user",
                variables={},
            )
        )
    status = (await client.get("/api/v1/status")).json()
    assert status["operational_dispatch"] is False
    assert status["authorized_operation"] is False
    assert status["real_payments"] is False
    assert status["external_rescue_notifications"] is False
