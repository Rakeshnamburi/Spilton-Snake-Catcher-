import json
import logging
import math
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.api.admin_marketplace import router as admin_marketplace_router
from app.api.bookings import router as bookings_router
from app.api.day5_payments import router as day5_payments_router
from app.api.day5_rescue import router as day5_rescue_router
from app.api.day5_reviews import router as day5_reviews_router
from app.api.deps import get_current_user, require_roles
from app.api.devices import router as devices_router
from app.api.locations import router as locations_router
from app.api.notifications import router as notifications_router
from app.api.realtime import router as realtime_router
from app.api.rescuers import router as rescuers_router
from app.api.tracking import router as tracking_router
from app.api.webhooks import router as webhooks_router
from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import create_access_token, hash_password, keyed_digest, verify_password
from app.db.session import get_db
from app.models.entities import (
    AccountDataRequest,
    AuditLog,
    EmergencyContact,
    Incident,
    IncidentEvent,
    IncidentMedia,
    IncidentStatus,
    Organization,
    Role,
    Urgency,
    User,
    VerificationStatus,
)
from app.schemas.api import (
    AccountDataRequestCreate,
    AccountDataRequestResponse,
    AdminIncidentPage,
    EmergencyContactResponse,
    IncidentCreate,
    IncidentEventResponse,
    IncidentMediaResponse,
    IncidentPage,
    IncidentResponse,
    IncidentStatusUpdate,
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.incident_workflow import (
    CITIZEN_CANCELLABLE,
    InvalidStatusTransition,
    validate_transition,
)
from app.services.media_storage import (
    MAX_MEDIA_BYTES,
    MAX_MEDIA_PER_INCIDENT,
    MediaValidationError,
    StorageError,
    get_media_storage,
    make_storage_key,
    safe_original_filename,
    validate_and_sanitize_image,
)
from app.services.rate_limit import rate_limiter

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


def api_error(status_code: int, code: str, message: str, *, details=None) -> APIError:
    return APIError(status_code, code, message, details=details)


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    retry_after = rate_limiter.check(key, limit=limit, window_seconds=window_seconds)
    if retry_after is not None:
        raise APIError(
            429,
            "RATE_LIMITED",
            "Too many requests. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )


def set_session_cookie(response: Response, token: str) -> str:
    settings = get_settings()
    csrf_token = secrets.token_urlsafe(32)
    common = {
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "max_age": settings.access_token_minutes * 60,
        "path": "/",
    }
    response.set_cookie("spilton_session", token, httponly=True, **common)
    response.set_cookie("spilton_csrf", csrf_token, httponly=False, **common)
    return csrf_token


def make_reference() -> str:
    return f"SPR-{datetime.now(timezone.utc):%y%m%d}-{secrets.token_hex(6).upper()}"


def request_digest(payload: IncidentCreate) -> str:
    excluded: set[str] = set()
    if "sighting_at" not in payload.model_fields_set:
        excluded.add("sighting_at")
    canonical = json.dumps(
        payload.model_dump(mode="json", exclude=excluded), sort_keys=True, separators=(",", ":")
    )
    return keyed_digest(canonical)


def idempotency_digest(user_id: UUID, key: str) -> str:
    return keyed_digest(f"{user_id}:{key}")


def validate_idempotency_key(key: str | None) -> str | None:
    if key is None:
        return None
    if not 8 <= len(key) <= 128 or not key.isascii() or any(ord(char) < 33 for char in key):
        raise api_error(
            400,
            "INVALID_IDEMPOTENCY_KEY",
            "Idempotency-Key must contain 8 to 128 visible ASCII characters",
        )
    return key


def authorized_incident_query(incident_id: UUID):
    return select(Incident).where(Incident.id == incident_id).options(selectinload(Incident.media))


def get_authorized_incident(db: Session, incident_id: UUID, user: User) -> Incident:
    incident = db.scalar(authorized_incident_query(incident_id))
    if incident is None:
        raise api_error(404, "INCIDENT_NOT_FOUND", "Incident not found")
    if incident.reporter_id != user.id and user.role not in {Role.COORDINATOR, Role.ADMIN}:
        raise api_error(403, "INCIDENT_ACCESS_DENIED", "You cannot access this incident")
    return incident


def load_incident(db: Session, incident_id: UUID) -> Incident:
    incident = db.scalar(authorized_incident_query(incident_id))
    if incident is None:
        raise api_error(404, "INCIDENT_NOT_FOUND", "Incident not found")
    return incident


@router.get("/status")
def platform_status():
    return {
        "mode": "DEMO",
        "operational_dispatch": False,
        "authorized_operation": False,
        "real_payments": False,
        "external_rescue_notifications": False,
        "message": "Demo Platform — Not an Active Emergency Rescue Service.",
    }


@router.post("/auth/register", response_model=LoginResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    remote = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"register:{remote}", limit=5, window_seconds=60)
    email = payload.email.lower()
    if db.scalar(select(User).where((User.email == email) | (User.phone == payload.phone))):
        raise api_error(409, "ACCOUNT_EXISTS", "An account with these details already exists")
    user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=Role.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.token_version)
    csrf_token = set_session_cookie(response, token)
    return LoginResponse(user=user, access_token=token, csrf_token=csrf_token)


@router.post("/auth/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
):
    remote = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"login:{remote}", limit=5, window_seconds=60)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid email or password")
    token = create_access_token(user.id, user.token_version)
    csrf_token = set_session_cookie(response, token)
    return LoginResponse(user=user, access_token=token, csrf_token=csrf_token)


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.token_version += 1
    db.add(
        AuditLog(
            actor_id=user.id,
            action="AUTH_SESSION_REVOKED",
            entity_type="user",
            entity_id=str(user.id),
        )
    )
    db.commit()
    response.delete_cookie("spilton_session", path="/")
    response.delete_cookie("spilton_csrf", path="/")


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/auth/refresh", response_model=LoginResponse)
def refresh_session(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rotate the short-lived access session and invalidate its previous token."""

    user.token_version += 1
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.token_version)
    csrf_token = set_session_cookie(response, token)
    return LoginResponse(user=user, access_token=token, csrf_token=csrf_token)


@router.patch("/auth/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise api_error(401, "INVALID_CREDENTIALS", "Current password is incorrect")
    email = str(payload.email).lower()
    duplicate = db.scalar(
        select(User).where(
            User.id != user.id,
            or_(User.email == email, User.phone == payload.phone),
        )
    )
    if duplicate:
        raise api_error(409, "ACCOUNT_EXISTS", "An account with these details already exists")
    user.name = payload.name
    user.email = email
    user.phone = payload.phone
    db.add(
        AuditLog(
            actor_id=user.id,
            action="PROFILE_UPDATED",
            entity_type="user",
            entity_id=str(user.id),
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/auth/account-requests",
    response_model=AccountDataRequestResponse,
    status_code=201,
)
def create_account_data_request(
    payload: AccountDataRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.scalar(
        select(AccountDataRequest).where(
            AccountDataRequest.user_id == user.id,
            AccountDataRequest.request_type == payload.request_type,
            AccountDataRequest.status.in_(["REQUESTED", "UNDER_REVIEW"]),
        )
    )
    if existing:
        return existing
    item = AccountDataRequest(
        user_id=user.id,
        request_type=payload.request_type,
        reason=payload.reason,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=user.id,
            action=f"ACCOUNT_{payload.request_type}_REQUESTED",
            entity_type="account_data_request",
            entity_id=str(item.id),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/auth/account-requests", response_model=list[AccountDataRequestResponse])
def list_account_data_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list(
        db.scalars(
            select(AccountDataRequest)
            .where(AccountDataRequest.user_id == user.id)
            .order_by(AccountDataRequest.created_at.desc())
        )
    )


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(
    payload: IncidentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_rate_limit(f"incident-create:{user.id}", limit=10, window_seconds=60)
    key = validate_idempotency_key(idempotency_key)
    key_hash = idempotency_digest(user.id, key) if key else None
    payload_hash = request_digest(payload) if key else None

    if key_hash:
        existing = db.scalar(
            select(Incident)
            .where(
                Incident.reporter_id == user.id,
                Incident.idempotency_key_hash == key_hash,
            )
            .options(selectinload(Incident.media))
        )
        if existing:
            if existing.idempotency_request_hash != payload_hash:
                raise api_error(
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "This idempotency key was already used for a different report",
                )
            response.headers["X-Idempotent-Replay"] = "true"
            return existing

    incident = Incident(
        reference_code=make_reference(),
        reporter_id=user.id,
        reporter_name=payload.reporter_name,
        contact_phone=payload.contact_phone,
        reporter_email=str(payload.reporter_email) if payload.reporter_email else None,
        state=payload.state,
        district=payload.district,
        city=payload.city,
        landmark=payload.landmark,
        address_description=payload.address_description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_accuracy=payload.location_accuracy,
        sighting_at=payload.sighting_at,
        description=payload.description,
        injury_reported=payload.injury_reported,
        snake_visible=payload.snake_visible,
        immediate_danger=payload.immediate_danger,
        urgency=(
            Urgency.SNAKEBITE
            if payload.injury_reported
            else Urgency.HIGH
            if payload.immediate_danger
            else payload.urgency
        ),
        status=IncidentStatus.CREATED,
        is_demo=True,
        idempotency_key_hash=key_hash,
        idempotency_request_hash=payload_hash,
    )
    db.add(incident)
    try:
        db.flush()
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                actor_id=user.id,
                event_type="INCIDENT_CREATED",
                details="Demo incident created; no responder was dispatched.",
            )
        )
        db.add(
            AuditLog(
                actor_id=user.id,
                action="incident.create",
                entity_type="incident",
                entity_id=str(incident.id),
            )
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if key_hash:
            existing = db.scalar(
                select(Incident)
                .where(
                    Incident.reporter_id == user.id,
                    Incident.idempotency_key_hash == key_hash,
                )
                .options(selectinload(Incident.media))
            )
            if existing and existing.idempotency_request_hash == payload_hash:
                response.headers["X-Idempotent-Replay"] = "true"
                return existing
        raise api_error(
            409, "INCIDENT_CONFLICT", "Could not create this report; retry safely"
        ) from error
    return load_incident(db, incident.id)


@router.get("/incidents/mine", response_model=IncidentPage)
def my_incidents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: IncidentStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = [Incident.reporter_id == user.id]
    if status:
        filters.append(Incident.status == status)
    total = db.scalar(select(func.count()).select_from(Incident).where(*filters)) or 0
    items = db.scalars(
        select(Incident)
        .where(*filters)
        .order_by(Incident.created_at.desc(), Incident.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def incident_detail(
    incident_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return get_authorized_incident(db, incident_id, user)


@router.get("/incidents/{incident_id}/events", response_model=list[IncidentEventResponse])
def incident_events(
    incident_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_authorized_incident(db, incident_id, user)
    return db.scalars(
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.created_at, IncidentEvent.id)
    ).all()


@router.get("/incidents/{incident_id}/media", response_model=list[IncidentMediaResponse])
def incident_media_list(
    incident_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    incident = get_authorized_incident(db, incident_id, user)
    return incident.media


@router.post(
    "/incidents/{incident_id}/media", response_model=IncidentMediaResponse, status_code=201
)
async def upload_incident_media(
    incident_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_rate_limit(f"incident-upload:{user.id}", limit=15, window_seconds=60)
    incident = db.scalar(authorized_incident_query(incident_id).with_for_update())
    if incident is None:
        raise api_error(404, "INCIDENT_NOT_FOUND", "Incident not found")
    if incident.reporter_id != user.id and user.role not in {Role.COORDINATOR, Role.ADMIN}:
        raise api_error(403, "INCIDENT_ACCESS_DENIED", "You cannot access this incident")
    if len(incident.media) >= MAX_MEDIA_PER_INCIDENT:
        raise api_error(409, "MEDIA_LIMIT_REACHED", "An incident can contain at most 3 images")

    try:
        raw = await file.read(MAX_MEDIA_BYTES + 1)
    finally:
        await file.close()
    try:
        sanitized, content_type, extension = await run_in_threadpool(
            validate_and_sanitize_image, raw, file.content_type
        )
    except MediaValidationError as error:
        raise api_error(422, error.code, str(error)) from error

    storage_key = make_storage_key(incident.id, extension)
    original_filename = safe_original_filename(file.filename, extension)
    storage = None
    try:
        storage = get_media_storage()
        await run_in_threadpool(storage.put, storage_key, sanitized, content_type)
    except Exception as error:
        raise api_error(
            503, "MEDIA_STORAGE_UNAVAILABLE", "Private media storage is unavailable"
        ) from error

    media = IncidentMedia(
        incident_id=incident.id,
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=content_type,
        file_size=len(sanitized),
    )
    db.add(media)
    try:
        db.flush()
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                actor_id=user.id,
                event_type="MEDIA_UPLOADED",
                details="An optional image was securely added to the demo incident.",
            )
        )
        db.add(
            AuditLog(
                actor_id=user.id,
                action="incident.media.upload",
                entity_type="incident_media",
                entity_id=str(media.id),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if storage is not None:
            try:
                await run_in_threadpool(storage.delete, storage_key)
            except Exception:
                logger.exception("Could not clean up private media after a database failure")
        raise
    db.refresh(media)
    return media


@router.get("/incidents/{incident_id}/media/{media_id}")
def retrieve_incident_media(
    incident_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_authorized_incident(db, incident_id, user)
    media = db.scalar(
        select(IncidentMedia).where(
            IncidentMedia.id == media_id, IncidentMedia.incident_id == incident_id
        )
    )
    if media is None:
        raise api_error(404, "MEDIA_NOT_FOUND", "Incident media not found")
    try:
        stored = get_media_storage().get(media.storage_key, media.content_type)
    except StorageError as error:
        raise api_error(404, "MEDIA_NOT_FOUND", "Incident media is unavailable") from error
    except Exception as error:
        raise api_error(
            503, "MEDIA_STORAGE_UNAVAILABLE", "Private media storage is unavailable"
        ) from error
    return Response(
        content=stored.body,
        media_type=stored.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="{media.original_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
        },
    )


@router.post("/incidents/{incident_id}/cancel", response_model=IncidentResponse)
def cancel_incident(
    incident_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    incident = db.scalar(authorized_incident_query(incident_id).with_for_update())
    if incident is None:
        raise api_error(404, "INCIDENT_NOT_FOUND", "Incident not found")
    if incident.reporter_id != user.id:
        raise api_error(403, "INCIDENT_ACCESS_DENIED", "Only the reporter can cancel this incident")
    if incident.status not in CITIZEN_CANCELLABLE:
        raise api_error(
            409,
            "INCIDENT_NOT_CANCELLABLE",
            "This incident can no longer be cancelled by its reporter",
        )
    previous = incident.status
    incident.status = IncidentStatus.CANCELLED
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            actor_id=user.id,
            event_type="INCIDENT_CANCELLED",
            details=f"Status changed from {previous.value} to CANCELLED by the reporter.",
        )
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="incident.cancel",
            entity_type="incident",
            entity_id=str(incident.id),
        )
    )
    db.commit()
    return load_incident(db, incident.id)


@router.get("/emergency-contacts", response_model=list[EmergencyContactResponse])
def emergency_contacts(
    state: str | None = None, district: str | None = None, db: Session = Depends(get_db)
):
    query = select(EmergencyContact).where(EmergencyContact.is_active.is_(True))
    if state:
        query = query.where(EmergencyContact.state == state)
    if district:
        query = query.where(EmergencyContact.district == district)
    return db.scalars(query.order_by(EmergencyContact.organization_name)).all()


@router.get("/admin/incidents", response_model=AdminIncidentPage)
def admin_incidents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: IncidentStatus | None = None,
    state: str | None = Query(default=None, max_length=80),
    district: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    filters = []
    if status:
        filters.append(Incident.status == status)
    if state:
        filters.append(Incident.state == state.strip())
    if district:
        filters.append(Incident.district == district.strip())
    if search and (term := search.strip()):
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                Incident.reference_code.ilike(pattern, escape="\\"),
                Incident.city.ilike(pattern, escape="\\"),
                Incident.district.ilike(pattern, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(Incident).where(*filters)) or 0
    items = db.scalars(
        select(Incident)
        .where(*filters)
        .order_by(Incident.created_at.desc(), Incident.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.patch("/admin/incidents/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: UUID,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    incident = db.scalar(authorized_incident_query(incident_id).with_for_update())
    if incident is None:
        raise api_error(404, "INCIDENT_NOT_FOUND", "Incident not found")
    if not incident.is_demo or not get_settings().demo_mode:
        raise api_error(
            409,
            "DEMO_MODE_REQUIRED",
            "Operational status changes are restricted to demo incidents",
        )
    try:
        validate_transition(incident.status, payload.status)
    except InvalidStatusTransition as error:
        raise api_error(409, "INVALID_STATUS_TRANSITION", str(error)) from error

    previous = incident.status
    incident.status = payload.status
    if payload.status == IncidentStatus.CANCELLED:
        event_type = "INCIDENT_CANCELLED"
    elif payload.status == IncidentStatus.CLOSED:
        event_type = "INCIDENT_CLOSED"
    else:
        event_type = "STATUS_UPDATED"
    details = f"Demo status changed from {previous.value} to {payload.status.value}." + (
        f" Note: {payload.note}" if payload.note else ""
    )
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            actor_id=user.id,
            event_type=event_type,
            details=details,
        )
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="incident.status.update",
            entity_type="incident",
            entity_id=str(incident.id),
        )
    )
    db.commit()
    return load_incident(db, incident.id)


@router.get("/admin/overview")
def admin_overview(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))):
    total = (
        db.scalar(select(func.count()).select_from(Incident).where(Incident.is_demo.is_(True))) or 0
    )
    pending = (
        db.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.status.in_([IncidentStatus.CREATED, IncidentStatus.UNDER_REVIEW]))
        )
        or 0
    )
    verification = (
        db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.verification_status == VerificationStatus.PENDING)
        )
        or 0
    )
    recent = db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(10)).all()
    audit = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)).all()
    return {
        "total_demo_incidents": total,
        "pending_incidents": pending,
        "organization_verification_queue": verification,
        "incidents": [
            {
                "id": str(incident.id),
                "reference_code": incident.reference_code,
                "state": incident.state,
                "district": incident.district,
                "urgency": incident.urgency,
                "status": incident.status,
                "created_at": incident.created_at,
            }
            for incident in recent
        ],
        "audit_activity": [
            {
                "id": str(entry.id),
                "action": entry.action,
                "entity_type": entry.entity_type,
                "created_at": entry.created_at,
            }
            for entry in audit
        ],
    }


router.include_router(locations_router)
router.include_router(rescuers_router)
router.include_router(bookings_router)
router.include_router(notifications_router)
router.include_router(devices_router)
router.include_router(tracking_router)
router.include_router(realtime_router)
router.include_router(webhooks_router)
router.include_router(admin_marketplace_router)
router.include_router(day5_rescue_router)
router.include_router(day5_payments_router)
router.include_router(day5_reviews_router)
