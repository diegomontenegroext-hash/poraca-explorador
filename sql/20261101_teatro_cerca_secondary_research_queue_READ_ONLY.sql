-- POR ACA · secondary research tray preflight · SELECT ONLY.
-- Goal: make Teatro Cerca discoveries usable WITHOUT treating a secondary
-- agenda as an official event, promoting venues, modifying receipts or writing.
-- Re-run after every FULL; dedupe conservatively and retain possible aliases.
WITH last_full AS (
 SELECT run_id FROM radar_definitivo.runs WHERE mode='full' AND finished_at IS NOT NULL
 ORDER BY started_at DESC LIMIT 1
), candidates AS (
 SELECT l.source_id,l.listing_key,l.title,l.event_date,l.event_time,l.venue,
        l.proof_url,l.evidence_tier,l.review_state,l.first_run_id,l.last_run_id
 FROM radar_definitivo.listing_occurrences l JOIN last_full run ON run.run_id=l.last_run_id
 WHERE l.source_id='rd-web-c53e461e'
 AND l.evidence_tier='secondary_specialized_agenda'
 AND l.review_state='observed_unverified'
 AND l.event_date BETWEEN
  (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+45
 AND l.event_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'
), compared AS (
 SELECT c.*,
 (
  SELECT count(*)::int FROM public.radar_agenda_events canon
  WHERE canon.event_date=c.event_date AND canon.event_time=c.event_time
  AND public.poraca_fact_key_v1(canon.title)=public.poraca_fact_key_v1(c.title)
 ) AS potential_same_title_time,
 (
  SELECT count(*)::int FROM public.radar_agenda_events canon
  WHERE canon.event_date=c.event_date AND canon.event_time=c.event_time
  AND canon.source_url=c.proof_url
 ) AS exact_original_url_matches,
 (
  SELECT jsonb_agg(jsonb_build_object('id',canon.event_key,
   'title',canon.title,'venue',canon.venue,'verification',canon.verification))
  FROM public.radar_agenda_events canon
  WHERE canon.event_date=c.event_date AND canon.event_time=c.event_time
   AND (canon.source_url=c.proof_url OR
        public.poraca_fact_key_v1(canon.title)=public.poraca_fact_key_v1(c.title))
 ) AS possible_catalogue_matches
 FROM candidates c
)
SELECT c.source_id,c.listing_key,c.title,c.event_date,c.event_time,c.venue,
 c.proof_url,c.evidence_tier,c.review_state,
 c.potential_same_title_time,c.exact_original_url_matches,
 coalesce(c.possible_catalogue_matches,'[]'::jsonb) AS possible_catalogue_matches,
 CASE
  WHEN c.exact_original_url_matches>0 OR c.potential_same_title_time>0
  THEN 'HOLD_POSSIBLE_EXISTING_EVENT'
  ELSE 'RESEARCH_SECONDARY_ONLY_VERIFY_ORIGINAL'
 END AS next_gate,
 false AS publication_approved,false AS destination_venue_approved,
 false AS authorization_to_write
FROM compared c
ORDER BY c.event_date,c.event_time,c.title,c.listing_key;