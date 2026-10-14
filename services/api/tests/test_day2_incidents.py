import io
from datetime import datetime, timezone

import pytest
from PIL import Image

from app.services.media_storage import MAX_MEDIA_BYTES

pytestmark = pytest.mark.anyio


def bearer(account: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {account['access_token']}"}


def incident_payload(**overrides) -> dict:
    payload = {
        "reporter_name": "Test Citizen",
        "contact_phone": "9876543210",
        "reporter_email": "citizen@example.com",
        "state": "Kerala",
        "district": "Ernakulam",
        "city": "Kochi",
        "landmark": "Demo community gate",
        "address_description": "Visible from the public road",
        "sighting_at": datetime.now(timezone.utc).isoformat(),
        "description": "Snake observed from a safe distance near the gate.",
        "injury_reported": False,
        "snake_visible": True,
        "immediate_danger": False,
        "urgency": "STANDARD",
        "consent": True,
    }
    payload.update(overrides)
    return payload


async def create_incident(client, citizen, **overrides) -> dict:
    response = await client.post(
        "/api/v1/incidents",
        json=incident_payload(**overrides),
        headers=bearer(citizen),
    )
    assert response.status_code == 201, response.text
    return response.json()


def image_bytes(image_format: str = "JPEG", *, include_exif: bool = False) -> bytes:
    image = Image.new("RGB", (24, 18), color=(20, 120, 60))
    output = io.BytesIO()
    kwargs = {}
    if include_exif:
        exif = Image.Exif()
        exif[0x010E] = "Synthetic test metadata"
        kwargs["exif"] = exif
    image.save(output, format=image_format, **kwargs)
    return output.getvalue()


def corrupt_png_bytes() -> bytes:
    body = bytearray(image_bytes("PNG"))
    idat = body.index(b"IDAT")
    body[idat + 4] ^= 1
    return bytes(body)


async def test_manual_location_and_snakebite_triage_create_demo_incident(client, citizen):
    response = await client.post(
        "/api/v1/incidents",
        json=incident_payload(injury_reported=True, latitude=None, longitude=None),
        headers=bearer(citizen),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "CREATED"
    assert body["is_demo"] is True
    assert body["urgency"] == "SNAKEBITE"
    assert body["latitude"] is None and body["longitude"] is None
    assert "contact_phone" not in body and "reporter_email" not in body


async def test_server_side_triage_escalates_immediate_danger(client, citizen):
    response = await client.post(
        "/api/v1/incidents",
        json=incident_payload(immediate_danger=True, urgency="STANDARD"),
        headers=bearer(citizen),
    )
    assert response.status_code == 201
    assert response.json()["urgency"] == "HIGH"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reporter_name", "  "),
        ("district", "  "),
        ("city", "  "),
        ("description", "          "),
    ],
)
async def test_required_incident_text_rejects_whitespace_only(client, citizen, field, value):
    response = await client.post(
        "/api/v1/incidents",
        json=incident_payload(**{field: value}),
        headers=bearer(citizen),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_coordinates_are_validated_as_a_pair_and_bounded(client, citizen):
    only_latitude = await client.post(
        "/api/v1/incidents",
        json=incident_payload(latitude=12.9),
        headers=bearer(citizen),
    )
    assert only_latitude.status_code == 422
    assert only_latitude.json()["error"]["code"] == "VALIDATION_ERROR"

    out_of_bounds = await client.post(
        "/api/v1/incidents",
        json=incident_payload(latitude=91, longitude=80),
        headers=bearer(citizen),
    )
    assert out_of_bounds.status_code == 422

    wrong_state = await client.post(
        "/api/v1/incidents",
        json=incident_payload(latitude=17.4, longitude=78.5),
        headers=bearer(citizen),
    )
    assert wrong_state.status_code == 422
    assert wrong_state.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_owner_can_view_incident_but_another_citizen_cannot(client, citizen, other_citizen):
    incident = await create_incident(client, citizen)
    own = await client.get(f"/api/v1/incidents/{incident['id']}", headers=bearer(citizen))
    assert own.status_code == 200
    denied = await client.get(f"/api/v1/incidents/{incident['id']}", headers=bearer(other_citizen))
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "INCIDENT_ACCESS_DENIED"


async def test_idempotency_key_replays_without_duplicate(client, citizen):
    headers = {**bearer(citizen), "Idempotency-Key": "mobile-report-000001"}
    payload = incident_payload()
    first = await client.post("/api/v1/incidents", json=payload, headers=headers)
    second = await client.post("/api/v1/incidents", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.headers["x-idempotent-replay"] == "true"

    listing = await client.get("/api/v1/incidents/mine", headers=bearer(citizen))
    assert listing.json()["total"] == 1

    conflict = await client.post(
        "/api/v1/incidents",
        json=incident_payload(description="A materially different sighting description."),
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


async def test_my_incidents_is_paginated_and_filterable(client, citizen):
    first = await create_incident(client, citizen, city="Kochi")
    await create_incident(client, citizen, city="Aluva")
    await client.post(f"/api/v1/incidents/{first['id']}/cancel", headers=bearer(citizen))

    response = await client.get(
        "/api/v1/incidents/mine?page=1&page_size=1&status=CREATED", headers=bearer(citizen)
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["page_size"] == 1
    assert response.json()["items"][0]["city"] == "Aluva"


async def test_citizen_can_cancel_eligible_report_and_event_is_recorded(client, citizen):
    incident = await create_incident(client, citizen)
    cancelled = await client.post(
        f"/api/v1/incidents/{incident['id']}/cancel", headers=bearer(citizen)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    again = await client.post(f"/api/v1/incidents/{incident['id']}/cancel", headers=bearer(citizen))
    assert again.status_code == 409
    events = await client.get(f"/api/v1/incidents/{incident['id']}/events", headers=bearer(citizen))
    assert [event["event_type"] for event in events.json()] == [
        "INCIDENT_CREATED",
        "INCIDENT_CANCELLED",
    ]


async def test_admin_workflow_and_invalid_transition(client, citizen, admin):
    incident = await create_incident(client, citizen)
    path = f"/api/v1/admin/incidents/{incident['id']}/status"

    citizen_attempt = await client.patch(
        path, json={"status": "UNDER_REVIEW"}, headers=bearer(citizen)
    )
    assert citizen_attempt.status_code == 403

    invalid = await client.patch(path, json={"status": "CLOSED"}, headers=bearer(admin))
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    for target in ["UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
        updated = await client.patch(
            path,
            json={"status": target, "note": "Synthetic workflow test"},
            headers=bearer(admin),
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == target

    events = await client.get(f"/api/v1/incidents/{incident['id']}/events", headers=bearer(admin))
    assert events.json()[-1]["event_type"] == "INCIDENT_CLOSED"


async def test_admin_list_is_protected_filtered_and_privacy_reduced(client, citizen, admin):
    await create_incident(client, citizen, state="Kerala", district="Ernakulam")
    denied = await client.get("/api/v1/admin/incidents", headers=bearer(citizen))
    assert denied.status_code == 403

    response = await client.get(
        "/api/v1/admin/incidents?state=Kerala&search=Ernakulam", headers=bearer(admin)
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert response.json()["total"] == 1
    for private_field in [
        "reporter_name",
        "contact_phone",
        "reporter_email",
        "latitude",
        "longitude",
        "description",
    ]:
        assert private_field not in item


async def test_valid_image_is_sanitized_stored_and_authorized(client, citizen, other_citizen):
    incident = await create_incident(client, citizen)
    original = image_bytes(include_exif=True)
    uploaded = await client.post(
        f"/api/v1/incidents/{incident['id']}/media",
        files={"file": ("snake-photo.jpg", original, "image/jpeg")},
        headers=bearer(citizen),
    )
    assert uploaded.status_code == 201, uploaded.text
    metadata = uploaded.json()
    assert metadata["content_type"] == "image/jpeg"
    assert metadata["file_size"] <= MAX_MEDIA_BYTES

    listed = await client.get(f"/api/v1/incidents/{incident['id']}/media", headers=bearer(citizen))
    assert listed.status_code == 200 and len(listed.json()) == 1

    denied = await client.get(metadata["download_url"], headers=bearer(other_citizen))
    assert denied.status_code == 403
    client.cookies.clear()
    public = await client.get(metadata["download_url"])
    assert public.status_code == 401

    downloaded = await client.get(metadata["download_url"], headers=bearer(citizen))
    assert downloaded.status_code == 200
    assert downloaded.headers["cache-control"] == "private, no-store"
    with Image.open(io.BytesIO(downloaded.content)) as image:
        assert not image.getexif()


async def test_upload_requires_authentication_and_incident_ownership(
    client, citizen, other_citizen
):
    incident = await create_incident(client, citizen)
    path = f"/api/v1/incidents/{incident['id']}/media"
    body = image_bytes("PNG")

    client.cookies.clear()
    unauthenticated = await client.post(path, files={"file": ("snake.png", body, "image/png")})
    assert unauthenticated.status_code == 401

    denied = await client.post(
        path,
        files={"file": ("snake.png", body, "image/png")},
        headers=bearer(other_citizen),
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "INCIDENT_ACCESS_DENIED"


@pytest.mark.parametrize(
    ("filename", "body", "content_type", "expected_code"),
    [
        ("fake.jpg", b"this is not an image", "image/jpeg", "UNSUPPORTED_IMAGE"),
        (
            "huge.png",
            b"\x89PNG\r\n\x1a\n" + b"0" * MAX_MEDIA_BYTES,
            "image/png",
            "FILE_TOO_LARGE",
        ),
        ("mismatch.png", image_bytes("PNG"), "image/jpeg", "CONTENT_TYPE_MISMATCH"),
        ("corrupt.png", corrupt_png_bytes(), "image/png", "INVALID_IMAGE"),
    ],
    ids=["unsupported-signature", "oversized", "type-mismatch", "corrupt-image"],
)
async def test_invalid_oversized_and_mismatched_images_are_rejected(
    client, citizen, filename, body, content_type, expected_code
):
    incident = await create_incident(client, citizen)
    response = await client.post(
        f"/api/v1/incidents/{incident['id']}/media",
        files={"file": (filename, body, content_type)},
        headers=bearer(citizen),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == expected_code


async def test_incident_media_limit_is_three(client, citizen):
    incident = await create_incident(client, citizen)
    body = image_bytes("PNG")
    for index in range(3):
        response = await client.post(
            f"/api/v1/incidents/{incident['id']}/media",
            files={"file": (f"image-{index}.png", body, "image/png")},
            headers=bearer(citizen),
        )
        assert response.status_code == 201
    fourth = await client.post(
        f"/api/v1/incidents/{incident['id']}/media",
        files={"file": ("image-4.png", body, "image/png")},
        headers=bearer(citizen),
    )
    assert fourth.status_code == 409
    assert fourth.json()["error"]["code"] == "MEDIA_LIMIT_REACHED"


async def test_cookie_session_requires_double_submit_csrf_token(client, citizen):
    without_token = await client.post("/api/v1/incidents", json=incident_payload())
    assert without_token.status_code == 403
    assert without_token.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

    with_token = await client.post(
        "/api/v1/incidents",
        json=incident_payload(),
        headers={"X-CSRF-Token": citizen["csrf_token"]},
    )
    assert with_token.status_code == 201
