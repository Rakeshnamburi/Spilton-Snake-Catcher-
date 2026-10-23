"""Read-only integrity report for imported Government LGD hierarchy data."""

import json

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.entities import (
    District,
    LocationImportJob,
    State,
    Subdistrict,
    UrbanLocalBody,
    Village,
    Ward,
)


def audit() -> dict:
    with SessionLocal() as db:
        counts = {
            "states": db.scalar(select(func.count()).select_from(State)) or 0,
            "districts": db.scalar(select(func.count()).select_from(District)) or 0,
            "subdistricts": db.scalar(select(func.count()).select_from(Subdistrict)) or 0,
            "villages": db.scalar(select(func.count()).select_from(Village)) or 0,
            "urban_local_bodies": db.scalar(select(func.count()).select_from(UrbanLocalBody)) or 0,
            "wards": db.scalar(select(func.count()).select_from(Ward)) or 0,
        }
        orphan_counts = {
            "districts": db.scalar(
                select(func.count())
                .select_from(District)
                .where(~select(State.id).where(State.lgd_code == District.state_code).exists())
            )
            or 0,
            "subdistricts": db.scalar(
                select(func.count())
                .select_from(Subdistrict)
                .where(
                    ~select(District.id)
                    .where(District.lgd_code == Subdistrict.district_code)
                    .exists()
                )
            )
            or 0,
            "villages": db.scalar(
                select(func.count())
                .select_from(Village)
                .where(
                    ~select(Subdistrict.id)
                    .where(Subdistrict.lgd_code == Village.subdistrict_code)
                    .exists()
                )
            )
            or 0,
        }
        source_versions = list(
            db.execute(
                select(LocationImportJob.source_version, func.count(LocationImportJob.id))
                .where(LocationImportJob.status == "COMPLETED")
                .group_by(LocationImportJob.source_version)
            ).all()
        )
    return {
        "counts": counts,
        "orphan_counts": orphan_counts,
        "source_versions": [
            {"source_version": version, "completed_import_jobs": count}
            for version, count in source_versions
        ],
        "complete_official_coverage_claimed": False,
        "integrity_ok": not any(orphan_counts.values()),
    }


def main() -> None:
    print(json.dumps(audit(), indent=2))


if __name__ == "__main__":
    main()
