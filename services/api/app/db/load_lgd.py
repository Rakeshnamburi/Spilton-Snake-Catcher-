"""Load the bundled open LGD dataset (states, districts, mandals, villages).

The repository ships a small, openly-licensed extract of the India Local
Government Directory so the State -> District -> Mandal -> Village selectors
work out of the box, without anyone having to download files from
lgdirectory.gov.in first.

Source: planemad/india-local-government-directory (Government Open Data
License - India), a mirror of https://lgdirectory.gov.in.
Villages are bundled for the five southern states only, to keep the download
small; the full national set can be imported any time with
`python -m app.db.import_lgd villages <file>`.

Run once, from the services/api directory:

    python -m app.db.load_lgd
"""

from pathlib import Path

from app.db.session import SessionLocal
from app.services.lgd_import import import_lgd_file

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "lgd"
SOURCE_VERSION = "planemad-lgd-2022"
SOURCE_URL = "https://github.com/planemad/india-local-government-directory"

FILES = (
    ("states", "states.csv"),
    ("districts", "districts.csv"),
    ("subdistricts", "subdistricts.csv"),
    ("villages", "villages-south-india.csv"),
)


def main() -> None:
    with SessionLocal() as db:
        for entity, filename in FILES:
            path = DATA_DIR / filename
            if not path.exists():
                print(f"skip {entity}: {path} not found")
                continue
            result = import_lgd_file(
                db,
                entity_type=entity,
                path=path,
                source_version=SOURCE_VERSION,
                source_url=SOURCE_URL,
            )
            print(
                f"{entity:14s} {result.status}: {result.rows_received} rows; "
                f"{result.rows_inserted} inserted, {result.rows_updated} updated, "
                f"{result.rows_skipped} skipped"
            )
    print("Bundled LGD data loaded. State / District / Mandal / Village selectors are ready.")


if __name__ == "__main__":
    main()
