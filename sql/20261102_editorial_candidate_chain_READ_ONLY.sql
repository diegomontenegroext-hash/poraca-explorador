-- POR ACÁ · AUDITORÍA DE CANDIDATO EDITORIAL SIN PUBLICACIÓN (READ ONLY).
-- Caso testigo del 02/11/2026; para reutilizar cambiar SOLAMENTE packet.
-- La evidencia de la fuente original no suple una DECISIÓN editorial atestada.
-- Nunca crear registros por esta consulta, ni cambiar verification o recibos.
WITH packet AS (
 SELECT 'Malena Muyala'::text AS title,
  '2026-11-21'::date AS event_day,
  '22:00'::text AS event_time,
  'Sala A - Casa Metro'::text AS venue,
  'https://casametro.com.ar/evento/malena-muyala/'::text AS original_url,
  'casa-metro'::text AS proposed_host_id
), proof AS (
 SELECT
  count(*)::int AS exact_original_observations,
  count(DISTINCT s.source_id)::int AS distinct_catalog_source_ids,
  count(*) FILTER(WHERE l.evidence_tier IN
    ('primary_venue','primary_ticket_listing','primary_program_ics','primary_structured_page')
    AND l.review_state='observed_unverified')::int AS structured_primary_observations,
  min(l.first_seen_at) AS first_seen,
  max(l.last_seen_at) AS last_seen
 FROM packet p JOIN radar_definitivo.listing_occurrences l
  ON l.title=p.title AND l.event_date=p.event_day
  AND l.event_time=p.event_time AND l.venue=p.venue
  AND l.proof_url=p.original_url
 JOIN radar_definitivo.sources s ON s.source_id=l.source_id
 WHERE s.enabled
), candidate_count AS (
 SELECT count(*)::int AS raw_similar_observations
 FROM packet p JOIN radar_definitivo.listing_occurrences l
  ON l.event_date=p.event_day AND l.event_time=p.event_time
  AND lower(btrim(l.title))=lower(btrim(p.title))
), canon AS (
 SELECT count(*)::int AS canonical_collision_count
 FROM packet p JOIN public.radar_agenda_events e
 ON e.event_date=p.event_day
 AND left(coalesce(e.event_time,''),5)=p.event_time
 AND (e.source_url=p.original_url OR (
    lower(btrim(e.title))=lower(btrim(p.title))
    AND lower(btrim(e.venue))=lower(btrim(p.venue))))
), host AS (
 SELECT count(*)::int AS approved_host_count
 FROM packet p JOIN public.poraca_knowledge_entities e
 ON e.entity_id=p.proposed_host_id
 AND e.entity_kind='venue' AND e.editorial_state='approved_public'
 AND e.merged_into_id IS NULL
), receipts AS (
 SELECT count(*)::int AS matching_original_receipts,
 count(*) FILTER(WHERE item->>'state'='ACCEPTED_EVENT')::int AS accepted_event_receipts
 FROM packet p JOIN public.radar_v3_checkpoints ck ON ck.stage='cultural_pipeline_v1'
 CROSS JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(ck.metrics->'results')='array' THEN ck.metrics->'results'
  ELSE '[]'::jsonb END) item
 WHERE item->>'sourceUrl'=p.original_url
), audit AS (
 SELECT p.title,p.event_day,p.event_time,p.venue,p.original_url,
 p.proposed_host_id,
 x.*,c.*,v.*,r.*
 FROM packet p CROSS JOIN proof x CROSS JOIN candidate_count c
 CROSS JOIN canon v CROSS JOIN host h CROSS JOIN receipts r
)
SELECT a.title,a.event_day,a.event_time,a.venue,a.original_url,a.proposed_host_id,
 a.exact_original_observations,a.distinct_catalog_source_ids,
 a.structured_primary_observations,a.raw_similar_observations,
 a.first_seen,a.last_seen,a.canonical_collision_count,
 (SELECT approved_host_count FROM host) AS approved_host_count,
 a.matching_original_receipts,a.accepted_event_receipts,
 CASE
  WHEN a.canonical_collision_count>0 THEN 'HOLD_ALREADY_CANONICAL_OR_IDENTITY_COLLISION'
  WHEN (SELECT approved_host_count FROM host)<>1 THEN 'HOLD_HOST_NOT_APPROVED'
  WHEN a.structured_primary_observations=0 THEN 'HOLD_NO_EXACT_ORIGINAL_SESSION'
  WHEN a.accepted_event_receipts=0 THEN 'READY_FOR_INDEPENDENT_EDITORIAL_DECISION_NOT_RELEASED'
  ELSE 'HAS_ACCEPTANCE_RECEIPT_REVIEW_KEY_AND_PUBLICATION_GATE_SEPARATELY'
 END AS next_gate,
 false AS publication_approved_by_this_audit,
 'READ_ONLY_NO_CANONICAL_DML'::text AS contract
FROM audit a;
