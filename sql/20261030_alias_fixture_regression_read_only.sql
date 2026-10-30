-- Real PostgreSQL fixture; no database mutation. Expected c-sab HOLD + c-gato REVIEW only.
WITH fixture_gate(observation_id,observed_title,observed_date,observed_time,observed_venue,source_event_url,mapped_public_source_id,gate_decision,existing_observation_count) AS (VALUES
 ('c-sab','Sindicato Argentino de Boleros',DATE '2026-11-04','21:00','Auditorio Charly García','https://casametro.com.ar/category/','src-one','REVIEW_ORIGINAL_BEFORE_ANY_INSERT',0),
 ('c-gato','Música como en casa – Gato Luna',DATE '2026-12-05','21:00','Casa Metro','https://casametro.com.ar/category/','src-other','REVIEW_ORIGINAL_BEFORE_ANY_INSERT',0),
 ('c-other-time','Sindicato Argentino de Boleros',DATE '2026-11-04','20:00','Casa Metro','https://casametro.com.ar/category/','src-one','REVIEW_ORIGINAL_BEFORE_ANY_INSERT',0),
 ('c-other-day','Sindicato Argentino de Boleros',DATE '2026-11-05','21:00','Casa Metro','https://casametro.com.ar/category/','src-one','REVIEW_ORIGINAL_BEFORE_ANY_INSERT',0)
), fixture_observations(observation_id,origin_source_id,observed_title,observed_date,observed_time,observed_venue,source_event_url,original_evidence) AS (VALUES
 ('obs-sab','src-one','Sindicato Argentino de Boleros',DATE '2026-11-04','21:00','Auditorio Charly García - Casa Metro','https://casametro.com.ar/evento/nombre/','{"editorialHandoff":{"publication":"DO_NOT_APPROVE"}}'::jsonb),
 ('obs-gato','src-one','Música como en casa – Gato Luna',DATE '2026-12-05','21:00','Sala A - Casa Metro','https://casametro.com.ar/evento/gato-luna/','{}'::jsonb)
), candidates AS (
 SELECT m.observation_id,m.observed_title,m.observed_date,m.observed_time,
        m.observed_venue,m.source_event_url,m.mapped_public_source_id,
        m.gate_decision,m.existing_observation_count,
        lower(regexp_replace(translate(coalesce(m.observed_title,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) title_key,
        lower(regexp_replace(translate(coalesce(m.observed_venue,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) venue_key
 FROM fixture_gate m
 WHERE m.existing_observation_count=0 AND m.observed_date IS NOT NULL
   AND m.observed_time IS NOT NULL AND m.mapped_public_source_id IS NOT NULL
), existing AS (
 SELECT o.observation_id,o.origin_source_id,o.observed_title,o.observed_date,
        o.observed_time,o.observed_venue,o.source_event_url,
        coalesce(o.original_evidence::text,'') LIKE '%DO_NOT_APPROVE%' AS editorial_hold,
        lower(regexp_replace(translate(coalesce(o.observed_title,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) title_key,
        lower(regexp_replace(translate(coalesce(o.observed_venue,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) venue_key
 FROM fixture_observations o
)
SELECT c.observation_id,c.gate_decision,e.observation_id AS public_observation_id,
       c.observed_title,c.observed_date::text,c.observed_time,
       c.source_event_url,e.source_event_url AS existing_original_url,
       e.observed_venue AS existing_venue,
       CASE WHEN e.editorial_hold THEN 'HOLD_EDITORIAL_DO_NOT_APPROVE'
            WHEN c.venue_key=e.venue_key OR strpos(c.venue_key,e.venue_key)>0
                 OR strpos(e.venue_key,c.venue_key)>0
            THEN 'REVIEW_EXISTING_OBSERVATION_DO_NOT_INSERT'
            ELSE 'HOLD_VENUE_OR_ROOM_IDENTITY_REVIEW' END AS safe_next_step
FROM candidates c JOIN existing e
ON c.observed_date=e.observed_date
AND left(c.observed_time,5)=left(e.observed_time,5)
AND c.title_key=e.title_key
AND length(c.title_key)>=10
-- Source and venue mismatches are a reason to REVIEW, never proof of novelty.
-- Room compatibility is not an automatic merge: same title can fill two rooms.
ORDER BY c.observed_date,c.observed_time,c.observation_id
LIMIT 600;
