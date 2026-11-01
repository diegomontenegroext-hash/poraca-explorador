-- POR ACA · 24 ACCEPTED relationship-only canonical identities missing (2026-11-01)
-- Complete P0 inventory, independent of whether an observation survived.
-- SELECT ONLY. Dates embedded in IDs are hints, NOT original verified dates.
-- No automatic archive, event admission, venue promotion, relation deletion.
WITH missing_rel AS (
 SELECT rel.subject_id AS event_id,
   count(*)::int AS accepted_relations,
   count(*) FILTER (WHERE rel.predicate='hosted_at')::int AS accepted_hosted_at,
   count(*) FILTER (WHERE rel.predicate<>'hosted_at')::int AS other_relations,
   coalesce(jsonb_agg(DISTINCT jsonb_build_object(
     'predicate',rel.predicate,
     'entityId',rel.object_id,
     'entityKind',entities.entity_kind,
     'editorialState',entities.editorial_state,
     'evidenceUrl',rel.evidence_url
   )),'[]'::jsonb) AS relation_dossier
 FROM public.poraca_knowledge_relations rel
 LEFT JOIN public.poraca_knowledge_entities entities ON entities.entity_id=rel.object_id
 WHERE rel.review_state='accepted' AND rel.subject_kind='event'
   AND NOT EXISTS(SELECT 1 FROM public.radar_agenda_events e
      WHERE e.event_key=rel.subject_id)
 GROUP BY rel.subject_id
), obs AS (
 SELECT o.matched_event_key AS event_id,
   count(*)::int AS observation_count,
   min(o.observed_date) AS earliest_observed_date,
   (array_agg(o.observed_title ORDER BY o.observed_date DESC))[1] AS latest_title,
   count(*) FILTER(WHERE o.observed_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')::int AS observed_timings,
   count(*) FILTER(WHERE o.source_event_url LIKE 'https://%')::int AS original_url_observations
 FROM public.radar_v3_source_observations o
 WHERE o.matched_event_key IS NOT NULL
 GROUP BY o.matched_event_key
), receipt AS (
 SELECT r.value->>'eventId' AS event_id,count(*)::int AS accepted_receipts
 FROM public.radar_v3_checkpoints ck
 CROSS JOIN LATERAL jsonb_array_elements(
   CASE WHEN jsonb_typeof(ck.metrics->'results')='array'
        THEN ck.metrics->'results' ELSE '[]'::jsonb END) r(value)
 WHERE ck.stage='cultural_pipeline_v1' AND r.value->>'state'='ACCEPTED_EVENT'
 GROUP BY r.value->>'eventId'
), classified AS (
 SELECT m.*,coalesce(o.observation_count,0) AS observations,
        o.earliest_observed_date,o.latest_title,
        coalesce(o.observed_timings,0) AS observed_timings,
        coalesce(o.original_url_observations,0) AS original_url_observations,
        coalesce(rc.accepted_receipts,0) AS accepted_receipts,
        CASE
         WHEN o.observation_count IS NOT NULL
           THEN 'HAS_OBSERVATION_SEPARATE_13_CASE_MATRIX'
         WHEN m.accepted_hosted_at=0
           THEN 'RELATION_ONLY_CYCLE_OR_ORGANIZER_NO_SESSION_PROOF'
         ELSE 'RELATION_ONLY_VENUE_WITHOUT_SESSION_OBSERVATION'
        END AS review_queue,
        CASE
         WHEN o.observation_count IS NOT NULL
           THEN 'USE_INDIVIDUAL_OBSERVATION_MATRIX'
         WHEN m.accepted_hosted_at=0
           THEN 'HOLD_SESSION_DATE_TIME_OR_VENUE_UNCONFIRMED'
         ELSE 'HOLD_FIRST_PARTY_SESSION_DATE_TIME_UNCONFIRMED'
        END AS next_gate
 FROM missing_rel m LEFT JOIN obs o USING(event_id)
 LEFT JOIN receipt rc USING(event_id)
)
SELECT event_id,latest_title,earliest_observed_date,
 accepted_relations,accepted_hosted_at,other_relations,
 observations,observed_timings,original_url_observations,
 accepted_receipts,review_queue,next_gate,relation_dossier,
 false AS publication_approved,false AS authorized_to_write,
 'IDs may contain unverified dates; do not treat as proof' AS caution
FROM classified ORDER BY observations ASC,accepted_receipts DESC,accepted_relations DESC,event_id;