-- POR ACA / 2026-11-03 / INTERNAL EDITORIAL OBSERVATIONS ONLY.
-- Authorized editorial owner, no autoapproval or public/canonical write.
-- Reusable guarded procedure; requested IDs are the reviewed batch.
-- Original: https://www.alternativateatral.com/obra103415-el-animo
-- Explicit dates: Fridays 2026-11-06 and 2026-11-27 at 21:00.
-- QA branch already has both HOLD observations; no duplicate re-insertion.

WITH requested(observation_id) AS (VALUES
 ('obs-stage-f416b398b13ad999fc693019'),
 ('obs-stage-780e4b6e4e4c424c457034f7')
), bridge AS (
-- POR ACA / 03-11-2026 / P0-A: handoff editorial seguro, SOLO SELECT.
-- No crea observaciones, recibos, relaciones ni canónicos. La fila es una
-- PROPUESTA de revisión, incluso cuando la fuente dice primary.
-- REQUIERE LECTURA OWNER/EDITORIAL: las fuentes public.radar_web_sources_v1
-- y entidades public.poraca_knowledge_entities NO son SELECT del rol
-- poraca_definitivo_scope. No ampliar privilegios de Radar para este informe.
-- Ejecutar en neondb / rama operativa; cada revisión requiere humano y
-- escritor autorizado por separado. No usar esta vista como INSERT.
WITH scope AS (
 SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today
), candidates AS (
 SELECT l.listing_key,l.source_id,s.source_role,s.circuit AS source_circuit,l.title,l.event_date,
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
      AND (o.original_evidence->'editorialHandoff'->>'publication' IN ('DO_NOT_APPROVE','DO_NOT_AUTO_APPROVE')
        OR o.reconciliation_state IN ('rejected','conflict','disputed')
        OR coalesce(o.original_evidence->>'conflict','false')<>'false'))
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
  -- Same original + event date but a different observed hour may be doors-vs-show.
  -- Do not duplicate an already-reviewed event at the wrong clock.
  EXISTS (SELECT 1 FROM public.radar_v3_source_observations o
    WHERE o.observed_date=c.event_date
      AND o.source_event_url=c.proof_url
      AND public.poraca_fact_key_v1(o.observed_title)=c.title_key
      AND left(coalesce(o.observed_time,''),5)<>c.event_time)
    AS alternate_time_observation,
  -- Extra tickets (meet/greet, upgrades) require editorial review and must
  -- never be counted as standalone performances merely from a dated page.
  (c.title ~* '^[[:space:]]*(meet[[:space:]]*(&|and|y)[[:space:]]*greet|upgrade[[:space:]]|entrada[[:space:]]+adicional)') AS possible_accessory_ticket,
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
SELECT title,event_date,event_time,venue,proof_url,e.source_id,source_role,
       source_circuit,
       evidence_tier,exact_original_detail,proposed_observation_id,
       venue_labels,legacy_observation_count,explicit_editorial_hold,
       possible_canonical,alternate_time_canonical,alternate_time_observation,
       possible_accessory_ticket,possible_approved_venue_count,
       reg.editorial_source_count,reg.editorial_source_id,reg.editorial_source_url,
       vmatch.editorial_venue_id,
       CASE
         WHEN explicit_editorial_hold THEN 'HOLD_PRIOR_EDITORIAL_DECISION'
         WHEN possible_canonical THEN 'NOOP_POSSIBLE_CANONICAL'
         WHEN alternate_time_canonical OR alternate_time_observation THEN 'HOLD_CLOCK_CONFLICT'
         WHEN possible_accessory_ticket THEN 'HOLD_ADDITIONAL_TICKET'
         WHEN NOT exact_original_detail THEN 'HOLD_ORIGINAL_DETAIL'
         WHEN venue_labels<>1 THEN 'HOLD_VENUE_VARIANTS'
         WHEN legacy_observation_count>0 THEN 'OBSERVATION_ALREADY_PRESENT'
         WHEN reg.editorial_source_count<>1 THEN 'HOLD_AUTHORIZED_SOURCE_MAPPING'
         WHEN vmatch.editorial_venue_id IS NULL THEN 'HOLD_APPROVED_VENUE_MAPPING'
         ELSE 'MANUAL_REVIEW_FOR_OBSERVATION_ONLY'
       END AS editorial_bridge_state,
       CASE
         WHEN explicit_editorial_hold THEN 'HOLD_PRIOR_EDITORIAL_DECISION'
         WHEN possible_canonical THEN 'NOOP_POSSIBLE_CANONICAL'
         WHEN alternate_time_canonical THEN 'HOLD_SCHEDULE_COLLISION'
         WHEN alternate_time_observation THEN 'HOLD_EXISTING_OBSERVATION_OTHER_TIME'
         WHEN possible_accessory_ticket THEN 'HOLD_ACCESSORY_TICKET_NOT_SEPARATE_EVENT'
         WHEN NOT exact_original_detail THEN 'HOLD_ORIGINAL_DETAIL_REQUIRED'
         WHEN venue_labels>1 THEN 'HOLD_VENUE_VARIANTS'
         WHEN possible_approved_venue_count<>1 THEN 'HOLD_VENUE_IDENTITY'
         WHEN legacy_observation_count=0 THEN 'MISSING_EDITORIAL_OBSERVATION'
         ELSE 'OBSERVATION_PRESENT_REVIEW_REQUIRED'
       END AS handoff_gate,
       false AS authorized_to_write,false AS publication_approved
FROM evaluated e
-- Same-host authority is for review only; multiple allowed sources = HOLD.
LEFT JOIN LATERAL (
 SELECT count(*)::int AS editorial_source_count,
        CASE WHEN count(*)=1 THEN min(r.source_id) END AS editorial_source_id,
        CASE WHEN count(*)=1 THEN min(r.source_url) END AS editorial_source_url
 FROM public.radar_web_sources_v1 r
 WHERE r.monitoring_state='enabled'
   AND r.source_role IN ('original_venue','institutional_program','theatre_ticketing')
   AND public.poraca_source_host_v1(r.source_url)=
       public.poraca_source_host_v1(e.proof_url)
) reg ON true
-- Venue must match ONE previously approved identity. Do not create new nodes.
LEFT JOIN LATERAL (
 SELECT CASE WHEN count(*)=1 THEN min(v.entity_id) END AS editorial_venue_id
 FROM public.poraca_knowledge_entities v
 WHERE v.entity_kind='venue' AND v.editorial_state='approved_public'
   AND v.merged_into_id IS NULL
   AND v.lifecycle_state IS DISTINCT FROM 'closed_confirmed'
   AND public.poraca_fact_key_v1(v.display_name)=public.poraca_fact_key_v1(e.venue)
) vmatch ON true
ORDER BY event_date,event_time,title,proof_url LIMIT 200
), candidate AS (
 SELECT x.*,l.listing_key,l.last_run_id,l.last_seen_at AS staging_seen_at,
  v.display_name AS approved_venue_name,
  row_number() OVER(PARTITION BY x.proposed_observation_id ORDER BY l.last_seen_at DESC,l.listing_key) AS rn
 FROM bridge x
 JOIN requested req ON req.observation_id=x.proposed_observation_id
 JOIN radar_definitivo.listing_occurrences l ON l.source_id=x.source_id
  AND l.title=x.title AND l.event_date=x.event_date AND l.event_time=x.event_time
  AND l.proof_url=x.proof_url
 JOIN public.poraca_knowledge_entities v ON v.entity_id=x.editorial_venue_id
  AND v.editorial_state='approved_public' AND v.merged_into_id IS NULL
 WHERE x.editorial_bridge_state='MANUAL_REVIEW_FOR_OBSERVATION_ONLY'
  AND x.editorial_source_count=1 AND x.editorial_source_id IS NOT NULL
  AND x.editorial_venue_id IS NOT NULL AND x.exact_original_detail
  AND l.last_seen_at>=now()-interval '7 days'
  AND x.event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
    AND ((now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+60)
  AND x.evidence_tier IN ('primary_ticket_listing','primary_venue',
   'primary_organizer','primary_program','primary_program_ics','primary_structured_page')
  AND x.source_circuit='teatro' AND x.source_role='theatre_ticketing'
), eligible AS (
 SELECT * FROM candidate c WHERE rn=1
 AND NOT EXISTS(SELECT 1 FROM public.radar_v3_source_observations o
  WHERE o.observed_date=c.event_date AND left(coalesce(o.observed_time,''),5)=c.event_time
  AND public.poraca_fact_key_v1(o.observed_title)=public.poraca_fact_key_v1(c.title)
  AND o.source_event_url=c.proof_url)
 AND NOT EXISTS(SELECT 1 FROM public.radar_agenda_events e
  WHERE e.event_date=c.event_date AND left(coalesce(e.event_time,''),5)=c.event_time
  AND (public.poraca_fact_key_v1(e.title)=public.poraca_fact_key_v1(c.title)
  OR e.source_url=c.proof_url))
), inserted AS (
 INSERT INTO public.radar_v3_source_observations
 (observation_id,origin_source_id,origin_source_url,observed_date,observed_time,
  observed_title,observed_venue,observed_category,source_event_url,reconciliation_state,
  matched_event_key,original_evidence,last_run_id)
 SELECT proposed_observation_id,editorial_source_id,editorial_source_url,
  event_date,event_time,title,approved_venue_name,'teatro',proof_url,
  'observed_unverified',NULL,
  jsonb_build_object(
   'schema','poraca-editorial-handoff-review-v2',
   'conflict','pending_editorial_handoff_review',
   'originalUrl',proof_url,'originalEvidenceTier',evidence_tier,
   'stagingSourceId',source_id,'stagingListingKey',listing_key,
   'stagingLastSeenAt',staging_seen_at,'editorialVenueId',editorial_venue_id,
   'editorialHandoff',jsonb_build_object(
     'publication','DO_NOT_APPROVE','state','PENDING_MANUAL_ORIGINAL_REVIEW',
     'canonicalCreationApproved',false,'requiresNewOriginalReview',true),
   'admission','observation_only_no_publication'),
  last_run_id
 FROM eligible
 ON CONFLICT(observation_id) DO NOTHING
 RETURNING observation_id, observed_date, observed_time, observed_title,
   origin_source_id, reconciliation_state, matched_event_key,
   original_evidence->'editorialHandoff' AS gate
)
SELECT * FROM inserted ORDER BY observed_date;
