import pytest

from src.metrics import rejection_rate, summarize_events

@pytest.mark.parametrize(
    ("total", "rejected", "expected"),
    [(0, 0, 0.0), (10, 0, 0.0), (10, 2, 20.0), (4, 4, 100.0)],
)
def test_rejection_rate(total, rejected, expected):
    assert rejection_rate(total, rejected) == expected


@pytest.mark.parametrize("total,rejected", [(-1, 0), (2, -1), (2, 3)])
def test_rejection_rate_rejects_invalid_counts(total, rejected):
    with pytest.raises(ValueError):
        rejection_rate(total, rejected)

def test_summarize_events_counts_types_completions_and_errors_by_version():
    events = [
        {"event_type": "level_completed", "game_version": "1.4.2"},
        {"event_type": "level_completed", "game_version": "1.4.2"},
        {"event_type": "game_error", "game_version": "1.4.2"},
        {"event_type": "game_error", "game_version": "1.5.0"},
        {"event_type": "session_started", "game_version": "1.5.0"},
    ]

    assert summarize_events(events) == {
        "total_events": 5,
        "events_by_type": {
            "game_error": 2,
            "level_completed": 2,
            "session_started": 1,
        },
        "levels_completed": 2,
        "errors_by_version": {"1.4.2": 1, "1.5.0": 1},
    }

def test_summarize_empty_events():
    assert summarize_events([]) == {
        "total_events": 0,
        "events_by_type": {},
        "levels_completed": 0,
        "errors_by_version": {},
    }
