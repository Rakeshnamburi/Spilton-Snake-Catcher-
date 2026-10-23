"""Small deployment scheduler for idempotent DEMO maintenance jobs.

Production platforms may replace this process with their native scheduler. The
database remains the source of truth, so a restart safely retries due work.
"""

import logging
import signal
import time
from collections.abc import Callable

from app.db.session import SessionLocal
from app.services.evidence_retention import cleanup_expired_evidence
from app.services.marketplace import expire_pending_bookings
from app.services.notifications import process_due_deliveries
from app.services.tracking import cleanup_tracking_locations

logger = logging.getLogger(__name__)
running = True


def stop(*_args) -> None:
    global running
    running = False


def execute(name: str, job: Callable) -> None:
    try:
        with SessionLocal() as db:
            result = job(db)
        logger.info("worker_job_completed name=%s result=%s", name, result)
    except Exception:
        logger.exception("worker_job_failed name=%s", name)


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    next_run = {"notifications": 0.0, "bookings": 0.0, "tracking": 0.0, "evidence": 0.0}
    intervals = {"notifications": 15, "bookings": 60, "tracking": 3600, "evidence": 3600}
    jobs = {
        "notifications": process_due_deliveries,
        "bookings": expire_pending_bookings,
        "tracking": cleanup_tracking_locations,
        "evidence": cleanup_expired_evidence,
    }
    logger.info("demo_worker_started")
    while running:
        now = time.monotonic()
        for name, job in jobs.items():
            if now >= next_run[name]:
                execute(name, job)
                next_run[name] = now + intervals[name]
        time.sleep(5)
    logger.info("demo_worker_stopped")


if __name__ == "__main__":
    main()
