-- POR ACA / F2+F3: sugerencias de ALIAS DE SEDE desde originales fechados.
-- Solo SELECT, no son vinculos aprobados ni altas de entidades/eventos.
-- Posibles sub-salas y edificios requieren revision humana de identidad.
WITH base AS (
 SELECT q.listing_key,q.title,q.event_date,left(coalesce(q.event_time,''),5) AS clock,
 q.venue,q.proof_url,q.evidence_tier,
 public.poraca_fact_key_v1(q.venue) AS venue_key
 FROM radar_definitivo.listing_quality_v1 q
 WHERE q.event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
   AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+45
 AND public.poraca_first_party_event_detail_v1(q.evidence_tier,q.proof_method,q.proof_url)
 AND nullif(trim(coalesce(q.venue,'')),'') IS NOT NULL
 AND coalesce(q.quality_state,'') NOT LIKE 'QUARANTINE%'
), approved AS (
 SELECT entity_id,display_name,public.poraca_fact_key_v1(display_name) AS key
 FROM public.poraca_knowledge_entities
 WHERE entity_kind='venue' AND editorial_state='approved_public'
 AND merged_into_id IS NULL
), pairs AS (
 SELECT DISTINCT b.title,b.event_date,b.clock,b.venue,b.proof_url,
    e.entity_id,e.display_name,
    CASE
      WHEN b.venue_key=e.key THEN 'EXACT_NAME_ALREADY_MATCHED'
      WHEN position(e.key in b.venue_key)>0 THEN 'PUBLIC_NAME_WITHIN_RAW_VENUE'
      WHEN position(b.venue_key in e.key)>0 THEN 'RAW_ALIAS_WITHIN_PUBLIC_NAME'
    END AS name_evidence,
    CASE WHEN b.venue ~* '(sala [a-z0-9]+|auditorio|edificio|piso|entre [0-9]|\bsubsuelo\b|,)' THEN
      'HOLD_SUBSPACE_OR_ADDRESS_VARIANT'
    ELSE 'HOLD_ALIAS_IDENTITY_REVIEW' END AS proposed_gate
 FROM base b JOIN approved e ON length(e.key)>=10 AND length(b.venue_key)>=10 AND
   (position(e.key in b.venue_key)>0 OR position(b.venue_key in e.key)>0)
 WHERE b.venue_key<>e.key
)
SELECT event_date,clock,title,venue AS raw_venue,display_name AS approved_venue,
 entity_id AS proposed_parent_venue_id,proof_url AS original_url,
 name_evidence,proposed_gate,
 false AS alias_approved,false AS event_publication_approved
FROM pairs
ORDER BY event_date,clock,title,entity_id LIMIT 80;