"""Normalisation des événements avant leur stockage."""

from datetime import datetime, timezone

STRING_FIELDS = (
    "event_id",
    "event_type",
    "player_id",
    "session_id",
    "occurred_at",
    "game_version",
)

def normalize_event(event: dict) -> dict:
    """Renvoie une copie normalisée sans modifier l'événement d'origine.

    Les champs textuels communs sont débarrassés des espaces superflus.
    Un horodatage ISO-8601 valide est converti en UTC et fournit event_day.
    Un horodatage invalide est laissé tel quel pour que le validateur le rejette.
    """
    if not isinstance(event, dict):
        return event

    normalized = dict(event)
    for field in STRING_FIELDS:
        value = normalized.get(field)
        if isinstance(value, str):
            normalized[field] = value.strip()

    occurred_at = normalized.get("occurred_at")
    if isinstance(occurred_at, str) and occurred_at:
        if "T" not in occurred_at.upper() and " " not in occurred_at:
            return normalized
        try:
            timestamp = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        except ValueError:
            return normalized

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        normalized["occurred_at"] = timestamp.isoformat()
        normalized["event_day"] = timestamp.date().isoformat()

    return normalized
