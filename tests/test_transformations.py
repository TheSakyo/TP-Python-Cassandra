from src.transformations import normalize_event  # Importe la fonction de transformation testée.


def test_normalize_event_trims_common_strings_and_converts_to_utc():  # Vérifie le nettoyage des champs et des dates.
    event = {  # Prépare un événement avec des espaces et un fuseau UTC+2.
        "event_id": " evt-1 ",  # Identifiant entouré d'espaces.
        "event_type": " session_started ",  # Type entouré d'espaces.
        "player_id": " player-001 ",  # Joueur entouré d'espaces.
        "session_id": " session-1 ",  # Session entourée d'espaces.
        "occurred_at": "2026-11-09T10:00:00+02:00",  # Date à convertir en UTC.
        "game_version": " 1.4.2 ",  # Version entourée d'espaces.
    }

    normalized = normalize_event(event)  # Applique la normalisation à une copie.

    assert normalized["event_id"] == "evt-1"  # Vérifie le nettoyage de l'identifiant.
    assert normalized["event_type"] == "session_started"  # Vérifie le nettoyage du type.
    assert normalized["player_id"] == "player-001"  # Vérifie le nettoyage du joueur.
    assert normalized["session_id"] == "session-1"  # Vérifie le nettoyage de la session.
    assert normalized["game_version"] == "1.4.2"  # Vérifie le nettoyage de la version.
    assert normalized["occurred_at"] == "2026-11-09T08:00:00+00:00"  # Vérifie la conversion vers UTC.
    assert normalized["event_day"] == "2026-11-09"  # Vérifie le jour calculé pour Cassandra.


def test_normalize_event_does_not_mutate_input():  # Vérifie que l'entrée initiale n'est pas modifiée.
    event = {"event_id": " evt-1 ", "occurred_at": "invalid"}  # Crée l'objet source.

    normalized = normalize_event(event)  # Transforme sa copie.

    assert event["event_id"] == " evt-1 "  # L'original garde sa valeur avec espaces.
    assert normalized["event_id"] == "evt-1"  # La copie renvoie la valeur nettoyée.


def test_invalid_timestamp_is_left_for_validator_to_reject():  # Vérifie qu'une mauvaise date n'est pas masquée.
    event = {"occurred_at": "date-invalide"}  # Crée un événement à date incorrecte.

    normalized = normalize_event(event)  # Tente la normalisation sans réparer la date.

    assert normalized["occurred_at"] == "date-invalide"  # Garde la valeur afin que le validateur la voie.
    assert "event_day" not in normalized  # N'invente pas de jour à partir d'une date incorrecte.
