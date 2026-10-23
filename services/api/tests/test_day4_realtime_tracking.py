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
    DeviceRegistration,
    District,
    NotificationDeliveryAttempt,
    NotificationEvent,
    Organization,
    RescuerProfile,
    Role,
    State,
    TrackingLocation,
    TrackingSession,
    TrackingStatus,
    User,
    VerificationStatus,
)
from app.services.notifications import DemoNotificationAdapter, NotificationMessage

pytestmark = pytest.mark.anyio


def _token(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _user(db, email: str, role: Role = Role.CITIZEN) -> User:
    user = User(
        name=email.split("@", 1)[0].title(),
        email=email,
        phone=f"90001{abs(hash(email)) % 100000:05d}",
        password_hash="not-used",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _setup_marketplace(db):
    db.add(
        State(
            lgd_code="D4-S",
            name="Synthetic Day 4 State",
            is_union_territory=False,
            is_active=True,
            source_version="synthetic-test-only",
        )
    )
    db.flush()
    db.add(
        District(
            lgd_code="D4-D",
            state_code="D4-S",
            name="Synthetic Day 4 District",
            is_active=True,
            source_version="synthetic-test-only",
        )
    )
    customer = _user(db, "day4.customer@example.com")
    other_customer = _user(db, "day4.other@example.com")
    rescuer_user = _user(db, "day4.rescuer@example.com", Role.RESCUER)
    other_rescuer_user = _user(db, "day4.other.rescuer@example.com", Role.RESCUER)
    organization = Organization(
        name="Fictional Day 4 Demo Organization",
        state="Synthetic Day 4 State",
        district="Synthetic Day 4 District",
        organization_type="SYNTHETIC_TEST",
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(organization)
    db.flush()

    def profile_for(user, latitude: float):
        profile = RescuerProfile(
            user_id=user.id,
            organization_id=organization.id,
            verification_status=VerificationStatus.VERIFIED,
            public_display_name=f"Fictional {user.name}",
            state_code="D4-S",
            district_code="D4-D",
            organization_name=organization.name,
            years_experience=4,
            languages=["English"],
            training_details="Synthetic automated test record.",
            authorization_reference="SYNTHETIC-DAY4",
            issuing_authority="Synthetic Test Authority",
            authorization_issue_date=date.today() - timedelta(days=30),
            authorization_expiry=date.today() + timedelta(days=365),
            service_area_description="Synthetic test district",
            service_radius_km=100,
            latitude=latitude,
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
        db.flush()
        return profile

    rescuer = profile_for(rescuer_user, 17.41)
    other_rescuer = profile_for(other_rescuer_user, 17.43)
    db.commit()
    return customer, other_customer, rescuer_user, other_rescuer_user, rescuer, other_rescuer


async def _create_and_accept(client):
    with SessionLocal() as db:
        values = _setup_marketplace(db)
        customer, other, rescuer_user, other_rescuer_user, rescuer, other_rescuer = values
        ids = tuple(
            item.id
            for item in (
                customer,
                other,
                rescuer_user,
                other_rescuer_user,
                rescuer,
                other_rescuer,
            )
        )
    customer_id, other_id, rescuer_user_id, other_rescuer_user_id, rescuer_id, _ = ids
    created = await client.post(
        "/api/v1/bookings",
        headers={**_token(customer_id), "Idempotency-Key": "day4-booking-key-0001"},
        json={
            "rescuer_id": str(rescuer_id),
            "state_code": "D4-S",
            "district_code": "D4-D",
            "latitude": 17.42,
            "longitude": 78.49,
            "location_accuracy": 15,
            "customer_notes": "Synthetic safe-distance demo request for Day 4 testing.",
            "confirm_demo_and_safety": True,
        },
    )
    assert created.status_code == 201, created.text
    booking_id = created.json()["id"]
    denied = await client.post(
        f"/api/v1/bookings/{booking_id}/accept",
        headers=_token(other_rescuer_user_id),
        json={"note": "Unauthorized synthetic attempt."},
    )
    assert denied.status_code == 403
    accepted = await client.post(
        f"/api/v1/bookings/{booking_id}/accept",
        headers=_token(rescuer_user_id),
        json={"note": "Accepted only inside the Day 4 simulation."},
    )
    assert accepted.status_code == 200 and accepted.json()["status"] == "ACCEPTED"
    return booking_id, customer_id, other_id, rescuer_user_id


async def test_demo_booking_notification_delivery_and_devices_are_private(client):
    with SessionLocal() as db:
        customer, _, rescuer_user, _, rescuer, _ = _setup_marketplace(db)
        customer_id, rescuer_user_id, rescuer_id = customer.id, rescuer_user.id, rescuer.id
    for channel in ("SMS", "WHATSAPP", "PUSH"):
        response = await client.put(
            "/api/v1/notifications/preferences",
            headers=_token(rescuer_user_id),
            json={"channel": channel, "enabled": True, "explicit_opt_in": True},
        )
        assert response.status_code == 200
    device = await client.post(
        "/api/v1/devices/register",
        headers=_token(rescuer_user_id),
        json={
            "platform": "ANDROID",
            "token": "synthetic-device-token-day4-123456",
            "device_label": "Synthetic test phone",
        },
    )
    assert device.status_code == 200
    assert "synthetic-device-token" not in device.text
    created = await client.post(
        "/api/v1/bookings",
        headers={**_token(customer_id), "Idempotency-Key": "day4-notify-key-0001"},
        json={
            "rescuer_id": str(rescuer_id),
            "state_code": "D4-S",
            "district_code": "D4-D",
            "manual_address": "Synthetic manual address",
            "customer_notes": "Synthetic booking used to verify safe notification adapters.",
            "confirm_demo_and_safety": True,
        },
    )
    assert created.status_code == 201
    with SessionLocal() as db:
        event = db.scalar(
            select(NotificationEvent).where(
                NotificationEvent.recipient_id == rescuer_user_id,
                NotificationEvent.event_type == "BOOKING_ASSIGNED",
            )
        )
        attempts = db.scalars(
            select(NotificationDeliveryAttempt).where(
                NotificationDeliveryAttempt.notification_event_id == event.id
            )
        ).all()
        assert {item.channel for item in attempts} == {
            "IN_APP",
            "EMAIL",
            "SMS",
            "WHATSAPP",
            "PUSH",
        }
        assert all(item.status in {"DELIVERED", "DEMO_RECORDED"} for item in attempts)
        customer_event = db.scalar(
            select(NotificationEvent).where(
                NotificationEvent.recipient_id == customer_id,
                NotificationEvent.event_type == "BOOKING_REQUESTED",
            )
        )
        assert customer_event is not None
        assert db.scalar(select(func.count()).select_from(DeviceRegistration)) == 1
    deleted = await client.delete(
        f"/api/v1/devices/{device.json()['id']}", headers=_token(rescuer_user_id)
    )
    assert deleted.status_code == 204


async def test_tracking_requires_consent_enforces_ownership_and_stops_on_arrival(client):
    booking_id, customer_id, other_id, rescuer_user_id = await _create_and_accept(client)
    missing_consent = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/start",
        headers=_token(rescuer_user_id),
        json={"consent": False, "disclosure_version": "day4-demo-v1"},
    )
    assert missing_consent.status_code == 422
    started = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/start",
        headers=_token(rescuer_user_id),
        json={"consent": True, "disclosure_version": "day4-demo-v1"},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "ACTIVE"
    assert started.json()["live_dispatch_enabled"] is False
    unrelated = await client.get(
        f"/api/v1/bookings/{booking_id}/tracking", headers=_token(other_id)
    )
    assert unrelated.status_code == 403
    invalid = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/location",
        headers=_token(rescuer_user_id),
        json={
            "latitude": 100,
            "longitude": 78.48,
            "accuracy": 10,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True,
        },
    )
    assert invalid.status_code == 422
    valid = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/location",
        headers=_token(rescuer_user_id),
        json={
            "latitude": 17.415,
            "longitude": 78.485,
            "accuracy": 12,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True,
        },
    )
    assert valid.status_code == 200, valid.text
    assert valid.json()["route"]["status"] == "UNAVAILABLE"
    assert valid.json()["route"]["geographic_distance_km"] is not None
    customer_view = await client.get(
        f"/api/v1/bookings/{booking_id}/tracking", headers=_token(customer_id)
    )
    assert customer_view.status_code == 200
    assert customer_view.json()["latest_location"]["is_simulated"] is True
    events = await client.get(f"/api/v1/bookings/{booking_id}/events", headers=_token(customer_id))
    sequences = [item["sequence"] for item in events.json()["items"]]
    assert sequences == sorted(set(sequences))
    arrived = await client.post(
        f"/api/v1/bookings/{booking_id}/arrived", headers=_token(rescuer_user_id)
    )
    assert arrived.status_code == 200
    assert arrived.json()["status"] == "STOPPED"
    after_arrival = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/location",
        headers=_token(rescuer_user_id),
        json={
            "latitude": 17.416,
            "longitude": 78.486,
            "accuracy": 10,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True,
        },
    )
    assert after_arrival.status_code == 409


