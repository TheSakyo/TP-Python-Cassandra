"""Calcul d'indicateurs sur la qualité et le contenu des événements."""

from collections import Counter

class EventSummary:
    """Agrégateur incrémental pour calculer les indicateurs sans garder les événements."""

    def __init__(self):
        self.total_events = 0
        self.events_by_type = Counter()
        self.errors_by_version = Counter()

    def add(self, event: dict) -> None:
        if not isinstance(event, dict):
            return

        self.total_events += 1
        event_type = event.get("event_type", "unknown")
        self.events_by_type[event_type] += 1

        if event_type == "game_error":
            self.errors_by_version[event.get("game_version", "unknown")] += 1

    def as_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "events_by_type": dict(sorted(self.events_by_type.items())),
            "levels_completed": self.events_by_type.get("level_completed", 0),
            "errors_by_version": dict(sorted(self.errors_by_version.items())),
        }

def rejection_rate(total: int, rejected: int) -> float:
    """Renvoie le pourcentage d'événements rejetés (0 si aucun événement)."""
    if total < 0 or rejected < 0 or rejected > total:
        raise ValueError("Les compteurs doivent respecter 0 <= rejetés <= total.")
    if total == 0:
        return 0.0
    return rejected * 100.0 / total


def summarize_events(events: list[dict]) -> dict:
    """Compte les types d'événements, niveaux terminés et erreurs par version."""
    summary = EventSummary()
    for event in events:
        summary.add(event)
    return summary.as_dict()
