# Présentation du projet — 5 minutes

## 0:00–0:45 — Besoin et architecture

Le studio veut suivre l'activité des joueurs, leur progression et les erreurs
techniques. Le projet simule les événements, les valide et les charge dans
Cassandra. Montrer le flux : générateur → JSONL → validation → transformation
→ tables Cassandra, avec une branche de quarantaine pour les lignes invalides.

## 0:45–1:45 — Contrat et qualité

Présenter les champs obligatoires et les types autorisés. Expliquer les cas de
rejet : champ manquant, date au mauvais format, type inconnu, durée de niveau
non positive et ligne JSON malformée. Les rejets conservent le numéro de ligne,
le texte reçu et les raisons dans `data/rejected_events.jsonl`.

## 1:45–2:45 — Modèle Cassandra

Les trois tables répondent à trois parcours de lecture : activité d'un joueur
par jour, chronologie d'une session et erreurs d'une version par jour. Le
modèle est dénormalisé pour correspondre à ces requêtes. Montrer les exemples
de `docs/requetes_demo.cql`.

## 2:45–3:45 — Démonstration

Générer les événements avec `python -m src.generator`, puis lancer
`python -m src.ingestion data/events.jsonl`. Montrer le résumé dans
`data/quality_report.json` et le contenu de la quarantaine s'il y a des rejets.
Exécuter ensuite deux requêtes de démonstration avec `cqlsh`.

## 3:45–5:00 — Indicateurs et limites

Présenter les nombres acceptés/rejetés, le taux de rejet, les niveaux terminés
et les erreurs par version. Préciser les limites : données synthétiques,
Cassandra mono-nœud avec facteur de réplication 1, écriture indépendante dans
les trois tables et absence de reprise automatique. Proposer comme suite
l'ajout de tests d'intégration contre un cluster réel et une configuration
sécurisée pour un environnement multi-nœud.
