"""Tableau de bord local pour explorer les événements Cassandra."""

from datetime import date  # Convertit les dates saisies dans les formulaires.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # Crée un petit serveur web local.
import json  # Sérialise les réponses de l'API.
from pathlib import Path  # Lit les fichiers de rapport et de quarantaine.
from urllib.parse import parse_qs, urlparse  # Sépare les routes web et leurs paramètres.
import webbrowser  # Ouvre automatiquement le tableau de bord dans le navigateur.

from cassandra.cluster import Cluster  # Connecte le tableau de bord à Cassandra.

HOST = "127.0.0.1"  # Limite le serveur à l'ordinateur local.
PORT = 8000  # Port HTTP utilisé par le tableau de bord.
REPORT_PATH = Path("data/quality_report.json")  # Fichier de résumé de la dernière ingestion.
REJECTED_PATH = Path("data/rejected_events.jsonl")  # Fichier contenant les événements rejetés.

# La chaîne HTML ci-dessous contient la page, son style CSS et son JavaScript ; elle reste intacte pour garder l'interface inchangée.
HTML = """<!doctype html> <!-- Déclare une page HTML moderne. -->
<html lang="fr"> <!-- Indique au navigateur que le texte est en français. -->
<head> <!-- Ouvre l'en-tête des métadonnées et du style. -->
  <meta charset="utf-8"> <!-- Permet d'afficher correctement les accents. -->
  <meta name="viewport" content="width=device-width, initial-scale=1"> <!-- Adapte la page aux écrans mobiles. -->
  <title>Télémétrie du jeu — tableau de bord</title> <!-- Texte affiché dans l'onglet du navigateur. -->
  <style>/* Commence les règles de présentation CSS. */
    :root { color-scheme: light; font-family: Segoe UI, sans-serif; color: #17212b; background: #f3f6fa; } /* Définit le thème clair, la police, le texte et le fond. */
    body { max-width: 1100px; margin: 32px auto; padding: 0 20px; } /* Centre le contenu et limite sa largeur. */
    h1, h2 { color: #142d4e; } /* Donne une couleur aux titres principaux. */
    .muted { color: #526171; } /* Atténue le texte secondaire. */
    .cards, .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; } /* Dispose les cartes et formulaires en grille adaptative. */
    .card, form, pre { background: white; border: 1px solid #d8e0e9; border-radius: 10px; padding: 16px; } /* Donne un fond et une bordure aux panneaux. */
    .metric { font-size: 1.8rem; font-weight: 650; margin: 8px 0; } /* Met les chiffres du rapport en évidence. */
    label { display: block; margin: 10px 0 4px; font-weight: 600; } /* Place les étiquettes de formulaire au-dessus des champs. */
    input { box-sizing: border-box; width: 100%; padding: 9px; border: 1px solid #aebbc9; border-radius: 6px; } /* Rend les champs lisibles et adaptés à la largeur. */
    button { margin-top: 12px; padding: 9px 14px; border: 0; border-radius: 6px; background: #1769aa; color: white; cursor: pointer; } /* Met en forme les boutons d'interrogation. */
    pre { overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; min-height: 40px; } /* Affiche le JSON sans le faire déborder. */
    .section { margin: 28px 0; } /* Sépare verticalement les grandes sections. */
    @media (max-width: 600px) { body { margin: 18px auto; } } /* Réduit les marges sur un petit écran. */
  </style> <!-- Termine les règles CSS. -->
</head> <!-- Termine l'en-tête de la page. -->
<body> <!-- Commence le contenu visible de la page. -->
  <h1>Télémétrie du jeu</h1> <!-- Titre du tableau de bord. -->
  <p class="muted">Consultation locale des rapports et des tables Cassandra.</p> <!-- Résume le rôle de la page. -->

  <section class="section"> <!-- Regroupe les indicateurs qualité. -->
    <h2>Qualité des données</h2> <!-- Titre de la zone qualité. -->
    <div id="summary" class="cards"><div class="card">Chargement du rapport…</div></div> <!-- Emplacement où JavaScript crée les cartes d'indicateurs. -->
  </section> <!-- Termine la zone qualité. -->

  <section class="section"> <!-- Regroupe les formulaires de consultation Cassandra. -->
    <h2>Événements Cassandra</h2> <!-- Titre de la zone de recherche. -->
    <div class="grid"> <!-- Aligne les trois formulaires en grille. -->
      <form data-endpoint="/api/player-day" data-output="#player-results"> <!-- Formulaire de recherche joueur/jour. -->
        <h3>Activité d'un joueur par jour</h3> <!-- Titre du premier formulaire. -->
        <label>Identifiant joueur</label><input name="player_id" value="player-001" required> <!-- Champ de partition joueur. -->
        <label>Jour (AAAA-MM-JJ)</label><input name="event_day" type="date" value="2026-11-09" required> <!-- Champ de partition jour. -->
        <button>Afficher les événements</button> <!-- Envoie la recherche joueur/jour. -->
      </form> <!-- Termine le premier formulaire. -->
      <form data-endpoint="/api/session" data-output="#session-results"> <!-- Formulaire de recherche par session. -->
        <h3>Chronologie d'une session</h3> <!-- Titre du deuxième formulaire. -->
        <label>Identifiant session</label><input name="session_id" value="session-abc123" required> <!-- Champ de partition session. -->
        <button>Afficher la session</button> <!-- Envoie la recherche par session. -->
      </form> <!-- Termine le deuxième formulaire. -->
      <form data-endpoint="/api/errors" data-output="#error-results"> <!-- Formulaire de recherche d'erreurs. -->
        <h3>Erreurs par version et par jour</h3> <!-- Titre du troisième formulaire. -->
        <label>Version du jeu</label><input name="game_version" value="1.4.2" required> <!-- Champ de partition version. -->
        <label>Jour (AAAA-MM-JJ)</label><input name="event_day" type="date" value="2026-11-09" required> <!-- Champ de partition jour. -->
        <button>Afficher les erreurs</button> <!-- Envoie la recherche d'erreurs. -->
      </form> <!-- Termine le troisième formulaire. -->
    </div> <!-- Termine la grille des formulaires. -->
    <h3>Résultats</h3> <!-- Titre des résultats renvoyés par Cassandra. -->
    <pre id="player-results">Utilise un formulaire pour interroger Cassandra.</pre> <!-- Zone de résultat joueur/jour. -->
    <pre id="session-results"></pre> <!-- Zone de résultat de session. -->
    <pre id="error-results"></pre> <!-- Zone de résultat des erreurs. -->
  </section> <!-- Termine la zone Cassandra. -->

  <section class="section"> <!-- Regroupe les événements rejetés. -->
    <h2>Événements rejetés</h2> <!-- Titre de la quarantaine. -->
    <pre id="rejected">Chargement de la quarantaine…</pre> <!-- Zone qui reçoit les erreurs du fichier de rejets. -->
  </section> <!-- Termine la zone de quarantaine. -->

  <script>// Commence le JavaScript qui relie la page aux routes du serveur.
    async function showJson(url, target) { // Récupère du JSON puis l'affiche dans l'élément demandé.
      const response = await fetch(url); // Envoie une requête HTTP GET au serveur local.
      const result = await response.json(); // Décode le corps de réponse JSON.
      document.querySelector(target).textContent = JSON.stringify(result, null, 2); // Affiche les données sans interpréter du HTML.
    } // Termine showJson.
    async function loadSummary() { // Charge les indicateurs et les transforme en cartes.
      const response = await fetch("/api/report"); // Demande le rapport qualité au serveur.
      const report = await response.json(); // Décode le rapport reçu.
      const cards = [ // Prépare les libellés et valeurs des cartes.
        ["Événements traités", report.total ?? 0], // Affiche le nombre de lignes lues.
        ["Acceptés", report.accepted ?? 0], // Affiche le nombre d'événements valides.
        ["Rejetés", report.rejected ?? 0], // Affiche le nombre d'événements refusés.
        ["Taux de rejet", `${Number(report.rejection_rate ?? 0).toFixed(1)} %`], // Affiche le taux avec une décimale.
        ["Niveaux terminés", report.levels_completed ?? 0], // Affiche le nombre de niveaux terminés.
        ["Erreurs par version", Object.entries(report.errors_by_version ?? {}).map(([version, count]) => `${version} : ${count}`).join(", ") || "Aucune"], // Regroupe les erreurs lisiblement par version.
      ]; // Termine la liste des cartes.
      const container = document.querySelector("#summary"); // Récupère le conteneur des indicateurs.
      container.replaceChildren(); // Enlève le texte provisoire de chargement.
      for (const [label, value] of cards) { // Crée un panneau pour chaque indicateur.
        const card = document.createElement("div"); // Crée la carte principale.
        const title = document.createElement("div"); // Crée la zone du libellé.
        const metric = document.createElement("div"); // Crée la zone de la valeur.
        card.className = "card"; // Applique le style de panneau.
        title.textContent = label; // Insère le nom de l'indicateur comme texte sûr.
        metric.className = "metric"; // Applique le style des chiffres.
        metric.textContent = value; // Affiche la valeur calculée.
        card.append(title, metric); // Place le titre et la valeur dans la carte.
        container.append(card); // Ajoute la carte au tableau de bord.
      } // Termine la création des cartes.
    } // Termine loadSummary.
    document.querySelectorAll("form[data-endpoint]").forEach((form) => { // Branche le comportement sur chaque formulaire de recherche.
      form.addEventListener("submit", async (event) => { // Intercepte l'envoi du formulaire.
        event.preventDefault(); // Empêche le navigateur de recharger la page.
        const params = new URLSearchParams(new FormData(form)); // Convertit les champs en paramètres d'URL.
        const target = form.dataset.output; // Récupère la zone où afficher les résultats.
        try { // Essaie d'interroger la route associée à ce formulaire.
          await showJson(`${form.dataset.endpoint}?${params}`, target); // Envoie les paramètres au serveur et affiche la réponse.
        } catch (error) { // Attrape un problème réseau ou de réponse.
          document.querySelector(target).textContent = `Erreur : ${error}`; // Montre l'erreur à l'utilisateur.
        } // Termine le traitement d'erreur.
      }); // Termine l'écouteur d'envoi.
    }); // Termine le branchement de tous les formulaires.
    loadSummary().catch((error) => { // Charge le rapport dès l'ouverture de la page.
      document.querySelector("#summary").textContent = `Rapport indisponible : ${error}`; // Signale un échec de chargement du rapport.
    }); // Termine le traitement d'échec du rapport.
    showJson("/api/rejected", "#rejected").catch((error) => { // Charge la quarantaine dès l'ouverture.
      document.querySelector("#rejected").textContent = `Quarantaine indisponible : ${error}`; // Signale un échec de chargement des rejets.
    }); // Termine le traitement d'échec de la quarantaine.
  </script> <!-- Termine le JavaScript de la page. -->
</body> <!-- Termine le contenu visible. -->
</html> <!-- Termine le document HTML. -->
"""


