"""Transactional, idempotent import helpers for official LGD directory exports."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    District,
    LocationImportJob,
    State,
    Subdistrict,
    UrbanLocalBody,
    Village,
    Ward,
)

LGD_DOWNLOAD_URL = "https://lgdirectory.gov.in/demo/downloadDirectory.do"


class LGDImportError(ValueError):
    pass


@dataclass(frozen=True)
class ImportResult:
    job_id: str
    status: str
    rows_received: int
    rows_inserted: int
    rows_updated: int
    rows_skipped: int


ENTITY_CONFIG = {
    "states": {
        "model": State,
        "code": ("statecode", "statecodelgd", "lgdstatecode"),
        "name": ("statenameenglish", "statenameinenglish", "statename", "name"),
        "local": ("statenamelocal", "statenameinlocal", "localname"),
    },
    "districts": {
        "model": District,
        "code": ("districtcode", "districtcodelgd", "lgddistrictcode"),
        "name": ("districtnameenglish", "districtnameinenglish", "districtname", "name"),
        "local": ("districtnamelocal", "districtnameinlocal", "localname"),
        "parent_field": "state_code",
        "parent_aliases": ("statecode", "statecodelgd", "lgdstatecode"),
        "parent_model": State,
    },
    "subdistricts": {
        "model": Subdistrict,
        "code": ("subdistrictcode", "subdistrictcodelgd", "lgdsubdistrictcode"),
        "name": (
            "subdistrictnameenglish",
            "subdistrictnameinenglish",
            "subdistrictname",
            "name",
        ),
        "local": ("subdistrictnamelocal", "subdistrictnameinlocal", "localname"),
        "parent_field": "district_code",
        "parent_aliases": ("districtcode", "districtcodelgd", "lgddistrictcode"),
        "parent_model": District,
    },
    "villages": {
        "model": Village,
        "code": ("villagecode", "villagecodelgd", "lgdvillagecode"),
        "name": ("villagenameenglish", "villagenameinenglish", "villagename", "name"),
        "local": ("villagenamelocal", "villagenameinlocal", "localname"),
        "parent_field": "subdistrict_code",
        "parent_aliases": (
            "subdistrictcode",
            "subdistrictcodelgd",
            "lgdsubdistrictcode",
        ),
        "parent_model": Subdistrict,
    },
    "urban_local_bodies": {
        "model": UrbanLocalBody,
        "code": ("localbodycode", "urbanlocalbodycode", "ulbcode", "lgdcode"),
        "name": ("localbodynameenglish", "urbanlocalbodyname", "ulbname", "name"),
        "local": ("localbodynamelocal", "localname"),
        "state_aliases": ("statecode", "statecodelgd", "lgdstatecode"),
        "district_aliases": ("districtcode", "districtcodelgd", "lgddistrictcode"),
        "type_aliases": ("localbodytype", "localbodytypename", "ulbtype"),
    },
    "wards": {
        "model": Ward,
        "code": ("wardcode", "wardcodelgd", "lgdwardcode"),
        "name": ("wardnameenglish", "wardnameinenglish", "wardname", "name"),
        "local": ("wardnamelocal", "localname"),
        "parent_field": "urban_local_body_code",
        "parent_aliases": ("localbodycode", "urbanlocalbodycode", "ulbcode"),
        "parent_model": UrbanLocalBody,
    },
}


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower().strip())


def _clean(value: object | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _value(row: dict[str, str], aliases: tuple[str, ...], *, required: bool = False) -> str:
    for alias in aliases:
        value = _clean(row.get(alias))
        if value:
            return value
    if required:
        raise LGDImportError(f"Required LGD column is missing or empty: {aliases[0]}")
    return ""


def _active(row: dict[str, str]) -> bool:
    value = _value(row, ("isactive", "active", "status"))
    if not value:
        return True
    return value.casefold() not in {"n", "no", "false", "0", "inactive", "deactivated"}


def _xlsx_rows(body: bytes) -> list[dict[str, str]]:
    """Read the first XLSX worksheet with only the Python standard library."""

    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile as error:
        raise LGDImportError("The XLSX file is not a valid Office Open XML archive") from error

    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared: list[str] = []
    if "xl/sharedStrings.xml" in archive.namelist():
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        for item in root.findall("x:si", namespace):
            shared.append("".join(node.text or "" for node in item.findall(".//x:t", namespace)))

    sheets = sorted(
        name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
    )
    if not sheets:
        raise LGDImportError("The XLSX file does not contain a worksheet")
    root = ElementTree.fromstring(archive.read(sheets[0]))
    values: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        cells: dict[int, str] = {}
        for cell in row.findall("x:c", namespace):
            reference = cell.attrib.get("r", "A1")
            letters = re.match(r"[A-Z]+", reference)
            if not letters:
                continue
            index = 0
            for character in letters.group(0):
                index = index * 26 + ord(character) - 64
            value_node = cell.find("x:v", namespace)
            inline_node = cell.find("x:is/x:t", namespace)
            value = (
                inline_node.text
                if inline_node is not None
                else (value_node.text if value_node is not None else "")
            )
            if cell.attrib.get("t") == "s" and value:
                try:
                    value = shared[int(value)]
                except (IndexError, ValueError) as error:
                    raise LGDImportError("The XLSX shared-string table is invalid") from error
            cells[index - 1] = value or ""
        if cells:
            values.append([cells.get(index, "") for index in range(max(cells) + 1)])
    return _tabular_rows(values)


def _tabular_rows(values: Iterable[list[str]]) -> list[dict[str, str]]:
    rows = list(values)
    if not rows:
        raise LGDImportError("The LGD source file is empty")
    headers = [_normalize_header(value) for value in rows[0]]
    if not any(headers):
        raise LGDImportError("The LGD source file has no usable header row")
    output: list[dict[str, str]] = []
    for raw in rows[1:]:
        mapped = {
            header: _clean(raw[index]) if index < len(raw) else ""
            for index, header in enumerate(headers)
            if header
        }
        if any(mapped.values()):
            output.append(mapped)
    return output


def read_lgd_rows(path: Path) -> tuple[bytes, list[dict[str, str]]]:
    body = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            decoded = body.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = body.decode("cp1252")
        values = list(csv.reader(io.StringIO(decoded)))
        return body, _tabular_rows(values)
    if suffix == ".xlsx":
        return body, _xlsx_rows(body)
    raise LGDImportError("LGD imports accept only CSV or XLSX files")


def _record_values(entity_type: str, row: dict[str, str], source_version: str) -> dict:
    config = ENTITY_CONFIG[entity_type]
    values: dict[str, object] = {
        "lgd_code": _value(row, config["code"], required=True),
        "name": _value(row, config["name"], required=True),
        "local_name": _value(row, config["local"]) or None,
        "is_active": _active(row),
        "source_version": source_version,
        "imported_at": datetime.now(timezone.utc),
    }
    if entity_type == "states":
        marker = _value(row, ("isunionterritory", "stateorut", "category"))
        values["is_union_territory"] = marker.casefold() in {
            "ut",
            "union territory",
            "unionterritory",
            "true",
            "yes",
            "y",
            "1",
        }
    elif entity_type == "urban_local_bodies":
        values["state_code"] = _value(row, config["state_aliases"], required=True)
        values["district_code"] = _value(row, config["district_aliases"]) or None
        values["local_body_type"] = _value(row, config["type_aliases"]) or None
    else:
        values[config["parent_field"]] = _value(row, config["parent_aliases"], required=True)
    return values


def _validate_parent(db: Session, entity_type: str, values: dict) -> None:
    config = ENTITY_CONFIG[entity_type]
    if entity_type == "states":
        return
    if entity_type == "urban_local_bodies":
        if db.scalar(select(State).where(State.lgd_code == values["state_code"])) is None:
            raise LGDImportError(f"Unknown parent state code: {values['state_code']}")
        district_code = values.get("district_code")
        if (
            district_code
            and db.scalar(select(District).where(District.lgd_code == district_code)) is None
        ):
            raise LGDImportError(f"Unknown parent district code: {district_code}")
        return
    parent_code = values[config["parent_field"]]
    parent_model = config["parent_model"]
    if db.scalar(select(parent_model).where(parent_model.lgd_code == parent_code)) is None:
        raise LGDImportError(f"Unknown parent code: {parent_code}")


def import_lgd_file(
    db: Session,
    *,
    entity_type: str,
    path: Path,
    source_version: str,
    source_url: str = LGD_DOWNLOAD_URL,
) -> ImportResult:
    if entity_type not in ENTITY_CONFIG:
        raise LGDImportError(f"Unsupported LGD entity type: {entity_type}")
    if not source_version.strip():
        raise LGDImportError("A source version or official export date is required")
    body, rows = read_lgd_rows(path)
    job = LocationImportJob(
        entity_type=entity_type,
        source_url=source_url,
        source_version=source_version.strip(),
        source_filename=path.name,
        source_sha256=hashlib.sha256(body).hexdigest(),
        status="RUNNING",
        rows_received=len(rows),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    inserted = updated = skipped = 0
    seen: dict[str, dict] = {}
    model = ENTITY_CONFIG[entity_type]["model"]
    try:
        for row_number, row in enumerate(rows, start=2):
            values = _record_values(entity_type, row, source_version.strip())
            code = str(values["lgd_code"])
            if code in seen:
                comparable = {key: value for key, value in values.items() if key != "imported_at"}
                previous = {key: value for key, value in seen[code].items() if key != "imported_at"}
                if comparable != previous:
                    raise LGDImportError(
                        f"Conflicting duplicate LGD code {code} at source row {row_number}"
                    )
                skipped += 1
                continue
            seen[code] = values
            _validate_parent(db, entity_type, values)
            existing = db.scalar(select(model).where(model.lgd_code == code))
            if existing is None:
                db.add(model(**values))
                inserted += 1
                db.flush()
                continue
            changed = False
            for key, value in values.items():
                if key == "imported_at":
                    continue
                if getattr(existing, key) != value:
                    setattr(existing, key, value)
                    changed = True
            if changed:
                existing.imported_at = values["imported_at"]
                updated += 1
            else:
                skipped += 1

        job = db.get(LocationImportJob, job.id)
        job.status = "COMPLETED"
        job.rows_inserted = inserted
        job.rows_updated = updated
        job.rows_skipped = skipped
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as error:
        db.rollback()
        failed = db.get(LocationImportJob, job.id)
        if failed is not None:
            failed.status = "FAILED"
            failed.error_summary = str(error)[:2000]
            failed.completed_at = datetime.now(timezone.utc)
            db.commit()
        if isinstance(error, LGDImportError):
            raise
        raise LGDImportError(
            "The LGD import failed and all entity changes were rolled back"
        ) from error

    return ImportResult(
        job_id=str(job.id),
        status="COMPLETED",
        rows_received=len(rows),
        rows_inserted=inserted,
        rows_updated=updated,
        rows_skipped=skipped,
    )
