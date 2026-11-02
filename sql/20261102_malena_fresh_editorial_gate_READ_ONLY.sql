-- Por Acá 02/11/2026 · testigo real de admisión editorial, SOLO SELECT.
-- Este reporte NO publica, ni inserta ni declara que las funciones ocurrieron.
-- Estado 'READY' de una fuente no sustituye receipt ACCEPTED_EVENT independiente.
WITH target AS (
 SELECT 'Malena Muyala'::text AS title,
 '2026-11-21'::date AS event_date,
 '22:00'::text AS event_time,
 'Sala A - Casa Metro'::text AS venue,
 'https://casametro.com.ar/evento/malena-muyala/'::text AS official_url
), staging AS (
 SELECT count(*)::int AS matching_original_observations,
 count(DISTINCT l.source_id)::int AS distinct_source_checks,
 min(l.first_seen_at) AS first_seen,
 max(l.last_seen_at) AS last_seen,
 count(*) FILTER(WHERE l.evidence_tier='primary_venue'
 AND l.review_state='observed_unverified')::int AS original_unverified
 FROM radar_definitivo.listing_occurrences l CROSS JOIN target t
 WHERE l.title=t.title AND l.event_date=t.event_date
 AND l.event_time=t.event_time AND l.venue=t.venue AND l.proof_url=t.official_url
), history AS (
 SELECT count(*)::int AS matching_canonical,
 jsonb_agg(jsonb_build_object('event_key',event_key,'verification',verification,'status',status))
 AS matched_event
 FROM public.radar_agenda_events e CROSS JOIN target t
 WHERE e.event_date=t.event_date AND e.event_time=t.event_time
 AND (e.source_url=t.official_url OR
  (lower(trim(e.title))=lower(trim(t.title)) AND
   lower(trim(e.venue))=lower(trim(t.venue))))
), receipts AS (
 SELECT count(*)::int AS accepted_origin_receipts
 FROM public.radar_v3_checkpoints c CROSS JOIN target t
 CROSS JOIN LATERAL jsonb_array_elements(
 CASE WHEN jsonb_typeof(c.metrics->'results')='array'
 THEN c.metrics->'results' ELSE '[]'::jsonb END) r(item)
 WHERE c.stage='cultural_pipeline_v1' AND r.item->>'state'='ACCEPTED_EVENT'
 AND r.item->>'sourceUrl'=t.official_url
 -- Receipt is a *candidate* reference, not verified identity unless its
 -- observation/date/title/venue are independently checked at admission.
), summary AS (
 SELECT t.*,s.*,h.matching_canonical,h.matched_event,r.accepted_origin_receipts
 FROM target t CROSS JOIN staging s CROSS JOIN history h CROSS JOIN receipts r
)
SELECT title,event_date,event_time,venue,official_url,
 matching_original_observations,distinct_source_checks,original_unverified,
 accepted_origin_receipts,matching_canonical,matched_event,first_seen,last_seen,
 CASE WHEN matching_original_observations=0 THEN 'SOURCE_NOT_IN_STAGING'
 WHEN matching_canonical>1 THEN 'POTENTIAL_CANONICAL_DUPLICATE_BLOCK'
 WHEN matching_canonical=1 THEN 'CANONICAL_PRESENT_READBACK_REQUIRED'
 WHEN accepted_origin_receipts=0 THEN 'AWAITING_INDEPENDENT_EDITORIAL_ACCEPTANCE'
 ELSE 'RECEIPT_PRESENT_VERIFY_OBSERVATION_ID_THEN_AUTHORIZE_HANDOFF'
 END AS exact_case_gate,
 FALSE AS can_auto_publish,
 'Confirm original URL, show clock, venue, observation ID and independent accepted receipt before authorized canonical handoff' AS next_action
FROM summary;
