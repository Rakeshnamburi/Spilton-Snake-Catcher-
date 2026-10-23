import math
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.marketplace_helpers import fail, utcnow
from app.db.session import get_db
from app.models.entities import (
    AccountDataRequest,
    AuditLog,
    AvailabilityStatus,
    Booking,
    BookingStatus,
    District,
    LocationImportJob,
    NotificationDeliveryAttempt,
    NotificationEvent,
    Organization,
    RescuerDocument,
    RescuerProfile,
    RescuerVerificationHistory,
    Role,
    State,
    Subdistrict,
    TrackingSession,
    TrackingStatus,
    User,
    VerificationStatus,
    Village,
)
from app.schemas.marketplace import VerificationUpdate
from app.services.media_storage import StorageError, get_media_storage

router = APIRouter(prefix="/admin", tags=["admin-marketplace"])


class OrganizationVerificationUpdate(BaseModel):
    status: VerificationStatus
    note: str = Field(min_length=3, max_length=500)


class AccountRequestUpdate(BaseModel):
    status: Literal["UNDER_REVIEW", "COMPLETED", "REJECTED"]
    note: str = Field(min_length=3, max_length=500)


def _expire_authorizations(db: Session) -> None:
    profiles = db.scalars(
        select(RescuerProfile).where(
            RescuerProfile.verification_status == VerificationStatus.VERIFIED,
            RescuerProfile.authorization_expiry < date.today(),
        )
    ).all()
    for profile in profiles:
        profile.verification_status = VerificationStatus.EXPIRED
        profile.availability = AvailabilityStatus.OFFLINE
        db.add(
            RescuerVerificationHistory(
                rescuer_profile_id=profile.id,
                actor_id=None,
                previous_status=VerificationStatus.VERIFIED.value,
                new_status=VerificationStatus.EXPIRED.value,
                note="Authorization expiry date passed; automatic demo eligibility removal.",
            )
        )
    if profiles:
        db.commit()


@router.get("/rescuers")
def admin_rescuers(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: VerificationStatus | None = None,
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    _expire_authorizations(db)
    filters = []
    if status:
        filters.append(RescuerProfile.verification_status == status)
    if search and (term := search.strip()):
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                User.name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
                RescuerProfile.public_display_name.ilike(pattern, escape="\\"),
                RescuerProfile.authorization_reference.ilike(pattern, escape="\\"),
            )
        )
    base = (
        select(RescuerProfile, User, Organization)
        .join(User, User.id == RescuerProfile.user_id)
        .outerjoin(Organization, Organization.id == RescuerProfile.organization_id)
        .where(*filters)
    )
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    rows = db.execute(
        base.order_by(RescuerProfile.created_at.desc(), RescuerProfile.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(profile.id),
                "user_id": str(profile.user_id),
                "full_name": user.name,
                "email": user.email,
                "phone": user.phone,
                "public_display_name": profile.public_display_name,
                "organization_id": str(profile.organization_id)
                if profile.organization_id
                else None,
                "organization": organization.name if organization else profile.organization_name,
                "organization_status": organization.verification_status if organization else None,
                "verification_status": profile.verification_status,
                "authorization_reference": profile.authorization_reference,
                "issuing_authority": profile.issuing_authority,
                "authorization_issue_date": profile.authorization_issue_date,
                "authorization_expiry": profile.authorization_expiry,
                "years_experience": profile.years_experience,
                "languages": profile.languages,
                "state_code": profile.state_code,
                "district_code": profile.district_code,
                "availability": profile.availability,
                "is_demo": profile.is_demo,
                "document_count": db.scalar(
                    select(func.count())
                    .select_from(RescuerDocument)
                    .where(RescuerDocument.rescuer_profile_id == profile.id)
                )
                or 0,
                "created_at": profile.created_at,
            }
            for profile, user, organization in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
    }


