import argparse

from app.db.session import SessionLocal
from app.services.notifications import process_due_deliveries


def main() -> None:
    parser = argparse.ArgumentParser(description="Process sanitized notification delivery jobs")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    parser.parse_args()
    with SessionLocal() as db:
        processed = process_due_deliveries(db)
    print(f"Processed {processed} notification delivery attempts.")


if __name__ == "__main__":
    main()
