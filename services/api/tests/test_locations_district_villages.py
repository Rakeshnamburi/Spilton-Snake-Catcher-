"""Villages can be listed for a whole district, with an optional name search."""

import pytest

from app.db.session import SessionLocal
from app.models.entities import District, State, Subdistrict, Village

pytestmark = pytest.mark.anyio

SOURCE = "synthetic-test-only"


def _seed_villages(db) -> None:
    db.add(State(lgd_code="V-S", name="Village Test State", is_active=True, source_version=SOURCE))
    db.add(
        District(
            lgd_code="V-D",
            state_code="V-S",
            name="Village Test District",
            is_active=True,
            source_version=SOURCE,
        )
    )
    db.add(
        Subdistrict(
            lgd_code="V-M1",
            district_code="V-D",
            name="First Mandal",
            is_active=True,
            source_version=SOURCE,
        )
    )
    db.add(
        Subdistrict(
            lgd_code="V-M2",
            district_code="V-D",
            name="Second Mandal",
            is_active=True,
            source_version=SOURCE,
        )
    )
    db.flush()
    for code, subdistrict, name in (
        ("V-1", "V-M1", "Amberpet"),
        ("V-2", "V-M1", "Amberpet Sarfekhas"),
        ("V-3", "V-M2", "Gachibowli"),
        ("V-4", "V-M2", "Kondapur"),
    ):
        db.add(
            Village(
                lgd_code=code,
                subdistrict_code=subdistrict,
                name=name,
                is_active=True,
                source_version=SOURCE,
            )
        )
    db.flush()


async def test_villages_list_for_a_whole_district(client):
    with SessionLocal() as db:
        _seed_villages(db)
        db.commit()

    everything = await client.get("/api/v1/locations/villages?district_code=V-D&limit=50")
    assert everything.status_code == 200
    assert everything.json()["total"] == 4
    assert [item["name"] for item in everything.json()["items"]] == [
        "Amberpet",
        "Amberpet Sarfekhas",
        "Gachibowli",
        "Kondapur",
    ]

    searched = await client.get("/api/v1/locations/villages?district_code=V-D&q=amber&limit=50")
    assert searched.status_code == 200
    assert searched.json()["total"] == 2

    by_mandal = await client.get("/api/v1/locations/villages?subdistrict_code=V-M2&limit=50")
    assert by_mandal.status_code == 200
    assert [item["name"] for item in by_mandal.json()["items"]] == ["Gachibowli", "Kondapur"]

    missing = await client.get("/api/v1/locations/villages")
    assert missing.status_code == 400
