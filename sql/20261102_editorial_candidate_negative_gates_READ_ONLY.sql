-- Por Acá · pruebas negativas del gate de expediente, sin datos nuevos ni DML.
-- Las fuentes hermanas del mismo URL no cuentan como prueba editorial independiente.
WITH cases(case_name,title,event_day,event_time,venue,original_url,proposed_host_id,expected) AS (
 VALUES
 ('original_exact','Malena Muyala','2026-11-21'::date,'22:00','Sala A - Casa Metro',
  'https://casametro.com.ar/evento/malena-muyala/','casa-metro','READY_FOR_EDITORIAL_DECISION'),
 ('clock_mismatch','Malena Muyala','2026-11-21'::date,'20:00','Sala A - Casa Metro',
  'https://casametro.com.ar/evento/malena-muyala/','casa-metro','HOLD_NO_EXACT_ORIGINAL'),
 ('venue_mismatch','Malena Muyala','2026-11-21'::date,'22:00','Sala B - Casa Metro',
  'https://casametro.com.ar/evento/malena-muyala/','casa-metro','HOLD_NO_EXACT_ORIGINAL'),
 ('source_mismatch','Malena Muyala','2026-11-21'::date,'22:00','Sala A - Casa Metro',
  'https://example.invalid/no-original','casa-metro','HOLD_NO_EXACT_ORIGINAL'),
 ('not_approved_host','Malena Muyala','2026-11-21'::date,'22:00','Sala A - Casa Metro',
  'https://casametro.com.ar/evento/malena-muyala/','unapproved-host-fixture','HOLD_HOST_NOT_APPROVED')
), checks AS (
 SELECT c.*,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  WHERE l.title=c.title AND l.event_date=c.event_day AND l.event_time=c.event_time
  AND l.venue=c.venue AND l.proof_url=c.original_url
  AND l.review_state='observed_unverified'
  AND l.evidence_tier IN ('primary_venue','primary_ticket_listing',
    'primary_program_ics','primary_structured_page')) AS primary_observations,
 (SELECT count(*)::int FROM public.poraca_knowledge_entities h
  WHERE h.entity_id=c.proposed_host_id AND h.entity_kind='venue'
  AND h.editorial_state='approved_public' AND h.merged_into_id IS NULL) AS host_approved,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date=c.event_day AND left(coalesce(e.event_time,''),5)=c.event_time
   AND (e.source_url=c.original_url
    OR (lower(btrim(e.title))=lower(btrim(c.title))
      AND lower(btrim(e.venue))=lower(btrim(c.venue))))) AS canon_collision
 FROM cases c
), verdict AS (
 SELECT *,
 CASE WHEN canon_collision>0 THEN 'HOLD_CANONICAL_CONFLICT'
 WHEN host_approved<>1 THEN 'HOLD_HOST_NOT_APPROVED'
 WHEN primary_observations=0 THEN 'HOLD_NO_EXACT_ORIGINAL'
 ELSE 'READY_FOR_EDITORIAL_DECISION' END AS actual
 FROM checks
)
SELECT case_name,expected,actual,expected=actual AS pass,
 primary_observations,host_approved,canon_collision,
 false AS publication_approved, 'READ_ONLY_NO_MUTATION' AS contract
FROM verdict ORDER BY case_name;
