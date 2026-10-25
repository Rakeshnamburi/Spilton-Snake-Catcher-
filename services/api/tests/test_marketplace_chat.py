"""Tests for rescuer travel coverage badges and in-app booking chat."""

import uuid

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import BookingMessage
from tests.test_day3_marketplace import (
    _booking_payload,
    _directory,
    _rescuer,
    _token,
    _user,
)

pytestmark = pytest.mark.anyio


async def test_nearby_reports_coverage_scope(client):
    with SessionLocal() as db:
        _directory(db)
        _, rescuer = _rescuer(db, email="coverage.rescuer@example.com")
        rescuer.subdistrict_code = "TEST-M"
        rescuer.coverage_subdistrict_codes = ["TEST-M2"]
        db.commit()

    mandal = await client.get(
        "/api/v1/rescuers/nearby?state_code=TEST-S&district_code=TEST-D"
        "&subdistrict_code=TEST-M2&radius_km=50"
    )
    assert mandal.status_code == 200
    assert mandal.json()["total"] == 1
    assert mandal.json()["items"][0]["coverage_scope"] == "MANDAL"

    district = await client.get(
        "/api/v1/rescuers/nearby?state_code=TEST-S&district_code=TEST-D&radius_km=50"
    )
    assert district.json()["items"][0]["coverage_scope"] == "DISTRICT"


async def test_booking_chat_is_limited_to_participants(client):
    with SessionLocal() as db:
        _directory(db)
        customer = _user(db, email="chat.customer@example.com")
        rescuer_user, rescuer = _rescuer(db, email="chat.rescuer@example.com")
        outsider = _user(db, email="chat.outsider@example.com")
        db.commit()
        customer_id = customer.id
        rescuer_user_id = rescuer_user.id
        outsider_id = outsider.id
        rescuer_id = str(rescuer.id)

    created = await client.post(
        "/api/v1/bookings",
        headers={**_token(customer_id), "Idempotency-Key": str(uuid.uuid4())},
        json=_booking_payload(rescuer_id),
    )
    assert created.status_code == 201
    booking_id = created.json()["id"]

    sent = await client.post(
        f"/api/v1/bookings/{booking_id}/messages",
        headers=_token(customer_id),
        json={"body": "The snake is near the back gate."},
    )
    assert sent.status_code == 201
    assert sent.json()["sender_role"] == "CUSTOMER"

    thread = await client.get(
        f"/api/v1/bookings/{booking_id}/messages", headers=_token(rescuer_user_id)
    )
    assert thread.status_code == 200
    assert len(thread.json()) == 1

    reply = await client.post(
        f"/api/v1/bookings/{booking_id}/messages",
        headers=_token(rescuer_user_id),
        json={"body": "On my way, about ten minutes."},
    )
    assert reply.status_code == 201
    assert reply.json()["sender_role"] == "RESCUER"

    # A user who is neither the customer nor the assigned rescuer is refused.
    blocked = await client.get(
        f"/api/v1/bookings/{booking_id}/messages", headers=_token(outsider_id)
    )
    assert blocked.status_code == 403

    with SessionLocal() as db:
        stored = db.scalars(
            select(BookingMessage).where(BookingMessage.booking_id == uuid.UUID(booking_id))
        ).all()
        assert len(stored) == 2


async def test_masked_contact_line_hides_real_numbers(client):
    with SessionLocal() as db:
        _directory(db)
        customer = _user(db, email="mask.customer@example.com")
        rescuer_user, rescuer = _rescuer(db, email="mask.rescuer@example.com")
        outsider = _user(db, email="mask.outsider@example.com")
        db.commit()
        customer_id = customer.id
        rescuer_user_id = rescuer_user.id
        outsider_id = outsider.id
        rescuer_id = str(rescuer.id)

    created = await client.post(
        "/api/v1/bookings",
        headers={**_token(customer_id), "Idempotency-Key": str(uuid.uuid4())},
        json=_booking_payload(rescuer_id),
    )
    booking_id = created.json()["id"]

    # The rescuer's line stays inactive until arrival.
    before = await client.get(
        f"/api/v1/bookings/{booking_id}/contact", headers=_token(rescuer_user_id)
    )
    assert before.status_code == 200
    body = before.json()
    assert body["connectable"] is False
    assert body["available_from"] == "ARRIVED"
    assert body["real_number_hidden"] is True
    assert body["proxy_number"].startswith("+91 80 4718")

    # Nobody's real phone number is ever returned by the masked-line endpoint.
    assert "phone" not in body

    # An unrelated user cannot use the masked line at all.
    blocked = await client.get(
        f"/api/v1/bookings/{booking_id}/contact", headers=_token(outsider_id)
    )
    assert blocked.status_code == 403


async def test_chat_redacts_phone_numbers_and_emails(client):
    from app.api.messages import redact_contacts

    assert redact_contacts("Call me on 9876543210 now") == "Call me on [number hidden] now"
    assert redact_contacts("mail a@b.com please") == "mail [email hidden] please"
    assert redact_contacts("reach +91 98765-43210 today") == "reach [number hidden] today"
    # Short numbers that are not phone numbers are left alone.
    assert redact_contacts("flat 1234 is fine") == "flat 1234 is fine"

    with SessionLocal() as db:
        _directory(db)
        customer = _user(db, email="redact.customer@example.com")
        _, rescuer = _rescuer(db, email="redact.rescuer@example.com")
        db.commit()
        customer_id = customer.id
        rescuer_id = str(rescuer.id)

    created = await client.post(
        "/api/v1/bookings",
        headers={**_token(customer_id), "Idempotency-Key": str(uuid.uuid4())},
        json=_booking_payload(rescuer_id),
    )
    booking_id = created.json()["id"]
    sent = await client.post(
        f"/api/v1/bookings/{booking_id}/messages",
        headers=_token(customer_id),
        json={"body": "Call 9876543210 or email test@gmail.com"},
    )
    assert sent.status_code == 201
    assert "9876543210" not in sent.json()["body"]
    assert "test@gmail.com" not in sent.json()["body"]
    assert "[number hidden]" in sent.json()["body"]
    assert "[email hidden]" in sent.json()["body"]
