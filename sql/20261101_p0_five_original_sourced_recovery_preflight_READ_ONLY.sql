-- POR ACA / P0 5 remaining observed event identities / READ ONLY / 2026-11-01.
-- All FIVE original dates/clocks now independently checked on organizer sites.
-- Casa Metro official category lists Oct 31 20:00; Revista MuLA corroborates.
-- Its saved observation had NULL time; this is preserved, not rewritten.
-- QA write attempt was blocked by safety controls; no write here.
WITH verified_case(event_key,original,review_class,expect_date,observation_time,verified_original_time,venue_entity) AS (
 VALUES
 ('camerata-concertante-city-bell-2026-10-31',
 'https://lumenartis.org/?p=2880&post_type=funcion',
 'ORIGINAL_PAST_ARCHIVE_REVIEW','2026-10-31'::date,'20:00','20:00',
 'lumen-artis-teatro-camara'),
 ('teatro-metro-pablo-fabregas-2026-10-31',
 'https://www.teatrometrolp.com.ar/entrada/pablo-fabregas-100961',
 'ORIGINAL_PAST_ARCHIVE_REVIEW','2026-10-31'::date,'21:00','21:00',
 'research-teatro-metro-laplata'),
 ('teatro-metro-pequeno-pez-2026-11-01',
 'https://www.teatrometrolp.com.ar/entrada/pequeno-pez-100882',
 'ORIGINAL_FUTURE_INTERNAL_VENUE_REVIEW','2026-11-01'::date,'17:00','17:00',
 'research-teatro-metro-laplata'),
 ('teatro-metro-nico-de-tracy-purga-2026-11-05',
 'https://www.teatrometrolp.com.ar/entrada/nico-de-tracy-purga-100764',
 'ORIGINAL_FUTURE_INTERNAL_VENUE_REVIEW','2026-11-05'::date,'21:00','21:00',
 'research-teatro-metro-laplata'),
 ('casa-metro-segundo-tiempo-sexteto-2026-10-31',
 'https://casametro.com.ar/categoria-producto/casa-metro/',
 'ORIGINAL_PAST_ARCHIVE_REVIEW','2026-10-31'::date,NULL,'20:00',
 'casa-metro')
), checks AS (
SELECT c.*,
 (SELECT count(*)::int FROM public.radar_agenda_events e WHERE e.event_key=c.event_key) AS canonical_count,
 (SELECT count(*)::int FROM public.radar_v3_source_observations o
  WHERE o.matched_event_key=c.event_key AND o.observed_date=c.expect_date
    AND (c.observation_time IS NULL OR o.observed_time=c.observation_time)) AS matching_observations,
 (SELECT count(*)::int FROM public.poraca_knowledge_relations rel
   WHERE rel.subject_kind='event' AND rel.subject_id=c.event_key
    AND rel.predicate='hosted_at' AND rel.review_state='accepted'
    AND rel.object_id=c.venue_entity) AS accepted_venue_relations,
 (SELECT editorial_state FROM public.poraca_knowledge_entities e
    WHERE e.entity_id=c.venue_entity) AS venue_state
FROM verified_case c
)
SELECT *,
 CASE WHEN verified_original_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'
      THEN 'DATE_TIME_VERIFIED_IN_ORIGINAL' ELSE 'TIME_UNPROVEN' END AS origin_date_time_state,
 CASE WHEN event_key='casa-metro-segundo-tiempo-sexteto-2026-10-31'
      THEN 'Original Casa Metro event category + independently dated Revista MuLA; observation time remains NULL'
      ELSE 'Original organizer event page' END AS evidence_note,
 false AS public_approval_granted,false AS authorized_to_write
FROM checks ORDER BY review_class,event_key;