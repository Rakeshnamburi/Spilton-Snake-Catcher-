import hashlib
import json
import math
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.marketplace_helpers import (
    booking_response,
    fail,
    get_profile_for_user,
    utcnow,
    validate_location_hierarchy,
)
from app.core.config import get_settings
from app.core.security import keyed_digest
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    AvailabilityHistory,
    AvailabilityStatus,
    Booking,
    BookingStatus,
    Incident,
    PaymentStatus,
    RescuerProfile,
    User,
)
from app.schemas.marketplace import BookingAction, BookingCreate, BookingPage, BookingResponse
from app.services.marketplace import (
    InvalidBookingTransition,
    add_booking_state,
    add_financial_snapshot,
    create_in_app_notification,
    expire_pending_bookings,
    haversine_km,
    rescuer_is_eligible,
    validate_booking_transition,
)
from app.services.rate_limit import rate_limiter
from app.services.tracking import stop_booking_tracking

router = APIRouter(tags=["bookings"])


def _idempotency_hash(user_id: UUID, key: str) -> str:
    return keyed_digest(f"booking:{user_id}:{key}")


def _payload_hash(payload: BookingCreate) -> str:
    body = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def _validated_idempotency_key(key: str | None) -> str:
    if not key:
        raise fail(400, "IDEMPOTENCY_KEY_REQUIRED", "An Idempotency-Key header is required")
    cleaned = key.strip()
    if not 8 <= len(cleaned) <= 128 or any(ord(character) < 33 for character in cleaned):
        raise fail(400, "INVALID_IDEMPOTENCY_KEY", "Use an 8–128 character idempotency key")
    return cleaned


def _limit(request: Request, user: User) -> None:
    retry = rate_limiter.check(
        f"booking-create:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=10,
        window_seconds=3600,
    )
    if retry is not None:
        raise fail(429, "RATE_LIMITED", "Too many booking requests", details={"retry_after": retry})


def _owned_booking(db: Session, booking_id: UUID, user: User, *, lock: bool = False) -> Booking:
    statement = select(Booking).where(Booking.id == booking_id)
    if lock:
        statement = statement.with_for_update()
    booking = db.scalar(statement)
    if booking is None:
        raise fail(404, "BOOKING_NOT_FOUND", "Booking not found")
    profile = get_profile_for_user(db, user.id)
    if (
        booking.customer_id != user.id
        and (profile is None or booking.rescuer_id != profile.id)
        and user.role.value not in {"COORDINATOR", "ADMIN"}
    ):
        raise fail(403, "BOOKING_ACCESS_DENIED", "You cannot access this booking")
    return booking