async def test_pause_resume_and_cancellation_stop_tracking(client):
    booking_id, customer_id, _, rescuer_user_id = await _create_and_accept(client)
    await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/start",
        headers=_token(rescuer_user_id),
        json={"consent": True, "disclosure_version": "day4-demo-v1"},
    )
    paused = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/pause", headers=_token(rescuer_user_id)
    )
    assert paused.status_code == 200 and paused.json()["status"] == "PAUSED"
    resumed = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/resume", headers=_token(rescuer_user_id)
    )
    assert resumed.status_code == 200 and resumed.json()["status"] == "ACTIVE"
    cancelled = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=_token(customer_id),
        json={"note": "Synthetic customer cancellation."},
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    with SessionLocal() as db:
        session = db.scalar(
            select(TrackingSession).where(TrackingSession.booking_id == UUID(booking_id))
        )
        assert session.status == TrackingStatus.STOPPED


async def test_expired_tracking_rejects_updates_and_demo_adapters_never_send(client):
    for channel in ("EMAIL", "SMS", "WHATSAPP", "PUSH"):
        result = DemoNotificationAdapter(channel).send(
            NotificationMessage(
                template_key="BOOKING_ACCEPTED",
                recipient_reference="synthetic-recipient",
            )
        )
        assert result.status == "DEMO_RECORDED"
        assert result.provider == "LOCAL_DEMO"
    booking_id, _, _, rescuer_user_id = await _create_and_accept(client)
    await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/start",
        headers=_token(rescuer_user_id),
        json={"consent": True, "disclosure_version": "day4-demo-v1"},
    )
    with SessionLocal() as db:
        session = db.scalar(
            select(TrackingSession).where(TrackingSession.booking_id == UUID(booking_id))
        )
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    expired = await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/location",
        headers=_token(rescuer_user_id),
        json={
            "latitude": 17.41,
            "longitude": 78.48,
            "accuracy": 10,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True,
        },
    )
    assert expired.status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(TrackingLocation)) == 0
        session = db.scalar(
            select(TrackingSession).where(TrackingSession.booking_id == UUID(booking_id))
        )
        assert session.status == TrackingStatus.EXPIRED
        booking = db.get(Booking, UUID(booking_id))
        assert booking.is_demo is True


async def test_terminal_completion_stops_existing_tracking_session(client):
    booking_id, customer_id, _, rescuer_user_id = await _create_and_accept(client)
    await client.post(
        f"/api/v1/bookings/{booking_id}/tracking/start",
        headers=_token(rescuer_user_id),
        json={"consent": True, "disclosure_version": "day4-demo-v1"},
    )
    with SessionLocal() as db:
        booking = db.get(Booking, UUID(booking_id))
        booking.status = "COMPLETED"
        db.commit()
    current = await client.get(
        f"/api/v1/bookings/{booking_id}/tracking", headers=_token(customer_id)
    )
    assert current.status_code == 200
    assert current.json()["status"] == "STOPPED"


async def test_realtime_stream_requires_authenticated_booking_ownership(client):
    booking_id, _, other_id, _ = await _create_and_accept(client)
    no_auth = await client.get(f"/api/v1/bookings/{booking_id}/events/stream")
    unrelated = await client.get(
        f"/api/v1/bookings/{booking_id}/events/stream", headers=_token(other_id)
    )
    assert no_auth.status_code == 401
    assert unrelated.status_code == 403
