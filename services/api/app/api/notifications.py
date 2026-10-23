from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.marketplace_helpers import fail
from app.db.session import get_db
from app.models.entities import NotificationEvent, NotificationPreference, User
from app.schemas.day4 import NotificationPreferenceResponse, NotificationPreferenceUpdate
from app.schemas.marketplace import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
@router.get("/mine", response_model=list[NotificationResponse])
def my_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = [NotificationEvent.recipient_id == user.id]
    if unread_only:
        filters.append(NotificationEvent.read_at.is_(None))
    return db.scalars(
        select(NotificationEvent)
        .where(*filters)
        .order_by(NotificationEvent.created_at.desc())
        .limit(limit)
    ).all()


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = db.get(NotificationEvent, notification_id)
    if event is None or event.recipient_id != user.id:
        raise fail(404, "NOTIFICATION_NOT_FOUND", "Notification not found")
    event.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


@router.get("/preferences", response_model=list[NotificationPreferenceResponse])
def notification_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user.id)
        .order_by(NotificationPreference.channel)
    ).all()


@router.put("/preferences", response_model=NotificationPreferenceResponse)
def update_notification_preference(
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if (
        payload.enabled
        and payload.channel in {"SMS", "WHATSAPP", "PUSH"}
        and not payload.explicit_opt_in
    ):
        raise fail(422, "EXPLICIT_OPT_IN_REQUIRED", "Explicit opt-in is required for this channel")
    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id,
            NotificationPreference.channel == payload.channel,
        )
    )
    now = datetime.now(timezone.utc)
    if preference is None:
        preference = NotificationPreference(user_id=user.id, channel=payload.channel)
        db.add(preference)
    preference.is_enabled = payload.enabled
    preference.opted_in_at = now if payload.enabled and payload.explicit_opt_in else None
    db.commit()
    db.refresh(preference)
    return preference
