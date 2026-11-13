"""Tableau de bord local pour explorer les événements Cassandra."""

from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser

from cassandra.cluster import Cluster

HOST = "127.0.0.1"
PORT = 8000
REPORT_PATH = Path("data/quality_report.json")
REJECTED_PATH = Path("data/rejected_events.jsonl")

HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Télémétrie du jeu — tableau de bord</title>
  <style>
    :root { color-scheme: light; font-family: Segoe UI, sans-serif; color: #17212b; background: #f3f6fa; }
    body { max-width: 1100px; margin: 32px auto; padding: 0 20px; }
    h1, h2 { color: #142d4e; }
    .muted { color: #526171; }
    .cards, .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
    .card, form, pre { background: white; border: 1px solid #d8e0e9; border-radius: 10px; padding: 16px; }
    .metric { font-size: 1.8rem; font-weight: 650; margin: 8px 0; }
    label { display: block; margin: 10px 0 4px; font-weight: 600; }
    input { box-sizing: border-box; width: 100%; padding: 9px; border: 1px solid #aebbc9; border-radius: 6px; }
    button { margin-top: 12px; padding: 9px 14px; border: 0; border-radius: 6px; background: #1769aa; color: white; cursor: pointer; }
    pre { overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; min-height: 40px; }
    .section { margin: 28px 0; }
    @media (max-width: 600px) { body { margin: 18px auto; } }
  </style>
</head>
<body>
  <h1>Télémétrie du jeu</h1>
  <p class="muted">Consultation locale des rapports et des tables Cassandra.</p>

  <section class="section">
    <h2>Qualité des données</h2>
    <div id="summary" class="cards"><div class="card">Chargement du rapport…</div></div>
  </section>

  <section class="section">
    <h2>Événements Cassandra</h2>
    <div class="grid">
      <form data-endpoint="/api/player-day" data-output="#player-results">
        <h3>Activité d'un joueur par jour</h3>
        <label>Identifiant joueur</label><input name="player_id" value="player-001" required>
        <label>Jour (AAAA-MM-JJ)</label><input name="event_day" type="date" value="2026-11-09" required>
        <button>Afficher les événements</button>
      </form>
      <form data-endpoint="/api/session" data-output="#session-results">
        <h3>Chronologie d'une session</h3>
        <label>Identifiant session</label><input name="session_id" value="session-abc123" required>
        <button>Afficher la session</button>
      </form>
      <form data-endpoint="/api/errors" data-output="#error-results">
        <h3>Erreurs par version et par jour</h3>
        <label>Version du jeu</label><input name="game_version" value="1.4.2" required>
        <label>Jour (AAAA-MM-JJ)</label><input name="event_day" type="date" value="2026-11-09" required>
        <button>Afficher les erreurs</button>
      </form>
    </div>
    <h3>Résultats</h3>
    <pre id="player-results">Utilise un formulaire pour interroger Cassandra.</pre>
    <pre id="session-results"></pre>
    <pre id="error-results"></pre>
  </section>

  <section class="section">
    <h2>Événements rejetés</h2>
    <pre id="rejected">Chargement de la quarantaine…</pre>
  </section>

  <script>
    async function showJson(url, target) {
      const response = await fetch(url);
      const result = await response.json();
      document.querySelector(target).textContent = JSON.stringify(result, null, 2);
    }
    async function loadSummary() {
      const response = await fetch("/api/report");
      const report = await response.json();
      const cards = [
        ["Événements traités", report.total ?? 0],
        ["Acceptés", report.accepted ?? 0],
        ["Rejetés", report.rejected ?? 0],
        ["Taux de rejet", `${Number(report.rejection_rate ?? 0).toFixed(1)} %`],
        ["Niveaux terminés", report.levels_completed ?? 0],
        ["Erreurs par version", Object.entries(report.errors_by_version ?? {}).map(([version, count]) => `${version} : ${count}`).join(", ") || "Aucune"],
      ];
      const container = document.querySelector("#summary");
      container.replaceChildren();
      for (const [label, value] of cards) {
        const card = document.createElement("div");
        const title = document.createElement("div");
        const metric = document.createElement("div");
        card.className = "card";
        title.textContent = label;
        metric.className = "metric";
        metric.textContent = value;
        card.append(title, metric);
        container.append(card);
      }
    }
    document.querySelectorAll("form[data-endpoint]").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const params = new URLSearchParams(new FormData(form));
        const target = form.dataset.output;
        try {
          await showJson(`${form.dataset.endpoint}?${params}`, target);
        } catch (error) {
          document.querySelector(target).textContent = `Erreur : ${error}`;
        }
      });
    });
    loadSummary().catch((error) => {
      document.querySelector("#summary").textContent = `Rapport indisponible : ${error}`;
    });
    showJson("/api/rejected", "#rejected").catch((error) => {
      document.querySelector("#rejected").textContent = `Quarantaine indisponible : ${error}`;
    });
  </script>
</body>
</html>
"""


def _json_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _rows_as_dicts(rows) -> list[dict]:
    return [row._asdict() for row in rows]


class DashboardHandler(BaseHTTPRequestHandler):
    queries = {}
    session = None

    def _respond(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _respond_json(self, value, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False, default=_json_value).encode("utf-8")
        self._respond(body, "application/json; charset=utf-8", status)

    def _parameter(self, parameters: dict, name: str) -> str:
        value = parameters.get(name, [""])[0].strip()
        if not value:
            raise ValueError("Le paramètre {0} est obligatoire.".format(name))
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parameters = parse_qs(parsed.query)

        if parsed.path == "/":
            self._respond(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/report":
            report = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.exists() else {}
            self._respond_json(report)
            return
        if parsed.path == "/api/rejected":
            if not REJECTED_PATH.exists():
                self._respond_json([])
                return
            rejected = [
                json.loads(line)
                for line in REJECTED_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self._respond_json(rejected)
            return

        try:
            if parsed.path == "/api/player-day":
                player_id = self._parameter(parameters, "player_id")
                event_day = date.fromisoformat(self._parameter(parameters, "event_day"))
                rows = self.session.execute(self.queries["player_day"], (player_id, event_day))
            elif parsed.path == "/api/session":
                session_id = self._parameter(parameters, "session_id")
                rows = self.session.execute(self.queries["session"], (session_id,))
            elif parsed.path == "/api/errors":
                game_version = self._parameter(parameters, "game_version")
                event_day = date.fromisoformat(self._parameter(parameters, "event_day"))
                rows = self.session.execute(self.queries["errors"], (game_version, event_day))
            else:
                self._respond_json({"error": "Route inconnue."}, 404)
                return
        except ValueError as error:
            self._respond_json({"error": str(error)}, 400)
            return
        except Exception as error:
            self._respond_json({"error": "Erreur Cassandra : {0}".format(error)}, 503)
            return

        self._respond_json(_rows_as_dicts(rows))

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    cluster = Cluster(["127.0.0.1"])
    session = cluster.connect("game_telemetry")
    queries = {
        "player_day": session.prepare(
            "SELECT player_id, event_day, occurred_at, event_id, event_type, game_version, payload "
            "FROM events_by_player_day WHERE player_id = ? AND event_day = ?"
        ),
        "session": session.prepare(
            "SELECT session_id, occurred_at, event_id, player_id, event_type, payload "
            "FROM events_by_session WHERE session_id = ?"
        ),
        "errors": session.prepare(
            "SELECT game_version, event_day, occurred_at, event_id, player_id, payload "
            "FROM errors_by_version_day WHERE game_version = ? AND event_day = ?"
        ),
    }

    handler = type(
        "ConfiguredDashboardHandler",
        (DashboardHandler,),
        {"queries": queries, "session": session},
    )
    server = ThreadingHTTPServer((HOST, PORT), handler)
    try:
        print("Tableau de bord : http://{0}:{1}".format(HOST, PORT))
        webbrowser.open("http://{0}:{1}".format(HOST, PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.shutdown()
        cluster.shutdown()


if __name__ == "__main__":
    main()
