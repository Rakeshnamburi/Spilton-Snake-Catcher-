from app.db.session import SessionLocal
from app.services.tracking import cleanup_tracking_locations


def main() -> None:
    with SessionLocal() as db:
        removed = cleanup_tracking_locations(db)
    print(f"Removed {removed} expired tracking locations.")


if __name__ == "__main__":
    main()