@router.get("/operations/health")
def operations_health(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    """Return low-cardinality demo operations metrics without private record details."""

    pending_bookings = (
        db.scalar(
            select(func.count(Booking.id)).where(
                Booking.status.in_(
                    [BookingStatus.REQUESTED, BookingStatus.PENDING_RESCUER_RESPONSE]
                )
            )
        )
        or 0
    )
    active_tracking = (
        db.scalar(
            select(func.count(TrackingSession.id)).where(
                TrackingSession.status.in_([TrackingStatus.ACTIVE, TrackingStatus.PAUSED])
            )
        )
        or 0
    )
    notification_pending = (
        db.scalar(
            select(func.count(NotificationDeliveryAttempt.id)).where(
                NotificationDeliveryAttempt.status.in_(["PENDING", "RETRY_PENDING"])
            )
        )
        or 0
    )
    notification_failed = (
        db.scalar(
            select(func.count(NotificationDeliveryAttempt.id)).where(
                NotificationDeliveryAttempt.status.in_(["FAILED", "DEMO_FAILED"])
            )
        )
        or 0
    )
    return {
        "mode": "DEMO",
        "database": "ok",
        "scheduler": "EXTERNAL_PROCESS_REQUIRED",
        "pending_bookings": pending_bookings,
        "active_tracking_sessions": active_tracking,
        "pending_notification_deliveries": notification_pending,
        "failed_notification_deliveries": notification_failed,
        "live_dispatch_enabled": False,
        "real_payments_enabled": False,
    }


@router.get("/account-requests")
def admin_account_requests(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, max_length=30),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    filters = [AccountDataRequest.status == status] if status else []
    base = (
        select(AccountDataRequest, User)
        .join(User, User.id == AccountDataRequest.user_id)
        .where(*filters)
    )
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    rows = db.execute(
        base.order_by(AccountDataRequest.created_at.desc()).offset((page - 1) * limit).limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(item.id),
                "user_id": str(item.user_id),
                "user_name": user.name,
                "user_email": user.email,
                "request_type": item.request_type,
                "status": item.status,
                "reason": item.reason,
                "created_at": item.created_at,
                "processed_at": item.processed_at,
            }
            for item, user in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
    }


@router.patch("/account-requests/{request_id}")
def update_account_request(
    request_id: UUID,
    payload: AccountRequestUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    item = db.get(AccountDataRequest, request_id)
    if item is None:
        raise fail(404, "ACCOUNT_REQUEST_NOT_FOUND", "Account data request not found")
    if item.status in {"COMPLETED", "REJECTED"}:
        raise fail(409, "ACCOUNT_REQUEST_FINAL", "This account data request is already final")
    item.status = payload.status
    item.processed_by = admin.id
    item.processed_at = (
        datetime.now(timezone.utc) if payload.status in {"COMPLETED", "REJECTED"} else None
    )
    db.add(
        AuditLog(
            actor_id=admin.id,
            action=f"ACCOUNT_REQUEST_{payload.status}",
            entity_type="account_data_request",
            entity_id=str(item.id),
        )
    )
    db.commit()
    db.refresh(item)
    return {
        "id": str(item.id),
        "request_type": item.request_type,
        "status": item.status,
        "note_recorded": True,
        "processed_at": item.processed_at,
    }


@router.patch("/organizations/{organization_id}/verification")
def verify_organization(
    organization_id: UUID,
    payload: OrganizationVerificationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    if payload.status not in {
        VerificationStatus.UNDER_REVIEW,
        VerificationStatus.VERIFIED,
        VerificationStatus.REJECTED,
        VerificationStatus.SUSPENDED,
    }:
        raise fail(422, "INVALID_ORGANIZATION_STATUS", "Unsupported organization status")
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise fail(404, "ORGANIZATION_NOT_FOUND", "Organization not found")
    organization.verification_status = payload.status
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="organization.verification.update",
            entity_type="organization",
            entity_id=str(organization.id),
        )
    )
    db.commit()
    return {
        "id": str(organization.id),
        "name": organization.name,
        "verification_status": organization.verification_status,
        "note_recorded": True,
    }


