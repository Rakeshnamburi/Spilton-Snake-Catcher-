import math

from fastapi import APIRouter, Depends, HTTPException, Query
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
    subdistrict_code: str | None = Query(default=None, max_length=20),
    district_code: str | None = Query(default=None, max_length=20),
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """Villages for a mandal, or for a whole district.

    Selecting a district lists every village in it (joined through the
    sub-district), which is what people expect when they only know their
    district. `q` filters by village name so large districts stay usable.
    """

    if not subdistrict_code and not district_code:
        raise HTTPException(
            status_code=400,
            detail="Provide subdistrict_code or district_code",
        )

    def _conditions() -> list:
        conditions = []
        if subdistrict_code:
            conditions.append(Village.subdistrict_code == subdistrict_code.strip())
        if not include_inactive:
            conditions.append(Village.is_active.is_(True))
        if q and q.strip():
            conditions.append(Village.name.ilike(f"%{q.strip()}%"))
        return conditions

    statement = select(Village)
    count_statement = select(func.count()).select_from(Village)
    if district_code:
        join_on = Village.subdistrict_code == Subdistrict.lgd_code
        statement = statement.join(Subdistrict, join_on)
        count_statement = count_statement.join(Subdistrict, join_on)
        district_filter = Subdistrict.district_code == district_code.strip()
        statement = statement.where(district_filter)
        count_statement = count_statement.where(district_filter)

    conditions = _conditions()
    statement = statement.where(*conditions)
    count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0
    items = db.scalars(
        statement.order_by(Village.name, Village.lgd_code)
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
