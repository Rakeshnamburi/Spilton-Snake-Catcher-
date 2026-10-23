import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.bookings import _owned_booking
from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.entities import BookingEvent, User
from app.schemas.day4 import BookingEventPage
from app.schemas.marketplace import BookingEventResponse

router = APIRouter(tags=["real-time booking events"])


def _events_after(db: Session, booking_id: UUID, sequence: int) -> list[BookingEvent]:
    return list(
        db.scalars(
            select(BookingEvent)
            .where(BookingEvent.booking_id == booking_id, BookingEvent.sequence > sequence)
            .order_by(BookingEvent.sequence)
            .limit(100)
        ).all()
    )


@router.get("/bookings/{booking_id}/events", response_model=BookingEventPage)
def booking_events(
    booking_id: UUID,
    after_sequence: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _owned_booking(db, booking_id, user)
    events = _events_after(db, booking_id, after_sequence)
    return BookingEventPage(
        items=[BookingEventResponse.model_validate(item) for item in events],
        last_sequence=events[-1].sequence if events else after_sequence,
    )


@router.get("/bookings/{booking_id}/events/stream")
async def booking_event_stream(
    booking_id: UUID,
    request: Request,
    after_sequence: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _owned_booking(db, booking_id, user)
    try:
        cursor = max(after_sequence, int(last_event_id or 0))
    except ValueError:
        cursor = after_sequence

    async def generate():
        nonlocal cursor
        yield "retry: 3000\n\n"
        while True:
            if await request.is_disconnected():
                break
            with SessionLocal() as stream_db:
                rows = _events_after(stream_db, booking_id, cursor)
            if rows:
                for event in rows:
                    cursor = event.sequence
                    data = json.dumps(
                        {
                            "sequence": event.sequence,
                            "event_type": event.event_type,
                            "details": event.details,
                            "created_at": event.created_at.isoformat(),
                        }
                    )
                    yield f"id: {event.sequence}\ndata: {data}\n\n"
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(15)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