def _json_value(value):  # Convertit les types Python non directement sérialisables en JSON.
    if hasattr(value, "isoformat"):  # Les dates et heures exposent cette méthode.
        return value.isoformat()  # Les transforme en chaîne ISO lisible.
    return str(value)  # Convertit les autres valeurs spéciales en texte.


def _rows_as_dicts(rows) -> list[dict]:  # Transforme les lignes Cassandra en dictionnaires JSON.
    return [row._asdict() for row in rows]  # Convertit chaque ligne nommée en objet clé-valeur.


class DashboardHandler(BaseHTTPRequestHandler):  # Traite les requêtes HTTP du navigateur.
    queries = {}  # Contiendra les requêtes Cassandra préparées au démarrage.
    session = None  # Contiendra la session Cassandra partagée par le serveur.

    def _respond(self, body: bytes, content_type: str, status: int = 200) -> None:  # Envoie une réponse HTTP.
        self.send_response(status)  # Définit le code HTTP comme 200, 400 ou 404.
        self.send_header("Content-Type", content_type)  # Indique au navigateur le type de contenu.
        self.send_header("Content-Length", str(len(body)))  # Indique la taille du corps de réponse.
        self.send_header("Cache-Control", "no-store")  # Demande au navigateur de ne pas garder une ancienne réponse.
        self.end_headers()  # Termine les en-têtes HTTP.
        self.wfile.write(body)  # Envoie les octets de la réponse.

    def _respond_json(self, value, status: int = 200) -> None:  # Envoie une valeur sous forme JSON.
        body = json.dumps(value, ensure_ascii=False, default=_json_value).encode("utf-8")  # Encode le JSON en UTF-8.
        self._respond(body, "application/json; charset=utf-8", status)  # Envoie le corps avec le bon type MIME.

    def _parameter(self, parameters: dict, name: str) -> str:  # Lit et vérifie un paramètre d'URL obligatoire.
        value = parameters.get(name, [""])[0].strip()  # Prend la première valeur et enlève ses espaces.
        if not value:  # Détecte un paramètre vide ou absent.
            raise ValueError("Le paramètre {0} est obligatoire.".format(name))  # Signale une erreur de formulaire.
        return value  # Renvoie la valeur propre.

    def do_GET(self) -> None:  # Répond à chaque requête HTTP GET du navigateur.
        parsed = urlparse(self.path)  # Sépare le chemin URL de sa chaîne de paramètres.
        parameters = parse_qs(parsed.query)  # Transforme les paramètres en dictionnaire.

        if parsed.path == "/":  # La route racine sert la page HTML.
            self._respond(HTML.encode("utf-8"), "text/html; charset=utf-8")  # Renvoie la page au navigateur.
            return  # Arrête le traitement de cette requête.
        if parsed.path == "/api/report":  # Cette route fournit le rapport qualité.
            report = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.exists() else {}  # Lit le rapport s'il existe.
            self._respond_json(report)  # Renvoie le rapport au navigateur.
            return  # Évite de traiter la route comme une requête Cassandra.
        if parsed.path == "/api/rejected":  # Cette route fournit les lignes de quarantaine.
            if not REJECTED_PATH.exists():  # Vérifie si une ingestion a créé ce fichier.
                self._respond_json([])  # Renvoie une liste vide avant toute ingestion.
                return  # Arrête le traitement de cette route.
            rejected = [  # Construit la liste des rejets à partir du JSONL.
                json.loads(line)  # Décode chaque ligne en dictionnaire.
                for line in REJECTED_PATH.read_text(encoding="utf-8").splitlines()  # Lit le fichier et le découpe par lignes.
                if line.strip()  # Ignore les lignes vides éventuelles.
            ]  # Termine la compréhension de liste.
            self._respond_json(rejected)  # Renvoie les rejets au navigateur.
            return  # Arrête le traitement de cette route.

        try:  # Traite les trois routes de consultation Cassandra.
            if parsed.path == "/api/player-day":  # Recherche la partition joueur + jour.
                player_id = self._parameter(parameters, "player_id")  # Lit l'identifiant du joueur du formulaire.
                event_day = date.fromisoformat(self._parameter(parameters, "event_day"))  # Convertit le jour en date Python.
                rows = self.session.execute(self.queries["player_day"], (player_id, event_day))  # Exécute la requête préparée.
            elif parsed.path == "/api/session":  # Recherche les événements d'une session.
                session_id = self._parameter(parameters, "session_id")  # Lit l'identifiant de session.
                rows = self.session.execute(self.queries["session"], (session_id,))  # Exécute la recherche de session.
            elif parsed.path == "/api/errors":  # Recherche les erreurs d'une version et d'un jour.
                game_version = self._parameter(parameters, "game_version")  # Lit la version du jeu demandée.
                event_day = date.fromisoformat(self._parameter(parameters, "event_day"))  # Convertit le jour du formulaire.
                rows = self.session.execute(self.queries["errors"], (game_version, event_day))  # Exécute la recherche d'erreurs.
            else:  # Aucune route connue ne correspond au chemin demandé.
                self._respond_json({"error": "Route inconnue."}, 404)  # Renvoie le code HTTP 404.
                return  # Arrête la requête inconnue.
        except ValueError as error:  # Attrape les paramètres absents ou les dates invalides.
            self._respond_json({"error": str(error)}, 400)  # Renvoie une erreur de formulaire au navigateur.
            return  # N'essaie pas d'envoyer de résultats.
        except Exception as error:  # Attrape une erreur inattendue de Cassandra.
            self._respond_json({"error": "Erreur Cassandra : {0}".format(error)}, 503)  # Signale que le service de données échoue.
            return  # Arrête le traitement après l'erreur.

        self._respond_json(_rows_as_dicts(rows))  # Convertit les lignes Cassandra et les renvoie en JSON.

    def log_message(self, format: str, *args) -> None:  # Personnalise les messages du serveur HTTP.
        return  # Désactive les logs de requête pour garder la fenêtre du lanceur propre.


