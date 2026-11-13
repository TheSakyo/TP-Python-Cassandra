-- Crée le keyspace du projet s'il n'existe pas encore.
CREATE KEYSPACE IF NOT EXISTS game_telemetry
-- Configure la réplication simple adaptée au Cassandra mono-nœud du TP.
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Sélectionne ce keyspace pour les instructions CQL suivantes.
USE game_telemetry;

-- Crée la table destinée aux recherches d'activité par joueur et par jour.
CREATE TABLE IF NOT EXISTS events_by_player_day (
    -- Première partie de la clé de partition : le joueur.
    player_id text,
    -- Deuxième partie de la clé de partition : le jour UTC.
    event_day date,
    -- Trie les événements dans une partition selon leur heure.
    occurred_at timestamp,
    -- Départage les événements qui ont le même horodatage.
    event_id text,
    -- Garde l'identifiant de session pour l'affichage.
    session_id text,
    -- Garde la catégorie de l'événement.
    event_type text,
    -- Garde la version du jeu.
    game_version text,
    -- Stocke l'objet d'événement complet sérialisé en JSON.
    payload text,
    -- Définit joueur+jour comme partition et date+id comme ordre des lignes.
    PRIMARY KEY ((player_id, event_day), occurred_at, event_id)
-- Affiche les événements les plus récents en premier pour cette vue.
) WITH CLUSTERING ORDER BY (occurred_at DESC, event_id ASC);

-- Crée la table destinée à la chronologie complète d'une session.
CREATE TABLE IF NOT EXISTS events_by_session (
    -- Identifiant de session utilisé comme partition.
    session_id text,
    -- Trie les événements de la session par heure.
    occurred_at timestamp,
    -- Départage les événements ayant le même horodatage.
    event_id text,
    -- Identifiant du joueur associé à l'événement.
    player_id text,
    -- Catégorie de l'événement.
    event_type text,
    -- Document complet sérialisé.
    payload text,
    -- Regroupe chaque session dans une partition et trie ses événements.
    PRIMARY KEY ((session_id), occurred_at, event_id)
-- Affiche la chronologie dans l'ordre du plus ancien au plus récent.
) WITH CLUSTERING ORDER BY (occurred_at ASC, event_id ASC);

-- Crée la table dédiée aux erreurs filtrées par version et par jour.
CREATE TABLE IF NOT EXISTS errors_by_version_day (
    -- Première partie de la clé de partition : version du jeu.
    game_version text,
    -- Deuxième partie de la clé de partition : jour UTC de l'erreur.
    event_day date,
    -- Trie les erreurs de cette version et de ce jour par heure.
    occurred_at timestamp,
    -- Départage les erreurs de même horodatage.
    event_id text,
    -- Identifiant du joueur associé à l'erreur.
    player_id text,
    -- Document complet sérialisé de l'erreur.
    payload text,
    -- Regroupe chaque version+jour dans une partition.
    PRIMARY KEY ((game_version, event_day), occurred_at, event_id)
-- Affiche les erreurs les plus récentes en premier.
) WITH CLUSTERING ORDER BY (occurred_at DESC, event_id ASC);
