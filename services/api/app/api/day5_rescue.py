from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Request, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.bookings import _owned_booking
from app.api.deps import get_current_user, require_roles
from app.api.marketplace_helpers import fail, get_profile_for_user, utcnow
from app.core.config import get_settings
from app.core.security import keyed_digest
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    AvailabilityStatus,
    Booking,
    BookingStatus,
    CompletionDispute,
    EvidenceAuditEvent,
    EvidenceLocationMetadata,
    RescueMedia,
    RescueOutcome,
    RescueReport,
    RescueReportEvent,
    RescuerProfile,
    RescueSession,
    Role,
    User,
)
from app.schemas.day5 import (
    CompletionConfirmResponse,
    DisputeCreate,
    DisputeResolution,
    DisputeResponse,
    EvidenceResponse,
    RescueOutcomeResponse,
    RescueReportCreate,
    RescueReportResponse,
    RescueSessionResponse,
)
from app.services.marketplace import (
    InvalidBookingTransition,
    add_booking_event,
    add_booking_state,
    create_in_app_notification,
    rescuer_is_eligible,
    validate_booking_transition,
)
from app.services.media_storage import (
    MAX_MEDIA_BYTES,
    MediaValidationError,
    StorageError,
    get_media_storage,
    safe_original_filename,
    validate_and_sanitize_image,
)
from app.services.rate_limit import rate_limiter
from app.services.tracking import stop_booking_tracking

router = APIRouter(tags=["day5-rescue"])
MAX_EVIDENCE_PER_BOOKING = 8
EVIDENCE_TYPES = {"ARRIVAL_AREA", "RESCUE_PROCESS", "OUTCOME", "OTHER"}


def _assigned_rescuer(db: Session, booking: Booking, user: User) -> RescuerProfile:
    profile = get_profile_for_user(db, user.id)
    if profile is None or user.role != Role.RESCUER or booking.rescuer_id != profile.id:
        raise fail(
            403,
            "ASSIGNED_RESCUER_REQUIRED",
            "Only the assigned verified demo rescuer can perform this action",
        )
    if not rescuer_is_eligible(db, profile, require_available=False):
        raise fail(409, "RESCUER_NOT_ELIGIBLE", "Rescuer verification is no longer eligible")
    return profile


def _validated_idempotency_key(key: str | None) -> str:
    if not key:
        raise fail(400, "IDEMPOTENCY_KEY_REQUIRED", "An Idempotency-Key header is required")
    cleaned = key.strip()
    if not 8 <= len(cleaned) <= 128 or any(ord(character) < 33 for character in cleaned):
        raise fail(400, "INVALID_IDEMPOTENCY_KEY", "Use an 8–128 character idempotency key")
    return cleaned


def _report_response(report: RescueReport, outcome: RescueOutcome) -> RescueReportResponse:
    return RescueReportResponse(
        id=report.id,
        booking_id=report.booking_id,
        rescue_session_id=report.rescue_session_id,
        outcome_code=outcome.code,
        outcome_label=outcome.label,
        observations=report.observations,
        authorized_action_summary=report.authorized_action_summary,
        referral_details=report.referral_details,
        notes=report.notes,
        species_text=report.species_text,
        species_verification=report.species_verification,
        completion_status=report.completion_status,
        completed_at=report.completed_at,
        is_demo=report.is_demo,
    )


def _evidence_response(db: Session, media: RescueMedia) -> EvidenceResponse:
    attached = db.scalar(
        select(func.count())
        .select_from(EvidenceLocationMetadata)
        .where(EvidenceLocationMetadata.rescue_media_id == media.id)
    )
    return EvidenceResponse(
        id=media.id,
        booking_id=media.booking_id,
        original_filename=media.original_filename,
        content_type=media.content_type,
        file_size=media.file_size,
        evidence_type=media.evidence_type,
        captured_at=media.captured_at,
        location_attached=bool(attached),
        retention_expires_at=media.retention_expires_at,
        created_at=media.created_at,
        is_demo=media.is_demo,
    )


