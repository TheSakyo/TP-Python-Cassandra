"""Normalisation des événements avant leur stockage."""

from datetime import datetime, timezone  # Parse les dates et les convertit en UTC.

STRING_FIELDS = (  # Champs texte communs à nettoyer.
    "event_id",  # Identifiant de l'événement.
    "event_type",  # Type d'événement.
    "player_id",  # Identifiant du joueur.
    "session_id",  # Identifiant de session.
    "occurred_at",  # Horodatage ISO-8601.
    "game_version",  # Version du jeu.
)

def normalize_event(event: dict) -> dict:  # Prépare un événement valide pour l'insertion.
    """Renvoie une copie normalisée sans modifier l'événement d'origine.

    Les champs textuels communs sont débarrassés des espaces superflus.
    Un horodatage ISO-8601 valide est converti en UTC et fournit event_day.
    Un horodatage invalide est laissé tel quel pour que le validateur le rejette.
    """
    if not isinstance(event, dict):  # Évite de traiter une valeur qui n'est pas un objet.
        return event  # Rend la valeur intacte pour que l'appelant puisse la rejeter.

    normalized = dict(event)  # Copie l'objet pour ne pas modifier celui reçu.
    for field in STRING_FIELDS:  # Parcourt les champs texte connus.
        value = normalized.get(field)  # Lit la valeur du champ courant.
        if isinstance(value, str):  # Nettoie seulement les valeurs textuelles.
            normalized[field] = value.strip()  # Enlève les espaces autour du texte.

    occurred_at = normalized.get("occurred_at")  # Récupère l'horodatage nettoyé.
    if isinstance(occurred_at, str) and occurred_at:  # Continue seulement avec une date texte non vide.
        if "T" not in occurred_at.upper() and " " not in occurred_at:  # Refuse de transformer une date sans heure.
            return normalized  # Laisse le validateur signaler ce format invalide.
        try:  # Essaie de lire la date ISO-8601.
            timestamp = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))  # Accepte aussi le suffixe UTC Z.
        except ValueError:  # Garde la valeur si le format est invalide.
            return normalized  # Laisse le validateur expliquer le rejet.

        if timestamp.tzinfo is None:  # Vérifie si l'heure n'a pas de fuseau associé.
            timestamp = timestamp.replace(tzinfo=timezone.utc)  # Interprète une heure sans fuseau comme UTC.
        else:  # Le texte contenait déjà un fuseau horaire.
            timestamp = timestamp.astimezone(timezone.utc)  # Convertit l'heure dans le fuseau UTC.

        normalized["occurred_at"] = timestamp.isoformat()  # Enregistre la date canonique en UTC.
        normalized["event_day"] = timestamp.date().isoformat()  # Ajoute le jour UTC utilisé par Cassandra.

    return normalized  # Renvoie la copie normalisée.
