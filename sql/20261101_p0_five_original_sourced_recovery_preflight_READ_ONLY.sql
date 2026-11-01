-- POR ACA / P0 5 remaining observed event identities / READ ONLY / 2026-11-01.
-- The 4 rows with official origin were independently checked in external web.
-- QA branch write attempt blocked by safety controls; no insertion performed.
-- Last row's time 20:00 appears in stored internal note, not externally
-- corroborated from original, so it MUST NOT be treated as confirmed.
WITH verified_case(event_key,original,review_class,expect_date,expect_time,venue_entity) AS (
 VALUES
 ('camerata-concertante-city-bell-2026-10-31',
 'https://lumenartis.org/?p=2880&post_type=funcion',
 'ORIGINAL_PAST_ARCHIVE_REVIEW','2026-10-31'::date,'20:00',
 'lumen-artis-teatro-camara'),
 ('teatro-metro-pablo-fabregas-2026-10-31',
 'https://www.teatrometrolp.com.ar/entrada/pablo-fabregas-100961',
 'ORIGINAL_PAST_ARCHIVE_REVIEW','2026-10-31'::date,'21:00',
 'research-teatro-metro-laplata'),
 ('teatro-metro-pequeno-pez-2026-11-01',
 'https://www.teatrometrolp.com.ar/entrada/pequeno-pez-100882',
 'ORIGINAL_FUTURE_INTERNAL_VENUE_REVIEW','2026-11-01'::date,'17:00',
 'research-teatro-metro-laplata'),
 ('teatro-metro-nico-de-tracy-purga-2026-11-05',
 'https://www.teatrometrolp.com.ar/entrada/nico-de-tracy-purga-100764',
 'ORIGINAL_FUTURE_INTERNAL_VENUE_REVIEW','2026-11-05'::date,'21:00',
 'research-teatro-metro-laplata'),
 ('casa-metro-segundo-tiempo-sexteto-2026-10-31',
 'https://casametro.com.ar/categoria-producto/casa-metro/',
 'HOLD_MISSING_CURRENT_ORIGINAL_DETAIL','2026-10-31'::date,NULL,
 'casa-metro')
), checks AS (
SELECT c.*,
 (SELECT count(*)::int FROM public.radar_agenda_events e WHERE e.event_key=c.event_key) AS canonical_count,
 (SELECT count(*)::int FROM public.radar_v3_source_observations o
  WHERE o.matched_event_key=c.event_key AND o.observed_date=c.expect_date
    AND (c.expect_time IS NULL OR o.observed_time=c.expect_time)) AS matching_observations,
 (SELECT count(*)::int FROM public.poraca_knowledge_relations rel
   WHERE rel.subject_kind='event' AND rel.subject_id=c.event_key
    AND rel.predicate='hosted_at' AND rel.review_state='accepted'
    AND rel.object_id=c.venue_entity) AS accepted_venue_relations,
 (SELECT editorial_state FROM public.poraca_knowledge_entities e
    WHERE e.entity_id=c.venue_entity) AS venue_state
FROM verified_case c
)
SELECT *,false AS public_approval_granted,false AS authorized_to_write
FROM checks ORDER BY review_class,event_key;