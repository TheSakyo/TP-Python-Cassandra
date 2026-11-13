import json  # Encode les exemples JSONL et relit les fichiers de résultat.
import sys  # Permet de remplacer le module Cassandra par un faux module.
from types import ModuleType  # Crée les modules simulés utilisés pendant le test.

import pytest  # Fournit les outils de test et les dossiers temporaires.

from src.ingestion import ingest_file  # Importe la fonction d'ingestion testée.

class FakeSession:  # Simule la session Cassandra sans contacter de base réelle.
    def __init__(self):  # Initialise l'état de la fausse session.
        self.prepared_queries = []  # Garde les requêtes préparées.
        self.executed = []  # Garde les requêtes réellement envoyées pendant le test.
        self.closed = False  # Suit si la session est bien fermée.

    def prepare(self, query):  # Simule la préparation d'une requête CQL.
        self.prepared_queries.append(query)  # Enregistre le texte de la requête.
        return query  # Renvoie la requête comme substitut de PreparedStatement.

    def execute(self, query, parameters):  # Simule une insertion Cassandra.
        self.executed.append((query, parameters))  # Mémorise la requête et ses paramètres.

    def shutdown(self):  # Simule la fermeture de la session.
        self.closed = True  # Note que le code a bien fermé la session.

class FakeCluster:  # Simule le cluster Cassandra du driver.
    def __init__(self, session):  # Reçoit la session simulée à réutiliser.
        self.session = session  # Stocke la session renvoyée par connect.
        self.hosts = None  # Réserve l'emplacement de la liste d'hôtes éventuelle.
        self.keyspace = None  # Garde le keyspace choisi lors de la connexion.
        self.closed = False  # Suit si le cluster est bien fermé.

    def connect(self, keyspace):  # Simule l'ouverture d'une session.
        self.keyspace = keyspace  # Mémorise le keyspace demandé.
        return self.session  # Renvoie la fausse session.

    def shutdown(self):  # Simule la fermeture du cluster.
        self.closed = True  # Note que le code a bien fermé le cluster.

def valid_event(event_type="session_started", event_id="evt-1"):  # Construit un événement valide personnalisable.
    event = {  # Commence par les champs communs obligatoires.
        "event_id": event_id,  # Identifiant de l'événement.
        "event_type": event_type,  # Type demandé par le test.
        "player_id": "player-001",  # Joueur de l'événement.
        "session_id": "session-1",  # Session de l'événement.
        "occurred_at": "2026-11-09T10:00:00+02:00",  # Horodatage avec fuseau UTC+2.
        "game_version": "1.4.2",  # Version du jeu.
    }  # Termine les champs communs.
    if event_type == "level_completed":  # Les fins de niveau ont une durée obligatoire.
        event["duration_seconds"] = 90  # Ajoute une durée positive.
    if event_type == "game_error":  # Les erreurs techniques ont un code explicatif.
        event["error_code"] = "NET_TIMEOUT"  # Ajoute le code d'erreur de test.
    return event  # Renvoie l'événement prêt à sérialiser.

