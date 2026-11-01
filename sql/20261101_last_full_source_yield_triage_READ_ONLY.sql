-- POR ACA / RADAR F3 / LAST FULL SOURCE TRIAGE / READ ONLY / 2026-11-01
-- Classifies expected output without changing the source's role/mode or
-- pretending index_only means a network error. Recheck after each regular FULL.
-- event_feed priority labels are hints for engineering, not auto-acceptance.
WITH last_full AS (
 SELECT run_id,started_at,finished_at,sources_selected,sources_checked,status
 FROM radar_definitivo.runs
 WHERE mode='full' AND finished_at IS NOT NULL
 ORDER BY started_at DESC LIMIT 1
), checks AS (
 SELECT c.source_id,s.name,s.url,s.kind,s.source_role,s.circuit,
  s.monitoring_mode,c.status,c.http_status,c.error_type,
  c.links_found,c.details_opened,
  CASE
   WHEN s.source_role IN ('local_press','specialized_agenda','official_ticketing',
     'ticketing_primary','ticketing_blocked','official_event_site',
     'original_event_date_check','institutional_program')
     THEN 'DATED_EVENT_SOURCE_TO_REVIEW'
   WHEN s.source_role IN ('original_venue','original_venue_with_official_ticketing',
     'institutional_program_and_community_venue','first_party_institution',
     'official_site','official_museum_archive')
     THEN 'MIXED_PROGRAM_AND_IDENTITY_SOURCE'
   ELSE 'IDENTITY_REGULAR_OR_BACKGROUND_SOURCE'
  END AS source_intent_triage
 FROM radar_definitivo.source_checks c
 JOIN radar_definitivo.sources s ON s.source_id=c.source_id
 WHERE c.run_id=(SELECT run_id FROM last_full)
), classified AS (
 SELECT *,
 CASE
  WHEN status='ok' THEN 'PASS_FOR_LAST_FULL'
  WHEN status='index_only' AND http_status=200
   AND source_intent_triage='DATED_EVENT_SOURCE_TO_REVIEW'
    THEN 'P1_REVIEW_EXTRACTION_OF_EXPLICIT_DATED_SESSIONS'
  WHEN status='index_only' AND http_status=200
   AND source_intent_triage='MIXED_PROGRAM_AND_IDENTITY_SOURCE'
    THEN 'P2_REVIEW_PROGRAM_INDEX_VS_IDENTITY'
  WHEN status='index_only' AND http_status=200
   AND source_intent_triage='IDENTITY_REGULAR_OR_BACKGROUND_SOURCE'
    THEN 'P2_VERIFY_IDENTITY_REGULAR_VALUE_NOT_FAKE_EVENT'
  WHEN status='index_only' THEN 'P1_REVIEW_NON_200_OR_UNKNOWN'
  ELSE 'P0_REVIEW_SOURCE_ERROR'
 END AS next_review_gate
 FROM checks
)
SELECT c.source_id,c.name,c.url,c.kind,c.source_role,c.circuit,c.monitoring_mode,
c.status,c.http_status,c.error_type,c.links_found,c.details_opened,
c.source_intent_triage,c.next_review_gate,
false AS auto_reclassified,false AS event_publication_approved,
(SELECT run_id FROM last_full) AS inspected_full_run
FROM classified c ORDER BY
 CASE c.next_review_gate
 WHEN 'P0_REVIEW_SOURCE_ERROR' THEN 0
 WHEN 'P1_REVIEW_NON_200_OR_UNKNOWN' THEN 1
 WHEN 'P1_REVIEW_EXTRACTION_OF_EXPLICIT_DATED_SESSIONS' THEN 2
 WHEN 'P2_REVIEW_PROGRAM_INDEX_VS_IDENTITY' THEN 3
 WHEN 'P2_VERIFY_IDENTITY_REGULAR_VALUE_NOT_FAKE_EVENT' THEN 4
 ELSE 5 END,c.circuit,c.source_id;
