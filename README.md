# Data Engineering & Big Data — M2
## Projet fil rouge : télémétrie d'un jeu vidéo connecté

### Prérequis
- Python 3.9+
- Docker Desktop ou Docker Engine + Docker Compose
- Environnement virtuel Python recommandé

### Démarrage de Cassandra
```bash
docker compose up -d
docker compose logs -f cassandra
```
Attendre que Cassandra soit prête. Puis :
```bash
docker exec -i game-cassandra cqlsh < cql/schema.cql
```

### Génération et ingestion
Depuis la racine du dépôt, générer un fichier JSONL puis l'ingérer :
```bash
python -m src.generator
python -m src.ingestion data/events.jsonl
```
L'ingestion affiche et écrit le rapport qualité dans `data/quality_report.json` :
événements acceptés/rejetés, taux de rejet, niveaux terminés et erreurs par
version. Les lignes invalides, avec leur numéro et leurs erreurs, sont
conservées dans `data/rejected_events.jsonl`. Les événements valides alimentent
les trois tables Cassandra. Le schéma doit avoir été appliqué avant l'ingestion.
La connexion Cassandra utilise `127.0.0.1:9042`.

### Tableau de bord web
Sur Windows, avec Cassandra démarré et le schéma appliqué, double-cliquer sur
`lancer_tableau_de_bord.bat`. Le navigateur s'ouvre sur `http://127.0.0.1:8000`.
L'interface affiche le rapport qualité et la quarantaine, et permet d'interroger
les événements par joueur/jour, par session ou les erreurs par version/jour.
Fermer la fenêtre du lanceur arrête le serveur web.

### Démonstration et limites
Les requêtes métier figurent dans [`cql/requetes_demo.cql`](cql/requetes_demo.cql).
Les hypothèses et limites du modèle sont décrites dans
[`docs/hypotheses_limites.md`](docs/hypotheses_limites.md). Un plan de
présentation de cinq minutes est disponible dans
[`docs/presentation_5min.md`](docs/presentation_5min.md).

### Environnement Python
```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows
python -m pip install -r requirements.txt
```

### Parcours conseillé
1. Générer des événements : `python -m src.generator`
2. Valider et transformer les événements.
3. Charger les données dans Cassandra.
4. Produire un rapport qualité et des indicateurs.
5. Lancer les tests : `pytest -q`

### Architecture
Source simulée → JSONL → validation/normalisation → Cassandra → indicateurs.
Ce dépôt est un environnement pédagogique. Le mode mono-nœud n'est pas une architecture de production.

Le module `src.metrics` fournit aussi `summarize_events(events)`, qui retourne
les comptes par type, le nombre de niveaux terminés et les erreurs par version.
