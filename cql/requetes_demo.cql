USE game_telemetry;

-- Activité d'un joueur pendant une journée (table events_by_player_day).
SELECT occurred_at, event_type, game_version, payload
FROM events_by_player_day
WHERE player_id = 'player-001' AND event_day = '2026-11-09'
LIMIT 20;

-- Chronologie d'une session (table events_by_session).
SELECT occurred_at, event_id, player_id, event_type, payload
FROM events_by_session
WHERE session_id = 'session-abc123'
LIMIT 20;

-- Erreurs techniques d'une version pendant une journée.
SELECT occurred_at, event_id, player_id, payload
FROM errors_by_version_day
WHERE game_version = '1.4.2' AND event_day = '2026-11-09'
LIMIT 20;
