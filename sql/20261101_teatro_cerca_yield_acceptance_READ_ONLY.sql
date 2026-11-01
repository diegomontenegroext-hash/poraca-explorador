-- POR ACA · Teatro Cerca · measurable FULL-run acceptance probe, SELECT ONLY.
-- Source identity is fixed: rd-web-c53e461e; reference URL is the actual index.
-- A commit or parser unit test does NOT certify a real Radar source run.
-- Reject automatic editorial publication; any extracted function remains secondary.
WITH full_run AS (
 SELECT run_id,started_at,finished_at,status
 FROM radar_definitivo.runs
 WHERE mode='full' AND finished_at IS NOT NULL
 ORDER BY started_at DESC LIMIT 1
), source_data AS (
 SELECT source_id,url,source_role,monitoring_mode
 FROM radar_definitivo.sources
 WHERE source_id='rd-web-c53e461e'
), source_check AS (
 SELECT c.run_id,c.status,c.http_status,c.links_found,c.details_opened
 FROM radar_definitivo.source_checks c
 WHERE c.source_id='rd-web-c53e461e'
 AND c.run_id=(SELECT run_id FROM full_run)
), all_listings AS (
 SELECT count(*)::int AS total,
   count(*) FILTER (WHERE last_run_id=(SELECT run_id FROM full_run))::int AS seen_in_full,
   count(*) FILTER (WHERE first_run_id=(SELECT run_id FROM full_run))::int AS first_seen_in_full,
   count(*) FILTER (WHERE event_date IS NOT NULL AND event_time ~
     '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')::int AS timed,
   count(*) FILTER (WHERE evidence_tier NOT IN (
    'secondary_specialized_agenda','secondary_agenda'))::int AS suspicious_primary_tier,
   count(*) FILTER (WHERE review_state<>'observed_unverified')::int AS unauthorized_review_state,
   min(event_date) AS earliest_date,max(event_date) AS latest_date
 FROM radar_definitivo.listing_occurrences WHERE source_id='rd-web-c53e461e'
)
SELECT s.source_id,s.url,s.source_role,s.monitoring_mode,
 f.run_id AS last_full_run_id,f.finished_at AS last_full_finished_at,
 c.status AS last_full_status,c.http_status AS last_full_http,
 c.links_found,c.details_opened,
 l.total AS stored_session_identities,l.seen_in_full,l.first_seen_in_full,
 l.timed,l.suspicious_primary_tier,l.unauthorized_review_state,
 l.earliest_date,l.latest_date,
 CASE
 WHEN c.run_id IS NULL THEN 'NOT_CHECKED_IN_LAST_FULL'
 WHEN c.http_status<>200 THEN 'FAIL_HTTP'
 WHEN l.unauthorized_review_state>0 OR l.suspicious_primary_tier>0
   THEN 'FAIL_EVIDENCE_BOUNDARY'
 WHEN c.status='ok' AND l.seen_in_full>0 AND l.timed>0
   THEN 'PASS_REAL_FULL_SOURCE_YIELD'
 WHEN c.status='index_only' AND l.seen_in_full=0
   THEN 'PENDING_PARSER_REAL_FULL_MEASUREMENT'
 ELSE 'PARTIAL_SOURCE_YIELD'
 END AS decision,
 false AS auto_publication_approved,
 false AS changes_written
FROM source_data s CROSS JOIN full_run f
LEFT JOIN source_check c ON true CROSS JOIN all_listings l;