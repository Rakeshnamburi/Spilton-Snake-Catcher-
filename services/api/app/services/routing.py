from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.services.marketplace import haversine_km


@dataclass(frozen=True)
class RouteResult:
    status: str
    provider: str | None
    road_distance_km: float | None
    geographic_distance_km: float
    duration_seconds: int | None
    eta_at: datetime | None
    coordinates: list[list[float]]
    message: str


_cache: dict[tuple[float, float, float, float], tuple[float, RouteResult]] = {}
_cache_lock = threading.Lock()


def route_between(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> RouteResult:
    settings = get_settings()
    geographic = round(
        haversine_km(
            origin_latitude,
            origin_longitude,
            destination_latitude,
            destination_longitude,
        ),
        2,
    )
    unavailable = RouteResult(
        status="UNAVAILABLE",
        provider=None,
        road_distance_km=None,
        geographic_distance_km=geographic,
        duration_seconds=None,
        eta_at=None,
        coordinates=[],
        message="Road route and ETA are unavailable; geographic distance is shown separately.",
    )
    if not settings.routing_provider_url:
        return unavailable
    key = tuple(
        round(value, 5)
        for value in (
            origin_latitude,
            origin_longitude,
            destination_latitude,
            destination_longitude,
        )
    )
    now_monotonic = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and cached[0] > now_monotonic:
            return cached[1]
    base = settings.routing_provider_url.rstrip("/")
    url = (
        f"{base}/route/v1/driving/{origin_longitude},{origin_latitude};"
        f"{destination_longitude},{destination_latitude}"
    )
    headers = {"User-Agent": "SPILTON-Snake-Rescue-Demo/1.0"}
    if settings.routing_api_key:
        headers["Authorization"] = f"Bearer {settings.routing_api_key}"
    try:
        response = httpx.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        route = payload["routes"][0]
        seconds = max(0, int(route["duration"]))
        result = RouteResult(
            status="AVAILABLE",
            provider="OSRM_COMPATIBLE",
            road_distance_km=round(float(route["distance"]) / 1000, 2),
            geographic_distance_km=geographic,
            duration_seconds=seconds,
            eta_at=datetime.now(timezone.utc) + timedelta(seconds=seconds),
            coordinates=[
                [float(point[0]), float(point[1])] for point in route["geometry"]["coordinates"]
            ],
            message="Demo route estimate from the configured provider; not a dispatch promise.",
        )
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return unavailable
    with _cache_lock:
        _cache[key] = (now_monotonic + settings.routing_cache_seconds, result)
    return result
