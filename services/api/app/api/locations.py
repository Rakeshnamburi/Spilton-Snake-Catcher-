import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import District, State, Subdistrict, UrbanLocalBody, Village, Ward
from app.schemas.marketplace import LocationItem, LocationPage, LocationSearchItem

router = APIRouter(prefix="/locations", tags=["locations"])


def _page(db: Session, model, filters: list, page: int, limit: int) -> LocationPage:
    total = db.scalar(select(func.count()).select_from(model).where(*filters)) or 0
    items = db.scalars(
        select(model)
        .where(*filters)
        .order_by(model.name, model.lgd_code)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return LocationPage(
        items=[LocationItem.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/states", response_model=LocationPage)
def states(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    filters = [] if include_inactive else [State.is_active.is_(True)]
    return _page(db, State, filters, page, limit)


@router.get("/districts", response_model=LocationPage)
def districts(
    state_code: str = Query(min_length=1, max_length=20),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    filters = [District.state_code == state_code.strip()]
    if not include_inactive:
        filters.append(District.is_active.is_(True))
    return _page(db, District, filters, page, limit)


@router.get("/subdistricts", response_model=LocationPage)
def subdistricts(
    district_code: str = Query(min_length=1, max_length=20),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    filters = [Subdistrict.district_code == district_code.strip()]
    if not include_inactive:
        filters.append(Subdistrict.is_active.is_(True))
    return _page(db, Subdistrict, filters, page, limit)


@router.get("/villages", response_model=LocationPage)
def villages(
    subdistrict_code: str = Query(min_length=1, max_length=20),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    filters = [Village.subdistrict_code == subdistrict_code.strip()]
    if not include_inactive:
        filters.append(Village.is_active.is_(True))
    return _page(db, Village, filters, page, limit)


@router.get("/search", response_model=list[LocationSearchItem])
def search_locations(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    term = q.strip()
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    results: list[LocationSearchItem] = []
    configs = (
        (State, "STATE", None),
        (District, "DISTRICT", "state_code"),
        (Subdistrict, "SUBDISTRICT", "district_code"),
        (Village, "VILLAGE", "subdistrict_code"),
        (UrbanLocalBody, "URBAN_LOCAL_BODY", "district_code"),
        (Ward, "WARD", "urban_local_body_code"),
    )
    for model, entity_type, parent_field in configs:
        if len(results) >= limit:
            break
        matches = db.scalars(
            select(model)
            .where(
                model.is_active.is_(True),
                or_(model.name.ilike(pattern, escape="\\"), model.lgd_code == term),
            )
            .order_by(model.name)
            .limit(limit - len(results))
        ).all()
        for match in matches:
            item = LocationSearchItem(
                **LocationItem.model_validate(match).model_dump(),
                entity_type=entity_type,
                parent_code=getattr(match, parent_field) if parent_field else None,
            )
            results.append(item)
    return results
