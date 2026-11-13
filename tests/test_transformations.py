from src.transformations import normalize_event

def test_normalize_event_trims_common_strings_and_converts_to_utc():
    event = {
        "event_id": " evt-1 ",
        "event_type": " session_started ",
        "player_id": " player-001 ",
        "session_id": " session-1 ",
        "occurred_at": "2026-11-09T10:00:00+02:00",
        "game_version": " 1.4.2 ",
    }

    normalized = normalize_event(event)

    assert normalized["event_id"] == "evt-1"
    assert normalized["event_type"] == "session_started"
    assert normalized["player_id"] == "player-001"
    assert normalized["session_id"] == "session-1"
    assert normalized["game_version"] == "1.4.2"
    assert normalized["occurred_at"] == "2026-11-09T08:00:00+00:00"
    assert normalized["event_day"] == "2026-11-09"

def test_normalize_event_does_not_mutate_input():
    event = {"event_id": " evt-1 ", "occurred_at": "invalid"}

    normalized = normalize_event(event)

    assert event["event_id"] == " evt-1 "
    assert normalized["event_id"] == "evt-1"

def test_invalid_timestamp_is_left_for_validator_to_reject():
    event = {"occurred_at": "date-invalide"}

    normalized = normalize_event(event)

    assert normalized["occurred_at"] == "date-invalide"
    assert "event_day" not in normalized
