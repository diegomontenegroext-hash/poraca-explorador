-- POR ACA · P0: 13 canonical identities still missing, independently classified.
-- Snapshot read-only; no automatic reconciliation, deletion or publication.
-- Re-run after the next ordinary Radar to compare actual identities and decisions.
WITH orphan_ids AS (
 SELECT o.matched_event_key AS event_id,
  min(o.observed_date) AS observed_day,
  count(*)::int AS observation_links,
  count(*) FILTER (WHERE o.observed_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')::int AS timed_observations,
  count(*) FILTER (WHERE o.source_event_url LIKE 'https://%')::int AS original_urls,
  (array_agg(o.observed_title ORDER BY o.observed_date DESC))[1] AS title,
  (array_agg(o.observed_venue ORDER BY o.observed_date DESC))[1] AS raw_venue
 FROM public.radar_v3_source_observations o
 WHERE o.matched_event_key IS NOT NULL
 AND NOT EXISTS(SELECT 1 FROM public.radar_agenda_events e WHERE e.event_key=o.matched_event_key)
 GROUP BY o.matched_event_key
), receipt AS (
 SELECT item->>'eventId' AS event_id,count(*)::int AS accepted_receipts
 FROM public.radar_v3_checkpoints c
 CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(c.metrics->'results')='array'
  THEN c.metrics->'results' ELSE '[]'::jsonb END) item
 WHERE c.stage='cultural_pipeline_v1'
 AND item->>'state'='ACCEPTED_EVENT'
 GROUP BY item->>'eventId'
), cases AS (
 SELECT o.*,COALESCE(r.accepted_receipts,0) AS accepted_receipts,
  venues.display_name AS venue_name,
  venues.entity_id AS venue_entity_id,
  venues.entity_kind AS venue_entity_kind,
  venues.editorial_state AS venue_editorial_state,
  venues.hosted_at_relations,
  CASE
   WHEN o.observed_day < (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
     THEN 'HOLD_HISTORICAL_ARCHIVE_DO_NOT_PUBLISH'
   WHEN venues.hosted_at_relations=0 OR venues.entity_id IS NULL
     THEN 'HOLD_UNKNOWN_PARENT_VENUE'
   WHEN venues.editorial_state <> 'approved_public'
     THEN 'HOLD_INTERNAL_ENTITY_REVIEW'
   WHEN venues.entity_kind <> 'venue'
     THEN 'HOLD_INSTITUTION_NOT_VENUE'
   WHEN o.timed_observations=0
     THEN 'HOLD_MISSING_ORIGINAL_TIME'
   WHEN o.original_urls=0
     THEN 'HOLD_NO_FIRST_PARTY_ORIGINAL'
   ELSE 'REVIEW_ORIGINAL_FOR_INDIVIDUAL_ADMISSION'
  END AS next_gate
 FROM orphan_ids o LEFT JOIN receipt r USING(event_id)
 LEFT JOIN LATERAL (
  SELECT e.display_name,e.entity_id,e.entity_kind,e.editorial_state,
         count(*) OVER()::int AS hosted_at_relations
  FROM public.poraca_knowledge_relations rel
  JOIN public.poraca_knowledge_entities e ON e.entity_id=rel.object_id
  WHERE rel.subject_kind='event'
   AND rel.subject_id=o.event_id AND rel.predicate='hosted_at'
   AND rel.review_state='accepted'
  ORDER BY rel.relation_id LIMIT 1
 ) venues ON true
)
SELECT event_id,title,observed_day,raw_venue,venue_name,venue_entity_id,
 venue_entity_kind,venue_editorial_state,observation_links,
 timed_observations,original_urls,accepted_receipts,next_gate,
 false AS publication_approved, false AS authorized_to_write
FROM cases ORDER BY next_gate,observed_day,event_id;
