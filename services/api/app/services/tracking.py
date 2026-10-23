from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import (
    Booking,
    BookingStatus,
    TrackingLocation,
    TrackingSession,
    TrackingStatus,
)
from app.services.marketplace import add_booking_event

TERMINAL_BOOKING_STATUSES = {
    BookingStatus.REJECTED,
    BookingStatus.EXPIRED,
    BookingStatus.CANCELLED,
    BookingStatus.COMPLETED,
    BookingStatus.UNABLE_TO_ASSIST,
}


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def expire_tracking_session(db: Session, session: TrackingSession, booking: Booking) -> bool:
    now = datetime.now(timezone.utc)
    terminal = booking.status in TERMINAL_BOOKING_STATUSES
    expired = _aware(session.expires_at) <= now
    if session.status in {TrackingStatus.ACTIVE, TrackingStatus.PAUSED} and (terminal or expired):
        session.status = TrackingStatus.EXPIRED if expired else TrackingStatus.STOPPED
        session.stopped_at = now
        add_booking_event(
            db,
            booking,
            actor_id=None,
            event_type="TRACKING_EXPIRED" if expired else "TRACKING_STOPPED",
            details=(
                "The demo tracking session expired automatically."
                if expired
                else "Demo tracking stopped automatically when the booking ended."
            ),
        )
        return True
    return False


def stop_booking_tracking(db: Session, booking: Booking, *, actor_id, reason: str) -> bool:
    session = db.scalar(
        select(TrackingSession)
        .where(
            TrackingSession.booking_id == booking.id,
            TrackingSession.status.in_((TrackingStatus.ACTIVE, TrackingStatus.PAUSED)),
        )
        .order_by(TrackingSession.created_at.desc())
        .with_for_update()
    )
    if session is None:
        return False
    session.status = TrackingStatus.STOPPED
    session.stopped_at = datetime.now(timezone.utc)
    add_booking_event(
        db,
        booking,
        actor_id=actor_id,
        event_type="TRACKING_STOPPED",
        details=reason,
    )
    return True


def cleanup_tracking_locations(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=get_settings().tracking_retention_hours)
    result = db.execute(delete(TrackingLocation).where(TrackingLocation.received_at < cutoff))
    db.commit()
    return result.rowcount or 0