@router.get("/rescue-outcomes", response_model=list[RescueOutcomeResponse])
def rescue_outcomes(db: Session = Depends(get_db)):
    return db.scalars(
        select(RescueOutcome).where(RescueOutcome.is_active.is_(True)).order_by(RescueOutcome.label)
    ).all()


@router.post(
    "/bookings/{booking_id}/rescue/start",
    response_model=RescueSessionResponse,
    status_code=201,
)
def start_rescue(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    profile = _assigned_rescuer(db, booking, user)
    existing = db.scalar(select(RescueSession).where(RescueSession.booking_id == booking.id))
    if existing is not None:
        return existing
    try:
        validate_booking_transition(booking.status, BookingStatus.IN_PROGRESS)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error
    now = utcnow()
    session = RescueSession(
        booking_id=booking.id,
        rescuer_id=profile.id,
        organization_id=profile.organization_id,
        incident_id=booking.incident_id,
        status="IN_PROGRESS",
        started_at=now,
        is_demo=True,
    )
    db.add(session)
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=booking.status,
        current=BookingStatus.IN_PROGRESS,
        event_type="RESCUE_SESSION_STARTED",
        details="The assigned fictional rescuer started the simulated rescue record.",
    )
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type="RESCUE_SESSION_STARTED",
        title="Demo assistance in progress",
        body=f"Simulation work started for {booking.booking_reference}.",
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="rescue.start.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "/bookings/{booking_id}/rescue",
    response_model=RescueSessionResponse,
)
def rescue_session(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    session = db.scalar(select(RescueSession).where(RescueSession.booking_id == booking.id))
    if session is None:
        raise fail(404, "RESCUE_SESSION_NOT_FOUND", "No rescue session exists for this booking")
    return session


@router.post(
    "/bookings/{booking_id}/complete",
    response_model=RescueReportResponse,
    status_code=201,
)
def complete_rescue(
    booking_id: UUID,
    payload: RescueReportCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    key = _validated_idempotency_key(idempotency_key)
    key_hash = keyed_digest(f"rescue-report:{user.id}:{key}")
    request_hash = hashlib.sha256(
        json.dumps(
            payload.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    existing = db.scalar(
        select(RescueReport).where(
            RescueReport.rescuer_id
            == select(RescuerProfile.id).where(RescuerProfile.user_id == user.id).scalar_subquery(),
            RescueReport.idempotency_key_hash == key_hash,
        )
    )
    if existing is not None:
        if existing.idempotency_request_hash != request_hash:
            raise fail(
                409,
                "IDEMPOTENCY_CONFLICT",
                "This key was already used with different completion details",
            )
        outcome = db.get(RescueOutcome, existing.outcome_id)
        response.headers["X-Idempotent-Replay"] = "true"
        return _report_response(existing, outcome)

    booking = _owned_booking(db, booking_id, user, lock=True)
    profile = _assigned_rescuer(db, booking, user)
    session = db.scalar(
        select(RescueSession).where(RescueSession.booking_id == booking.id).with_for_update()
    )
    if session is None or session.status != "IN_PROGRESS":
        raise fail(409, "RESCUE_SESSION_NOT_ACTIVE", "Start the demo rescue session first")
    outcome = db.scalar(
        select(RescueOutcome).where(
            RescueOutcome.code == payload.outcome_code,
            RescueOutcome.is_active.is_(True),
        )
    )
    if outcome is None:
        raise fail(422, "INVALID_RESCUE_OUTCOME", "Select an active rescue outcome")
    target = (
        BookingStatus.UNABLE_TO_ASSIST
        if outcome.code == "UNABLE_TO_ASSIST"
        else BookingStatus.COMPLETED
    )
    try:
        validate_booking_transition(booking.status, target)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error

    now = utcnow()
    report = RescueReport(
        rescue_session_id=session.id,
        booking_id=booking.id,
        rescuer_id=profile.id,
        organization_id=profile.organization_id,
        outcome_id=outcome.id,
        observations=payload.observations,
        authorized_action_summary=payload.authorized_action_summary,
        referral_details=payload.referral_details,
        notes=payload.notes,
        species_text=payload.species_text,
        species_verification="UNVERIFIED",
        completion_status="AWAITING_CUSTOMER_CONFIRMATION"
        if target == BookingStatus.COMPLETED
        else "UNABLE_TO_ASSIST",
        completed_at=now,
        idempotency_key_hash=key_hash,
        idempotency_request_hash=request_hash,
        is_demo=True,
    )
    db.add(report)
    db.flush()
    db.add(
        RescueReportEvent(
            rescue_report_id=report.id,
            actor_id=user.id,
            event_type="REPORT_SUBMITTED",
            details="A simulated completion report was submitted.",
        )
    )
    session.status = target.value
    session.ended_at = now
    booking.completed_at = now
    stop_booking_tracking(
        db,
        booking,
        actor_id=user.id,
        reason="Demo tracking stopped when the rescue record ended.",
    )
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=booking.status,
        current=target,
        event_type=f"BOOKING_{target.value}",
        details="The fictional demo rescue outcome was documented.",
    )
    profile.availability = AvailabilityStatus.AVAILABLE
    profile.availability_updated_at = now
    profile.last_seen_at = now
    if target == BookingStatus.COMPLETED:
        profile.completed_service_count += 1
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type="RESCUE_REPORT_SUBMITTED",
        title="Demo rescue report submitted",
        body=f"A simulated rescue report was submitted for {booking.booking_reference}.",
    )
    create_in_app_notification(
        db,
        recipient_id=booking.customer_id,
        booking_id=booking.id,
        event_type=f"BOOKING_{target.value}",
        title="Demo rescue record updated",
        body=f"Simulation outcome was recorded for {booking.booking_reference}.",
    )
    db.add(
        AuditLog(
            actor_id=user.id,
            action=f"rescue.{target.value.lower()}.demo",
            entity_type="rescue_report",
            entity_id=str(report.id),
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        replay = db.scalar(
            select(RescueReport).where(
                RescueReport.rescuer_id == profile.id,
                RescueReport.idempotency_key_hash == key_hash,
            )
        )
        if replay and replay.idempotency_request_hash == request_hash:
            response.headers["X-Idempotent-Replay"] = "true"
            replay_outcome = db.get(RescueOutcome, replay.outcome_id)
            return _report_response(replay, replay_outcome)
        raise fail(409, "COMPLETION_CONFLICT", "Completion could not be saved safely") from error
    db.refresh(report)
    return _report_response(report, outcome)


@router.get(
    "/bookings/{booking_id}/rescue/report",
    response_model=RescueReportResponse,
)
def rescue_report(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    report = db.scalar(select(RescueReport).where(RescueReport.booking_id == booking.id))
    if report is None:
        raise fail(404, "RESCUE_REPORT_NOT_FOUND", "No completion report exists")
    outcome = db.get(RescueOutcome, report.outcome_id)
    return _report_response(report, outcome)


@router.post(
    "/bookings/{booking_id}/confirm-completion",
    response_model=CompletionConfirmResponse,
)
def confirm_completion(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    if booking.customer_id != user.id:
        raise fail(403, "CUSTOMER_REQUIRED", "Only the booking customer can confirm completion")
    if booking.status != BookingStatus.COMPLETED:
        raise fail(409, "BOOKING_NOT_COMPLETED", "Only a completed booking can be confirmed")
    report = db.scalar(
        select(RescueReport).where(RescueReport.booking_id == booking.id).with_for_update()
    )
    if report is None:
        raise fail(409, "RESCUE_REPORT_REQUIRED", "A rescue report is required")
    if booking.customer_confirmed_at is None:
        booking.customer_confirmed_at = utcnow()
        report.completion_status = "CUSTOMER_CONFIRMED"
        db.add(
            RescueReportEvent(
                rescue_report_id=report.id,
                actor_id=user.id,
                event_type="CUSTOMER_CONFIRMED",
                details="The customer confirmed the simulated completion.",
            )
        )
        add_booking_event(
            db,
            booking,
            actor_id=user.id,
            event_type="COMPLETION_CONFIRMED",
            details="The customer confirmed the simulated completion.",
        )
        db.commit()
    return CompletionConfirmResponse(
        booking_id=booking.id,
        status=booking.status.value,
        completion_status=report.completion_status,
        customer_confirmed_at=booking.customer_confirmed_at,
        is_demo=True,
    )


@router.post(
    "/bookings/{booking_id}/dispute",
    response_model=DisputeResponse,
    status_code=201,
)
def dispute_completion(
    booking_id: UUID,
    payload: DisputeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    if booking.customer_id != user.id:
        raise fail(403, "CUSTOMER_REQUIRED", "Only the booking customer can dispute completion")
    try:
        validate_booking_transition(booking.status, BookingStatus.DISPUTED)
    except InvalidBookingTransition as error:
        raise fail(409, "INVALID_BOOKING_TRANSITION", str(error)) from error
    existing = db.scalar(
        select(CompletionDispute).where(
            CompletionDispute.booking_id == booking.id,
            CompletionDispute.status == "OPEN",
        )
    )
    if existing is not None:
        return existing
    dispute = CompletionDispute(
        booking_id=booking.id,
        customer_id=user.id,
        reason=payload.reason,
        status="OPEN",
        is_demo=True,
    )
    db.add(dispute)
    add_booking_state(
        db,
        booking,
        actor_id=user.id,
        previous=booking.status,
        current=BookingStatus.DISPUTED,
        event_type="COMPLETION_DISPUTED",
        details="The customer opened a simulated completion dispute.",
    )
    profile = db.get(RescuerProfile, booking.rescuer_id)
    if profile is not None:
        create_in_app_notification(
            db,
            recipient_id=profile.user_id,
            booking_id=booking.id,
            event_type="COMPLETION_DISPUTED",
            title="Demo completion sent for review",
            body=f"A simulated completion issue was opened for {booking.booking_reference}.",
        )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="completion.dispute.demo",
            entity_type="booking",
            entity_id=str(booking.id),
        )
    )
    db.commit()
    db.refresh(dispute)
    return dispute


@router.patch(
    "/admin/disputes/{dispute_id}",
    response_model=DisputeResponse,
)
def resolve_dispute(
    dispute_id: UUID,
    payload: DisputeResolution,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    dispute = db.scalar(
        select(CompletionDispute).where(CompletionDispute.id == dispute_id).with_for_update()
    )
    if dispute is None:
        raise fail(404, "DISPUTE_NOT_FOUND", "Dispute not found")
    if dispute.status != "OPEN":
        raise fail(409, "DISPUTE_ALREADY_RESOLVED", "This dispute is already resolved")
    booking = db.scalar(select(Booking).where(Booking.id == dispute.booking_id).with_for_update())
    dispute.status = "RESOLVED"
    dispute.coordinator_id = admin.id
    dispute.resolution_note = payload.resolution_note
    dispute.resolved_at = utcnow()
    if payload.restore_completed and booking.status == BookingStatus.DISPUTED:
        add_booking_state(
            db,
            booking,
            actor_id=admin.id,
            previous=booking.status,
            current=BookingStatus.COMPLETED,
            event_type="DISPUTE_RESOLVED",
            details="An authorized coordinator resolved the simulated dispute.",
        )
    db.commit()
    db.refresh(dispute)
    return dispute


@router.post(
    "/bookings/{booking_id}/rescue/evidence",
    response_model=EvidenceResponse,
    status_code=201,
)
async def upload_evidence(
    booking_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    evidence_type: str = Form(...),
    captured_at: datetime | None = Form(default=None),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    accuracy: float | None = Form(default=None),
    location_consent: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    _assigned_rescuer(db, booking, user)
    session = db.scalar(select(RescueSession).where(RescueSession.booking_id == booking.id))
    if session is None:
        raise fail(409, "RESCUE_SESSION_REQUIRED", "Start the demo rescue session first")
    normalized_type = evidence_type.strip().upper()
    if normalized_type not in EVIDENCE_TYPES:
        raise fail(422, "INVALID_EVIDENCE_TYPE", "Select a supported evidence category")
    count = db.scalar(
        select(func.count())
        .select_from(RescueMedia)
        .where(
            RescueMedia.booking_id == booking.id,
            RescueMedia.deleted_at.is_(None),
        )
    )
    if count >= MAX_EVIDENCE_PER_BOOKING:
        raise fail(409, "EVIDENCE_LIMIT_REACHED", "A booking can contain up to 8 images")
    retry = rate_limiter.check(
        f"evidence:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=20,
        window_seconds=3600,
    )
    if retry is not None:
        raise fail(
            429,
            "EVIDENCE_RATE_LIMITED",
            "Too many evidence uploads",
            details={"retry_after": retry},
        )
    if (file.content_type or "").startswith("video/"):
        raise fail(
            503,
            "VIDEO_PIPELINE_NOT_CONFIGURED",
            "Video evidence remains disabled until duration, malware, and metadata "
            "sanitization are configured.",
        )
    if (latitude is None) != (longitude is None):
        raise fail(422, "INVALID_EVIDENCE_LOCATION", "Latitude and longitude must be paired")
    if latitude is not None:
        if not location_consent:
            raise fail(422, "LOCATION_CONSENT_REQUIRED", "Explicit location consent is required")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise fail(422, "INVALID_COORDINATES", "Evidence coordinates are invalid")
        if accuracy is None or not 0 <= accuracy <= 10_000:
            raise fail(422, "INVALID_LOCATION_ACCURACY", "A valid accuracy value is required")
    elif accuracy is not None:
        raise fail(422, "INVALID_EVIDENCE_LOCATION", "Accuracy requires coordinates")

    body = await file.read(MAX_MEDIA_BYTES + 1)
    try:
        sanitized, content_type, extension = validate_and_sanitize_image(body, file.content_type)
    except MediaValidationError as error:
        raise fail(422, error.code, str(error)) from error
    storage_key = f"rescue-evidence/{booking.id}/{secrets.token_hex(24)}{extension}"
    storage = get_media_storage()
    try:
        storage.put(storage_key, sanitized, content_type)
    except StorageError as error:
        raise fail(503, "PRIVATE_STORAGE_ERROR", "Evidence could not be stored safely") from error
    media = RescueMedia(
        booking_id=booking.id,
        rescue_session_id=session.id,
        uploader_id=user.id,
        storage_key=storage_key,
        original_filename=safe_original_filename(file.filename, extension),
        content_type=content_type,
        file_size=len(sanitized),
        evidence_type=normalized_type,
        captured_at=captured_at,
        retention_expires_at=utcnow() + timedelta(days=get_settings().evidence_retention_days),
        malware_scan_status="SANITIZED_IMAGE",
        is_demo=True,
    )
    db.add(media)
    db.flush()
    if latitude is not None:
        db.add(
            EvidenceLocationMetadata(
                rescue_media_id=media.id,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                consent_timestamp=utcnow(),
                captured_at=captured_at,
                association_only=True,
            )
        )
    db.add(
        EvidenceAuditEvent(
            rescue_media_id=media.id,
            actor_id=user.id,
            action="UPLOADED",
            details="A sanitized private demo image was stored.",
        )
    )
    add_booking_event(
        db,
        booking,
        actor_id=user.id,
        event_type="RESCUE_EVIDENCE_UPLOADED",
        details="A private sanitized demo image was attached; no coordinates were logged.",
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage.delete(storage_key)
        except StorageError:
            pass
        raise
    db.refresh(media)
    return _evidence_response(db, media)


@router.get(
    "/bookings/{booking_id}/rescue/evidence",
    response_model=list[EvidenceResponse],
)
def list_evidence(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    rows = db.scalars(
        select(RescueMedia)
        .where(
            RescueMedia.booking_id == booking.id,
            RescueMedia.deleted_at.is_(None),
        )
        .order_by(RescueMedia.created_at.desc())
    ).all()
    return [_evidence_response(db, row) for row in rows]


@router.get("/bookings/{booking_id}/rescue/evidence/{media_id}")
def retrieve_evidence(
    booking_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    media = db.scalar(
        select(RescueMedia).where(
            RescueMedia.id == media_id,
            RescueMedia.booking_id == booking.id,
            RescueMedia.deleted_at.is_(None),
        )
    )
    if media is None:
        raise fail(404, "EVIDENCE_NOT_FOUND", "Evidence not found")
    try:
        stored = get_media_storage().get(media.storage_key, media.content_type)
    except StorageError as error:
        raise fail(404, "EVIDENCE_NOT_FOUND", "Evidence not found") from error
    db.add(
        EvidenceAuditEvent(
            rescue_media_id=media.id,
            actor_id=user.id,
            action="VIEWED",
            details="Private demo evidence was retrieved by an authorized participant.",
        )
    )
    db.commit()
    return Response(
        content=stored.body,
        media_type=stored.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="{media.original_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/bookings/{booking_id}/rescue/evidence/{media_id}",
    status_code=204,
)
def delete_evidence(
    booking_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user)
    profile = get_profile_for_user(db, user.id)
    is_assigned = bool(profile and profile.id == booking.rescuer_id)
    if not is_assigned and user.role not in {Role.COORDINATOR, Role.ADMIN}:
        raise fail(403, "EVIDENCE_DELETE_DENIED", "You cannot remove this evidence")
    media = db.scalar(
        select(RescueMedia).where(
            RescueMedia.id == media_id,
            RescueMedia.booking_id == booking.id,
            RescueMedia.deleted_at.is_(None),
        )
    )
    if media is None:
        raise fail(404, "EVIDENCE_NOT_FOUND", "Evidence not found")
    try:
        get_media_storage().delete(media.storage_key)
    except StorageError as error:
        raise fail(503, "PRIVATE_STORAGE_ERROR", "Evidence could not be removed safely") from error
    media.deleted_at = utcnow()
    db.add(
        EvidenceAuditEvent(
            rescue_media_id=media.id,
            actor_id=user.id,
            action="DELETED",
            details="Private demo evidence was removed.",
        )
    )
    db.commit()
    return Response(status_code=204)


@router.get("/admin/disputes", response_model=list[DisputeResponse])
def admin_disputes(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    return db.scalars(select(CompletionDispute).order_by(CompletionDispute.created_at.desc())).all()


@router.get("/admin/rescue-reports")
def admin_rescue_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    rows = db.execute(
        select(RescueReport, RescueOutcome, Booking.booking_reference)
        .join(RescueOutcome, RescueOutcome.id == RescueReport.outcome_id)
        .join(Booking, Booking.id == RescueReport.booking_id)
        .order_by(RescueReport.completed_at.desc())
    ).all()
    return [
        {
            "id": report.id,
            "booking_id": report.booking_id,
            "booking_reference": reference,
            "outcome_code": outcome.code,
            "outcome_label": outcome.label,
            "completion_status": report.completion_status,
            "completed_at": report.completed_at,
            "evidence_count": db.scalar(
                select(func.count())
                .select_from(RescueMedia)
                .where(
                    RescueMedia.booking_id == report.booking_id,
                    RescueMedia.deleted_at.is_(None),
                )
            )
            or 0,
            "is_demo": report.is_demo,
        }
        for report, outcome, reference in rows
    ]


@router.get("/admin/evidence")
def admin_evidence(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    rows = db.execute(
        select(RescueMedia, Booking.booking_reference)
        .join(Booking, Booking.id == RescueMedia.booking_id)
        .where(RescueMedia.deleted_at.is_(None))
        .order_by(RescueMedia.created_at.desc())
    ).all()
    return [
        {
            "id": media.id,
            "booking_id": media.booking_id,
            "booking_reference": reference,
            "original_filename": media.original_filename,
            "content_type": media.content_type,
            "file_size": media.file_size,
            "evidence_type": media.evidence_type,
            "retention_expires_at": media.retention_expires_at,
            "malware_scan_status": media.malware_scan_status,
            "is_demo": media.is_demo,
            "created_at": media.created_at,
        }
        for media, reference in rows
    ]
