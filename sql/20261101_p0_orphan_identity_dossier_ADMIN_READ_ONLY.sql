-- POR ACA F1 / 2026-11-01. DOSSIER DE IDENTIDADES HUERFANAS. SOLO SELECT.
-- Acceso administrativo de lectura en Neon operativo, NO incluir en el workflow
-- del rol poraca_definitivo_scope: ese rol no puede leer checkpoints.
-- La coincidencia de un recibo no autoriza crear/restaurar un canon.
-- Sedes verified_internal nunca se promueven automaticamente.
WITH accepted AS (
 SELECT DISTINCT ON (item->>'eventId')
   item->>'eventId' event_id, item->>'sourceUrl' receipt_original,
   item->>'observationId' receipt_observation_id,
   c.recorded_at AS receipt_at
 FROM public.radar_v3_checkpoints c
 CROSS JOIN LATERAL jsonb_array_elements(
   CASE WHEN jsonb_typeof(c.metrics->'results')='array'
   THEN c.metrics->'results' ELSE '[]'::jsonb END) item
 WHERE c.stage='cultural_pipeline_v1'
   AND item->>'state'='ACCEPTED_EVENT'
   AND nullif(item->>'eventId','') IS NOT NULL
 ORDER BY item->>'eventId', c.recorded_at DESC
), observations AS (
 SELECT o.matched_event_key event_id,
   count(*)::int observation_count,
   min(o.observed_date) first_event_date,
   max(o.observed_date) last_event_date,
   (array_agg(o.observed_title ORDER BY o.first_seen_at DESC))[1] title,
   (array_agg(o.observed_time ORDER BY o.first_seen_at DESC))[1] clock,
   (array_agg(o.observed_venue ORDER BY o.first_seen_at DESC))[1] venue,
   (array_agg(o.source_event_url ORDER BY o.first_seen_at DESC))[1] observation_original
 FROM public.radar_v3_source_observations o
 WHERE nullif(o.matched_event_key,'') IS NOT NULL
 GROUP BY o.matched_event_key
), relations AS (
 SELECT r.subject_id event_id,
    count(*)::int accepted_relations,
    count(*) FILTER(WHERE r.predicate='hosted_at')::int venue_relations,
    array_agg(DISTINCT e.editorial_state) FILTER(WHERE r.predicate='hosted_at') AS venue_states,
    array_agg(DISTINCT e.display_name) FILTER(WHERE r.predicate='hosted_at') AS venue_names,
    array_agg(DISTINCT r.evidence_url) FILTER(WHERE r.evidence_url IS NOT NULL) AS relation_originals
 FROM public.poraca_knowledge_relations r
 LEFT JOIN public.poraca_knowledge_entities e
   ON e.entity_id=r.object_id
 WHERE r.subject_kind='event' AND r.review_state='accepted'
 GROUP BY r.subject_id
), ids AS (
 SELECT event_id FROM accepted
 UNION SELECT event_id FROM observations
 UNION SELECT event_id FROM relations
), orphaned AS (
 SELECT ids.event_id,
   a.receipt_at,a.receipt_original,a.receipt_observation_id,
   o.observation_count,o.first_event_date,o.last_event_date,o.title,o.clock,o.venue,
   o.observation_original,
   r.accepted_relations,r.venue_relations,r.venue_states,r.venue_names,r.relation_originals,
   CASE WHEN a.event_id IS NOT NULL THEN 'ACCEPTED_RECEIPT_MISSING_CANON'
        WHEN o.event_id IS NOT NULL THEN 'OBSERVATION_LINKED_WITHOUT_CANON'
        ELSE 'ACCEPTED_RELATION_WITHOUT_CANON_OR_OBSERVATION' END AS triage,
   CASE
     WHEN a.event_id IS NOT NULL AND 'verified_internal'=ANY(r.venue_states)
       THEN 'HOLD_INTERNAL_VENUE_REVIEW_HISTORY'
     WHEN a.event_id IS NOT NULL THEN 'RECONCILE_RECEIPT_AND_VENUE_NO_AUTO_RESTORE'
     WHEN o.event_id IS NOT NULL THEN 'RECONCILE_OBSERVATION_AND_RELATIONS'
     ELSE 'INVESTIGATE_RELATION_PROVENANCE_NO_AUTO_CANON' END AS next_gate
 FROM ids
 LEFT JOIN public.radar_agenda_events canon ON canon.event_key=ids.event_id
 LEFT JOIN accepted a ON a.event_id=ids.event_id
 LEFT JOIN observations o ON o.event_id=ids.event_id
 LEFT JOIN relations r ON r.event_id=ids.event_id
 WHERE canon.event_key IS NULL
)
SELECT event_id,triage,next_gate,
  coalesce(observation_count,0) observation_count,
  coalesce(accepted_relations,0) accepted_relations,
  receipt_at,first_event_date,last_event_date,title,clock,venue,venue_names,venue_states,
  receipt_original,observation_original,relation_originals,
  false AS authorized_to_write
FROM orphaned
ORDER BY
 CASE triage WHEN 'ACCEPTED_RECEIPT_MISSING_CANON' THEN 0
             WHEN 'OBSERVATION_LINKED_WITHOUT_CANON' THEN 1 ELSE 2 END,
 first_event_date NULLS LAST,event_id;