@router.patch("/rescuers/{profile_id}/verification")
def verify_rescuer(
    profile_id: UUID,
    payload: VerificationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    profile = db.scalar(
        select(RescuerProfile).where(RescuerProfile.id == profile_id).with_for_update()
    )
    if profile is None:
        raise fail(404, "RESCUER_NOT_FOUND", "Rescuer application not found")
    allowed = {
        VerificationStatus.PENDING: {
            VerificationStatus.UNDER_REVIEW,
            VerificationStatus.REJECTED,
        },
        VerificationStatus.PENDING_VERIFICATION: {
            VerificationStatus.UNDER_REVIEW,
            VerificationStatus.REJECTED,
        },
        VerificationStatus.UNDER_REVIEW: {
            VerificationStatus.VERIFIED,
            VerificationStatus.REJECTED,
        },
        VerificationStatus.VERIFIED: {
            VerificationStatus.SUSPENDED,
            VerificationStatus.EXPIRED,
        },
        VerificationStatus.REJECTED: {VerificationStatus.UNDER_REVIEW},
        VerificationStatus.SUSPENDED: {VerificationStatus.UNDER_REVIEW},
        VerificationStatus.EXPIRED: {VerificationStatus.UNDER_REVIEW},
    }
    if payload.status not in allowed.get(profile.verification_status, set()):
        raise fail(
            409,
            "INVALID_VERIFICATION_TRANSITION",
            "Cannot change verification from "
            f"{profile.verification_status.value} to {payload.status.value}",
        )
    if payload.organization_id:
        organization = db.get(Organization, payload.organization_id)
        if organization is None:
            raise fail(422, "ORGANIZATION_NOT_FOUND", "Organization not found")
        profile.organization_id = organization.id
        profile.organization_name = organization.name
    organization = (
        db.get(Organization, profile.organization_id) if profile.organization_id else None
    )
    if payload.status == VerificationStatus.VERIFIED:
        if organization is None or organization.verification_status != VerificationStatus.VERIFIED:
            raise fail(409, "ORGANIZATION_NOT_VERIFIED", "Verify the affiliated organization first")
        if profile.authorization_expiry is None or profile.authorization_expiry < date.today():
            raise fail(409, "AUTHORIZATION_EXPIRED", "Expired authorization cannot be verified")
        documents = (
            db.scalar(
                select(func.count())
                .select_from(RescuerDocument)
                .where(RescuerDocument.rescuer_profile_id == profile.id)
            )
            or 0
        )
        if documents < 1:
            raise fail(
                409, "EVIDENCE_REQUIRED", "At least one private authorization document is required"
            )
        user = db.get(User, profile.user_id)
        user.role = Role.RESCUER

    previous = profile.verification_status
    profile.verification_status = payload.status
    profile.availability = AvailabilityStatus.OFFLINE
    profile.availability_updated_at = utcnow()
    db.add(
        RescuerVerificationHistory(
            rescuer_profile_id=profile.id,
            actor_id=admin.id,
            previous_status=previous.value,
            new_status=payload.status.value,
            note=payload.note,
        )
    )
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="rescuer.verification.update",
            entity_type="rescuer_profile",
            entity_id=str(profile.id),
        )
    )
    db.commit()
    return {
        "id": str(profile.id),
        "verification_status": profile.verification_status,
        "availability": profile.availability,
        "demo_only": True,
    }


@router.get("/rescuers/{profile_id}/documents")
def list_rescuer_documents(
    profile_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    if db.get(RescuerProfile, profile_id) is None:
        raise fail(404, "RESCUER_NOT_FOUND", "Rescuer application not found")
    documents = db.scalars(
        select(RescuerDocument)
        .where(RescuerDocument.rescuer_profile_id == profile_id)
        .order_by(RescuerDocument.uploaded_at.desc())
    ).all()
    return [
        {
            "id": str(document.id),
            "original_filename": document.original_filename,
            "content_type": document.content_type,
            "file_size": document.file_size,
            "uploaded_at": document.uploaded_at,
        }
        for document in documents
    ]


@router.get("/rescuers/{profile_id}/documents/{document_id}")
def retrieve_rescuer_document(
    profile_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    document = db.get(RescuerDocument, document_id)
    if document is None or document.rescuer_profile_id != profile_id:
        raise fail(404, "DOCUMENT_NOT_FOUND", "Authorization document not found")
    try:
        stored = get_media_storage().get(document.storage_key, document.content_type)
    except StorageError as error:
        raise fail(404, "DOCUMENT_NOT_FOUND", "Authorization document is unavailable") from error
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="rescuer.document.review",
            entity_type="rescuer_document",
            entity_id=str(document.id),
        )
    )
    db.commit()
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


@router.get("/bookings")
def admin_bookings(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: BookingStatus | None = None,
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN, Role.COORDINATOR)),
):
    filters = [Booking.is_demo.is_(True)]
    if status:
        filters.append(Booking.status == status)
    if search and (term := search.strip()):
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(Booking.booking_reference.ilike(f"%{escaped}%", escape="\\"))
    total = db.scalar(select(func.count()).select_from(Booking).where(*filters)) or 0
    rows = db.scalars(
        select(Booking)
        .where(*filters)
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(booking.id),
                "booking_reference": booking.booking_reference,
                "rescuer_id": str(booking.rescuer_id),
                "state_code": booking.state_code,
                "district_code": booking.district_code,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "is_demo": booking.is_demo,
                "created_at": booking.created_at,
                "expires_at": booking.expires_at,
            }
            for booking in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
        "privacy_note": (
            "Customer contact details and exact coordinates are excluded from this list."
        ),
    }


