import math
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.entities import (
    Booking,
    BookingEvent,
    BookingStatusHistory,
    District,
    Organization,
    RescuerProfile,
    State,
    Subdistrict,
    User,
    Village,
)
from app.schemas.marketplace import (
    BookingEventResponse,
    BookingHistoryResponse,
    BookingResponse,
    PublicRescuer,
)


def fail(status: int, code: str, message: str, *, details=None) -> APIError:
    return APIError(status, code, message, details=details)


def validate_location_hierarchy(
    db: Session,
    *,
    state_code: str,
    district_code: str | None,
    subdistrict_code: str | None,
    village_code: str | None,
) -> Village | None:
    state = db.scalar(select(State).where(State.lgd_code == state_code, State.is_active.is_(True)))
    if state is None:
        raise fail(
            422, "INVALID_STATE_CODE", "Select an active state from the imported LGD directory"
        )
    district = None
    if district_code:
        district = db.scalar(
            select(District).where(
                District.lgd_code == district_code,
                District.state_code == state_code,
                District.is_active.is_(True),
            )
        )
        if district is None:
            raise fail(
                422,
                "INVALID_DISTRICT_HIERARCHY",
                "The district does not belong to the selected state",
            )
    if subdistrict_code:
        if district is None:
            raise fail(422, "DISTRICT_REQUIRED", "A district is required before a subdistrict")
        subdistrict = db.scalar(
            select(Subdistrict).where(
                Subdistrict.lgd_code == subdistrict_code,
                Subdistrict.district_code == district_code,
                Subdistrict.is_active.is_(True),
            )
        )
        if subdistrict is None:
            raise fail(
                422,
                "INVALID_SUBDISTRICT_HIERARCHY",
                "The subdistrict does not belong to the selected district",
            )
    if village_code:
        if not subdistrict_code:
            raise fail(422, "SUBDISTRICT_REQUIRED", "A subdistrict is required before a village")
        village = db.scalar(
            select(Village).where(
                Village.lgd_code == village_code,
                Village.subdistrict_code == subdistrict_code,
                Village.is_active.is_(True),
            )
        )
        if village is None:
            raise fail(
                422,
                "INVALID_VILLAGE_HIERARCHY",
                "The village does not belong to the selected subdistrict",
            )
        return village
    return None


def public_rescuer(
    profile: RescuerProfile,
    user: User,
    organization: Organization,
    distance_km: float | None = None,
) -> PublicRescuer:
    return PublicRescuer(
        id=profile.id,
        display_name=profile.public_display_name or user.name,
        organization=organization.name,
        years_experience=profile.years_experience,
        languages=profile.languages or [],
        service_area=profile.service_area_description,
        availability=profile.availability,
        verification_status=profile.verification_status,
        authorization_expiry=profile.authorization_expiry,
        average_rating=Decimal(profile.average_rating or 0),
        review_count=profile.review_count,
        completed_service_count=profile.completed_service_count,
        distance_km=round(distance_km, 1) if distance_km is not None else None,
        is_demo=profile.is_demo,
        pricing_enabled=False,
        service_charge=None,
    )


def booking_response(db: Session, booking: Booking, viewer: User) -> BookingResponse:
    profile = db.get(RescuerProfile, booking.rescuer_id)
    rescuer_user = db.get(User, profile.user_id) if profile else None
    organization = (
        db.get(Organization, booking.organization_id) if booking.organization_id else None
    )
    is_customer = booking.customer_id == viewer.id
    is_privileged = viewer.role.value in {"COORDINATOR", "ADMIN"}
    is_rescuer = bool(profile and profile.user_id == viewer.id)
    if not (is_customer or is_rescuer or is_privileged):
        raise fail(403, "BOOKING_ACCESS_DENIED", "You cannot access this booking")

    latitude = booking.latitude
    longitude = booking.longitude
    manual_address = booking.manual_address
    landmark = booking.landmark
    precision = "EXACT_OWNER_VIEW"
    if is_rescuer and not is_customer and not is_privileged:
        latitude = round(latitude, 2) if latitude is not None else None
        longitude = round(longitude, 2) if longitude is not None else None
        manual_address = None
        landmark = None
        precision = "APPROXIMATE_RESCUER_VIEW"

    events = db.scalars(
        select(BookingEvent)
        .where(BookingEvent.booking_id == booking.id)
        .order_by(BookingEvent.created_at, BookingEvent.id)
    ).all()
    history = db.scalars(
        select(BookingStatusHistory)
        .where(BookingStatusHistory.booking_id == booking.id)
        .order_by(BookingStatusHistory.created_at, BookingStatusHistory.id)
    ).all()
    return BookingResponse(
        id=booking.id,
        booking_reference=booking.booking_reference,
        customer_id=booking.customer_id,
        rescuer_id=booking.rescuer_id,
        rescuer_display_name=(profile.public_display_name if profile else None)
        or (rescuer_user.name if rescuer_user else "Demo rescuer"),
        organization=organization.name
        if organization
        else (profile.organization_name if profile else ""),
        incident_id=booking.incident_id,
        state_code=booking.state_code,
        district_code=booking.district_code,
        subdistrict_code=booking.subdistrict_code,
        village_code=booking.village_code,
        manual_address=manual_address,
        landmark=landmark,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=booking.location_accuracy if is_customer or is_privileged else None,
        location_precision=precision,
        customer_notes=booking.customer_notes,
        status=booking.status,
        quoted_amount=booking.quoted_amount,
        currency=booking.currency,
        commission_rate_snapshot=booking.commission_rate_snapshot,
        payment_status=booking.payment_status.value,
        is_demo=booking.is_demo,
        pricing_enabled=False,
        live_dispatch_enabled=False,
        accepted_at=booking.accepted_at,
        responded_at=booking.responded_at,
        expires_at=booking.expires_at,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
        events=[BookingEventResponse.model_validate(item) for item in events],
        history=[BookingHistoryResponse.model_validate(item) for item in history],
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def pages(total: int, limit: int) -> int:
    return math.ceil(total / limit) if total else 0


def get_profile_for_user(db: Session, user_id: UUID) -> RescuerProfile | None:
    return db.scalar(select(RescuerProfile).where(RescuerProfile.user_id == user_id))
