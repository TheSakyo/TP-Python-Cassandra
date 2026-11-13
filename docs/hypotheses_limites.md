# Hypothèses et limites

## Hypothèses

- `occurred_at` est interprété comme un instant ISO-8601. Les dates sans fuseau
  sont considérées comme UTC ; les dates avec fuseau sont converties en UTC.
- `event_day` est calculé à partir de cet instant UTC afin de former la clé de
  partition des tables journalières.
- Un événement `level_completed` doit avoir un `duration_seconds` numérique et
  strictement positif. `error_code` reste recommandé, mais facultatif.
- Le schéma CQL est appliqué avant l'ingestion avec `cqlsh`; l'application ne
  crée pas automatiquement le keyspace ni les tables.
- Le fichier de quarantaine et le rapport qualité représentent la dernière
  exécution : ils sont réécrits à chaque ingestion.

## Limites

- La configuration vise un Cassandra local sur `127.0.0.1:9042`, sans
  authentification ni reprise automatique après erreur.
- Le schéma du TP utilise un seul nœud et `SimpleStrategy` avec facteur de
  réplication 1. Il sert à l'apprentissage et n'est pas tolérant aux pannes.
- Les écritures dans les trois tables sont indépendantes. Cassandra ne fournit
  pas de transaction atomique entre ces tables ; une erreur pendant une
  ingestion peut donc laisser une partie des vues écrites.
- Le générateur crée des données synthétiques. Les identifiants de joueurs sont
  pseudonymes et aucune déduplication métier n'est effectuée au-delà des clés
  primaires Cassandra.
- Les métriques calculées pendant l'ingestion décrivent les événements valides
  qui ont été traités avec succès, ainsi que le nombre de lignes rejetées.
