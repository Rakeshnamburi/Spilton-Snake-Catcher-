from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.bookings import _owned_booking
from app.api.deps import get_current_user, require_roles
from app.api.marketplace_helpers import fail
from app.db.session import get_db
from app.models.entities import (
    AuditLog,
    BookingStatus,
    RescuerProfile,
    Review,
    ReviewAbuseReport,
    Role,
    User,
)
from app.schemas.day5 import (
    PublicReviewResponse,
    ReviewCreate,
    ReviewModeration,
    ReviewReportCreate,
    ReviewResponse,
    ReviewSummary,
    ReviewUpdate,
)
from app.services.marketplace import create_in_app_notification
from app.services.rate_limit import rate_limiter

router = APIRouter(tags=["day5-reviews"])


def _refresh_rating(db: Session, rescuer_id: UUID) -> None:
    profile = db.get(RescuerProfile, rescuer_id)
    average, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.rescuer_id == rescuer_id,
            Review.moderation_status == "PUBLISHED_DEMO",
        )
    ).one()
    profile.average_rating = Decimal(str(average or 0)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    profile.review_count = int(count or 0)


@router.post(
    "/bookings/{booking_id}/review",
    response_model=ReviewResponse,
    status_code=201,
)
def create_review(
    booking_id: UUID,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = _owned_booking(db, booking_id, user, lock=True)
    if booking.customer_id != user.id:
        raise fail(403, "CUSTOMER_REQUIRED", "Only the booking customer can submit a review")
    if booking.status != BookingStatus.COMPLETED or booking.customer_confirmed_at is None:
        raise fail(
            409,
            "REVIEW_NOT_ELIGIBLE",
            "Confirm the completed demo booking before submitting a review",
        )
    existing = db.scalar(select(Review).where(Review.booking_id == booking.id))
    if existing is not None:
        raise fail(409, "REVIEW_ALREADY_EXISTS", "This booking already has a review")
    review = Review(
        booking_id=booking.id,
        customer_id=user.id,
        rescuer_id=booking.rescuer_id,
        rating=payload.rating,
        review_text=payload.review_text.strip() if payload.review_text else None,
        moderation_status="PUBLISHED_DEMO",
        is_demo=True,
    )
    db.add(review)
    db.flush()
    _refresh_rating(db, booking.rescuer_id)
    profile = db.get(RescuerProfile, booking.rescuer_id)
    if profile is not None:
        create_in_app_notification(
            db,
            recipient_id=profile.user_id,
            booking_id=booking.id,
            event_type="REVIEW_SUBMITTED",
            title="Demo review submitted",
            body=f"A simulated review was submitted for {booking.booking_reference}.",
        )
    db.add(
        AuditLog(
            actor_id=user.id,
            action="review.create.demo",
            entity_type="review",
            entity_id=str(review.id),
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise fail(409, "REVIEW_ALREADY_EXISTS", "This booking already has a review") from error
    db.refresh(review)
    return review


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: UUID,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    review = db.scalar(select(Review).where(Review.id == review_id).with_for_update())
    if review is None:
        raise fail(404, "REVIEW_NOT_FOUND", "Review not found")
    if review.customer_id != user.id:
        raise fail(403, "REVIEW_ACCESS_DENIED", "You cannot edit this review")
    if payload.rating is not None:
        review.rating = payload.rating
    if "review_text" in payload.model_fields_set:
        review.review_text = payload.review_text.strip() if payload.review_text else None
    review.moderation_status = "PUBLISHED_DEMO"
    _refresh_rating(db, review.rescuer_id)
    db.commit()
    db.refresh(review)
    return review


@router.get(
    "/rescuers/{rescuer_id}/reviews",
    response_model=list[PublicReviewResponse],
)
def public_reviews(
    rescuer_id: UUID,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if page < 1 or limit < 1 or limit > 50:
        raise fail(422, "INVALID_PAGINATION", "Use page >= 1 and limit between 1 and 50")
    rows = db.scalars(
        select(Review)
        .where(
            Review.rescuer_id == rescuer_id,
            Review.moderation_status == "PUBLISHED_DEMO",
        )
        .order_by(Review.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return [
        PublicReviewResponse(
            id=row.id,
            rating=row.rating,
            review_text=row.review_text,
            created_at=row.created_at,
            is_demo=row.is_demo,
        )
        for row in rows
    ]


@router.get(
    "/rescuers/{rescuer_id}/rating-summary",
    response_model=ReviewSummary,
)
def rating_summary(
    rescuer_id: UUID,
    db: Session = Depends(get_db),
):
    profile = db.get(RescuerProfile, rescuer_id)
    if profile is None:
        raise fail(404, "RESCUER_NOT_FOUND", "Rescuer not found")
    counts = dict(
        db.execute(
            select(Review.rating, func.count(Review.id))
            .where(
                Review.rescuer_id == rescuer_id,
                Review.moderation_status == "PUBLISHED_DEMO",
            )
            .group_by(Review.rating)
        ).all()
    )
    return ReviewSummary(
        rescuer_id=profile.id,
        average_rating=Decimal(profile.average_rating or 0),
        review_count=profile.review_count,
        distribution={rating: int(counts.get(rating, 0)) for rating in range(1, 6)},
        is_demo=True,
    )


@router.post("/reviews/{review_id}/report", status_code=201)
def report_review(
    review_id: UUID,
    payload: ReviewReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    review = db.get(Review, review_id)
    if review is None or review.moderation_status == "REMOVED":
        raise fail(404, "REVIEW_NOT_FOUND", "Review not found")
    retry = rate_limiter.check(
        f"review-report:{user.id}:{request.client.host if request.client else 'unknown'}",
        limit=10,
        window_seconds=3600,
    )
    if retry is not None:
        raise fail(429, "REVIEW_REPORT_RATE_LIMITED", "Too many review reports")
    existing = db.scalar(
        select(ReviewAbuseReport).where(
            ReviewAbuseReport.review_id == review.id,
            ReviewAbuseReport.reporter_id == user.id,
        )
    )
    if existing is not None:
        return {"id": str(existing.id), "status": existing.status, "is_demo": True}
    abuse = ReviewAbuseReport(
        review_id=review.id,
        reporter_id=user.id,
        reason=payload.reason,
        status="OPEN",
    )
    db.add(abuse)
    db.commit()
    db.refresh(abuse)
    return {"id": str(abuse.id), "status": abuse.status, "is_demo": True}


@router.get("/admin/reviews", response_model=list[ReviewResponse])
def admin_reviews(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    return db.scalars(select(Review).order_by(Review.created_at.desc())).all()


@router.patch("/admin/reviews/{review_id}", response_model=ReviewResponse)
def moderate_review(
    review_id: UUID,
    payload: ReviewModeration,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.COORDINATOR, Role.ADMIN)),
):
    review = db.scalar(select(Review).where(Review.id == review_id).with_for_update())
    if review is None:
        raise fail(404, "REVIEW_NOT_FOUND", "Review not found")
    review.moderation_status = payload.status
    reports = db.scalars(
        select(ReviewAbuseReport).where(
            ReviewAbuseReport.review_id == review.id,
            ReviewAbuseReport.status == "OPEN",
        )
    ).all()
    for report in reports:
        report.status = "RESOLVED"
        report.resolved_by = admin.id
        report.resolution_note = payload.resolution_note
    _refresh_rating(db, review.rescuer_id)
    db.add(
        AuditLog(
            actor_id=admin.id,
            action=f"review.moderate.{payload.status.lower()}",
            entity_type="review",
            entity_id=str(review.id),
        )
    )
    db.commit()
    db.refresh(review)
    return review
