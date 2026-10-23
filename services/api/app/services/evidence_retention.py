from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import EvidenceAuditEvent, RescueMedia
from app.services.media_storage import StorageError, get_media_storage


def cleanup_expired_evidence(db: Session, *, limit: int = 100) -> tuple[int, int]:
    """Delete expired private objects and retain a minimal auditable tombstone."""

    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(RescueMedia)
        .where(
            RescueMedia.deleted_at.is_(None),
            RescueMedia.retention_expires_at <= now,
        )
        .order_by(RescueMedia.retention_expires_at)
        .limit(limit)
    ).all()
    storage = get_media_storage()
    removed = 0
    failed = 0
    for media in rows:
        try:
            storage.delete(media.storage_key)
        except StorageError:
            failed += 1
            continue
        media.deleted_at = now
        db.add(
            EvidenceAuditEvent(
                rescue_media_id=media.id,
                actor_id=None,
                action="RETENTION_DELETED",
                details="Expired private demo evidence was removed by the retention worker.",
            )
        )
        removed += 1
    if removed:
        db.commit()
    return removed, failed
