import math

import pytest

from src.validator import validate_event


def valid_event():
    return {
        "event_id": "evt-1",
        "event_type": "session_started",
        "player_id": "player-001",
        "session_id": "session-1",
        "occurred_at": "2026-11-09T09:00:00+00:00",
        "game_version": "1.4.2",
    }


def test_valid_event_has_no_errors():
    assert validate_event(valid_event()) == []


def test_non_object_event_is_rejected():
    assert validate_event(["not", "an", "object"]) == [
        "L'événement doit être un objet JSON."
    ]


def test_missing_required_field_is_reported():
    event = valid_event()
    del event["player_id"]

    assert any("player_id" in error for error in validate_event(event))


def test_empty_required_field_is_rejected():
    event = valid_event()
    event["session_id"] = "  "

    assert any("session_id" in error for error in validate_event(event))


def test_unknown_event_type_is_rejected():
    event = valid_event()
    event["event_type"] = "teleport"

    assert any("Type d'événement inconnu" in error for error in validate_event(event))


@pytest.mark.parametrize("timestamp", ["date-invalide", "2026-11-09", ""])
def test_invalid_timestamp_is_rejected(timestamp):
    event = valid_event()
    event["occurred_at"] = timestamp

    assert any("occurred_at" in error for error in validate_event(event))


@pytest.mark.parametrize(
    "duration",
    [None, 0, -1, "30", True, math.nan, math.inf],
)
def test_level_completion_requires_positive_finite_numeric_duration(duration):
    event = valid_event()
    event.update(event_type="level_completed", duration_seconds=duration)

    assert any("duration_seconds" in error for error in validate_event(event))


def test_level_completion_accepts_positive_duration():
    event = valid_event()
    event.update(event_type="level_completed", duration_seconds=30)

    assert validate_event(event) == []


def test_other_event_types_do_not_require_duration():
    assert validate_event(valid_event()) == []
