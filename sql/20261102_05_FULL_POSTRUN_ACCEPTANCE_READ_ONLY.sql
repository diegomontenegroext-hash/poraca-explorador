-- POR ACA · Certificación observacional FULL 05:00 ART, 2026-11-02.
-- READ-ONLY / Neon operational branch br-mute-recipe-b4odj2bl / neondb.
-- Repetir después de completar el workflow NORMAL; no lanza Radar ni escribe.
-- No incluir los 123 históricos con status='scheduled' como próximas funciones.
WITH window AS (
 SELECT '2026-11-02 05:00:00-03'::timestamptz AS begins_at,
        '2026-11-03 05:00:00-03'::timestamptz AS ends_at,
        (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today
), target AS (
 SELECT r.* FROM radar_definitivo.runs r CROSS JOIN window w
 WHERE r.mode='full' AND r.started_at >= w.begins_at
   AND r.started_at < w.ends_at
 ORDER BY r.started_at DESC LIMIT 1
), sc AS (
 SELECT count(*)::int checked,
        count(*) FILTER(WHERE status='ok')::int ok,
        count(*) FILTER(WHERE status='index_only')::int index_only,
        count(*) FILTER(WHERE status NOT IN ('ok','index_only'))::int other,
        count(*) FILTER(WHERE http_status NOT BETWEEN 200 AND 299)::int http_non_2xx,
        count(*) FILTER(WHERE coalesce(error_type,'')<>'')::int parser_or_access_errors
 FROM radar_definitivo.source_checks c
 WHERE c.run_id=(SELECT run_id FROM target)
), catalog AS (
 SELECT (SELECT count(*)::int FROM radar_definitivo.listing_occurrences) staging_total,
        (SELECT count(*)::int FROM radar_definitivo.listing_occurrences WHERE event_date>=(SELECT today FROM window)) staging_future,
        (SELECT count(*)::int FROM public.radar_agenda_events) canonical_total,
        (SELECT count(*)::int FROM public.radar_agenda_events WHERE event_date>=(SELECT today FROM window)) canonical_future,
        (SELECT count(*)::int FROM public.radar_agenda_events WHERE event_date>=(SELECT today FROM window) AND verification='confirmed') canonical_future_confirmed,
        (SELECT count(*)::int FROM public.poraca_knowledge_entities) entities,
        (SELECT count(*)::int FROM public.poraca_knowledge_relations) cultural_relations,
        (SELECT count(*)::int FROM public.poraca_event_release_readiness_v2
          WHERE first_program_day>=(SELECT today FROM window)
          AND release_quality_gate LIKE 'hold%') future_editorial_holds
), identity AS (
 SELECT pg_has_role('poraca_radar_limited_prod','neon_superuser','member') AS is_elevated,
 has_table_privilege('poraca_radar_limited_prod','radar_definitivo.runs','INSERT,UPDATE') AS runs_write,
 has_table_privilege('poraca_radar_limited_prod','radar_definitivo.listing_occurrences','INSERT,UPDATE') AS staging_write,
 has_table_privilege('poraca_radar_limited_prod','public.radar_agenda_events','INSERT,UPDATE,DELETE,TRUNCATE') AS canonical_write
)
SELECT CASE
 WHEN t.run_id IS NULL THEN '05_FULL_NOT_YET_STARTED'
 WHEN t.finished_at IS NULL THEN '05_FULL_RUNNING'
 WHEN t.status NOT IN ('complete','partial') THEN '05_FULL_FAILED_OR_INTERRUPTED'
 WHEN s.checked<>t.sources_selected OR s.other>0 OR s.http_non_2xx>0
   OR s.parser_or_access_errors>0 THEN '05_FULL_ACQUISITION_NEEDS_REVIEW'
 WHEN t.summary->'health'->>'schema'<>'poraca-health-v2'
   OR t.summary->'health'->>'controls'<>'correcto' THEN '05_FULL_HEALTH_CONTRACT_NOT_CERTIFIED'
 WHEN t.summary->'editorial_funnel_v1'->>'schema'<>'poraca-radar-run-editorial-funnel-v1'
   THEN '05_FULL_EDITORIAL_FUNNEL_MISSING'
 ELSE '05_FULL_STAGING_OPERABLE_WITH_YIELD_GAPS_POSSIBLE' END AS verdict,
 t.run_id,t.mode,t.status,t.started_at,t.finished_at,
 t.sources_selected,t.sources_checked,
 t.summary->'health' AS run_health,
 t.summary->'stability' AS run_stability,
 jsonb_build_object('checked',s.checked,'ok',s.ok,'indexOnly',s.index_only,
 'other',s.other,'httpNon2xx',s.http_non_2xx,'parserOrAccessErrors',s.parser_or_access_errors) AS source_metrics,
 COALESCE(t.summary->'editorial_funnel_v1'->'counts','{}'::jsonb) AS run_editorial_counts,
 COALESCE(t.summary->'editorial_funnel_v1'->'sourceYieldV1'->'priorityReview','[]'::jsonb) AS sources_prioritized_for_review,
 to_jsonb(c) AS current_catalog,
 jsonb_build_object('restrictedUserIsElevated',i.is_elevated,
 'canWriteRuns',i.runs_write,'canWriteStaging',i.staging_write,
 'canWriteCanonical',i.canonical_write) AS role_fence,
 'Publication is NOT inferred: accepted event receipts and live SSO must be checked separately' AS interpretation
FROM sc s CROSS JOIN catalog c CROSS JOIN identity i LEFT JOIN target t ON true;
