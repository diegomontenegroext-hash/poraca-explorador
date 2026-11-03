-- Por Acá / O3 / last seven NATURAL FULLs, cutover-aware, SELECT ONLY.
-- Observation window starts after the 03/11 museum source-mode cutover.
-- A Github Actions SUCCESS is NOT evidence of a complete FULL or publication.
-- Do not edit past run statuses, delete failed checks or trigger new FULLs.
WITH boundary AS (
 SELECT TIMESTAMPTZ '2026-11-03 12:00:00-03' AS lower_bound
), latest AS (
 SELECT r.run_id,r.mode,r.started_at,r.finished_at,r.status,
        r.sources_selected,r.sources_checked,r.sources_success,
        r.urls_discovered,r.candidates_new,r.summary
 FROM radar_definitivo.runs r
 WHERE r.mode='full' AND r.finished_at IS NOT NULL
 ORDER BY r.started_at DESC,r.run_id DESC LIMIT 7
), checked AS (
 SELECT c.run_id,count(*)::int AS persisted_checks,
        count(*) FILTER (WHERE c.status='ok')::int AS ok,
        count(*) FILTER (WHERE c.status='index_only')::int AS index_only,
        count(*) FILTER (WHERE c.status NOT IN ('ok','index_only')
                            OR c.http_status NOT BETWEEN 200 AND 299
                            OR coalesce(c.error_type,'')<>'')::int AS failed_or_errored,
        coalesce(jsonb_agg(jsonb_build_object(
          'sourceId',c.source_id,'checkStatus',c.status,
          'http',c.http_status,'errorType',c.error_type)
          ORDER BY c.source_id) FILTER (
          WHERE c.status NOT IN ('ok','index_only')
             OR c.http_status NOT BETWEEN 200 AND 299
             OR coalesce(c.error_type,'')<>''
          ),'[]'::jsonb) AS negative_checks
 FROM radar_definitivo.source_checks c
 WHERE c.run_id IN(SELECT run_id FROM latest)
 GROUP BY c.run_id
)
SELECT l.run_id,l.started_at,l.finished_at,l.status,
       l.sources_selected,l.sources_checked,l.sources_success,
       l.urls_discovered,l.candidates_new,
       coalesce(c.persisted_checks,0) AS persisted_checks,
       coalesce(c.ok,0) AS sources_ok,
       coalesce(c.index_only,0) AS sources_index_only,
       coalesce(c.failed_or_errored,0) AS failed_or_errored,
       coalesce(c.negative_checks,'[]'::jsonb) AS negative_checks,
       l.summary->'health'->>'schema' AS health_schema,
       l.summary->'health'->>'overall' AS declared_health,
       l.summary->'health'->>'acquisition' AS declared_acquisition,
       b.lower_bound AS post_cutover_from,
       (l.started_at>=b.lower_bound) AS is_post_cutover,
       CASE
        WHEN l.status='complete' AND l.sources_selected>0
         AND coalesce(c.persisted_checks,0)=l.sources_selected
         AND coalesce(c.failed_or_errored,0)=0
         AND l.summary->'health'->>'schema'='poraca-health-v2'
         THEN 'STRICT_COMPLETE'
        ELSE 'PARTIAL_OR_UNCERTIFIED'
       END AS o3_run_state
FROM latest l CROSS JOIN boundary b LEFT JOIN checked c USING(run_id)
ORDER BY l.started_at DESC,l.run_id DESC;