@router.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(
    payload: BookingCreate,
    request: Request,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.demo_mode or settings.authorized_operation_enabled:
        raise fail(503, "DEMO_MODE_REQUIRED", "Day 3 bookings are permitted only in demo mode")
    _limit(request, user)
    key = _validated_idempotency_key(idempotency_key)
    key_hash = _idempotency_hash(user.id, key)
    request_hash = _payload_hash(payload)
    existing = db.scalar(
        select(Booking).where(
            Booking.customer_id == user.id, Booking.idempotency_key_hash == key_hash
        )
    )
    if existing is not None:
        if existing.idempotency_request_hash != request_hash:
            raise fail(
                409,
                "IDEMPOTENCY_CONFLICT",
                "This idempotency key was already used for different booking details",
            )
        response.headers["X-Idempotent-Replay"] = "true"
        return booking_response(db, existing, user)

    profile = db.scalar(
        select(RescuerProfile).where(RescuerProfile.id == payload.rescuer_id).with_for_update()
    )
    if profile is None or not rescuer_is_eligible(db, profile, require_available=True):
        raise fail(409, "RESCUER_NOT_ELIGIBLE", "This demo rescuer is not eligible or available")
    if profile.user_id == user.id:
        raise fail(
            409, "SELF_BOOKING_NOT_ALLOWED", "A rescuer cannot create a booking with themselves"
        )
    village = validate_location_hierarchy(
        db,
        state_code=payload.state_code,
        district_code=payload.district_code,
        subdistrict_code=payload.subdistrict_code,
        village_code=payload.village_code,
    )
    if profile.state_code != payload.state_code or (
        payload.district_code and profile.district_code != payload.district_code
    ):
        raise fail(
            409,
            "OUTSIDE_SERVICE_AREA",
            "The selected location is outside this rescuer's approved coverage",
        )
    if payload.latitude is not None and profile.latitude is not None:
        distance = haversine_km(
            payload.latitude, payload.longitude, profile.latitude, profile.longitude
        )
        if distance > profile.service_radius_km:
            raise fail(
                409,
                "OUTSIDE_SERVICE_RADIUS",
                "The selected location is outside this rescuer's service radius",
            )
    if payload.incident_id:
        incident = db.get(Incident, payload.incident_id)
        if incident is None or incident.reporter_id != user.id:
            raise fail(404, "INCIDENT_NOT_FOUND", "Linked incident not found")

    now = utcnow()
    booking = Booking(
        booking_reference=f"DEMO-{secrets.token_hex(6).upper()}",
        customer_id=user.id,
        rescuer_id=profile.id,
        organization_id=profile.organization_id,
        incident_id=payload.incident_id,
        location_id=village.id if village else None,
        state_code=payload.state_code,
        district_code=payload.district_code,
        subdistrict_code=payload.subdistrict_code,
        village_code=payload.village_code,
        manual_address=payload.manual_address,
        landmark=payload.landmark,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_accuracy=payload.location_accuracy,
        customer_notes=payload.customer_notes,
        status=BookingStatus.REQUESTED,
        quoted_amount=None,
        currency="INR",
        commission_rate_snapshot=settings.default_commission_percent,
        payment_status=PaymentStatus.DISABLED,
        idempotency_key_hash=key_hash,
        idempotency_request_hash=request_hash,
        is_demo=True,
        expires_at=now + timedelta(minutes=settings.booking_response_minutes),
    )
    db.add(booking)
    db.flush()
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=None,
        current=BookingStatus.REQUESTED,
        event_type="BOOKING_REQUESTED",
        details="A simulated assistance request was created; no live dispatch occurred.",
    )
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=BookingStatus.REQUESTED,
        current=BookingStatus.PENDING_RESCUER_RESPONSE,
        event_type="BOOKING_PENDING",
        details="The simulated request is awaiting a fictional demo response.",
    )
    add_financial_snapshot(db, booking)
    create_in_app_notification(
        db,
        recipient_id=user.id,
        booking_id=booking.id,
        event_type="BOOKING_REQUESTED",
        title="Demo request received",
        body=f"Demo booking {booking.booking_reference} is awaiting a simulated response.",
    )
    create_in_app_notification(
        db,
        recipient_id=profile.user_id,
        booking_id=booking.id,
        event_type="BOOKING_ASSIGNED",
        title="New simulated booking assigned",
        body=f"Demo booking {booking.booking_reference} is awaiting a simulated response.",
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="booking.create.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        replay = db.scalar(
            select(Booking).where(
                Booking.customer_id == user.id, Booking.idempotency_key_hash == key_hash
            )
        )
        if replay and replay.idempotency_request_hash == request_hash:
            response.headers["X-Idempotent-Replay"] = "true"
            return booking_response(db, replay, user)
        raise fail(409, "BOOKING_CONFLICT", "The booking could not be created safely") from error
    db.refresh(booking)
    return booking_response(db, booking, user)


