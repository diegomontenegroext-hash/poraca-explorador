-- POR ACA | EL DIA | acceptance after next naturally scheduled FULL | SELECT ONLY
-- No new Radar triggers, no publication. Article source is a SECONDARY press.
-- Source URL was corrected 01/11/2026 keeping id rd-web-1ee7792f.
WITH last_full AS (
 SELECT run_id,started_at,status FROM radar_definitivo.runs
 WHERE mode='full' AND finished_at IS NOT NULL
 ORDER BY started_at DESC LIMIT 1
), check_row AS (
 SELECT c.status,c.http_status,c.links_found,c.details_opened
 FROM radar_definitivo.source_checks c
 WHERE c.run_id=(SELECT run_id FROM last_full)
 AND c.source_id='rd-web-1ee7792f'
), measurement AS (
 SELECT count(*)::int AS sessions_seen,
  count(*) FILTER (WHERE l.review_state='observed_unverified')::int AS held_for_review,
  count(*) FILTER (WHERE l.evidence_tier='secondary_press_agenda')::int AS secondary_evidence,
  count(*) FILTER (WHERE l.event_date IS NOT NULL
    AND l.event_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')::int AS dated_with_clock,
  count(*) FILTER (WHERE l.proof_url ~
    '^https://(www\\.)?eldia\\.com/(espectaculos|septimo-dia)/agenda')::int AS publisher_agenda_originals
 FROM radar_definitivo.listing_occurrences l
 WHERE l.source_id='rd-web-1ee7792f'
 AND l.last_run_id=(SELECT run_id FROM last_full)
)
SELECT s.source_id,s.name,s.url,f.run_id AS last_full_id,f.status AS full_status,
 c.status AS source_status,c.http_status,c.links_found,c.details_opened,
 m.sessions_seen,m.held_for_review,m.secondary_evidence,m.dated_with_clock,
 m.publisher_agenda_originals,
 CASE
 WHEN s.url<>'https://www.eldia.com/espectaculos' THEN 'SOURCE_ROOT_MISMATCH'
 WHEN f.run_id='definitivo-20261101T212516Z-5bb102' THEN 'PENDING_NEXT_FULL_AFTER_URL_CORRECTION'
 WHEN c.status='ok' AND m.sessions_seen>0
  AND m.held_for_review=m.sessions_seen AND m.secondary_evidence=m.sessions_seen
  AND m.publisher_agenda_originals>0 THEN 'PASS_EL_DIA_PRESS_TO_NEON_UNVERIFIED'
 WHEN c.http_status<>200 THEN 'FAIL_HTTP'
 ELSE 'PARTIAL_DATED_AGENDA_YIELD_STILL_GAP'
 END AS source_gate,
 false AS automatic_publication
FROM radar_definitivo.sources s
CROSS JOIN last_full f LEFT JOIN check_row c ON true CROSS JOIN measurement m
WHERE s.source_id='rd-web-1ee7792f';