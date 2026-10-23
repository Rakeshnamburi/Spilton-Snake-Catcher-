from app.db.session import SessionLocal
from app.services.evidence_retention import cleanup_expired_evidence


def main() -> None:
    with SessionLocal() as db:
        removed, failed = cleanup_expired_evidence(db)
        print(f"expired_evidence_removed={removed} failed={failed}")


if __name__ == "__main__":
    main()
