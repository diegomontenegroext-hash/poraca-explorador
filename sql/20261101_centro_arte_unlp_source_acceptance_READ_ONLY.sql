-- POR ACA / CENTRO DE ARTE UNLP / READ ONLY / 2026-11-01
-- Acceptance for original dated performances, not for undated biennials.
-- Re-evaluate after next ordinary FULL; do not create an extra Radar cron.
WITH last_full AS (
 SELECT run_id,started_at,finished_at,status
 FROM radar_definitivo.runs WHERE mode='full' AND finished_at IS NOT NULL
 ORDER BY started_at DESC LIMIT 1
), measures AS (
 SELECT count(*)::int AS total,
  count(*) FILTER(WHERE proof_method='centro_arte_unlp_official_original_explicit_session')::int AS official_originals,
  count(*) FILTER(WHERE evidence_tier='primary_venue')::int AS primary_evidence,
  count(*) FILTER(WHERE review_state='observed_unverified')::int AS unverified,
  count(*) FILTER(WHERE event_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')::int AS with_clock,
  count(*) FILTER(WHERE proof_url ~ '^https://(www\.)?centrodearte\.unlp\.edu\.ar/[a-z0-9-]+/?$')::int AS original_links,
  count(DISTINCT listing_key)::int AS unique_listing_keys
 FROM radar_definitivo.listing_occurrences l
 WHERE source_id='rd-web-6d71ee20'
 AND l.last_run_id=(SELECT run_id FROM last_full)
)
SELECT s.source_id,s.name,s.url,lf.run_id AS latest_full,c.status AS check_status,
 c.http_status,c.links_found,c.details_opened,
 m.total,m.official_originals,m.primary_evidence,m.unverified,
 m.with_clock,m.original_links,m.unique_listing_keys,
 CASE
 WHEN lf.run_id='definitivo-20261101T212516Z-5bb102'
  THEN 'PENDING_NEXT_FULL_AFTER_CENTRO_UNLP_PARSER'
 WHEN c.http_status<>200 THEN 'FAIL_HTTP'
 WHEN m.total>0 AND m.total=m.official_originals
  AND m.total=m.primary_evidence AND m.total=m.unverified
  AND m.total=m.with_clock AND m.total=m.original_links
  AND m.total=m.unique_listing_keys
  THEN 'PASS_EXPLICIT_ORIGINAL_TO_NEON_UNVERIFIED'
 WHEN c.http_status=200 AND m.total=0
  THEN 'NO_EXPLICIT_CURRENT_SESSION_REQUIRES_PROGRAM_REVIEW'
 ELSE 'PARTIAL_ORIGINAL_EVIDENCE_REVIEW'
 END AS acceptance,
 false AS auto_publication_approved,false AS writes_performed
FROM radar_definitivo.sources s CROSS JOIN last_full lf
LEFT JOIN radar_definitivo.source_checks c ON c.source_id=s.source_id AND c.run_id=lf.run_id
CROSS JOIN measures m
WHERE s.source_id='rd-web-6d71ee20';