@router.get("/bookings/mine", response_model=BookingPage)
def my_bookings(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    status: BookingStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    expire_pending_bookings(db)
    filters = [Booking.customer_id == user.id]
    if status:
        filters.append(Booking.status == status)
    total = db.scalar(select(func.count()).select_from(Booking).where(*filters)) or 0
    rows = db.scalars(
        select(Booking)
        .where(*filters)
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return BookingPage(
        items=[booking_response(db, booking, user) for booking in rows],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/bookings/assigned", response_model=BookingPage)
def assigned_bookings(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    status: BookingStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_profile_for_user(db, user.id)
    if profile is None or user.role.value != "RESCUER":
        raise fail(403, "RESCUER_REQUIRED", "A verified rescuer account is required")
    expire_pending_bookings(db)
    filters = [Booking.rescuer_id == profile.id]
    if status:
        filters.append(Booking.status == status)
    total = db.scalar(select(func.count()).select_from(Booking).where(*filters)) or 0
    rows = db.scalars(
        select(Booking)
        .where(*filters)
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return BookingPage(
        items=[booking_response(db, booking, user) for booking in rows],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    expire_pending_bookings(db)
    return booking_response(db, _owned_booking(db, booking_id, user), user)


def _rescuer_action(
    db: Session,
    booking_id: UUID,
    user: User,
    target: BookingStatus,
    note: str | None,
) -> BookingResponse:
    booking = _owned_booking(db, booking_id, user, lock=True)
    profile = get_profile_for_user(db, user.id)
    if profile is None or booking.rescuer_id != profile.id:
        raise fail(403, "ASSIGNED_RESCUER_REQUIRED", "Only the assigned rescuer can respond")
    if not rescuer_is_eligible(db, profile, require_available=target == BookingStatus.ACCEPTED):
        raise fail(
            409, "RESCUER_NOT_ELIGIBLE", "Rescuer authorization or availability is not eligible"
        )
    try:
        validate_booking_transition(booking.status, target)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error
    previous = booking.status
    now = utcnow()
    booking.responded_at = now
    if target == BookingStatus.ACCEPTED:
        booking.accepted_at = now
        old_availability = profile.availability
        profile.availability = AvailabilityStatus.BUSY
        profile.availability_updated_at = now
        db.add(
            AvailabilityHistory(
                rescuer_profile_id=profile.id,
                previous_status=old_availability.value,
                new_status=AvailabilityStatus.BUSY.value,
            )
        )
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=previous,
        current=target,
        event_type=f"BOOKING_{target.value}",
        details=f"The fictional demo rescuer {target.value.lower()} the simulated request.",
        note=note,
    )
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type=f"BOOKING_{target.value}",
        title=f"Demo request {target.value.lower()}",
        body=f"Demo booking {booking.booking_reference} was {target.value.lower()} in simulation.",
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action=f"booking.{target.value.lower()}.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    db.commit()
    db.refresh(booking)
    return booking_response(db, booking, user)


@router.post("/bookings/{booking_id}/accept", response_model=BookingResponse)
def accept_booking(
    booking_id: UUID,
    payload: BookingAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _rescuer_action(db, booking_id, user, BookingStatus.ACCEPTED, payload.note)


@router.post("/bookings/{booking_id}/reject", response_model=BookingResponse)
def reject_booking(
    booking_id: UUID,
    payload: BookingAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _rescuer_action(db, booking_id, user, BookingStatus.REJECTED, payload.note)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: UUID,
    payload: BookingAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    if booking.customer_id != user.id:
        raise fail(403, "CUSTOMER_REQUIRED", "Only the customer can cancel this booking")
    try:
        validate_booking_transition(booking.status, BookingStatus.CANCELLED)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error
    previous = booking.status
    stop_booking_tracking(
        db,
        booking,
        actor_id=user.id,
        reason="Demo tracking stopped automatically because the customer cancelled the booking.",
    )
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=previous,
        current=BookingStatus.CANCELLED,
        event_type="BOOKING_CANCELLED",
        details="The customer cancelled the simulated request.",
        note=payload.note,
    )
    profile = db.get(RescuerProfile, booking.rescuer_id)
    if (
        previous
        in {
            BookingStatus.ACCEPTED,
            BookingStatus.EN_ROUTE,
            BookingStatus.ARRIVED,
            BookingStatus.IN_PROGRESS,
        }
        and profile
    ):
        profile.availability = AvailabilityStatus.AVAILABLE
        profile.availability_updated_at = utcnow()
        profile.last_seen_at = utcnow()
    if profile:
        create_in_app_notification(
            db,
            recipient_id=profile.user_id,
            booking_id=booking.id,
            event_type="BOOKING_CANCELLED",
            title="Demo request cancelled",
            body=f"Demo booking {booking.booking_reference} was cancelled.",
        )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="booking.cancel.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    db.commit()
    db.refresh(booking)
    return booking_response(db, booking, user)
