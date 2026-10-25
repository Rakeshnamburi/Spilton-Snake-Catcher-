"""In-app chat between a customer and the assigned demo rescuer.

Phone numbers and emails stay hidden by design; this is the only contact channel
inside a demo booking. Both parties must already have access to the booking.
"""

import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.bookings import _owned_booking
from app.api.deps import get_current_user
from app.api.marketplace_helpers import fail, get_profile_for_user
from app.db.session import get_db
from app.models.entities import Booking, BookingMessage, User
from app.schemas.marketplace import (
    BookingContactResponse,
    BookingMessageCreate,
    BookingMessageResponse,
)
from app.services.rate_limit import rate_limiter

router = APIRouter(prefix="/api/v1", tags=["messages"])
MAX_MESSAGES = 200

# Statuses at which each side may reach the other over the masked line.
CUSTOMER_CAN_CALL_FROM = {
    "ACCEPTED", "EN_ROUTE", "ARRIVED", "IN_PROGRESS", "COMPLETED", "DISPUTED"
}
RESCUER_CAN_CALL_FROM = {"ARRIVED", "IN_PROGRESS", "COMPLETED", "UNABLE_TO_ASSIST", "DISPUTED"}


# Chat is never a back door around the masked line: phone numbers and emails
# typed into a message are replaced before the message is stored.
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\s().-]*){6,}\d")


def redact_contacts(text: str) -> str:
    """Replace emails and phone numbers so the in-app chat stays masked."""

    cleaned = _EMAIL_PATTERN.sub("[email hidden]", text)
    return _PHONE_PATTERN.sub("[number hidden]", cleaned)


def _proxy_number(booking_id: UUID) -> str:
    """A stable, clearly-fake platform number. Never a real subscriber number."""

    last4 = int(hashlib.sha256(str(booking_id).encode()).hexdigest()[:4], 16) % 10000
    return f"+91 80 4718 {last4:04d}"


@router.get("/bookings/{booking_id}/contact", response_model=BookingContactResponse)
def booking_contact(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Masked calling line, like a delivery app's proxy number.

    Neither side ever receives the other's real phone number. The rescuer's line
    only activates once the rescuer marks arrival at the customer's location.
    """

    booking = _owned_booking(db, booking_id, user)
    is_customer = booking.customer_id == user.id
    profile = get_profile_for_user(db, user.id)
    is_rescuer = profile is not None and booking.rescuer_id == profile.id
    if not (is_customer or is_rescuer):
        raise fail(
            403,
            "CONTACT_NOT_ALLOWED",
            "Only the customer and the assigned rescuer can use the masked line",
        )

    status = booking.status.value
    connectable = (
        status in RESCUER_CAN_CALL_FROM if is_rescuer else status in CUSTOMER_CAN_CALL_FROM
    )
    return BookingContactResponse(
        booking_id=booking.id,
        proxy_number=_proxy_number(booking.id),
        label="SPILTON masked line (demo)",
        counterpart_role="CUSTOMER" if is_rescuer else "RESCUER",
        connectable=connectable,
        available_from="ARRIVED" if is_rescuer else "ACCEPTED",
        message=(
            "Masked line is active. Calls route through this proxy number, so neither "
            "side sees the other's real number."
            if connectable
            else (
                "The masked line activates once you mark arrival at the customer's location."
                if is_rescuer
                else "The masked line activates once the rescuer accepts your request."
            )
        ),
    )


def _sender_role(booking: Booking, user: User) -> str:
    return "CUSTOMER" if booking.customer_id == user.id else "RESCUER"


@router.get("/bookings/{booking_id}/messages", response_model=list[BookingMessageResponse])
def list_messages(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    return list(
        db.scalars(
            select(BookingMessage)
            .where(BookingMessage.booking_id == booking.id)
            .order_by(BookingMessage.created_at.asc(), BookingMessage.id.asc())
            .limit(MAX_MESSAGES)
        )
    )


@router.post(
    "/bookings/{booking_id}/messages",
    response_model=BookingMessageResponse,
    status_code=201,
)
def send_message(
    booking_id: UUID,
    payload: BookingMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    retry = rate_limiter.check(
        f"chat:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=60,
        window_seconds=300,
    )
    if retry is not None:
        raise fail(429, "RATE_LIMITED", "Too many messages; try again shortly")

    booking = _owned_booking(db, booking_id, user)
    # Administrators may view a booking but must not post as a participant.
    if user.role.value in {"ADMIN", "COORDINATOR"} and booking.customer_id != user.id:
        raise fail(403, "CHAT_NOT_ALLOWED", "Only the customer and the assigned rescuer can chat")

    message = BookingMessage(
        booking_id=booking.id,
        sender_id=user.id,
        sender_role=_sender_role(booking, user),
        body=redact_contacts(payload.body),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/bookings/{booking_id}/messages/read", status_code=204)
def mark_messages_read(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    unread = db.scalars(
        select(BookingMessage).where(
            BookingMessage.booking_id == booking.id,
            BookingMessage.sender_id != user.id,
            BookingMessage.read_at.is_(None),
        )
    ).all()
    now = datetime.now(timezone.utc)
    for message in unread:
        message.read_at = now
    if unread:
        db.commit()
