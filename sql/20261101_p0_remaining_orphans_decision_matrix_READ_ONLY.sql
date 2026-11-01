-- POR ACA / P0 / GENERALIZED ORPHAN TRIAGE / READ ONLY
-- No event IDs, domain names, dates or sources hardcoded.
-- One row per missing event ID across linked observations and accepted graph relations.
-- Classify evidence, not authorize admission, deletion or silent repair.
-- Archive only if ALL linked observations are past: prevents a mixed old/future
-- event identity from being prematurely marked archival.
WITH obs AS (
 SELECT o.matched_event_key AS event_id,
        count(*)::int AS observation_links,
        max(o.observed_date) AS last_observed_day,
        max((o.observed_date::text || ' ' || o.observed_time)::timestamp)
          FILTER (WHERE o.observed_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$') AS last_valid_start,
        count(*) FILTER (WHERE o.observed_time ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')::int AS timed_observations,
        count(*) FILTER (WHERE o.source_event_url LIKE 'https://%')::int AS original_urls,
        (array_agg(o.observed_title ORDER BY o.observed_date DESC))[1] AS observed_title
 FROM public.radar_v3_source_observations o
 WHERE o.matched_event_key IS NOT NULL
   AND NOT EXISTS(SELECT 1 FROM public.radar_agenda_events c WHERE c.event_key=o.matched_event_key)
 GROUP BY o.matched_event_key
),
rels AS (
 SELECT r.subject_id AS event_id,
        count(*)::int AS accepted_relations,
        count(*) FILTER (WHERE r.predicate='hosted_at')::int AS hosted_at_relations,
        count(*) FILTER (WHERE r.predicate IN ('organized_by','part_of_cycle'))::int AS context_relations,
        bool_or(e.entity_kind='venue' AND e.editorial_state='approved_public') AS has_approved_venue,
        bool_or(e.entity_kind='venue' AND e.editorial_state <> 'approved_public') AS has_nonpublic_venue,
        count(*) FILTER (WHERE r.evidence_url LIKE 'https://%')::int AS relation_evidence_urls,
        string_agg(DISTINCT r.predicate,', ' ORDER BY r.predicate) AS predicates
 FROM public.poraca_knowledge_relations r
 LEFT JOIN public.poraca_knowledge_entities e ON e.entity_id=r.object_id
 WHERE r.subject_kind='event' AND r.review_state='accepted'
   AND NOT EXISTS(SELECT 1 FROM public.radar_agenda_events c WHERE c.event_key=r.subject_id)
 GROUP BY r.subject_id
),
ids AS (SELECT event_id FROM obs UNION SELECT event_id FROM rels),
dated AS (
 SELECT i.event_id,o.observed_title,o.last_observed_day,o.last_valid_start,
        coalesce(o.observation_links,0) AS observation_links,
        coalesce(o.timed_observations,0) AS timed_observations,
        coalesce(o.original_urls,0) AS original_urls,
        coalesce(r.accepted_relations,0) AS accepted_relations,
        coalesce(r.hosted_at_relations,0) AS hosted_at_relations,
        coalesce(r.context_relations,0) AS context_relations,
        coalesce(r.relation_evidence_urls,0) AS relation_evidence_urls,
        coalesce(r.has_approved_venue,false) AS has_approved_venue,
        coalesce(r.has_nonpublic_venue,false) AS has_nonpublic_venue,
        r.predicates,(now() AT TIME ZONE 'America/Argentina/Buenos_Aires') AS now_local
 FROM ids i LEFT JOIN obs o USING(event_id) LEFT JOIN rels r USING(event_id)
)
SELECT event_id,observed_title,last_observed_day,last_valid_start,
       observation_links,timed_observations,original_urls,
       accepted_relations,hosted_at_relations,context_relations,predicates,
       has_approved_venue,has_nonpublic_venue,relation_evidence_urls,
       CASE
         WHEN observation_links=0 THEN 'RESEARCH_RELATION_NO_OBSERVATION'
         WHEN last_observed_day<now_local::date THEN 'ARCHIVE_ONLY_REVIEW'
         WHEN timed_observations=observation_links AND last_valid_start<=now_local THEN 'ARCHIVE_ONLY_REVIEW'
         WHEN has_nonpublic_venue THEN 'HOLD_INTERNAL_VENUE_REVIEW'
         WHEN timed_observations=0 THEN 'HOLD_MISSING_ORIGINAL_TIME'
         WHEN original_urls=0 THEN 'HOLD_NO_FIRST_PARTY_ORIGINAL'
         WHEN NOT has_approved_venue THEN 'HOLD_VENUE_REVIEW'
         ELSE 'INDIVIDUAL_EDITORIAL_REVIEW'
       END AS suggested_next_gate,
       false AS publication_approved,
       false AS authorized_to_write
FROM dated
ORDER BY suggested_next_gate,event_id;