def test_ingest_file_inserts_valid_events_and_quarantines_invalid_lines(  # Vérifie ingestion, insertions et rejets.
    tmp_path, monkeypatch  # Fournit un dossier isolé et le remplacement des dépendances.
):
    session = FakeSession()  # Crée une session Cassandra factice.
    cluster = FakeCluster(session)  # Crée un cluster factice lié à la session.
    cassandra_module = ModuleType("cassandra")  # Crée le module parent Cassandra simulé.
    cassandra_module.__path__ = []  # Marque ce module comme paquet Python.
    cluster_module = ModuleType("cassandra.cluster")  # Crée le sous-module du driver.
    cluster_module.Cluster = lambda hosts: cluster  # Fait renvoyer notre cluster quand le code appelle Cluster.
    cassandra_module.cluster = cluster_module  # Relie le sous-module au paquet parent.
    monkeypatch.setitem(sys.modules, "cassandra", cassandra_module)  # Remplace le paquet réel pendant le test.
    monkeypatch.setitem(sys.modules, "cassandra.cluster", cluster_module)  # Remplace le module cluster importé par l'ingestion.
    monkeypatch.chdir(tmp_path)  # Isole les fichiers de rapport et quarantaine dans le dossier temporaire.

    source = tmp_path / "events.jsonl"  # Définit le fichier JSONL d'entrée.
    invalid_type_event = valid_event()  # Prépare un événement qui sera volontairement invalide.
    invalid_type_event["event_type"] = "unknown_type"  # Remplace son type par une valeur non autorisée.
    source.write_text(  # Écrit des cas valides et invalides dans le fichier d'entrée.
        "\n".join(  # Sépare chaque événement par un retour à la ligne.
            [  # Liste les cinq lignes du fichier d'essai.
                json.dumps(valid_event()),  # Événement valide simple.
                json.dumps(valid_event("level_completed", "evt-2")),  # Fin de niveau valide.
                json.dumps(valid_event("game_error", "evt-3")),  # Erreur technique valide.
                json.dumps(invalid_type_event),  # Type d'événement inconnu.
                '{"broken_json":',  # Ligne volontairement mal formée.
            ]  # Termine la liste des lignes.
        )  # Termine la jointure JSONL.
        + "\n",  # Ajoute le retour de ligne final.
        encoding="utf-8",  # Écrit le fichier en UTF-8.
    )  # Termine l'écriture du fichier de test.

    result = ingest_file(str(source))  # Lance l'ingestion avec le faux driver.

    assert result["total"] == 5  # Les cinq lignes ont été traitées.
    assert result["accepted"] == 3  # Trois événements valides ont été acceptés.
    assert result["rejected"] == 2  # Deux lignes invalides ont été rejetées.
    assert result["rejection_rate"] == 40.0  # Deux rejets sur cinq donnent 40 %.
    assert result["levels_completed"] == 1  # Le résumé compte la fin de niveau valide.
    assert result["errors_by_version"] == {"1.4.2": 1}  # Le résumé regroupe l'erreur technique par version.
    assert cluster.keyspace == "game_telemetry"  # Vérifie le keyspace utilisé par l'ingestion.
    assert cluster.closed  # Vérifie la fermeture du cluster.
    assert session.closed  # Vérifie la fermeture de la session.
    assert len(session.executed) == 7  # Trois événements dans deux tables, plus un insert dans la table d'erreurs.

    query, parameters = session.executed[0]  # Récupère la première insertion enregistrée.
    assert query in session.prepared_queries  # Vérifie qu'elle utilisait une requête préparée.
    assert parameters[0] == "player-001"  # Vérifie la valeur du joueur insérée.
    assert parameters[1].isoformat() == "2026-11-09"  # Vérifie le jour UTC de partition.
    assert parameters[2].isoformat() == "2026-11-09T08:00:00+00:00"  # Vérifie la conversion du fuseau en UTC.

    query_texts = [query for query, _ in session.executed]  # Extrait les textes des requêtes envoyées.
    assert sum("INSERT INTO events_by_player_day" in query for query in query_texts) == 3  # Un insert par événement valide.
    assert sum("INSERT INTO events_by_session" in query for query in query_texts) == 3  # Un insert dans la vue session chacun.
    assert sum("INSERT INTO errors_by_version_day" in query for query in query_texts) == 1  # Seule l'erreur va dans la table erreurs.

    quarantine_path = tmp_path / "data" / "rejected_events.jsonl"  # Chemin du fichier de rejets écrit par ingest_file.
    rejected = [json.loads(line) for line in quarantine_path.read_text(encoding="utf-8").splitlines()]  # Relit chaque rejet JSON.
    assert [item["line"] for item in rejected] == [4, 5]  # Vérifie les numéros des deux lignes rejetées.
    assert "Type d'événement inconnu" in " ".join(rejected[0]["errors"])  # Vérifie l'erreur de type.
    assert "JSON invalide" in " ".join(rejected[1]["errors"])  # Vérifie l'erreur de syntaxe JSON.

    report_path = tmp_path / "data" / "quality_report.json"  # Chemin du rapport qualité créé.
    assert json.loads(report_path.read_text(encoding="utf-8")) == result  # Vérifie le contenu du rapport JSON.
