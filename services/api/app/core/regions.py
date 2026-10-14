from typing import Final

STATE_BOUNDS: Final[dict[str, tuple[float, float, float, float]]] = {
    # south, west, north, east; intentionally broad validation envelopes.
    "Andhra Pradesh": (12.6, 76.7, 19.2, 84.9),
    "Telangana": (15.7, 77.1, 19.9, 81.0),
    "Karnataka": (11.5, 74.0, 18.5, 78.7),
    "Tamil Nadu": (8.0, 76.2, 13.6, 80.4),
    "Kerala": (8.1, 74.8, 12.8, 77.5),
}

TARGET_STATES: Final[frozenset[str]] = frozenset(STATE_BOUNDS)


def coordinates_are_in_state(state: str, latitude: float, longitude: float) -> bool:
    south, west, north, east = STATE_BOUNDS[state]
    return south <= latitude <= north and west <= longitude <= east
