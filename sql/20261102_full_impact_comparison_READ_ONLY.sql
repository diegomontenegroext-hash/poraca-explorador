-- Por Acá — comparación reproducible de las últimas dos FULL finalizadas.
-- Ejecutar EXCLUSIVAMENTE en Neon project frosty-union-52906378,
-- branch br-mute-recipe-b4odj2bl, database neondb.
-- READ ONLY: no edita fuentes, agenda, roles, eventos ni recibos.
WITH finished_fulls AS (
 SELECT run_id,started_at,finished_at,status,sources_selected,sources_checked,
        candidates_new,candidates_seen,summary,
        row_number() OVER(ORDER BY started_at DESC,run_id DESC) AS sequence
 FROM radar_definitivo.runs
 WHERE mode='full' AND finished_at IS NOT NULL
), recent AS (
 SELECT * FROM finished_fulls WHERE sequence<=2
), outcomes AS (
 SELECT f.sequence,f.run_id,s.source_id,s.circuit,s.monitoring_mode,
        j.item->>'status' AS fetch_status,
        GREATEST(0,COALESCE(NULLIF(j.item->>'observed_sessions','')::int,0)) AS sessions_reported
 FROM recent f
 CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(f.summary->'source_outcomes')='array'
       THEN f.summary->'source_outcomes' ELSE '[]'::jsonb END
 ) AS j(item)
 JOIN radar_definitivo.sources s ON s.source_id=j.item->>'source_id'
), metrics AS (
 SELECT f.sequence,f.run_id,f.started_at,f.finished_at,f.status,
        f.sources_selected,f.sources_checked,f.candidates_new,f.candidates_seen,
        COUNT(*) FILTER(WHERE o.monitoring_mode='fetch')::int AS fetch_checks,
        COUNT(*) FILTER(WHERE o.monitoring_mode='fetch' AND o.fetch_status='ok')::int AS fetch_ok,
        COUNT(*) FILTER(WHERE o.monitoring_mode='fetch' AND o.fetch_status='index_only')::int AS fetch_index_only,
        COUNT(*) FILTER(WHERE o.monitoring_mode='fetch' AND o.sessions_reported>0)::int AS productive_fetch_sources,
        COALESCE(SUM(o.sessions_reported) FILTER(WHERE o.monitoring_mode='fetch'),0)::int AS sightings_not_unique_events,
        (SELECT count(*) FROM radar_definitivo.listing_occurrences l
         WHERE l.first_run_id=f.run_id)::int AS unique_staging_records_first_seen_this_run,
        f.summary->'health'->>'overall' AS overall_health,
        f.summary->'stability'->'3d'->>'state' AS stability_3d,
        f.summary->'stability'->'7d'->>'state' AS stability_7d
 FROM recent f LEFT JOIN outcomes o ON o.run_id=f.run_id
 GROUP BY f.sequence,f.run_id,f.started_at,f.finished_at,f.status,
          f.sources_selected,f.sources_checked,f.candidates_new,
          f.candidates_seen,f.summary
)
SELECT * FROM metrics ORDER BY sequence;
