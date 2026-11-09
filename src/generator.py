"""Générateur de télémétrie synthétique — TP Data Engineering.

Objectif :
- générer des événements de jeu ;
- produire un fichier JSONL ;
- pouvoir injecter des données invalides pour tester le futur validateur.

Les étudiants doivent compléter les parties marquées TODO.
Compatible Python 3.9.
"""

from datetime import datetime, timezone
import json
import random
import uuid
from pathlib import Path
from typing import Optional


EVENT_TYPES = [
    "session_started",
    "level_completed",
    "player_death",
    "match_finished",
    "game_error",
]

VERSIONS = ["1.4.1", "1.4.2", "1.5.0"]


def generate_event(player_id: Optional[str] = None) -> dict:
    """Génère un événement de télémétrie synthétique."""
    event_type = random.choice(EVENT_TYPES)

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "player_id": player_id or "player-{0:03d}".format(random.randint(1, 100)),
        "session_id": "session-{0}".format(uuid.uuid4().hex[:12]),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "game_version": random.choice(VERSIONS),
    }

    if event_type == "level_completed":
        event["level_id"] = "level-{0:02d}".format(random.randint(1, 20))
        event["duration_seconds"] = random.randint(30, 900)
    elif event_type == "player_death":
        event["level_id"] = "level-{0:02d}".format(random.randint(1, 20))
        event["cause"] = random.choice(["enemy", "fall", "trap", "unknown"])
    elif event_type == "game_error":
        event["error_code"] = random.choice(
            ["NET_TIMEOUT", "ASSET_MISSING", "AUTH_FAILED"]
        )

    return event


def write_events(
    path: str = "data/events.jsonl",
    count: int = 1000,
    corrupt: bool = False,
) -> None:
    """Écrit des événements au format JSONL.

    Si corrupt=True, le fichier doit contenir quelques événements invalides
    et une ligne JSON malformée afin de tester le validateur.
    """
    if count < 0:
        raise ValueError("Le nombre d'événements ne peut pas être négatif.")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    events = [generate_event() for _ in range(count)]

    if corrupt and events:
        events[0].pop("player_id", None)
        if len(events) > 1:
            events[1]["occurred_at"] = "date-invalide"
        if len(events) > 2:
            events[2]["event_type"] = "unknown_type"
        if len(events) > 3:
            events[3]["event_type"] = "level_completed"
            events[3]["level_id"] = "level-{0:02d}".format(random.randint(1, 20))
            events[3]["duration_seconds"] = -10

    with target.open("w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

        if corrupt:
            file.write('{"broken_json":\n')


if __name__ == "__main__":
    write_events()
    print("Fichier généré : data/events.jsonl")
