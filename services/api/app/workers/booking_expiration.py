"""Expire unanswered demo booking requests from a scheduler or one-shot job."""

from app.db.session import SessionLocal
from app.services.marketplace import expire_pending_bookings


def main() -> None:
    with SessionLocal() as db:
        expired = expire_pending_bookings(db)
    print(f"Expired {expired} unanswered demo booking requests.")


if __name__ == "__main__":
    main()
