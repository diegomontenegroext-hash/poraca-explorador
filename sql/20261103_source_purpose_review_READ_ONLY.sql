-- POR ACA / 03-11-2026 / P0-C: health/purpose review, SELECT-only.
-- Calcula chequeos y hallazgos por separado para evitar multiplicacion de joins.
WITH scope AS (
 SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today
), checks AS (
 SELECT c.source_id,
   count(*) FILTER (WHERE r.started_at>=now()-interval '7 days')::int AS checks7d,
   count(*) FILTER (WHERE r.started_at>=now()-interval '7 days'
     AND c.status='index_only')::int AS index_only7d,
   count(*) FILTER (WHERE r.started_at>=now()-interval '7 days'
     AND c.status='failed')::int AS failed7d,
   count(*) FILTER (WHERE r.started_at>=now()-interval '7 days'
     AND c.status='ok')::int AS ok7d
 FROM radar_definitivo.source_checks c
 JOIN radar_definitivo.runs r ON r.run_id=c.run_id
 WHERE r.started_at>=now()-interval '7 days'
 GROUP BY c.source_id
), upcoming AS (
 SELECT l.source_id,count(DISTINCT l.listing_key)::int AS dated_future_rows
 FROM radar_definitivo.listing_occurrences l CROSS JOIN scope x
 WHERE l.event_date>=x.today
 GROUP BY l.source_id
), evidence AS (
 SELECT s.source_id,s.name,s.url,s.source_role,s.circuit,s.monitoring_mode,
        s.last_status,s.consecutive_failures,
        coalesce(c.checks7d,0) AS checks7d,
        coalesce(c.index_only7d,0) AS index_only7d,
        coalesce(c.failed7d,0) AS failed7d,
        coalesce(c.ok7d,0) AS ok7d,
        coalesce(u.dated_future_rows,0) AS dated_future_rows
 FROM radar_definitivo.sources s
 LEFT JOIN checks c USING(source_id)
 LEFT JOIN upcoming u USING(source_id)
 WHERE s.enabled AND s.monitoring_mode='fetch'
), triage AS (
 SELECT e.*,
  CASE WHEN source_role IN ('official_museum_archive',
                           'historical_original_organizer_not_current_venue',
                           'official_custodian')
          AND checks7d>=3 AND dated_future_rows=0
          AND index_only7d+failed7d>=3
       THEN 'REVIEW_REFERENCE_SOURCE_MODE'
       WHEN failed7d>0 THEN 'RECOVER_SOURCE_HTTP'
       WHEN index_only7d>=3 AND ok7d=0 THEN 'REVIEW_INDEX_PURPOSE'
       ELSE 'PRESERVE_SOURCE_SCOPE' END AS proposed_review_lane,
  (SELECT count(*)::int FROM radar_definitivo.sources other
    WHERE other.source_id<>e.source_id AND other.enabled
      AND other.monitoring_mode='fetch' AND other.circuit=e.circuit
      AND other.source_role IN ('original_institutional',
        'first_party_institution','institutional_program','original_venue')
  ) AS other_institutional_sources_in_circuit
 FROM evidence e
)
SELECT source_id,name,url,source_role,circuit,monitoring_mode,
       checks7d,index_only7d,failed7d,ok7d,dated_future_rows,last_status,
       proposed_review_lane,other_institutional_sources_in_circuit,
       false AS alternative_entity_identity_verified,
       false AS source_mode_changed,
       false AS failure_erased,
       'HUMAN_REVIEW_WITH_PROVENANCE_AND_ROLLBACK'::text AS required_action
FROM triage
WHERE proposed_review_lane<>'PRESERVE_SOURCE_SCOPE'
ORDER BY CASE proposed_review_lane
 WHEN 'REVIEW_REFERENCE_SOURCE_MODE' THEN 0
 WHEN 'RECOVER_SOURCE_HTTP' THEN 1 ELSE 2 END,
 failed7d DESC,index_only7d DESC,source_id LIMIT 60;