@router.get("/locations")
def admin_location_overview(
    db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))
):
    recent = db.scalars(
        select(LocationImportJob).order_by(LocationImportJob.started_at.desc()).limit(20)
    ).all()
    return {
        "counts": {
            "states": db.scalar(select(func.count()).select_from(State)) or 0,
            "districts": db.scalar(select(func.count()).select_from(District)) or 0,
            "subdistricts": db.scalar(select(func.count()).select_from(Subdistrict)) or 0,
            "villages": db.scalar(select(func.count()).select_from(Village)) or 0,
        },
        "imports": [
            {
                "id": str(job.id),
                "entity_type": job.entity_type,
                "source_url": job.source_url,
                "source_version": job.source_version,
                "source_filename": job.source_filename,
                "status": job.status,
                "rows_received": job.rows_received,
                "rows_inserted": job.rows_inserted,
                "rows_updated": job.rows_updated,
                "rows_skipped": job.rows_skipped,
                "error_summary": job.error_summary,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
            }
            for job in recent
        ],
        "coverage_complete": False,
        "coverage_note": (
            "Coverage is only as complete as the official LGD exports imported by an administrator."
        ),
    }


@router.get("/marketplace/overview")
def marketplace_overview(
    db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))
):
    def booking_count(status: BookingStatus | None = None) -> int:
        query = select(func.count()).select_from(Booking).where(Booking.is_demo.is_(True))
        if status:
            query = query.where(Booking.status == status)
        return db.scalar(query) or 0

    return {
        "demo_bookings_created": booking_count(),
        "demo_bookings_accepted": booking_count(BookingStatus.ACCEPTED),
        "demo_bookings_rejected": booking_count(BookingStatus.REJECTED),
        "demo_bookings_cancelled": booking_count(BookingStatus.CANCELLED),
        "demo_journeys_in_progress": booking_count(BookingStatus.EN_ROUTE),
        "active_demo_tracking_sessions": db.scalar(
            select(func.count())
            .select_from(TrackingSession)
            .where(TrackingSession.status.in_([TrackingStatus.ACTIVE, TrackingStatus.PAUSED]))
        )
        or 0,
        "failed_notification_deliveries": db.scalar(
            select(func.count())
            .select_from(NotificationDeliveryAttempt)
            .where(NotificationDeliveryAttempt.status == "FAILED")
        )
        or 0,
        "verified_demo_rescuers": db.scalar(
            select(func.count())
            .select_from(RescuerProfile)
            .where(
                RescuerProfile.verification_status == VerificationStatus.VERIFIED,
                RescuerProfile.is_demo.is_(True),
            )
        )
        or 0,
        "pending_rescuer_applications": db.scalar(
            select(func.count())
            .select_from(RescuerProfile)
            .where(
                RescuerProfile.verification_status.in_(
                    [VerificationStatus.PENDING_VERIFICATION, VerificationStatus.UNDER_REVIEW]
                )
            )
        )
        or 0,
        "authorized_operation_enabled": False,
        "payments_enabled": False,
    }


@router.get("/notifications")
def admin_notification_deliveries(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    status: str | None = Query(default=None, max_length=30),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    filters = []
    if status:
        filters.append(NotificationDeliveryAttempt.status == status.upper())
    total = (
        db.scalar(select(func.count()).select_from(NotificationDeliveryAttempt).where(*filters))
        or 0
    )
    rows = db.execute(
        select(NotificationDeliveryAttempt, NotificationEvent)
        .join(
            NotificationEvent,
            NotificationEvent.id == NotificationDeliveryAttempt.notification_event_id,
        )
        .where(*filters)
        .order_by(NotificationDeliveryAttempt.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(attempt.id),
                "event_type": event.event_type,
                "booking_id": str(event.booking_id) if event.booking_id else None,
                "channel": attempt.channel,
                "provider": attempt.provider,
                "status": attempt.status,
                "attempt_count": attempt.attempt_count,
                "max_attempts": attempt.max_attempts,
                "sanitized_result": attempt.sanitized_result,
                "created_at": attempt.created_at,
            }
            for attempt, event in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
        "privacy_note": "Recipients, device tokens and message bodies are excluded.",
    }


@router.get("/tracking")
def admin_tracking_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    status: TrackingStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
):
    filters = [TrackingSession.is_demo.is_(True)]
    if status:
        filters.append(TrackingSession.status == status)
    total = db.scalar(select(func.count()).select_from(TrackingSession).where(*filters)) or 0
    rows = db.execute(
        select(TrackingSession, Booking)
        .join(Booking, Booking.id == TrackingSession.booking_id)
        .where(*filters)
        .order_by(TrackingSession.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(session.id),
                "booking_reference": booking.booking_reference,
                "status": session.status,
                "started_at": session.started_at,
                "last_location_at": session.last_location_at,
                "expires_at": session.expires_at,
                "is_demo": session.is_demo,
            }
            for session, booking in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
        "privacy_note": "Exact movement coordinates are deliberately excluded.",
    }
