-- P0 chronology-aware identity reconciliation; SELECT ONLY.
-- 5 manual, ORIGINAL-documented announced slots; never infer events from IDs.
-- Unlike date-only reports, a show earlier TODAY is already archival.
-- No writes, no trigger changes, no publication approval and no venue promotion.
WITH evidence(event_id,first_party_evidence,original_announced_start,venue_entity_id) AS (
 VALUES
 ('camerata-concertante-city-bell-2026-10-31','https://lumenartis.org/?p=2880&post_type=funcion','2026-10-31 20:00'::timestamp,'lumen-artis-teatro-camara'),
 ('casa-metro-segundo-tiempo-sexteto-2026-10-31','https://casametro.com.ar/categoria-producto/casa-metro/','2026-10-31 20:00'::timestamp,'casa-metro'),
 ('teatro-metro-pablo-fabregas-2026-10-31','https://www.teatrometrolp.com.ar/entrada/pablo-fabregas-100961','2026-10-31 21:00'::timestamp,'research-teatro-metro-laplata'),
 ('teatro-metro-pequeno-pez-2026-11-01','https://www.teatrometrolp.com.ar/entrada/pequeno-pez-100882','2026-11-01 17:00'::timestamp,'research-teatro-metro-laplata'),
 ('teatro-metro-nico-de-tracy-purga-2026-11-05','https://www.teatrometrolp.com.ar/entrada/nico-de-tracy-purga-100764','2026-11-05 21:00'::timestamp,'research-teatro-metro-laplata')
), observed AS (
 SELECT e.*,
  (now() AT TIME ZONE 'America/Argentina/Buenos_Aires') AS now_local,
  (SELECT count(*)::int FROM public.radar_v3_source_observations o
   WHERE o.matched_event_key=e.event_id) AS observation_count,
  (SELECT count(*)::int FROM public.poraca_knowledge_relations r
   WHERE r.subject_kind='event' AND r.subject_id=e.event_id
     AND r.review_state='accepted' AND r.predicate='hosted_at'
     AND r.object_id=e.venue_entity_id) AS accepted_hosted_at_count,
  (SELECT count(*)::int FROM public.radar_agenda_events c
   WHERE c.event_key=e.event_id) AS canonical_count,
  (SELECT editorial_state FROM public.poraca_knowledge_entities v
   WHERE v.entity_id=e.venue_entity_id) AS venue_editorial_state
 FROM evidence e
)
SELECT event_id,first_party_evidence,original_announced_start,now_local,
 venue_entity_id,venue_editorial_state,observation_count,accepted_hosted_at_count,
 canonical_count,
 CASE WHEN canonical_count>0 THEN 'ALREADY_RECONCILED'
 WHEN observation_count=0 OR accepted_hosted_at_count=0 THEN 'HOLD_EVIDENCE_LINK_MISMATCH'
 WHEN original_announced_start<=now_local THEN 'ARCHIVE_ONLY_NO_FUTURE_PUBLICATION'
 WHEN venue_editorial_state='approved_public' THEN 'FUTURE_ORIGINAL_FOR_INDIVIDUAL_EDITORIAL_REVIEW'
 ELSE 'FUTURE_INTERNAL_VENUE_RESEARCH_ONLY'
 END AS required_next_state,
 false AS authorization_to_write, false AS confirmed_occurred
FROM observed ORDER BY original_announced_start,event_id;