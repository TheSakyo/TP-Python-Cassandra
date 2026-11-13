"""Générateur de télémétrie synthétique — TP Data Engineering.

Objectif :
- générer des événements de jeu ;
- produire un fichier JSONL ;
- pouvoir injecter des données invalides pour tester le futur validateur.

Les étudiants doivent compléter les parties marquées TODO.
Compatible Python 3.9.
"""

from datetime import datetime, timezone  # Fournit les dates UTC des événements.
import json  # Encode les événements au format JSON.
import random  # Choisit des valeurs synthétiques au hasard.
import uuid  # Produit des identifiants uniques.
from pathlib import Path  # Manipule le chemin de sortie indépendamment de l'OS.
from typing import Optional  # Indique qu'un player_id peut être absent.


EVENT_TYPES = [  # Types d'événement que le générateur sait produire.
    "session_started",  # Début de session.
    "level_completed",  # Niveau terminé.
    "player_death",  # Mort du joueur.
    "match_finished",  # Fin de partie.
    "game_error",  # Erreur technique du jeu.
]

VERSIONS = ["1.4.1", "1.4.2", "1.5.0"]  # Versions possibles du jeu.


def generate_event(player_id: Optional[str] = None) -> dict:  # Génère un événement complet.
    """Génère un événement de télémétrie synthétique."""
    event_type = random.choice(EVENT_TYPES)  # Sélectionne son type au hasard.

    event = {  # Champs communs à tous les événements.
        "event_id": str(uuid.uuid4()),  # Identifiant unique de l'événement.
        "event_type": event_type,  # Type choisi plus haut.
        "player_id": player_id or "player-{0:03d}".format(random.randint(1, 100)),  # Joueur fourni ou généré.
        "session_id": "session-{0}".format(uuid.uuid4().hex[:12]),  # Identifiant court de session.
        "occurred_at": datetime.now(timezone.utc).isoformat(),  # Instant UTC au format ISO-8601.
        "game_version": random.choice(VERSIONS),  # Version choisie parmi les versions simulées.
    }

    if event_type == "level_completed":  # Ajoute les informations propres à un niveau terminé.
        event["level_id"] = "level-{0:02d}".format(random.randint(1, 20))  # Niveau entre 01 et 20.
        event["duration_seconds"] = random.randint(30, 900)  # Durée entre 30 et 900 secondes.
    elif event_type == "player_death":  # Ajoute les informations propres à une mort.
        event["level_id"] = "level-{0:02d}".format(random.randint(1, 20))  # Niveau où le joueur est mort.
        event["cause"] = random.choice(["enemy", "fall", "trap", "unknown"])  # Cause de la mort.
    elif event_type == "game_error":  # Ajoute les informations propres à une erreur technique.
        event["error_code"] = random.choice(  # Choisit un code d'erreur connu.
            ["NET_TIMEOUT", "ASSET_MISSING", "AUTH_FAILED"]  # Codes d'erreur possibles.
        )  # Fin du choix du code d'erreur.

    return event  # Renvoie l'événement composé.


def write_events(
    path: str = "data/events.jsonl",  # Fichier à écrire.
    count: int = 1000,  # Nombre d'événements JSON à produire.
    corrupt: bool = False,  # Active ou non l'insertion de cas invalides.
) -> None:
    """Écrit des événements au format JSONL.

    Si corrupt=True, le fichier doit contenir quelques événements invalides
    et une ligne JSON malformée afin de tester le validateur.
    """
    if count < 0:  # Refuse une quantité impossible.
        raise ValueError("Le nombre d'événements ne peut pas être négatif.")  # Signale l'erreur d'appel.

    target = Path(path)  # Convertit le chemin texte en objet Path.
    target.parent.mkdir(parents=True, exist_ok=True)  # Crée le dossier parent s'il manque.

    events = [generate_event() for _ in range(count)]  # Fabrique la liste d'événements synthétiques.

    if corrupt and events:  # N'injecte des défauts que si le mode est activé et qu'il existe des événements.
        events[0].pop("player_id", None)  # Rend le premier événement incomplet.
        if len(events) > 1:  # Vérifie qu'un deuxième événement existe.
            events[1]["occurred_at"] = "date-invalide"  # Rend sa date incorrecte.
        if len(events) > 2:  # Vérifie qu'un troisième événement existe.
            events[2]["event_type"] = "unknown_type"  # Rend son type inconnu.
        if len(events) > 3:  # Vérifie qu'un quatrième événement existe.
            events[3]["event_type"] = "level_completed"  # Force un événement de fin de niveau.
            events[3]["level_id"] = "level-{0:02d}".format(random.randint(1, 20))  # Ajoute un niveau valide.
            events[3]["duration_seconds"] = -10  # Injecte une durée fonctionnellement invalide.

    with target.open("w", encoding="utf-8") as file:  # Ouvre le fichier en écriture UTF-8.
        for event in events:  # Parcourt les événements à écrire.
            file.write(json.dumps(event, ensure_ascii=False) + "\n")  # Écrit un objet JSON par ligne.

        if corrupt:  # Ajoute aussi une ligne que le parseur JSON ne pourra pas lire.
            file.write('{"broken_json":\n')  # Simule une erreur de syntaxe JSON.


if __name__ == "__main__":  # Exécute ce bloc seulement si le fichier est lancé directement comme module.
    write_events()  # Génère les 1000 événements avec les paramètres par défaut.
    print("Fichier généré : data/events.jsonl")  # Affiche l'emplacement du fichier créé.
