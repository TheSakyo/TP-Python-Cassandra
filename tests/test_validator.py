import math  # Sert à tester les valeurs NaN et infinies.

import pytest  # Fournit les tests paramétrés et la vérification d'exceptions.

from src.validator import validate_event  # Importe la fonction de validation testée.

def valid_event():  # Construit un événement de référence valide pour les tests.
    return {  # Renvoie les champs minimum du contrat.
        "event_id": "evt-1",  # Identifiant du test.
        "event_type": "session_started",  # Type autorisé.
        "player_id": "player-001",  # Identifiant joueur non vide.
        "session_id": "session-1",  # Identifiant session non vide.
        "occurred_at": "2026-11-09T09:00:00+00:00",  # Date ISO-8601 valide.
        "game_version": "1.4.2",  # Version texte valide.
    }

def test_valid_event_has_no_errors():  # Vérifie qu'un événement conforme est accepté.
    assert validate_event(valid_event()) == []  # Aucun message signifie aucune erreur.

def test_non_object_event_is_rejected():  # Vérifie le rejet d'une valeur qui n'est pas un objet.
    assert validate_event(["not", "an", "object"]) == [  # Une liste JSON ne respecte pas la forme attendue.
        "L'événement doit être un objet JSON."
    ]

def test_missing_required_field_is_reported():  # Vérifie qu'un champ obligatoire absent est signalé.
    event = valid_event()  # Part d'un événement correct.
    del event["player_id"]  # Retire un champ obligatoire.

    assert any("player_id" in error for error in validate_event(event))  # Cherche l'erreur liée au joueur.

def test_empty_required_field_is_rejected():  # Vérifie le rejet d'une valeur vide.
    event = valid_event()  # Crée l'événement de référence.
    event["session_id"] = "  "  # Remplace le contenu par des espaces seulement.

    assert any("session_id" in error for error in validate_event(event))  # Vérifie que le champ est déclaré invalide.

def test_unknown_event_type_is_rejected():  # Vérifie le rejet d'un type non autorisé.
    event = valid_event()  # Crée un événement conforme.
    event["event_type"] = "teleport"  # Met un type absent de la liste autorisée.

    assert any("Type d'événement inconnu" in error for error in validate_event(event))  # Vérifie le message de type inconnu.

@pytest.mark.parametrize("timestamp", ["date-invalide", "2026-11-09", ""])  # Essaie plusieurs dates invalides.
def test_invalid_timestamp_is_rejected(timestamp):  # Vérifie le rejet de chacune de ces dates.
    event = valid_event()  # Part d'un événement valide.
    event["occurred_at"] = timestamp  # Remplace l'horodatage par le cas testé.

    assert any("occurred_at" in error for error in validate_event(event))  # Attend une erreur de date.

@pytest.mark.parametrize(
    "duration",  # Nom du paramètre transmis au test.
    [None, 0, -1, "30", True, math.nan, math.inf],  # Valeurs absentes, fausses, non numériques ou infinies.
)
def test_level_completion_requires_positive_finite_numeric_duration(duration):  # Vérifie toutes les durées invalides.
    event = valid_event()  # Crée l'événement de base.
    event.update(event_type="level_completed", duration_seconds=duration)  # Le transforme en fin de niveau.

    assert any("duration_seconds" in error for error in validate_event(event))  # Attend l'erreur de durée.

def test_level_completion_accepts_positive_duration():  # Vérifie qu'une durée correcte est acceptée.
    event = valid_event()  # Crée l'événement de base.
    event.update(event_type="level_completed", duration_seconds=30)  # Ajoute un type et une durée valides.

    assert validate_event(event) == []  # Vérifie l'absence d'erreurs.

def test_other_event_types_do_not_require_duration():  # Vérifie que les autres types n'ont pas besoin d'une durée.
    assert validate_event(valid_event()) == []  # session_started reste valide sans duration_seconds.
