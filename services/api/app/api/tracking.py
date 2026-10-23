from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.bookings import _owned_booking
from app.api.deps import get_current_user
from app.api.marketplace_helpers import fail, get_profile_for_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    Booking,
    BookingStatus,
    RescuerProfile,
    TrackingLocation,
    TrackingSession,
    TrackingStatus,
    User,
)
from app.schemas.day4 import (
    RouteResponse,
    TrackingConsent,
    TrackingLocationCreate,
    TrackingLocationResponse,
    TrackingResponse,
)
from app.schemas.day5 import ArrivalCreate
from app.services.marketplace import (
    InvalidBookingTransition,
    add_booking_event,
    add_booking_state,
    create_in_app_notification,
    haversine_km,
    rescuer_is_eligible,
    validate_booking_transition,
)
from app.services.rate_limit import rate_limiter
from app.services.routing import route_between
from app.services.tracking import expire_tracking_session, stop_booking_tracking

router = APIRouter(tags=["tracking"])
ACTIVE_TRACKING = (TrackingStatus.ACTIVE, TrackingStatus.PAUSED)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _assigned_rescuer(db: Session, booking: Booking, user: User) -> RescuerProfile:
    profile = get_profile_for_user(db, user.id)
    if profile is None or user.role.value != "RESCUER" or booking.rescuer_id != profile.id:
        raise fail(403, "ASSIGNED_RESCUER_REQUIRED", "Only the assigned demo rescuer can track")
    if not rescuer_is_eligible(db, profile, require_available=False):
        raise fail(409, "RESCUER_NOT_ELIGIBLE", "Rescuer verification is no longer eligible")
    return profile