def main() -> None:  # Connecte les services et démarre le tableau de bord.
    cluster = Cluster(["127.0.0.1"])  # Crée le client Cassandra local.
    session = cluster.connect("game_telemetry")  # Ouvre le keyspace de télémétrie.
    queries = {  # Prépare les requêtes utilisées par les formulaires web.
        "player_day": session.prepare(  # Requête partitionnée par joueur et jour.
            "SELECT player_id, event_day, occurred_at, event_id, event_type, game_version, payload "  # Colonnes affichées dans la vue joueur/jour.
            "FROM events_by_player_day WHERE player_id = ? AND event_day = ?"  # Filtre par les deux colonnes de partition.
        ),  # Termine la préparation de cette requête.
        "session": session.prepare(  # Requête partitionnée par session.
            "SELECT session_id, occurred_at, event_id, player_id, event_type, payload "  # Colonnes de chronologie affichées.
            "FROM events_by_session WHERE session_id = ?"  # Filtre sur l'identifiant de session.
        ),  # Termine la préparation de cette requête.
        "errors": session.prepare(  # Requête partitionnée par version et jour.
            "SELECT game_version, event_day, occurred_at, event_id, player_id, payload "  # Colonnes d'erreur affichées.
            "FROM errors_by_version_day WHERE game_version = ? AND event_day = ?"  # Filtre par version et date.
        ),  # Termine la préparation de cette requête.
    }  # Termine le dictionnaire des requêtes.

    handler = type(  # Crée une classe de gestion configurée avec cette session et ces requêtes.
        "ConfiguredDashboardHandler",  # Donne un nom à la classe configurée.
        (DashboardHandler,),  # Hérite du gestionnaire HTTP défini plus haut.
        {"queries": queries, "session": session},  # Injecte les requêtes et la session dans la classe.
    )  # Termine la création dynamique du gestionnaire.
    server = ThreadingHTTPServer((HOST, PORT), handler)  # Écoute les requêtes locales en parallèle.
    try:  # Lance le navigateur et garde le serveur actif.
        print("Tableau de bord : http://{0}:{1}".format(HOST, PORT))  # Affiche l'adresse d'accès.
        webbrowser.open("http://{0}:{1}".format(HOST, PORT))  # Ouvre cette adresse dans le navigateur par défaut.
        server.serve_forever()  # Attend et traite les requêtes tant que le serveur tourne.
    except KeyboardInterrupt:  # Réagit à Ctrl+C dans la fenêtre du lanceur.
        pass  # Passe à la fermeture propre des ressources.
    finally:  # Libère les ressources même en cas d'arrêt ou d'erreur.
        server.server_close()  # Ferme le port HTTP.
        session.shutdown()  # Ferme la session Cassandra.
        cluster.shutdown()  # Ferme le client du cluster.


if __name__ == "__main__":  # N'exécute main que lors du lancement de ce module.
    main()  # Démarre le tableau de bord web local.
