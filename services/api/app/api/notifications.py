from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.marketplace_helpers import fail
from app.db.session import get_db
from app.models.entities import NotificationEvent, User
from app.schemas.marketplace import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


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