def _latest_session(db: Session, booking_id: UUID, *, lock: bool = False) -> TrackingSession | None:
    statement = (
        select(TrackingSession)
        .where(TrackingSession.booking_id == booking_id)
        .order_by(TrackingSession.created_at.desc())
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def _latest_location(db: Session, session_id: UUID) -> TrackingLocation | None:
    return db.scalar(
        select(TrackingLocation)
        .where(TrackingLocation.tracking_session_id == session_id)
        .order_by(TrackingLocation.recorded_at.desc(), TrackingLocation.id.desc())
    )


def _response(
    db: Session, booking: Booking, viewer: User, session: TrackingSession | None
) -> TrackingResponse:
    is_customer = booking.customer_id == viewer.id
    profile = db.get(RescuerProfile, booking.rescuer_id)
    is_rescuer = bool(profile and profile.user_id == viewer.id)
    destination_latitude = None
    destination_longitude = None
    precision = "WITHHELD"
    if is_customer:
        destination_latitude = booking.latitude
        destination_longitude = booking.longitude
        precision = "EXACT_CUSTOMER_DESTINATION"
    elif is_rescuer:
        destination_latitude = round(booking.latitude, 2) if booking.latitude is not None else None
        destination_longitude = (
            round(booking.longitude, 2) if booking.longitude is not None else None
        )
        precision = "APPROXIMATE_ASSIGNED_RESCUER_DESTINATION"
    latest = _latest_location(db, session.id) if session else None
    route = RouteResponse(
        status="UNAVAILABLE",
        provider=None,
        road_distance_km=None,
        geographic_distance_km=None,
        duration_seconds=None,
        eta_at=None,
        coordinates=[],
        message="ETA unavailable until a current simulated tracking point and destination exist.",
    )
    if latest and destination_latitude is not None and destination_longitude is not None:
        result = route_between(
            latest.latitude,
            latest.longitude,
            destination_latitude,
            destination_longitude,
        )
        route = RouteResponse(
            status=result.status,
            provider=result.provider,
            road_distance_km=result.road_distance_km,
            geographic_distance_km=result.geographic_distance_km,
            duration_seconds=result.duration_seconds,
            eta_at=result.eta_at,
            coordinates=result.coordinates,
            message=result.message,
        )
    location_response = None
    if latest:
        location_response = TrackingLocationResponse.model_validate(
            {
                "id": latest.id,
                "latitude": latest.latitude,
                "longitude": latest.longitude,
                "accuracy": latest.accuracy,
                "recorded_at": latest.recorded_at,
                "received_at": latest.received_at,
                "is_simulated": latest.is_simulated,
            }
        )
    return TrackingResponse(
        session_id=session.id if session else None,
        booking_id=booking.id,
        status=session.status if session else None,
        consent_timestamp=session.consent_timestamp if session else None,
        started_at=session.started_at if session else None,
        paused_at=session.paused_at if session else None,
        stopped_at=session.stopped_at if session else None,
        expires_at=session.expires_at if session else None,
        last_location_at=session.last_location_at if session else None,
        latest_location=location_response,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
        destination_precision=precision,
        route=route,
    )


@router.post("/bookings/{booking_id}/tracking/start", response_model=TrackingResponse)
def start_tracking(
    booking_id: UUID,
    payload: TrackingConsent,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.demo_mode or settings.authorized_operation_enabled:
        raise fail(503, "DEMO_MODE_REQUIRED", "Day 4 tracking is demo-only")
    booking = _owned_booking(db, booking_id, user, lock=True)
    profile = _assigned_rescuer(db, booking, user)
    if booking.status != BookingStatus.ACCEPTED:
        raise fail(409, "TRACKING_NOT_ALLOWED", "Accept the demo booking before starting a journey")
    existing = _latest_session(db, booking.id, lock=True)
    if existing and existing.status in ACTIVE_TRACKING:
        raise fail(409, "TRACKING_ALREADY_ACTIVE", "A tracking session is already active")
    now = datetime.now(timezone.utc)
    session = TrackingSession(
        booking_id=booking.id,
        rescuer_id=profile.id,
        status=TrackingStatus.ACTIVE,
        consent_timestamp=now,
        consent_version=payload.disclosure_version,
        started_at=now,
        expires_at=now + timedelta(minutes=settings.tracking_session_minutes),
        is_demo=True,
    )
    db.add(session)
    try:
        validate_booking_transition(booking.status, BookingStatus.EN_ROUTE)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=BookingStatus.ACCEPTED,
        current=BookingStatus.EN_ROUTE,
        event_type="BOOKING_EN_ROUTE",
        details="The fictional demo rescuer started a simulated journey.",
    )
    add_booking_event(
        db,
        booking,
        actor_id=user.id,
        event_type="TRACKING_STARTED",
        details="Explicit foreground-only demo location consent was recorded.",
    )
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type="TRACKING_STARTED",
        title="Simulated journey started",
        body=f"Foreground demo tracking started for {booking.booking_reference}.",
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="tracking.start.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    db.commit()
    db.refresh(session)
    return _response(db, booking, user, session)


def _change_tracking(
    db: Session,
    booking_id: UUID,
    user: User,
    expected: TrackingStatus,
    target: TrackingStatus,
    event_type: str,
) -> TrackingResponse:
    booking = _owned_booking(db, booking_id, user, lock=True)
    _assigned_rescuer(db, booking, user)
    session = _latest_session(db, booking.id, lock=True)
    if session is None or session.status != expected:
        raise fail(409, "INVALID_TRACKING_STATE", f"Tracking must be {expected.value.lower()}")
    if expire_tracking_session(db, session, booking):
        db.commit()
        raise fail(409, "TRACKING_SESSION_ENDED", "The tracking session has ended")
    now = datetime.now(timezone.utc)
    session.status = target
    if target == TrackingStatus.PAUSED:
        session.paused_at = now
    elif target == TrackingStatus.ACTIVE:
        session.paused_at = None
    else:
        session.stopped_at = now
    add_booking_event(
        db,
        booking,
        actor_id=user.id,
        event_type=event_type,
        details=f"Foreground demo location sharing was {target.value.lower()} by the rescuer.",
    )
    db.commit()
    db.refresh(session)
    return _response(db, booking, user, session)


@router.post("/bookings/{booking_id}/tracking/pause", response_model=TrackingResponse)
def pause_tracking(
    booking_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _change_tracking(
        db, booking_id, user, TrackingStatus.ACTIVE, TrackingStatus.PAUSED, "TRACKING_PAUSED"
    )


@router.post("/bookings/{booking_id}/tracking/resume", response_model=TrackingResponse)
def resume_tracking(
    booking_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _change_tracking(
        db, booking_id, user, TrackingStatus.PAUSED, TrackingStatus.ACTIVE, "TRACKING_RESUMED"
    )


@router.post("/bookings/{booking_id}/tracking/stop", response_model=TrackingResponse)
def stop_tracking(
    booking_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    _assigned_rescuer(db, booking, user)
    session = _latest_session(db, booking.id, lock=True)
    if session is None or session.status not in ACTIVE_TRACKING:
        raise fail(409, "INVALID_TRACKING_STATE", "No active tracking session exists")
    stop_booking_tracking(
        db,
        booking,
        actor_id=user.id,
        reason="The rescuer explicitly stopped foreground demo location sharing.",
    )
    db.commit()
    db.refresh(session)
    return _response(db, booking, user, session)


@router.post("/bookings/{booking_id}/tracking/location", response_model=TrackingResponse)
def update_location(
    booking_id: UUID,
    payload: TrackingLocationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    _assigned_rescuer(db, booking, user)
    session = _latest_session(db, booking.id, lock=True)
    if session is None or session.status != TrackingStatus.ACTIVE:
        raise fail(409, "TRACKING_NOT_ACTIVE", "Start or resume tracking before sending location")
    if expire_tracking_session(db, session, booking):
        db.commit()
        raise fail(409, "TRACKING_SESSION_ENDED", "The tracking session has ended")
    now = datetime.now(timezone.utc)
    recorded_at = _aware(payload.recorded_at)
    if recorded_at > now + timedelta(minutes=2) or recorded_at < now - timedelta(minutes=10):
        raise fail(
            422, "INVALID_LOCATION_TIME", "Location timestamp is outside the accepted window"
        )
    settings = get_settings()
    if (
        session.last_location_at
        and (now - _aware(session.last_location_at)).total_seconds()
        < settings.tracking_min_update_seconds
    ):
        raise fail(429, "LOCATION_UPDATE_TOO_FREQUENT", "Wait before sending another location")
    retry = rate_limiter.check(
        f"tracking:{session.id}:{request.client.host if request.client else 'unknown'}",
        limit=120,
        window_seconds=3600,
    )
    if retry is not None:
        raise fail(
            429,
            "TRACKING_RATE_LIMITED",
            "Too many location updates",
            details={"retry_after": retry},
        )
    location = TrackingLocation(
        tracking_session_id=session.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        recorded_at=recorded_at,
        received_at=now,
        is_simulated=True,
    )
    db.add(location)
    session.last_location_at = now
    add_booking_event(
        db,
        booking,
        actor_id=user.id,
        event_type="TRACKING_LOCATION_UPDATED",
        details=(
            "A private simulated tracking point was received; coordinates are not "
            "included in events."
        ),
    )
    db.commit()
    return _response(db, booking, user, session)


@router.get("/bookings/{booking_id}/tracking", response_model=TrackingResponse)
def get_tracking(
    booking_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    booking = _owned_booking(db, booking_id, user)
    session = _latest_session(db, booking.id)
    if session and expire_tracking_session(db, session, booking):
        db.commit()
    return _response(db, booking, user, session)


@router.post("/bookings/{booking_id}/arrive", response_model=TrackingResponse)
@router.post("/bookings/{booking_id}/arrived", response_model=TrackingResponse)
def mark_arrived(
    booking_id: UUID,
    payload: ArrivalCreate | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    _assigned_rescuer(db, booking, user)
    try:
        validate_booking_transition(booking.status, BookingStatus.ARRIVED)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error
    session = _latest_session(db, booking.id, lock=True)
    now = datetime.now(timezone.utc)
    if session and session.status in ACTIVE_TRACKING:
        session.status = TrackingStatus.STOPPED
        session.stopped_at = now
    arrival = payload or ArrivalCreate()
    booking.arrived_at = now
    if arrival.latitude is not None:
        booking.arrival_latitude = arrival.latitude
        booking.arrival_longitude = arrival.longitude
        booking.arrival_accuracy = arrival.accuracy
        if booking.latitude is not None and booking.longitude is not None:
            booking.arrival_review_warning = (
                haversine_km(
                    arrival.latitude,
                    arrival.longitude,
                    booking.latitude,
                    booking.longitude,
                )
                > 2
            )
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=booking.status,
        current=BookingStatus.ARRIVED,
        event_type="RESCUER_ARRIVED",
        details=(
            "The fictional demo rescuer marked the simulated journey as arrived. "
            "Arrival coordinates remain private."
        ),
    )
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type="RESCUER_ARRIVED",
        title="Simulated arrival",
        body=f"The simulated journey for {booking.booking_reference} was marked arrived.",
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="booking.arrived.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    db.commit()
    return _response(db, booking, user, session)
