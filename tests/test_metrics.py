import pytest  # Fournit les tests paramétrés et l'assertion d'exception.

from src.metrics import rejection_rate, summarize_events  # Importe les indicateurs à vérifier.

@pytest.mark.parametrize(  # Répète un même test avec plusieurs jeux de compteurs.
    ("total", "rejected", "expected"),  # Noms des valeurs injectées dans le test.
    [(0, 0, 0.0), (10, 0, 0.0), (10, 2, 20.0), (4, 4, 100.0)],  # Cas vide, aucun rejet, rejet partiel et rejet total.
)
def test_rejection_rate(total, rejected, expected):  # Vérifie le pourcentage de rejet.
    assert rejection_rate(total, rejected) == expected  # Compare le résultat au pourcentage attendu.

@pytest.mark.parametrize("total,rejected", [(-1, 0), (2, -1), (2, 3)])  # Cas de compteurs impossibles.
def test_rejection_rate_rejects_invalid_counts(total, rejected):  # Vérifie la gestion des compteurs incorrects.
    with pytest.raises(ValueError):  # Attend une erreur de valeur.
        rejection_rate(total, rejected)  # Le calcul doit refuser ces nombres.

def test_summarize_events_counts_types_completions_and_errors_by_version():  # Vérifie les trois indicateurs métier.
    events = [  # Prépare des événements de plusieurs types et versions.
        {"event_type": "level_completed", "game_version": "1.4.2"},  # Première fin de niveau.
        {"event_type": "level_completed", "game_version": "1.4.2"},  # Deuxième fin de niveau.
        {"event_type": "game_error", "game_version": "1.4.2"},  # Erreur sur la version 1.4.2.
        {"event_type": "game_error", "game_version": "1.5.0"},  # Erreur sur la version 1.5.0.
        {"event_type": "session_started", "game_version": "1.5.0"},  # Début de session.
    ]  # Termine les données d'essai.

    assert summarize_events(events) == {  # Compare le résumé complet attendu.
        "total_events": 5,  # Cinq événements sont fournis.
        "events_by_type": {  # Compte les événements par type.
            "game_error": 2,  # Deux erreurs techniques.
            "level_completed": 2,  # Deux niveaux terminés.
            "session_started": 1,  # Une session démarrée.
        },  # Termine les compteurs par type.
        "levels_completed": 2,  # Vérifie l'indicateur des niveaux terminés.
        "errors_by_version": {"1.4.2": 1, "1.5.0": 1},  # Vérifie les erreurs par version.
    }  # Termine le résumé attendu.

def test_summarize_empty_events():  # Vérifie les valeurs initiales pour une liste vide.
    assert summarize_events([]) == {  # Un lot vide doit avoir des compteurs à zéro.
        "total_events": 0,  # Aucun événement.
        "events_by_type": {},  # Aucun type compté.
        "levels_completed": 0,  # Aucun niveau terminé.
        "errors_by_version": {},  # Aucune erreur par version.
    }  # Termine le résumé vide attendu.
