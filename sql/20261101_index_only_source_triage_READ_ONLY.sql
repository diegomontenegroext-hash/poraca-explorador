-- POR ACA F3 · 2026-11-01. FUENTES "index_only" DEL ULTIMO RUN; SOLO SELECT.
-- Una respuesta HTTP 200 no certifica extraccion ni significa bloqueo/ban.
-- El circuito de la fuente no demuestra el genero de una actividad.
-- Ningun resultado modifica enabled, monitoring_mode, cadencia o categorizacion.
WITH latest AS (
 SELECT run_id,finished_at FROM radar_definitivo.runs
 WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1
), checks AS (
 SELECT c.source_id,c.status,c.http_status,c.links_found,c.details_opened,c.error_type,
   s.name,s.url,s.source_role,s.circuit,s.priority,s.kind,s.monitoring_mode,
   s.next_due_at,s.last_checked_at
 FROM radar_definitivo.source_checks c JOIN latest l ON l.run_id=c.run_id
 JOIN radar_definitivo.sources s ON s.source_id=c.source_id
 WHERE c.status='index_only'
), history AS (
 SELECT c.source_id,
  count(*)::int check_count_7d,
  count(*) FILTER (WHERE c.status='index_only')::int index_only_checks_7d,
  count(*) FILTER (WHERE c.status='ok')::int ok_checks_7d
 FROM radar_definitivo.source_checks c
 WHERE c.checked_at>=now()-interval '7 days'
 GROUP BY c.source_id
), yield AS (
 SELECT o.source_id,
  count(*)::int listings_total,
  count(*) FILTER (WHERE o.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date)::int future_listings,
  max(o.last_seen_at) AS last_yield
 FROM radar_definitivo.listing_occurrences o
 GROUP BY o.source_id
)
SELECT c.name,c.url,c.source_id,c.circuit,c.source_role,c.kind,c.priority,
 c.http_status,c.links_found,c.details_opened,
 coalesce(h.check_count_7d,0) check_count_7d,
 coalesce(h.index_only_checks_7d,0) index_only_checks_7d,
 coalesce(h.ok_checks_7d,0) ok_checks_7d,
 coalesce(y.future_listings,0) future_listings,
 y.last_yield,
 CASE
  WHEN c.http_status IN (401,403,429) THEN 'TECH_HTTP_ACCESS_ISSUE'
  WHEN c.details_opened>0 THEN 'INSPECT_DETAILS_NO_DATED_SESSION'
  WHEN c.links_found>0 THEN 'INSPECT_LINKS_AND_EVENT_DATE_PARSER'
  WHEN c.source_role IN ('original_venue','original_editorial_venue','community_venue',
      'official_museum_archive','first_party_institution','original_organizer')
       THEN 'CHECK_IF_REFERENCE_OR_REGULAR_OFFER_NOT_TIMED_EVENT'
  WHEN c.source_role IN ('ticketing_primary','official_ticketing') THEN 'CHECK_TICKETING_OR_PAST_EVENT'
  ELSE 'REVIEW_SOURCE_PURPOSE_NO_CONCLUSION'
 END AS diagnostic_hypothesis,
 false AS confirmed_root_cause,
 false AS update_authorized
FROM checks c LEFT JOIN history h ON h.source_id=c.source_id
 LEFT JOIN yield y ON y.source_id=c.source_id
ORDER BY c.priority DESC,c.name,c.source_id;