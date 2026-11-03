-- POR ACÁ · ROLLBACK REVISADO: UNA FUENTE, RESTAURAR MODO ORIGINAL.
-- No reescribe source_checks, runs, agenda, entidades ni relaciones.
WITH restore AS (
 UPDATE radar_definitivo.sources
 SET monitoring_mode='fetch'
 WHERE source_id='rd-web-2f6489bc'
   AND source_role='official_museum_archive'
   AND monitoring_mode='discover_only'
 RETURNING source_id,name,monitoring_mode
)
SELECT * FROM restore;