-- POR ACA | SOURCE INTENT AND CONTENT COVERAGE | SELECT ONLY | 2026-11-01
-- Not every source is a dated-event producer. No source state, identity or
-- publication status is changed by this report. Run after the FULL.
WITH focus(source_id,expected_intent) AS (
 VALUES
 ('rd-web-56c74fce','IDENTITY_AND_REGULAR_WINE_ACTIVITY'),
 ('rd-web-79bed621','IDENTITY_AND_REGULAR_YOGA'),
 ('rd-web-5404c6e2','IDENTITY_AND_REGULAR_YOGA'),
 ('rd-web-59daab0a','IDENTITY_AND_REGULAR_WORKSHOP'),
 ('rd-web-5dc0c60d','INSTITUTIONAL_COURSES_NOT_SHOWS'),
 ('rd-web-6d71ee20','MIXED_ART_INSTITUTION_WITH_PROGRAM'),
 ('rd-web-1ee7792f','DATED_PRESS_AGENDA')
), last_full AS (
 SELECT run_id,finished_at FROM radar_definitivo.runs
 WHERE mode='full' AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1
), measures AS (
 SELECT f.*,s.name,s.url,s.source_role,s.circuit,s.monitoring_mode,
  c.status AS latest_check_state,c.http_status,c.links_found,c.details_opened,
  (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l WHERE l.source_id=f.source_id AND l.last_run_id=run.run_id) AS dated_sessions_last_full,
  (SELECT count(*)::int FROM public.radar_v3_source_observations o WHERE o.origin_source_id=f.source_id) AS persisted_observations,
  (SELECT count(*)::int FROM public.poraca_knowledge_entities e
   WHERE trim(trailing '/' from lower(e.official_url))=
         trim(trailing '/' from lower(s.url))
     AND e.merged_into_id IS NULL) AS entity_matches,
  (SELECT coalesce(jsonb_agg(jsonb_build_object(
   'name',e.display_name,'kind',e.entity_kind,'editorialState',e.editorial_state
   ) ORDER BY e.display_name),'[]'::jsonb)
   FROM public.poraca_knowledge_entities e
   WHERE trim(trailing '/' from lower(e.official_url))=
         trim(trailing '/' from lower(s.url))
     AND e.merged_into_id IS NULL) AS identity_evidence,
   run.run_id AS checked_full_run_id
 FROM focus f JOIN radar_definitivo.sources s USING (source_id)
 CROSS JOIN last_full run
 LEFT JOIN radar_definitivo.source_checks c ON c.source_id=f.source_id AND c.run_id=run.run_id
)
SELECT *,
 CASE
  WHEN latest_check_state IS NULL THEN 'NOT_CHECKED'
  WHEN http_status<>200 OR latest_check_state NOT IN ('ok','index_only') THEN 'TECHNICAL_SOURCE_FAILURE_REVIEW'
  WHEN dated_sessions_last_full>0 THEN 'DATED_SESSIONS_EXTRACTED_NO_AUTOAPPROVAL'
  WHEN expected_intent='DATED_PRESS_AGENDA' THEN 'DATED_AGENDA_EXTRACTION_GAP_P1'
  WHEN expected_intent='MIXED_ART_INSTITUTION_WITH_PROGRAM' THEN
      'PLACE_DOCUMENTED_PROGRAM_UNCAPTURED_P1'
  WHEN entity_matches>0 THEN 'IDENTITY_CAPTURED_REVIEW_REGULAR_OFFER_NOT_EVENT'
  ELSE 'ENTITY_OR_REGULAR_OFFER_RESEARCH_P1'
 END AS operational_diagnosis,
 false AS auto_published,false AS requires_new_cron
FROM measures ORDER BY expected_intent,source_id;