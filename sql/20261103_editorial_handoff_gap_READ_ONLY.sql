-- POR ACA / 03-11-2026 / P0-A: handoff editorial seguro, SOLO SELECT.
-- No crea observaciones, recibos, relaciones ni canónicos. La fila es una
-- PROPUESTA de revisión, incluso cuando la fuente dice primary.
-- Ejecutar en neondb / rama operativa; cada revisión requiere humano y
-- escritor autorizado por separado. No usar esta vista como INSERT.
WITH scope AS (
 SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today
), candidates AS (
 SELECT l.listing_key,l.source_id,s.source_role,l.title,l.event_date,
        l.event_time,l.venue,l.proof_url,l.proof_method,l.evidence_tier,
        l.last_seen_at,public.poraca_fact_key_v1(l.title) AS title_key,
        public.poraca_first_party_event_detail_v1(
          l.evidence_tier,l.proof_method,l.proof_url) AS exact_original_detail,
        row_number() OVER (
          PARTITION BY public.poraca_fact_key_v1(l.title),
            l.event_date,left(l.event_time,5),l.proof_url
          ORDER BY CASE WHEN public.poraca_first_party_event_detail_v1(
            l.evidence_tier,l.proof_method,l.proof_url) THEN 0 ELSE 1 END,
            l.last_seen_at DESC,l.listing_key
        ) AS same_original_rank
 FROM radar_definitivo.listing_occurrences l
 JOIN radar_definitivo.sources s ON s.source_id=l.source_id AND s.enabled
 CROSS JOIN scope d
 WHERE l.event_date BETWEEN d.today AND d.today+45
   AND l.review_state='observed_unverified'
   AND l.event_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'
   AND l.proof_url LIKE 'https://%'
   AND nullif(btrim(l.title),'') IS NOT NULL
   AND nullif(btrim(l.venue),'') IS NOT NULL
   AND l.evidence_tier IN (
     'primary_venue','primary_ticket_listing','primary_program',
     'primary_program_ics','primary_structured_page',
     'primary_organizer','primary_venue_program_index'
   )
), distinct_proposals AS (
 SELECT * FROM candidates WHERE same_original_rank=1
), evaluated AS (
 SELECT c.*,
  concat('obs-stage-',left(md5(concat_ws('|',c.title_key,
      c.event_date::text,left(c.event_time,5),c.proof_url)),24))
    AS proposed_observation_id,
  (SELECT count(DISTINCT public.poraca_fact_key_v1(x.venue))
   FROM candidates x WHERE x.title_key=c.title_key
      AND x.event_date=c.event_date AND x.event_time=c.event_time)
    AS venue_labels,
  (SELECT count(*) FROM public.radar_v3_source_observations o
    WHERE o.observed_date=c.event_date
      AND left(coalesce(o.observed_time,''),5)=c.event_time
      AND public.poraca_fact_key_v1(o.observed_title)=c.title_key
      AND o.source_event_url=c.proof_url)
    AS legacy_observation_count,
  EXISTS (SELECT 1 FROM public.radar_v3_source_observations o
    WHERE o.observed_date=c.event_date
      AND public.poraca_fact_key_v1(o.observed_title)=c.title_key
      AND o.source_event_url=c.proof_url
      AND (o.original_evidence->'editorialHandoff'->>'publication'='DO_NOT_APPROVE'
        OR o.reconciliation_state IN ('rejected','conflict','disputed')
        OR o.original_evidence->>'conflict'='true'))
    AS explicit_editorial_hold,
  EXISTS (SELECT 1 FROM public.radar_agenda_events e
    WHERE e.event_date=c.event_date
      AND left(coalesce(e.event_time,''),5)=c.event_time
      AND (public.poraca_fact_key_v1(e.title)=c.title_key
        OR e.source_url=c.proof_url))
    AS possible_canonical,
  EXISTS (SELECT 1 FROM public.radar_agenda_events e
    WHERE e.event_date=c.event_date
      AND public.poraca_fact_key_v1(e.title)=c.title_key
      AND left(coalesce(e.event_time,''),5)<>c.event_time)
    AS alternate_time_canonical,
  (SELECT count(*) FROM public.poraca_knowledge_entities v
    WHERE v.entity_kind='venue' AND v.editorial_state='approved_public'
      AND v.merged_into_id IS NULL
      AND (
        public.poraca_fact_key_v1(v.display_name)=public.poraca_fact_key_v1(c.venue)
        OR (
          c.source_role IN ('original_venue','original_venue_program',
                            'original_venue_ticketing')
          AND public.poraca_source_host_v1(v.official_url)=
              public.poraca_source_host_v1(c.proof_url)
          AND public.poraca_source_host_v1(c.proof_url)
              NOT IN ('instagram.com','www.instagram.com')
        )
      ))
    AS possible_approved_venue_count
 FROM distinct_proposals c
)
SELECT title,event_date,event_time,venue,proof_url,source_id,source_role,
       evidence_tier,exact_original_detail,proposed_observation_id,
       venue_labels,legacy_observation_count,explicit_editorial_hold,
       possible_canonical,alternate_time_canonical,possible_approved_venue_count,
       CASE
         WHEN explicit_editorial_hold THEN 'HOLD_PRIOR_EDITORIAL_DECISION'
         WHEN possible_canonical THEN 'NOOP_POSSIBLE_CANONICAL'
         WHEN alternate_time_canonical THEN 'HOLD_SCHEDULE_COLLISION'
         WHEN NOT exact_original_detail THEN 'HOLD_ORIGINAL_DETAIL_REQUIRED'
         WHEN venue_labels>1 THEN 'HOLD_VENUE_VARIANTS'
         WHEN possible_approved_venue_count<>1 THEN 'HOLD_VENUE_IDENTITY'
         WHEN legacy_observation_count=0 THEN 'MISSING_EDITORIAL_OBSERVATION'
         ELSE 'OBSERVATION_PRESENT_REVIEW_REQUIRED'
       END AS handoff_gate,
       false AS authorized_to_write,false AS publication_approved
FROM evaluated
ORDER BY event_date,event_time,title,proof_url LIMIT 200;