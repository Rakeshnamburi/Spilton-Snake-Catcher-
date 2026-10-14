from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import (
    AvailabilityHistory,
    AvailabilityStatus,
    Booking,
    BookingEvent,
    BookingFinancialSnapshot,
    BookingStatus,
    BookingStatusHistory,
    NotificationDeliveryAttempt,
    NotificationEvent,
    Organization,
    RescuerProfile,
    User,
    VerificationStatus,
)

logger = logging.getLogger(__name__)
MONEY = Decimal("0.01")


class InvalidBookingTransition(ValueError):
    pass


def haversine_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    radius = 6371.0088
    phi_a, phi_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def financial_values(
    service_amount: Decimal | str, commission_rate: Decimal | str
) -> tuple[Decimal, Decimal, Decimal]:
    amount = Decimal(service_amount).quantize(MONEY, rounding=ROUND_HALF_UP)
    rate = Decimal(commission_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
    if amount < 0 or rate < 0 or rate > 100:
        raise ValueError("Invalid financial values")
    commission = (amount * rate / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
    share = (amount - commission).quantize(MONEY, rounding=ROUND_HALF_UP)
    return amount, commission, share


def add_financial_snapshot(db: Session, booking: Booking) -> BookingFinancialSnapshot:
    settings = get_settings()
    rate = Decimal(settings.default_commission_percent)
    amount, commission, share = financial_values(Decimal("0.00"), rate)
    snapshot = BookingFinancialSnapshot(
        booking_id=booking.id,
        service_amount=amount,
        commission_rate=rate,
        commission_amount=commission,
        rescuer_share=share,
        currency="INR",
        pricing_authorized=False,
        is_illustrative=True,
    )
    db.add(snapshot)
    return snapshot


def organization_is_approved(db: Session, profile: RescuerProfile) -> bool:
    if profile.organization_id is None:
        return False
    organization = db.get(Organization, profile.organization_id)
    return bool(organization and organization.verification_status == VerificationStatus.VERIFIED)


def rescuer_is_eligible(
    db: Session, profile: RescuerProfile, *, require_available: bool = True
) -> bool:
    today = date.today()
    if profile.verification_status != VerificationStatus.VERIFIED:
        return False
    if not profile.is_demo or not organization_is_approved(db, profile):
        return False
    if profile.authorization_expiry is None or profile.authorization_expiry < today:
        return False
    if require_available and profile.availability != AvailabilityStatus.AVAILABLE:
        return False
    return True


def expire_stale_rescuers(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=get_settings().rescuer_stale_minutes)
    stale = db.scalars(
        select(RescuerProfile).where(
            RescuerProfile.availability == AvailabilityStatus.AVAILABLE,
            (RescuerProfile.last_seen_at.is_(None)) | (RescuerProfile.last_seen_at < cutoff),
        )
    ).all()
    for profile in stale:
        profile.availability = AvailabilityStatus.OFFLINE
        profile.availability_updated_at = datetime.now(timezone.utc)
        db.add(
            AvailabilityHistory(
                rescuer_profile_id=profile.id,
                previous_status=AvailabilityStatus.AVAILABLE.value,
                new_status=AvailabilityStatus.OFFLINE.value,
            )
        )
    if stale:
        db.commit()
    return len(stale)


def create_in_app_notification(
    db: Session,
    *,
    recipient_id,
    booking_id,
    event_type: str,
    title: str,
    body: str,
) -> NotificationEvent:
    event = NotificationEvent(
        recipient_id=recipient_id,
        booking_id=booking_id,
        event_type=event_type,
        title=title,
        body=body,
        is_demo=True,
    )
    db.add(event)
    db.flush()
    db.add(
        NotificationDeliveryAttempt(
            notification_event_id=event.id,
            channel="IN_APP",
            provider="LOCAL_DEMO",
            status="DELIVERED",
            sanitized_result=(
                "Stored as a local in-app demo notification; no external message sent."
            ),
        )
    )
    logger.info(
        "demo_notification event=%s recipient_id=%s booking_id=%s",
        event_type,
        recipient_id,
        booking_id,
    )
    return event


def add_booking_state(
    db: Session,
    booking: Booking,
    *,
    actor_id,
    previous: BookingStatus | None,
    current: BookingStatus,
    event_type: str,
    details: str,
    note: str | None = None,
) -> None:
    booking.status = current
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            actor_id=actor_id,
            previous_status=previous.value if previous else None,
            status=current.value,
            note=note,
        )
    )
    db.add(
        BookingEvent(
            booking_id=booking.id,
            actor_id=actor_id,
            event_type=event_type,
            details=details,
        )
    )


def validate_booking_transition(current: BookingStatus, target: BookingStatus) -> None:
    allowed = {
        BookingStatus.REQUESTED: {BookingStatus.PENDING_RESCUER_RESPONSE},
        BookingStatus.PENDING_RESCUER_RESPONSE: {
            BookingStatus.ACCEPTED,
            BookingStatus.REJECTED,
            BookingStatus.EXPIRED,
            BookingStatus.CANCELLED,
        },
        BookingStatus.ACCEPTED: {BookingStatus.CANCELLED},
        BookingStatus.REJECTED: set(),
        BookingStatus.EXPIRED: set(),
        BookingStatus.CANCELLED: set(),
        BookingStatus.EN_ROUTE: set(),
        BookingStatus.ARRIVED: set(),
        BookingStatus.IN_PROGRESS: set(),
        BookingStatus.COMPLETED: set(),
        BookingStatus.UNABLE_TO_ASSIST: set(),
    }
    if target not in allowed[current]:
        raise InvalidBookingTransition(
            f"Cannot change booking from {current.value} to {target.value}"
        )


def expire_pending_bookings(db: Session) -> int:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Booking).where(
            Booking.status == BookingStatus.PENDING_RESCUER_RESPONSE,
            Booking.expires_at <= now,
        )
    ).all()
    for booking in rows:
        previous = booking.status
        add_booking_state(
            db,
            booking,
            actor_id=None,
            previous=previous,
            current=BookingStatus.EXPIRED,
            event_type="BOOKING_EXPIRED",
            details="The simulated response window expired without acceptance.",
        )
        create_in_app_notification(
            db,
            recipient_id=booking.customer_id,
            booking_id=booking.id,
            event_type="BOOKING_EXPIRED",
            title="Demo request expired",
            body=f"Demo booking {booking.booking_reference} expired without a response.",
        )
    if rows:
        db.commit()
    return len(rows)


def get_rescuer_user(db: Session, profile: RescuerProfile) -> User | None:
    return db.get(User, profile.user_id)
