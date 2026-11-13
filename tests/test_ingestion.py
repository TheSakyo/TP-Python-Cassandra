import json
import sys
from types import ModuleType

import pytest

from src.ingestion import ingest_file

class FakeSession:
    def __init__(self):
        self.prepared_queries = []
        self.executed = []
        self.closed = False

    def prepare(self, query):
        self.prepared_queries.append(query)
        return query

    def execute(self, query, parameters):
        self.executed.append((query, parameters))

    def shutdown(self):
        self.closed = True

class FakeCluster:
    def __init__(self, session):
        self.session = session
        self.hosts = None
        self.keyspace = None
        self.closed = False

    def connect(self, keyspace):
        self.keyspace = keyspace
        return self.session

    def shutdown(self):
        self.closed = True

def valid_event(event_type="session_started", event_id="evt-1"):
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "player_id": "player-001",
        "session_id": "session-1",
        "occurred_at": "2026-11-09T10:00:00+02:00",
        "game_version": "1.4.2",
    }
    if event_type == "level_completed":
        event["duration_seconds"] = 90
    if event_type == "game_error":
        event["error_code"] = "NET_TIMEOUT"
    return event

def test_ingest_file_inserts_valid_events_and_quarantines_invalid_lines(
    tmp_path, monkeypatch
):
    session = FakeSession()
    cluster = FakeCluster(session)
    cassandra_module = ModuleType("cassandra")
    cassandra_module.__path__ = []
    cluster_module = ModuleType("cassandra.cluster")
    cluster_module.Cluster = lambda hosts: cluster
    cassandra_module.cluster = cluster_module
    monkeypatch.setitem(sys.modules, "cassandra", cassandra_module)
    monkeypatch.setitem(sys.modules, "cassandra.cluster", cluster_module)
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "events.jsonl"
    invalid_type_event = valid_event()
    invalid_type_event["event_type"] = "unknown_type"
    source.write_text(
        "\n".join(
            [
                json.dumps(valid_event()),
                json.dumps(valid_event("level_completed", "evt-2")),
                json.dumps(valid_event("game_error", "evt-3")),
                json.dumps(invalid_type_event),
                '{"broken_json":',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = ingest_file(str(source))

    assert result["total"] == 5
    assert result["accepted"] == 3
    assert result["rejected"] == 2
    assert result["rejection_rate"] == 40.0
    assert result["levels_completed"] == 1
    assert result["errors_by_version"] == {"1.4.2": 1}
    assert cluster.keyspace == "game_telemetry"
    assert cluster.closed
    assert session.closed
    assert len(session.executed) == 7

    query, parameters = session.executed[0]
    assert query in session.prepared_queries
    assert parameters[0] == "player-001"
    assert parameters[1].isoformat() == "2026-11-09"
    assert parameters[2].isoformat() == "2026-11-09T08:00:00+00:00"

    query_texts = [query for query, _ in session.executed]
    assert sum("INSERT INTO events_by_player_day" in query for query in query_texts) == 3
    assert sum("INSERT INTO events_by_session" in query for query in query_texts) == 3
    assert sum("INSERT INTO errors_by_version_day" in query for query in query_texts) == 1

    quarantine_path = tmp_path / "data" / "rejected_events.jsonl"
    rejected = [json.loads(line) for line in quarantine_path.read_text(encoding="utf-8").splitlines()]
    assert [item["line"] for item in rejected] == [4, 5]
    assert "Type d'événement inconnu" in " ".join(rejected[0]["errors"])
    assert "JSON invalide" in " ".join(rejected[1]["errors"])

    report_path = tmp_path / "data" / "quality_report.json"
    assert json.loads(report_path.read_text(encoding="utf-8")) == result
