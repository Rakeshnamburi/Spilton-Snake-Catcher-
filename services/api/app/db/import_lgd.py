"""Command-line entry point for importing an official LGD CSV/XLSX export."""

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.lgd_import import LGD_DOWNLOAD_URL, import_lgd_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "entity",
        choices=("states", "districts", "subdistricts", "villages", "urban_local_bodies", "wards"),
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--source-version", required=True, help="Official LGD export date/version")
    parser.add_argument("--source-url", default=LGD_DOWNLOAD_URL)
    arguments = parser.parse_args()

    with SessionLocal() as db:
        result = import_lgd_file(
            db,
            entity_type=arguments.entity,
            path=arguments.file.resolve(),
            source_version=arguments.source_version,
            source_url=arguments.source_url,
        )
    print(
        f"{result.status}: {result.rows_received} rows; "
        f"{result.rows_inserted} inserted, {result.rows_updated} updated, "
        f"{result.rows_skipped} unchanged/duplicate. Job {result.job_id}."
    )


if __name__ == "__main__":
    main()
