from app.models.entities import IncidentStatus


class InvalidStatusTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.CREATED: frozenset(
        {
            IncidentStatus.UNDER_REVIEW,
            IncidentStatus.CANCELLED,
            IncidentStatus.UNABLE_TO_ASSIST,
        }
    ),
    IncidentStatus.UNDER_REVIEW: frozenset(
        {
            IncidentStatus.ASSIGNED,
            IncidentStatus.CANCELLED,
            IncidentStatus.UNABLE_TO_ASSIST,
        }
    ),
    IncidentStatus.ASSIGNED: frozenset(
        {IncidentStatus.IN_PROGRESS, IncidentStatus.CANCELLED, IncidentStatus.UNABLE_TO_ASSIST}
    ),
    IncidentStatus.IN_PROGRESS: frozenset(
        {IncidentStatus.RESOLVED, IncidentStatus.UNABLE_TO_ASSIST}
    ),
    IncidentStatus.RESOLVED: frozenset({IncidentStatus.CLOSED}),
    IncidentStatus.CLOSED: frozenset(),
    IncidentStatus.CANCELLED: frozenset(),
    IncidentStatus.UNABLE_TO_ASSIST: frozenset({IncidentStatus.CLOSED}),
}

CITIZEN_CANCELLABLE = frozenset({IncidentStatus.CREATED, IncidentStatus.UNDER_REVIEW})


def validate_transition(current: IncidentStatus, target: IncidentStatus) -> None:
    if target == current:
        raise InvalidStatusTransition(f"Incident is already {target.value}")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(
            f"Cannot change an incident from {current.value} to {target.value}"
        )
