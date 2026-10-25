import math
import re
import secrets
from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.api.marketplace_helpers import (
    fail,
    get_profile_for_user,
    public_rescuer,
    utcnow,
    validate_location_hierarchy,
)
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    AvailabilityHistory,
    AvailabilityStatus,
    District,
    Organization,
    RescuerDocument,
    RescuerProfile,
    RescuerVerificationHistory,
    Role,
    State,
    User,
    VerificationStatus,
)
from app.schemas.marketplace import (
    AvailabilityUpdate,
    PublicRescuer,
    RescuerApplicationCreate,
    RescuerApplicationResponse,
    RescuerPage,
)
from app.services.marketplace import (
    expire_stale_rescuers,
    haversine_km,
    organization_is_approved,
    rescuer_is_eligible,
)
from app.services.media_storage import (
    MediaValidationError,
    StorageError,
    get_media_storage,
    validate_and_sanitize_image,
)
from app.services.rate_limit import rate_limiter

router = APIRouter(tags=["rescuers"])
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _limit(request: Request, user: User, action: str, limit: int, window: int) -> None:
    retry = rate_limiter.check(
        f"{action}:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=limit,
        window_seconds=window,
    )
    if retry is not None:
        raise fail(
            429,
            "RATE_LIMITED",
            "Too many requests; try again later",
            details={"retry_after": retry},
        )


