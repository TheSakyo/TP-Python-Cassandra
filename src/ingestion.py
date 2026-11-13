"""Ingestion Cassandra — exercice étudiant."""

from datetime import datetime
import json
from pathlib import Path

from .metrics import EventSummary, rejection_rate
from .transformations import normalize_event
from .validator import validate_event

def _read_validate_and_write(path: str, session) -> tuple[int, list[dict], dict]:
    # Étapes :
    # 1. Préparer les requêtes d'insertion dans les tables Cassandra.
    # 2. Lire le fichier JSONL ligne par ligne et décoder chaque événement.
    # 3. Valider chaque événement et conserver les lignes invalides en rejet.
    # 4. Normaliser les événements valides puis les insérer dans Cassandra.
    # 5. Renvoyer le nombre d'événements insérés et les lignes rejetées.
    """Traite les événements JSONL et écrit les événements valides dans Cassandra.

    Renvoie le nombre d'événements insérés et les lignes à mettre en quarantaine.
    """
    query = session.prepare(
        """
        INSERT INTO events_by_player_day (
            player_id, event_day, occurred_at, event_id, session_id,
            event_type, game_version, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )
    session_query = session.prepare(
        """
        INSERT INTO events_by_session (
            session_id, occurred_at, event_id, player_id, event_type, payload
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
    )
    error_query = session.prepare(
        """
        INSERT INTO errors_by_version_day (
            game_version, event_day, occurred_at, event_id, player_id, payload
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
    )

    inserted = 0
    rejected = []
    summary = EventSummary()

    with open(path, "r", encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as error:
                rejected.append({
                    "line": line_number,
                    "raw": raw_line.rstrip("\r\n"),
                    "errors": ["JSON invalide : {0}".format(error)],
                })
                continue

            if not isinstance(event, dict):
                errors = ["L'événement JSON doit être un objet."]
            else:
                errors = validate_event(event)

            if errors:
                rejected.append({
                    "line": line_number,
                    "raw": raw_line.rstrip("\r\n"),
                    "errors": errors,
                })
                continue

            event = normalize_event(event)
            try:
                occurred_at = datetime.fromisoformat(
                    event["occurred_at"].replace("Z", "+00:00")
                )
            except ValueError as error:
                rejected.append({
                    "line": line_number,
                    "raw": raw_line.rstrip("\r\n"),
                    "errors": ["Date invalide : {0}".format(error)],
                })
                continue

            event_day = occurred_at.date()
            payload = json.dumps(event, ensure_ascii=False)
            session.execute(
                query,
                (
                    event["player_id"], event_day, occurred_at, event["event_id"],
                    event["session_id"], event["event_type"],
                    event["game_version"], payload,
                ),
            )
            session.execute(
                session_query,
                (
                    event["session_id"], occurred_at, event["event_id"],
                    event["player_id"], event["event_type"], payload,
                ),
            )
            if event["event_type"] == "game_error":
                session.execute(
                    error_query,
                    (
                        event["game_version"], event_day, occurred_at,
                        event["event_id"], event["player_id"], payload,
                    ),
                )
            summary.add(event)
            inserted += 1

    return inserted, rejected, summary.as_dict()

def ingest_file(path: str) -> dict:
    """Ingère un fichier JSONL dans Cassandra et écrit les rejets en quarantaine.

    Le schéma doit déjà avoir été appliqué avec cqlsh (voir README.md).
    """
    from cassandra.cluster import Cluster

    cluster = Cluster(["127.0.0.1"])
    session = None
    try:
        session = cluster.connect("game_telemetry")
        inserted, rejected, event_summary = _read_validate_and_write(path, session)
    finally:
        if session is not None:
            session.shutdown()
        cluster.shutdown()

    rejected_path = Path("data/rejected_events.jsonl")
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    with rejected_path.open("w", encoding="utf-8") as destination:
        for item in rejected:
            destination.write(json.dumps(item, ensure_ascii=False) + "\n")

    total = inserted + len(rejected)
    report = {
        "total": total,
        "accepted": inserted,
        "rejected": len(rejected),
        "rejection_rate": rejection_rate(total, len(rejected)),
        "events_by_type": event_summary["events_by_type"],
        "levels_completed": event_summary["levels_completed"],
        "errors_by_version": event_summary["errors_by_version"],
    }

    report_path = Path("data/quality_report.json")
    with report_path.open("w", encoding="utf-8") as destination:
        json.dump(report, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    return report

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingère un fichier JSONL dans Cassandra.")
    parser.add_argument("path", nargs="?", default="data/events.jsonl")
    arguments = parser.parse_args()
    print(json.dumps(ingest_file(arguments.path), ensure_ascii=False, indent=2))
