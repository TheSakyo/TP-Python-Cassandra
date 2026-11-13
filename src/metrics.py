"""Calcul d'indicateurs sur la qualité et le contenu des événements."""

from collections import Counter  # Compte efficacement des occurrences par clé.

class EventSummary:  # Accumulateur d'indicateurs utilisable pendant une lecture en flux.
    """Agrégateur incrémental pour calculer les indicateurs sans garder les événements."""

    def __init__(self):  # Initialise les compteurs vides.
        self.total_events = 0  # Nombre d'événements ajoutés.
        self.events_by_type = Counter()  # Nombre d'événements pour chaque type.
        self.errors_by_version = Counter()  # Nombre d'erreurs pour chaque version.

    def add(self, event: dict) -> None:  # Ajoute un événement valide aux indicateurs.
        if not isinstance(event, dict):  # Ignore les valeurs qui ne sont pas des objets.
            return  # Ne modifie aucun compteur.

        self.total_events += 1  # Incrémente le total d'événements.
        event_type = event.get("event_type", "unknown")  # Lit le type ou prend une valeur de secours.
        self.events_by_type[event_type] += 1  # Compte une occurrence de ce type.

        if event_type == "game_error":  # Ajoute un compte dédié pour les erreurs techniques.
            self.errors_by_version[event.get("game_version", "unknown")] += 1  # Regroupe l'erreur par version.

    def as_dict(self) -> dict:  # Rend les compteurs prêts à être écrits en JSON.
        return {  # Construit le résumé final.
            "total_events": self.total_events,  # Total des événements valides observés.
            "events_by_type": dict(sorted(self.events_by_type.items())),  # Compteurs triés par type.
            "levels_completed": self.events_by_type.get("level_completed", 0),  # Nombre de niveaux terminés.
            "errors_by_version": dict(sorted(self.errors_by_version.items())),  # Erreurs triées par version.
        }

def rejection_rate(total: int, rejected: int) -> float:  # Calcule le taux de rejet en pourcentage.
    """Renvoie le pourcentage d'événements rejetés (0 si aucun événement)."""
    if total < 0 or rejected < 0 or rejected > total:  # Vérifie la cohérence des compteurs.
        raise ValueError("Les compteurs doivent respecter 0 <= rejetés <= total.")  # Signale des valeurs impossibles.
    if total == 0:  # Évite de diviser par zéro quand le fichier est vide.
        return 0.0  # Un lot vide reçoit un taux de 0 %.
    return rejected * 100.0 / total  # Convertit la proportion rejetée en pourcentage.


def summarize_events(events: list[dict]) -> dict:  # Calcule les indicateurs d'une liste d'événements.
    """Compte les types d'événements, niveaux terminés et erreurs par version."""
    summary = EventSummary()  # Crée des compteurs neufs pour cet appel.
    for event in events:  # Parcourt tous les événements fournis.
        summary.add(event)  # Met à jour les compteurs pour l'événement courant.
    return summary.as_dict()  # Renvoie les indicateurs sous forme de dictionnaire.
