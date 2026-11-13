USE game_telemetry; -- Exécute les exemples dans le keyspace du projet.

-- Activité d'un joueur pendant une journée (table events_by_player_day).
-- Sélectionne les colonnes utiles pour afficher l'activité.
SELECT occurred_at, event_type, game_version, payload
-- Lit les données dans la table conçue pour les recherches joueur/jour.
FROM events_by_player_day
-- Fixe les deux valeurs de la clé de partition requise par Cassandra.
WHERE player_id = 'player-001' AND event_day = '2026-11-09'
-- Limite le nombre de lignes retournées à l'écran.
LIMIT 20;

-- Chronologie d'une session (table events_by_session).
-- Sélectionne les colonnes à afficher dans la chronologie.
SELECT occurred_at, event_id, player_id, event_type, payload
-- Lit dans la table organisée par session.
FROM events_by_session
-- Recherche la partition correspondant à cette session.
WHERE session_id = 'session-abc123'
-- Limite le nombre de résultats.
LIMIT 20;

-- Erreurs techniques d'une version pendant une journée.
-- Sélectionne l'instant, l'identifiant, le joueur et le détail JSON de l'erreur.
SELECT occurred_at, event_id, player_id, payload
-- Lit dans la table dédiée aux erreurs.
FROM errors_by_version_day
-- Fixe les deux valeurs de partition : version et jour.
WHERE game_version = '1.4.2' AND event_day = '2026-11-09'
-- Limite le nombre de résultats.
LIMIT 20;