@router.post("/rescuers/onboarding", response_model=RescuerApplicationResponse, status_code=201)
def create_rescuer_application(
    payload: RescuerApplicationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _limit(request, user, "rescuer-application", 5, 3600)
    if get_profile_for_user(db, user.id) is not None:
        raise fail(
            409, "APPLICATION_EXISTS", "A rescuer application already exists for this account"
        )
    validate_location_hierarchy(
        db,
        state_code=payload.state_code,
        district_code=payload.district_code,
        subdistrict_code=payload.subdistrict_code,
        village_code=payload.village_code,
    )
    organization = (
        db.get(Organization, payload.organization_id) if payload.organization_id else None
    )
    if payload.organization_id and organization is None:
        raise fail(422, "ORGANIZATION_NOT_FOUND", "The selected organization does not exist")
    if organization is None:
        state = db.scalar(select(State).where(State.lgd_code == payload.state_code))
        district = db.scalar(select(District).where(District.lgd_code == payload.district_code))
        organization = Organization(
            name=payload.organization_name,
            state=state.name,
            district=district.name,
            organization_type="RESCUER_APPLICATION",
            verification_status=VerificationStatus.PENDING,
        )
        db.add(organization)
        db.flush()

    profile = RescuerProfile(
        user_id=user.id,
        organization_id=organization.id,
        verification_status=VerificationStatus.PENDING_VERIFICATION,
        public_display_name=payload.public_display_name,
        state_code=payload.state_code,
        district_code=payload.district_code,
        subdistrict_code=payload.subdistrict_code,
        village_code=payload.village_code,
        organization_name=organization.name,
        years_experience=payload.years_experience,
        languages=payload.languages,
        training_details=payload.training_details,
        authorization_reference=payload.authorization_reference,
        issuing_authority=payload.issuing_authority,
        authorization_issue_date=payload.authorization_issue_date,
        authorization_expiry=payload.authorization_expiry,
        service_area_description=payload.service_area_description,
        service_radius_km=payload.service_radius_km,
        coverage_subdistrict_codes=payload.coverage_subdistrict_codes,
        latitude=payload.latitude,
        longitude=payload.longitude,
        operating_hours=payload.operating_hours,
        availability=AvailabilityStatus.OFFLINE,
        is_demo=True,
    )
    db.add(profile)
    db.flush()
    db.add(
        RescuerVerificationHistory(
            rescuer_profile_id=profile.id,
            actor_id=user.id,
            previous_status=None,
            new_status=VerificationStatus.PENDING_VERIFICATION.value,
            note="Public demo rescuer application submitted; no verification was granted.",
        )
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="rescuer.application.create",
            entity_type="rescuer_profile",
            entity_id=str(profile.id),
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/rescuers/me", response_model=RescuerApplicationResponse)
def my_rescuer_application(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = get_profile_for_user(db, user.id)
    if profile is None:
        raise fail(404, "APPLICATION_NOT_FOUND", "No rescuer application exists for this account")
    return profile


@router.patch("/rescuers/me/availability", response_model=RescuerApplicationResponse)
def update_availability(
    payload: AvailabilityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_profile_for_user(db, user.id)
    if profile is None:
        raise fail(404, "APPLICATION_NOT_FOUND", "No rescuer application exists for this account")
    if user.role != Role.RESCUER or profile.verification_status != VerificationStatus.VERIFIED:
        raise fail(
            403,
            "RESCUER_NOT_VERIFIED",
            "Only an administrator-verified rescuer can update availability",
        )
    if profile.authorization_expiry is None or profile.authorization_expiry < date.today():
        raise fail(409, "AUTHORIZATION_EXPIRED", "Expired authorization cannot be marked available")
    if not organization_is_approved(db, profile):
        raise fail(409, "ORGANIZATION_NOT_VERIFIED", "The affiliated organization is not verified")
    previous = profile.availability
    profile.availability = payload.status
    profile.last_seen_at = utcnow()
    profile.availability_updated_at = utcnow()
    if payload.operating_hours is not None:
        profile.operating_hours = payload.operating_hours
    db.add(
        AvailabilityHistory(
            rescuer_profile_id=profile.id,
            previous_status=previous.value,
            new_status=payload.status.value,
        )
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="rescuer.availability.update",
            entity_type="rescuer_profile",
            entity_id=str(profile.id),
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/rescuers/nearby", response_model=RescuerPage)
def nearby_rescuers(
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=100),
    state_code: str | None = Query(default=None, max_length=20),
    district_code: str | None = Query(default=None, max_length=20),
    subdistrict_code: str | None = Query(default=None, max_length=20),
    min_experience: int = Query(default=0, ge=0, le=80),
    min_rating: float = Query(default=0, ge=0, le=5),
    language: str | None = Query(default=None, max_length=60),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if (latitude is None) != (longitude is None):
        raise fail(
            422, "COORDINATE_PAIR_REQUIRED", "Latitude and longitude must be supplied together"
        )
    if latitude is None and not state_code:
        raise fail(422, "LOCATION_REQUIRED", "Share coordinates or select an imported LGD state")
    expire_stale_rescuers(db)
    conditions = [
        RescuerProfile.verification_status == VerificationStatus.VERIFIED,
        RescuerProfile.availability == AvailabilityStatus.AVAILABLE,
        RescuerProfile.authorization_expiry >= date.today(),
        RescuerProfile.is_demo.is_(True),
        RescuerProfile.years_experience >= min_experience,
        RescuerProfile.average_rating >= min_rating,
        Organization.verification_status == VerificationStatus.VERIFIED,
        User.is_active.is_(True),
    ]
    if state_code:
        conditions.append(RescuerProfile.state_code == state_code.strip())
    if district_code:
        conditions.append(RescuerProfile.district_code == district_code.strip())
    if language:
        # JSON containment differs by database; keep the portable pre-filter bounded and
        # apply a normalized exact language filter below.
        language = language.strip().casefold()

    postgis_distance = None
    if latitude is not None and db.get_bind().dialect.name == "postgresql":
        rescuer_point = func.ST_SetSRID(
            func.ST_MakePoint(RescuerProfile.longitude, RescuerProfile.latitude), 4326
        )
        customer_point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        postgis_distance = (func.ST_DistanceSphere(rescuer_point, customer_point) / 1000.0).label(
            "distance_km"
        )
        conditions.extend(
            [
                RescuerProfile.latitude.is_not(None),
                RescuerProfile.longitude.is_not(None),
                # The geometry bounding predicate uses the matching GiST expression
                # index; the exact spherical distance is still enforced below.
                func.ST_DWithin(rescuer_point, customer_point, radius_km / 111.32),
            ]
        )
    columns = [RescuerProfile, User, Organization]
    if postgis_distance is not None:
        columns.append(postgis_distance)
    statement = (
        select(*columns)
        .join(User, User.id == RescuerProfile.user_id)
        .join(Organization, Organization.id == RescuerProfile.organization_id)
        .where(*conditions)
        .order_by(RescuerProfile.years_experience.desc(), RescuerProfile.created_at)
    )
    rows = db.execute(statement).all()
    def coverage_scope(profile: RescuerProfile) -> str | None:
        """How this profile covers the searched area, without exposing exact codes."""

        if subdistrict_code:
            covers = profile.subdistrict_code == subdistrict_code or subdistrict_code in (
                profile.coverage_subdistrict_codes or []
            )
            if covers:
                return "MANDAL"
            if district_code and profile.district_code == district_code:
                return "DISTRICT"
            return "OTHER"
        if district_code:
            return "DISTRICT" if profile.district_code == district_code else "OTHER"
        if state_code:
            return "STATE" if profile.state_code == state_code else "OTHER"
        return None

    eligible: list[tuple[RescuerProfile, User, Organization, float | None, str | None]] = []
    for row in rows:
        profile, rescuer_user, organization = row[:3]
        if language and language not in {item.casefold() for item in (profile.languages or [])}:
            continue
        distance = float(row[3]) if postgis_distance is not None else None
        if latitude is not None:
            if profile.latitude is None or profile.longitude is None:
                continue
            if distance is None:
                distance = haversine_km(latitude, longitude, profile.latitude, profile.longitude)
            if distance > min(radius_km, profile.service_radius_km):
                continue
        eligible.append((profile, rescuer_user, organization, distance, coverage_scope(profile)))
    eligible.sort(key=lambda row: (row[3] is None, row[3] or 0, -row[0].years_experience))
    total = len(eligible)
    selected = eligible[(page - 1) * limit : page * limit]
    return RescuerPage(
        items=[
            public_rescuer(profile, item_user, org, distance, scope)
            for profile, item_user, org, distance, scope in selected
        ],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/rescuers/{rescuer_id}", response_model=PublicRescuer)
def rescuer_profile(rescuer_id: UUID, db: Session = Depends(get_db)):
    row = db.execute(
        select(RescuerProfile, User, Organization)
        .join(User, User.id == RescuerProfile.user_id)
        .join(Organization, Organization.id == RescuerProfile.organization_id)
        .where(RescuerProfile.id == rescuer_id)
    ).one_or_none()
    if row is None:
        raise fail(404, "RESCUER_NOT_FOUND", "Rescuer profile not found")
    profile, rescuer_user, organization = row
    if not rescuer_is_eligible(db, profile, require_available=False):
        raise fail(404, "RESCUER_NOT_BOOKABLE", "No eligible demo rescuer profile is available")
    return public_rescuer(profile, rescuer_user, organization)


def _safe_document_name(filename: str | None, extension: str) -> str:
    candidate = Path((filename or "authorization-document").replace("\x00", "")).name
    stem = re.sub(r"[^A-Za-z0-9 _.-]", "_", Path(candidate).stem)[:180].strip(" .")
    return f"{stem or 'authorization-document'}{extension}"


@router.post("/rescuers/onboarding/documents", status_code=201)
async def upload_authorization_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _limit(request, user, "rescuer-document", 10, 3600)
    profile = get_profile_for_user(db, user.id)
    if profile is None:
        raise fail(404, "APPLICATION_NOT_FOUND", "Create a rescuer application first")
    body = await file.read(MAX_DOCUMENT_BYTES + 1)
    await file.close()
    if not body:
        raise fail(422, "EMPTY_DOCUMENT", "The authorization document is empty")
    if len(body) > MAX_DOCUMENT_BYTES:
        raise fail(413, "DOCUMENT_TOO_LARGE", "Authorization documents must be 10 MB or smaller")

    declared = (file.content_type or "").split(";", 1)[0].lower()
    if body.startswith(b"%PDF-"):
        if declared not in {"", "application/pdf"}:
            raise fail(422, "DOCUMENT_TYPE_MISMATCH", "The file signature does not match its type")
        stored_body, content_type, extension = body, "application/pdf", ".pdf"
    else:
        try:
            stored_body, content_type, extension = await run_in_threadpool(
                validate_and_sanitize_image, body, declared
            )
        except MediaValidationError as error:
            raise fail(422, error.code, str(error)) from error

    storage_key = f"rescuers/{profile.id}/{secrets.token_hex(24)}{extension}"
    try:
        await run_in_threadpool(get_media_storage().put, storage_key, stored_body, content_type)
    except Exception as error:
        raise fail(
            503, "PRIVATE_STORAGE_UNAVAILABLE", "Private document storage is unavailable"
        ) from error
    document = RescuerDocument(
        rescuer_profile_id=profile.id,
        storage_key=storage_key,
        original_filename=_safe_document_name(file.filename, extension),
        content_type=content_type,
        file_size=len(stored_body),
    )
    db.add(document)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="rescuer.document.upload",
            entity_type="rescuer_profile",
            entity_id=str(profile.id),
        )
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        await run_in_threadpool(get_media_storage().delete, storage_key)
        raise
    db.refresh(document)
    return {
        "id": str(document.id),
        "original_filename": document.original_filename,
        "content_type": document.content_type,
        "file_size": document.file_size,
        "uploaded_at": document.uploaded_at,
        "private": True,
    }


@router.get("/rescuers/me/documents/{document_id}")
def retrieve_own_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_profile_for_user(db, user.id)
    document = db.get(RescuerDocument, document_id)
    if profile is None or document is None or document.rescuer_profile_id != profile.id:
        raise fail(404, "DOCUMENT_NOT_FOUND", "Authorization document not found")
    try:
        stored = get_media_storage().get(document.storage_key, document.content_type)
    except StorageError as error:
        raise fail(404, "DOCUMENT_NOT_FOUND", "Authorization document is unavailable") from error
    return Response(
        stored.body,
        media_type=stored.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'attachment; filename="{document.original_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
