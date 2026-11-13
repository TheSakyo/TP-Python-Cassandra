"""Ingestion Cassandra — exercice étudiant."""

from datetime import datetime  # Convertit les horodatages en objets date/heure.
import json  # Lit les lignes JSONL et sérialise les données stockées.
from pathlib import Path  # Crée les dossiers et manipule les chemins de sortie.

from .metrics import EventSummary, rejection_rate  # Fournit les compteurs et le taux de rejet.
from .transformations import normalize_event  # Normalise les événements acceptés.
from .validator import validate_event  # Vérifie le contrat d'événement.

def _read_validate_and_write(path: str, session) -> tuple[int, list[dict], dict]:  # Traite un fichier avec une session déjà ouverte.
    # Étapes :
    # 1. Préparer les requêtes d'insertion dans les tables Cassandra.
    # 2. Lire le fichier JSONL ligne par ligne et décoder chaque événement.
    # 3. Valider chaque événement et conserver les lignes invalides en rejet.
    # 4. Normaliser les événements valides puis les insérer dans Cassandra.
    # 5. Renvoyer le nombre d'événements insérés et les lignes rejetées.
    """Traite les événements JSONL et écrit les événements valides dans Cassandra.

    Renvoie le nombre d'événements insérés et les lignes à mettre en quarantaine.
    """
    query = session.prepare(  # Prépare l'écriture des événements par joueur et par jour.
        """
        INSERT INTO events_by_player_day (
            player_id, event_day, occurred_at, event_id, session_id,
            event_type, game_version, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )
    session_query = session.prepare(  # Prépare l'écriture de la chronologie par session.
        """
        INSERT INTO events_by_session (
            session_id, occurred_at, event_id, player_id, event_type, payload
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
    )
    error_query = session.prepare(  # Prépare l'écriture dédiée des erreurs par version et jour.
        """
        INSERT INTO errors_by_version_day (
            game_version, event_day, occurred_at, event_id, player_id, payload
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
    )

    inserted = 0  # Compte les événements valides écrits dans Cassandra.
    rejected = []  # Conserve les lignes invalides pour le fichier de quarantaine.
    summary = EventSummary()  # Agrège les indicateurs sans garder tous les événements.

    with open(path, "r", encoding="utf-8") as source:  # Ouvre le flux source en texte UTF-8.
        for line_number, raw_line in enumerate(source, start=1):  # Lit chaque ligne en gardant son numéro.
            try:  # Essaie de décoder la ligne comme un objet JSON.
                event = json.loads(raw_line)  # Transforme le texte JSON en dictionnaire Python.
            except json.JSONDecodeError as error:  # Attrape une ligne JSON mal formée.
                rejected.append({  # Ajoute le cas à la liste de quarantaine.
                    "line": line_number,  # Garde le numéro pour retrouver la ligne source.
                    "raw": raw_line.rstrip("\r\n"),  # Garde le texte original sans son retour de ligne.
                    "errors": ["JSON invalide : {0}".format(error)],  # Explique l'erreur de syntaxe JSON.
                })  # Termine l'enregistrement du rejet.
                continue  # Passe directement à la prochaine ligne.

            if not isinstance(event, dict):  # Refuse une liste, un nombre ou une chaîne JSON.
                errors = ["L'événement JSON doit être un objet."]  # Produit son message de rejet.
            else:  # Le JSON est bien un objet.
                errors = validate_event(event)  # Vérifie les champs, le type, la date et la durée.

            if errors:  # Vérifie si le validateur a trouvé des problèmes.
                rejected.append({  # Ajoute l'événement invalide à la quarantaine.
                    "line": line_number,  # Indique sa position dans le fichier.
                    "raw": raw_line.rstrip("\r\n"),  # Conserve la ligne d'origine.
                    "errors": errors,  # Conserve toutes les raisons du rejet.
                })  # Termine l'enregistrement du rejet.
                continue  # N'insère pas cet événement et passe au suivant.

            event = normalize_event(event)  # Nettoie le texte et convertit la date valide en UTC.
            try:  # Convertit la date normalisée en datetime Python pour Cassandra.
                occurred_at = datetime.fromisoformat(  # Interprète la date ISO normalisée.
                    event["occurred_at"].replace("Z", "+00:00")  # Accepte aussi le suffixe UTC Z.
                )  # Termine la conversion.
            except ValueError as error:  # Protège l'ingestion si la date reste illisible.
                rejected.append({  # Ajoute la ligne à la quarantaine.
                    "line": line_number,  # Numéro de la ligne concernée.
                    "raw": raw_line.rstrip("\r\n"),  # Contenu reçu à l'origine.
                    "errors": ["Date invalide : {0}".format(error)],  # Message explicatif.
                })  # Termine l'enregistrement du rejet.
                continue  # N'écrit pas l'événement et passe au suivant.

            event_day = occurred_at.date()  # Dérive le jour UTC pour les clés de partition.
            payload = json.dumps(event, ensure_ascii=False)  # Garde l'événement complet dans la colonne texte.
            session.execute(  # Écrit la vue destinée aux recherches par joueur et par jour.
                query,  # Requête préparée plus haut.
                (  # Valeurs associées aux marqueurs ? de la requête.
                    event["player_id"], event_day, occurred_at, event["event_id"],  # Clé et ordre chronologique.
                    event["session_id"], event["event_type"],  # Champs utiles pour lire l'événement.
                    event["game_version"], payload,  # Version du jeu et contenu JSON complet.
                ),  # Termine les paramètres de l'insertion.
            )  # Termine l'écriture dans la première table.
            session.execute(  # Écrit aussi la vue destinée aux recherches par session.
                session_query,  # Requête préparée pour events_by_session.
                (  # Valeurs dans l'ordre des colonnes de cette table.
                    event["session_id"], occurred_at, event["event_id"],  # Clé de session et ordre chronologique.
                    event["player_id"], event["event_type"], payload,  # Infos de recherche et document complet.
                ),  # Termine les paramètres de l'insertion.
            )  # Termine l'écriture dans la deuxième table.
            if event["event_type"] == "game_error":  # Les erreurs ont une vue Cassandra dédiée.
                session.execute(  # Insère uniquement les erreurs dans cette troisième table.
                    error_query,  # Requête préparée pour errors_by_version_day.
                    (  # Valeurs dans l'ordre des colonnes de la table d'erreurs.
                        event["game_version"], event_day, occurred_at,  # Partition par version et jour.
                        event["event_id"], event["player_id"], payload,  # Identifiants et contenu complet.
                    ),  # Termine les paramètres de l'insertion.
                )  # Termine l'écriture de la vue des erreurs.
            summary.add(event)  # Met à jour les indicateurs avec cet événement accepté.
            inserted += 1  # Compte l'événement après les écritures réussies.

    return inserted, rejected, summary.as_dict()  # Renvoie compteurs, rejets et résumé des événements valides.

def ingest_file(path: str) -> dict:  # Fonction de haut niveau appelée par le CLI.
    """Ingère un fichier JSONL dans Cassandra et écrit les rejets en quarantaine.

    Le schéma doit déjà avoir été appliqué avec cqlsh (voir README.md).
    """
    from cassandra.cluster import Cluster  # Importe le client Cassandra au moment où on lance l'ingestion.

    cluster = Cluster(["127.0.0.1"])  # Crée le client vers Cassandra local.
    session = None  # Initialise la session pour pouvoir la fermer en toute situation.
    try:  # Garantit la fermeture des connexions après le traitement.
        session = cluster.connect("game_telemetry")  # Ouvre une session dans le keyspace du projet.
        inserted, rejected, event_summary = _read_validate_and_write(path, session)  # Traite le flux JSONL.
    finally:  # Cette partie s'exécute même si une insertion échoue.
        if session is not None:  # Vérifie que la connexion a bien été ouverte.
            session.shutdown()  # Ferme la session Cassandra.
        cluster.shutdown()  # Libère les ressources du cluster client.

    rejected_path = Path("data/rejected_events.jsonl")  # Choisit le fichier de quarantaine.
    rejected_path.parent.mkdir(parents=True, exist_ok=True)  # Crée le dossier data s'il manque.
    with rejected_path.open("w", encoding="utf-8") as destination:  # Réécrit la quarantaine de cette exécution.
        for item in rejected:  # Parcourt toutes les lignes refusées.
            destination.write(json.dumps(item, ensure_ascii=False) + "\n")  # Écrit un rejet JSON par ligne.

    total = inserted + len(rejected)  # Calcule le nombre de lignes traitées au total.
    report = {  # Prépare le rapport qualité retourné et écrit en JSON.
        "total": total,  # Nombre de lignes d'événement lues.
        "accepted": inserted,  # Nombre d'événements valides insérés.
        "rejected": len(rejected),  # Nombre d'événements mis en quarantaine.
        "rejection_rate": rejection_rate(total, len(rejected)),  # Pourcentage de rejets.
        "events_by_type": event_summary["events_by_type"],  # Compte des types valides.
        "levels_completed": event_summary["levels_completed"],  # Nombre de niveaux terminés valides.
        "errors_by_version": event_summary["errors_by_version"],  # Erreurs valides regroupées par version.
    }

    report_path = Path("data/quality_report.json")  # Choisit le chemin du résumé qualité.
    with report_path.open("w", encoding="utf-8") as destination:  # Ouvre le rapport en écriture UTF-8.
        json.dump(report, destination, ensure_ascii=False, indent=2)  # Écrit le dictionnaire de manière lisible.
        destination.write("\n")  # Ajoute un retour de ligne final au fichier.
    return report  # Renvoie le rapport pour l'affichage dans le terminal ou le tableau de bord.

if __name__ == "__main__":  # Lance le CLI seulement si ce module est exécuté directement.
    import argparse  # Lit les arguments fournis par l'utilisateur.

    parser = argparse.ArgumentParser(description="Ingère un fichier JSONL dans Cassandra.")  # Construit l'analyseur d'arguments.
    parser.add_argument("path", nargs="?", default="data/events.jsonl")  # Rend le chemin optionnel avec une valeur par défaut.
    arguments = parser.parse_args()  # Récupère les arguments de la ligne de commande.
    print(json.dumps(ingest_file(arguments.path), ensure_ascii=False, indent=2))  # Lance l'ingestion et affiche le rapport JSON.
