"""Validation du contrat des événements de télémétrie."""

from datetime import datetime  # Parse les dates ISO-8601.
import math  # Vérifie que les durées flottantes ne sont pas NaN ou infinies.

REQUIRED_FIELDS = {  # Champs qui doivent apparaître dans chaque événement.
    "event_id",  # Identifiant unique.
    "event_type",  # Catégorie d'événement.
    "player_id",  # Identifiant pseudonyme du joueur.
    "session_id",  # Identifiant de session.
    "occurred_at",  # Date et heure de l'événement.
    "game_version",  # Version du jeu qui a produit l'événement.
}
ALLOWED_TYPES = {  # Valeurs autorisées pour le champ event_type.
    "session_started",  # Session démarrée.
    "level_completed",  # Niveau terminé.
    "player_death",  # Joueur mort.
    "match_finished",  # Partie terminée.
    "game_error",  # Erreur technique.
}

def _validate_required_fields(event: dict) -> list[str]:  # Contrôle les champs communs et leur contenu.
    errors = []  # Accumule les messages plutôt que d'arrêter au premier défaut.
    for field in sorted(REQUIRED_FIELDS.difference(event)):  # Trouve les champs qui manquent.
        errors.append("Champ obligatoire absent : {0}.".format(field))  # Ajoute une erreur par champ absent.

    for field in sorted(REQUIRED_FIELDS.intersection(event)):  # Vérifie les champs présents.
        value = event[field]  # Récupère leur valeur.
        if not isinstance(value, str) or not value.strip():  # Exige une chaîne qui n'est pas vide.
            errors.append("Le champ {0} doit être une chaîne non vide.".format(field))  # Explique le défaut.
    return errors  # Renvoie toutes les erreurs trouvées.

def _validate_event_type(event: dict) -> list[str]:  # Vérifie que le type est connu.
    event_type = event.get("event_type")  # Lit le type sans erreur s'il manque.
    if isinstance(event_type, str) and event_type not in ALLOWED_TYPES:  # Compare les chaînes à la liste autorisée.
        return ["Type d'événement inconnu : {0}.".format(event_type)]  # Renvoie le défaut de type.
    return []  # Une liste vide signifie qu'aucune erreur de type n'a été trouvée.

def _validate_timestamp(event: dict) -> list[str]:  # Vérifie le format du champ occurred_at.
    occurred_at = event.get("occurred_at")  # Récupère l'horodatage.
    if not isinstance(occurred_at, str) or not occurred_at.strip():  # Laisse le contrôle vide au validateur de champs.
        return []  # Évite de produire un second message pour un champ absent ou vide.

    timestamp_text = occurred_at.strip()  # Enlève les espaces autour de la date.
    try:  # Tente de convertir la chaîne en date.
        if "T" not in timestamp_text.upper() and " " not in timestamp_text:  # Rejette une date sans heure.
            raise ValueError("Un horodatage doit inclure une heure.")  # Réutilise la gestion d'erreur du parseur.
        datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))  # Convertit le suffixe Z en fuseau UTC reconnu.
    except ValueError:  # Intercepte toute date non conforme au format attendu.
        return ["Le champ occurred_at doit être une date ISO-8601 valide."]  # Décrit l'erreur de format.
    return []  # Signale que l'horodatage est correct.

def _validate_duration(event: dict) -> list[str]:  # Vérifie la durée seulement pour un niveau terminé.
    if event.get("event_type") != "level_completed":  # Les autres types n'ont pas ce champ obligatoire.
        return []  # Aucune erreur de durée pour ces événements.

    duration = event.get("duration_seconds")  # Récupère la durée du niveau.
    invalid_duration = (  # Vérifie son type et sa valeur minimale.
        isinstance(duration, bool)  # Évite que True/False soient traités comme 1/0.
        or not isinstance(duration, (int, float))  # Accepte seulement les nombres.
        or duration <= 0  # Exige une durée strictement positive.
    )  # Termine la combinaison des conditions invalides.
    if isinstance(duration, float) and not math.isfinite(duration):  # Refuse NaN et les infinis.
        invalid_duration = True  # Marque ces flottants comme invalides.

    if invalid_duration:  # Vérifie si au moins une condition invalide s'applique.
        return [  # Renvoie une explication du problème.
            "duration_seconds doit être un nombre strictement positif "  # Première partie du message.
            "pour level_completed."  # Termine le message.
        ]  # Ferme la liste d'erreurs.
    return []  # La durée est valide.

def validate_event(event: dict) -> list[str]:  # Fonction publique appelée par le pipeline.
    """Retourne les erreurs du contrat, ou une liste vide si l'événement est valide."""
    if not isinstance(event, dict):  # Vérifie la forme générale de l'événement.
        return ["L'événement doit être un objet JSON."]  # Arrête les contrôles impossibles sur autre chose qu'un dictionnaire.

    errors = []  # Crée la liste finale des messages d'erreur.
    errors.extend(_validate_required_fields(event))  # Ajoute les erreurs de champs obligatoires.
    errors.extend(_validate_event_type(event))  # Ajoute les erreurs de type inconnu.
    errors.extend(_validate_timestamp(event))  # Ajoute les erreurs de date.
    errors.extend(_validate_duration(event))  # Ajoute les erreurs de durée.
    return errors  # Une liste vide signifie que l'événement respecte le contrat.
