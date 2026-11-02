-- POR ACÁ / Radar, two source onboarding witnesses, SELECT ONLY.
-- Run after next NATURAL full; do not infer editorial approval or publication
-- from HTTP 200, an original candidate, or a source marked enabled.
WITH expected(source_id, original_url, source_role, circuit, event_day) AS (
 VALUES
 ('rd-web-e60bb2a8'::text, 'https://www.nochedelaslibrerias.com.ar/'::text,
  'first_party_organizer'::text, 'literatura'::text, DATE '2026-11-06'),
 ('rd-web-17f06bfe', 'https://www.passline.com/eventos/feria-catar-v-edicion',
  'first_party_ticketing', 'vinos', DATE '2026-11-27')
)
SELECT x.source_id,x.circuit,x.original_url,
 s.monitoring_mode,s.enabled,s.source_role,
 s.last_checked_at,s.last_status,
 c.kind AS candidate_kind,c.review_state AS candidate_review,
 c.last_seen_at AS candidate_seen,
 (c.evidence->>'root_original_review')::boolean AS opened_original_review,
 (c.evidence->>'auto_publish')::boolean AS auto_publish,
 (SELECT count(*)::int FROM radar_definitivo.source_checks k
   WHERE k.source_id=x.source_id) AS source_checks,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
   WHERE l.source_id=x.source_id AND l.event_date=x.event_day) AS exact_day_occurrences,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
   WHERE l.source_id=x.source_id AND l.proof_url=x.original_url
     AND l.review_state='observed_unverified'
     AND c.kind='cultural_cycle_index') AS historical_unverified_cycle_root_rows,
 (SELECT count(*)::int FROM public.radar_agenda_events e
   WHERE e.source_url=x.original_url AND e.event_date=x.event_day) AS approved_canonical_matches,
 CASE
   WHEN s.source_id IS NULL THEN 'NOT_ENROLLED'
   WHEN s.monitoring_mode <> 'fetch' OR NOT s.enabled THEN 'ENROLLED_NOT_MONITORED'
   WHEN s.last_checked_at IS NULL THEN 'ENROLLED_PENDING_FIRST_FETCH'
   WHEN c.url IS NULL THEN 'SOURCE_CHECKED_ORIGINAL_NOT_CAPTURED'
   WHEN coalesce(c.review_state,'') NOT IN ('unverified','pending','needs_review') THEN 'REVIEW_STATE_NEEDS_AUDIT'
   WHEN c.evidence->>'root_original_review' <> 'true' THEN 'CANDIDATE_OLD_OR_NOT_OPENED_ORIGINAL'
   ELSE 'ORIGINAL_CAPTURED_UNVERIFIED'
 END AS intake_state
FROM expected x
LEFT JOIN radar_definitivo.sources s ON s.source_id=x.source_id AND s.url=x.original_url
LEFT JOIN radar_definitivo.candidates c ON c.url=x.original_url
ORDER BY x.circuit,x.source_id;
