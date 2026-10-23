import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.entities import (
    AvailabilityStatus,
    Booking,
    CommissionEntry,
    District,
    FinancialLedgerEntry,
    NotificationEvent,
    Organization,
    Payment,
    RescueMedia,
    RescueOutcome,
    RescuerProfile,
    Review,
    Role,
    State,
    User,
    VerificationStatus,
)
from app.services.day5_finance import ledger_group_is_balanced

pytestmark = pytest.mark.anyio


def _token(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _user(db, email: str, role: Role = Role.CITIZEN) -> User:
    user = User(
        name=email.split("@", 1)[0].title(),
        email=email,
        phone=f"90005{abs(hash(email)) % 100000:05d}",
        password_hash="not-used",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _setup(db):
    db.add(
        State(
            lgd_code="D5-S",
            name="Synthetic Day 5 State",
            is_union_territory=False,
            is_active=True,
            source_version="synthetic-test-only",
        )
    )
    db.flush()
    db.add(
        District(
            lgd_code="D5-D",
            state_code="D5-S",
            name="Synthetic Day 5 District",
            is_active=True,
            source_version="synthetic-test-only",
        )
    )
    customer = _user(db, "day5.customer@example.com")
    other = _user(db, "day5.other@example.com")
    rescuer_user = _user(db, "day5.rescuer@example.com", Role.RESCUER)
    admin = _user(db, "day5.admin@example.com", Role.ADMIN)
    organization = Organization(
        name="Fictional Day 5 Demo Organization",
        state="Synthetic Day 5 State",
        district="Synthetic Day 5 District",
        organization_type="SYNTHETIC_TEST",
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(organization)
    db.flush()
    profile = RescuerProfile(
        user_id=rescuer_user.id,
        organization_id=organization.id,
        verification_status=VerificationStatus.VERIFIED,
        public_display_name="Fictional Day 5 Rescuer",
        state_code="D5-S",
        district_code="D5-D",
        organization_name=organization.name,
        years_experience=5,
        languages=["English"],
        training_details="Synthetic automated test record.",
        authorization_reference="SYNTHETIC-DAY5",
        issuing_authority="Synthetic Test Authority",
        authorization_issue_date=date.today() - timedelta(days=30),
        authorization_expiry=date.today() + timedelta(days=365),
        service_area_description="Synthetic test district",
        service_radius_km=100,
        latitude=17.41,
        longitude=78.48,
        availability=AvailabilityStatus.AVAILABLE,
        last_seen_at=datetime.now(timezone.utc),
        availability_updated_at=datetime.now(timezone.utc),
        average_rating=Decimal("0.00"),
        review_count=0,
        completed_service_count=0,
        is_demo=True,
    )
    db.add(profile)
    db.add_all(
        [
            RescueOutcome(
                code="AUTHORIZED_RESCUE_COMPLETED",
                label="Authorized rescue completed",
                description="Synthetic demo completion.",
                is_active=True,
            ),
            RescueOutcome(
                code="UNABLE_TO_ASSIST",
                label="Unable to assist",
                description="Synthetic unable-to-assist outcome.",
                is_active=True,
            ),
        ]
    )
    db.commit()
    return customer.id, other.id, rescuer_user.id, admin.id, profile.id


async def _arrived_booking(client):
    with SessionLocal() as db:
        customer_id, other_id, rescuer_user_id, admin_id, profile_id = _setup(db)
    created = await client.post(
        "/api/v1/bookings",
        headers={
            **_token(customer_id),
            "Idempotency-Key": "day5-booking-key-0001",
        },
        json={
            "rescuer_id": str(profile_id),
            "state_code": "D5-S",
            "district_code": "D5-D",
            "latitude": 17.42,
            "longitude": 78.49,
            "location_accuracy": 20,
            "customer_notes": "Synthetic Day 5 safe-distance demo request.",
            "confirm_demo_and_safety": True,
        },
    )
    assert created.status_code == 201, created.text
    booking_id = created.json()["id"]
    accepted = await client.post(
        f"/api/v1/bookings/{booking_id}/accept",
        headers=_token(rescuer_user_id),
        json={"note": "Synthetic acceptance."},
    )
    assert accepted.status_code == 200
    tracking = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/start",
        headers=_token(rescuer_user_id),
        json={
            "consent": True,
            "disclosure_version": "day4-demo-v1",
            "is_simulation": True,
        },
    )
    assert tracking.status_code == 200, tracking.text
    arrived = await client.post(
        f"/api/v1/bookings/{booking_id}/arrive",
        headers=_token(rescuer_user_id),
        json={
            "latitude": 17.4201,
            "longitude": 78.4901,
            "accuracy": 14,
            "location_consent": True,
        },
    )
    assert arrived.status_code == 200, arrived.text
    return booking_id, customer_id, other_id, rescuer_user_id, admin_id


async def _completed_booking(client):
    booking_id, customer_id, other_id, rescuer_user_id, admin_id = await _arrived_booking(client)
    started = await client.post(
        f"/api/v1/bookings/{booking_id}/rescue/start",
        headers=_token(rescuer_user_id),
    )
    assert started.status_code == 201, started.text
    completed = await client.post(
        f"/api/v1/bookings/{booking_id}/complete",
        headers={
            **_token(rescuer_user_id),
            "Idempotency-Key": "day5-complete-key-0001",
        },
        json={
            "outcome_code": "AUTHORIZED_RESCUE_COMPLETED",
            "observations": "Synthetic observations recorded from a safe distance.",
            "authorized_action_summary": (
                "Synthetic authorized workflow documented without live dispatch."
            ),
            "notes": "No real rescue occurred.",
            "species_text": "Unverified snake observation",
            "confirm_demo": True,
        },
    )
    assert completed.status_code == 201, completed.text
    replay = await client.post(
        f"/api/v1/bookings/{booking_id}/complete",
        headers={
            **_token(rescuer_user_id),
            "Idempotency-Key": "day5-complete-key-0001",
        },
        json={
            "outcome_code": "AUTHORIZED_RESCUE_COMPLETED",
            "observations": "Synthetic observations recorded from a safe distance.",
            "authorized_action_summary": (
                "Synthetic authorized workflow documented without live dispatch."
            ),
            "notes": "No real rescue occurred.",
            "species_text": "Unverified snake observation",
            "confirm_demo": True,
        },
    )
    assert replay.status_code == 201
    assert replay.headers["X-Idempotent-Replay"] == "true"
    return booking_id, customer_id, other_id, rescuer_user_id, admin_id


async def test_completion_requires_assignment_and_supports_customer_confirmation(client):
    booking_id, customer_id, other_id, rescuer_user_id, _ = await _arrived_booking(client)
    denied = await client.post(
        f"/api/v1/bookings/{booking_id}/rescue/start",
        headers=_token(other_id),
    )
    assert denied.status_code == 403
    assert (
        await client.post(
            f"/api/v1/bookings/{booking_id}/rescue/start",
            headers=_token(rescuer_user_id),
        )
    ).status_code == 201
    completed = await client.post(
        f"/api/v1/bookings/{booking_id}/complete",
        headers={
            **_token(rescuer_user_id),
            "Idempotency-Key": "day5-completion-auth-0001",
        },
        json={
            "outcome_code": "AUTHORIZED_RESCUE_COMPLETED",
            "observations": "Synthetic observations recorded safely.",
            "authorized_action_summary": "Synthetic authorized completion only.",
            "confirm_demo": True,
        },
    )
    assert completed.status_code == 201
    unauthorized = await client.post(
        f"/api/v1/bookings/{booking_id}/confirm-completion",
        headers=_token(other_id),
    )
    assert unauthorized.status_code == 403
    confirmed = await client.post(
        f"/api/v1/bookings/{booking_id}/confirm-completion",
        headers=_token(customer_id),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["completion_status"] == "CUSTOMER_CONFIRMED"
    disputed = await client.post(
        f"/api/v1/bookings/{booking_id}/dispute",
        headers=_token(customer_id),
        json={"reason": "Synthetic completion issue requiring coordinator review."},
    )
    assert disputed.status_code == 201, disputed.text
    with SessionLocal() as db:
        event_types = set(db.scalars(select(NotificationEvent.event_type)).all())
        assert "COMPLETION_DISPUTED" in event_types


async def test_private_evidence_is_sanitized_and_owner_protected(client):
    booking_id, customer_id, other_id, rescuer_user_id, _ = await _arrived_booking(client)
    await client.post(
        f"/api/v1/bookings/{booking_id}/rescue/start",
        headers=_token(rescuer_user_id),
    )
    stream = io.BytesIO()
    image = Image.new("RGB", (20, 20), color=(20, 100, 40))
    image.save(stream, format="JPEG", exif=b"synthetic-private-metadata")
    upload = await client.post(
        f"/api/v1/bookings/{booking_id}/rescue/evidence",
        headers=_token(rescuer_user_id),
        data={
            "evidence_type": "OUTCOME",
            "latitude": "17.42",
            "longitude": "78.49",
            "accuracy": "10",
            "location_consent": "true",
        },
        files={"file": ("demo.jpg", stream.getvalue(), "image/jpeg")},
    )
    assert upload.status_code == 201, upload.text
    media_id = upload.json()["id"]
    assert upload.json()["location_attached"] is True
    authorized = await client.get(
        f"/api/v1/bookings/{booking_id}/rescue/evidence/{media_id}",
        headers=_token(customer_id),
    )
    assert authorized.status_code == 200
    assert b"synthetic-private-metadata" not in authorized.content
    denied = await client.get(
        f"/api/v1/bookings/{booking_id}/rescue/evidence/{media_id}",
        headers=_token(other_id),
    )
    assert denied.status_code == 403
    invalid = await client.post(
        f"/api/v1/bookings/{booking_id}/rescue/evidence",
        headers=_token(rescuer_user_id),
        data={"evidence_type": "OUTCOME"},
        files={"file": ("fake.jpg", b"not-an-image", "image/jpeg")},
    )
    assert invalid.status_code == 422
    with SessionLocal() as db:
        media = db.get(RescueMedia, UUID(media_id))
        assert media.storage_key.startswith(f"rescue-evidence/{booking_id}/")


async def test_demo_payment_commission_ledger_refund_and_review(client):
    booking_id, customer_id, _, rescuer_user_id, admin_id = await _completed_booking(client)
    confirmation = await client.post(
        f"/api/v1/bookings/{booking_id}/confirm-completion",
        headers=_token(customer_id),
    )
    assert confirmation.status_code == 200
    failed_created = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        headers={
            **_token(customer_id),
            "Idempotency-Key": "day5-payment-failure-key-0001",
        },
        json={
            "method": "DEMO_ONLINE",
            "amount": "25.00",
            "currency": "INR",
            "confirm_demo": True,
        },
    )
    assert failed_created.status_code == 201, failed_created.text
    failed = await client.post(
        f"/api/v1/payments/{failed_created.json()['id']}/confirm",
        headers=_token(customer_id),
        json={"simulate_failure": True},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "DEMO_FAILED"
    created = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        headers={
            **_token(customer_id),
            "Idempotency-Key": "day5-payment-key-0001",
        },
        json={
            "method": "DEMO_ONLINE",
            "amount": "1000.00",
            "currency": "INR",
            "confirm_demo": True,
        },
    )
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]
    paid = await client.post(
        f"/api/v1/payments/{payment_id}/confirm",
        headers=_token(customer_id),
        json={"simulate_failure": False},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["commission_amount"] == "100.00"
    assert paid.json()["rescuer_share"] == "900.00"
    earnings = await client.get(
        "/api/v1/rescuer/earnings",
        headers=_token(rescuer_user_id),
    )
    assert earnings.status_code == 200
    assert earnings.json()["withdrawable"] is False
    refund = await client.post(
        f"/api/v1/admin/payments/{payment_id}/refund",
        headers={
            **_token(admin_id),
            "Idempotency-Key": "day5-refund-key-0001",
        },
        json={"amount": "250.00", "reason": "Synthetic partial refund test."},
    )
    assert refund.status_code == 200, refund.text
    review = await client.post(
        f"/api/v1/bookings/{booking_id}/review",
        headers=_token(customer_id),
        json={"rating": 5, "review_text": "Helpful simulated workflow."},
    )
    assert review.status_code == 201, review.text
    duplicate = await client.post(
        f"/api/v1/bookings/{booking_id}/review",
        headers=_token(customer_id),
        json={"rating": 4},
    )
    assert duplicate.status_code == 409
    with SessionLocal() as db:
        payment = db.get(Payment, UUID(payment_id))
        commission = db.scalar(
            select(CommissionEntry).where(CommissionEntry.payment_id == payment.id)
        )
        assert commission.commission_amount == Decimal("100.00")
        assert commission.rescuer_share == Decimal("900.00")
        assert db.scalar(select(Review).where(Review.booking_id == UUID(booking_id)))
        event_types = set(db.scalars(select(NotificationEvent.event_type)).all())
        assert {
            "RESCUE_SESSION_STARTED",
            "RESCUE_REPORT_SUBMITTED",
            "BOOKING_COMPLETED",
            "DEMO_PAYMENT_FAILED",
            "DEMO_PAYMENT_SUCCEEDED",
            "REVIEW_SUBMITTED",
        } <= event_types
        groups = db.scalars(select(FinancialLedgerEntry.transaction_group).distinct()).all()
        assert groups and all(ledger_group_is_balanced(db, group) for group in groups)
        assert db.get(Booking, UUID(booking_id)).payment_status.value == "PAID"


async def test_demo_cash_requires_assigned_rescuer_confirmation(client):
    booking_id, customer_id, other_id, rescuer_user_id, _ = await _completed_booking(client)
    created = await client.post(
        f"/api/v1/bookings/{booking_id}/payments",
        headers={
            **_token(customer_id),
            "Idempotency-Key": "day5-cash-payment-key-0001",
        },
        json={
            "method": "DEMO_CASH",
            "amount": "500.00",
            "currency": "INR",
            "confirm_demo": True,
        },
    )
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]
    assert created.json()["status"] == "CASH_AWAITING_CONFIRMATION"
    denied = await client.post(
        f"/api/v1/payments/{payment_id}/cash-confirm",
        headers=_token(other_id),
        json={"confirm_received": True},
    )
    assert denied.status_code == 403
    confirmed = await client.post(
        f"/api/v1/payments/{payment_id}/cash-confirm",
        headers=_token(rescuer_user_id),
        json={"confirm_received": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "DEMO_SUCCEEDED"
    assert confirmed.json()["commission_amount"] == "50.00"
