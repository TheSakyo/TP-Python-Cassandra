"""Validation du contrat des événements de télémétrie."""

from datetime import datetime
import math

REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "player_id",
    "session_id",
    "occurred_at",
    "game_version",
}
ALLOWED_TYPES = {
    "session_started",
    "level_completed",
    "player_death",
    "match_finished",
    "game_error",
}

def _validate_required_fields(event: dict) -> list[str]:
    errors = []
    for field in sorted(REQUIRED_FIELDS.difference(event)):
        errors.append("Champ obligatoire absent : {0}.".format(field))

    for field in sorted(REQUIRED_FIELDS.intersection(event)):
        value = event[field]
        if not isinstance(value, str) or not value.strip():
            errors.append("Le champ {0} doit être une chaîne non vide.".format(field))
    return errors

def _validate_event_type(event: dict) -> list[str]:
    event_type = event.get("event_type")
    if isinstance(event_type, str) and event_type not in ALLOWED_TYPES:
        return ["Type d'événement inconnu : {0}.".format(event_type)]
    return []

def _validate_timestamp(event: dict) -> list[str]:
    occurred_at = event.get("occurred_at")
    if not isinstance(occurred_at, str) or not occurred_at.strip():
        return []

    timestamp_text = occurred_at.strip()
    try:
        if "T" not in timestamp_text.upper() and " " not in timestamp_text:
            raise ValueError("Un horodatage doit inclure une heure.")
        datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
    except ValueError:
        return ["Le champ occurred_at doit être une date ISO-8601 valide."]
    return []

def _validate_duration(event: dict) -> list[str]:
    if event.get("event_type") != "level_completed":
        return []

    duration = event.get("duration_seconds")
    invalid_duration = (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or duration <= 0
    )
    if isinstance(duration, float) and not math.isfinite(duration):
        invalid_duration = True

    if invalid_duration:
        return [
            "duration_seconds doit être un nombre strictement positif "
            "pour level_completed."
        ]
    return []

def validate_event(event: dict) -> list[str]:
    """Retourne les erreurs du contrat, ou une liste vide si l'événement est valide."""
    if not isinstance(event, dict):
        return ["L'événement doit être un objet JSON."]

    errors = []
    errors.extend(_validate_required_fields(event))
    errors.extend(_validate_event_type(event))
    errors.extend(_validate_timestamp(event))
    errors.extend(_validate_duration(event))
    return errors
