-- P0 gate function-level preview v2. READ ONLY. Never execute a write.
-- URLs identify evidence; title/date/time/host/room identify potential functions.
WITH raw AS (
 SELECT m.observation_id,m.observed_title,m.observed_date,m.observed_time,
        m.observed_venue,m.source_event_url,m.mapped_public_source_id,
        m.evidence_tier,m.proof_method,m.gate_decision,
        lower(regexp_replace(translate(coalesce(m.observed_title,''),
        'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) AS title_key,
        CASE WHEN lower(m.observed_venue) LIKE '%casa metro%' THEN 'casa-metro'
             WHEN lower(m.observed_venue) LIKE '%teatro metro%' THEN 'teatro-metro'
             WHEN lower(m.observed_venue) LIKE '%teatro argentino%' THEN 'teatro-argentino'
             WHEN lower(m.observed_venue) LIKE '%en eso estamos%' THEN 'en-eso-estamos'
             ELSE lower(regexp_replace(translate(coalesce(m.observed_venue,''),
             'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) END AS host_key,
        CASE WHEN lower(m.observed_venue) LIKE '%auditorio charly garc%' THEN 'auditorio-charly'
             WHEN lower(m.observed_venue) ~ 'sala[[:space:]]+[a-z]([^[:alpha:]]|$)'
             THEN 'sala-'||substring(lower(m.observed_venue) from 'sala[[:space:]]+([a-z])([^[:alpha:]]|$)')
             ELSE NULL END AS room_key,
        (m.evidence_tier LIKE 'primary%' AND m.source_event_url ~*
         '^https://(www[.])?(casametro[.]com[.]ar/evento/[^/?#]+/?|teatrometrolp[.]com[.]ar/entrada/[^/?#]+/?|alternativateatral[.]com/obra[0-9]+[^/?#]*/?)$') AS individual_original
 FROM radar_definitivo.motor_ingest_gate_v1 m
 WHERE m.observation_kind='listing'
   AND m.observed_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
   AND m.mapped_public_source_id IS NOT NULL
   AND m.observed_time IS NOT NULL AND m.observed_venue IS NOT NULL
   AND m.observed_venue !~* '<|>|class[[:space:]]*=|javascript:|document[.]'
), grouped AS (
 SELECT min(observed_title) AS title,observed_date,observed_time,
        mapped_public_source_id,host_key,title_key,
        count(*) AS evidence_rows,
        count(*) FILTER(WHERE NOT individual_original) AS supporting_rows,
        count(DISTINCT source_event_url) FILTER(WHERE individual_original) AS unique_detail_urls,
        count(DISTINCT room_key) FILTER(WHERE individual_original AND room_key IS NOT NULL) AS specific_rooms,
        array_agg(DISTINCT room_key) FILTER(WHERE room_key IS NOT NULL) AS room_labels,
        array_agg(DISTINCT source_event_url) FILTER(WHERE individual_original) AS detail_urls,
        array_agg(DISTINCT gate_decision) AS v1_gate_states
 FROM raw
 GROUP BY observed_date,observed_time,mapped_public_source_id,host_key,title_key
 HAVING count(*) FILTER(WHERE individual_original)>0
), checks AS (
 SELECT g.*,
        (SELECT count(*) FROM public.radar_agenda_events p
         WHERE p.event_date=g.observed_date
           AND left(p.event_time,5)=left(g.observed_time,5)
           AND p.source_url=ANY(g.detail_urls)) AS canonical_by_original,
        (SELECT count(*) FROM public.radar_v3_source_observations p
         WHERE p.observed_date=g.observed_date
           AND left(p.observed_time,5)=left(g.observed_time,5)
           AND p.source_event_url=ANY(g.detail_urls)) AS observation_by_original,
        (SELECT count(*) FROM public.radar_v3_source_observations p
         WHERE p.origin_source_id=g.mapped_public_source_id
           AND p.observed_date=g.observed_date
           AND left(p.observed_time,5)=left(g.observed_time,5)
           AND lower(regexp_replace(translate(coalesce(p.observed_title,''),
              'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g'))=g.title_key
           AND (CASE WHEN lower(coalesce(p.observed_venue,'')) LIKE '%casa metro%' THEN 'casa-metro'
                     WHEN lower(coalesce(p.observed_venue,'')) LIKE '%teatro metro%' THEN 'teatro-metro'
                     WHEN lower(coalesce(p.observed_venue,'')) LIKE '%teatro argentino%' THEN 'teatro-argentino'
                     WHEN lower(coalesce(p.observed_venue,'')) LIKE '%en eso estamos%' THEN 'en-eso-estamos'
                     ELSE lower(regexp_replace(translate(coalesce(p.observed_venue,''),
                     'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) END)=g.host_key
        ) AS observation_by_identity,
        (SELECT count(*) FROM public.radar_agenda_events p
         WHERE p.event_date=g.observed_date
           AND left(p.event_time,5)=left(g.observed_time,5)
           AND lower(regexp_replace(translate(coalesce(p.title,''),
              'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g'))=g.title_key
           AND (CASE WHEN lower(coalesce(p.venue,'')) LIKE '%casa metro%' THEN 'casa-metro'
                     WHEN lower(coalesce(p.venue,'')) LIKE '%teatro metro%' THEN 'teatro-metro'
                     WHEN lower(coalesce(p.venue,'')) LIKE '%teatro argentino%' THEN 'teatro-argentino'
                     WHEN lower(coalesce(p.venue,'')) LIKE '%en eso estamos%' THEN 'en-eso-estamos'
                     ELSE lower(regexp_replace(translate(coalesce(p.venue,''),
                     'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) END)=g.host_key
        ) AS canonical_by_identity,
        (SELECT count(DISTINCT r.host_key) FROM raw r
         WHERE r.observed_date=g.observed_date
           AND r.observed_time=g.observed_time
           AND r.title_key=g.title_key
           AND r.individual_original
           AND r.source_event_url=ANY(g.detail_urls)
           AND r.host_key<>g.host_key) AS other_hosts_same_original,
        (SELECT count(*) FROM public.radar_agenda_events p
         WHERE p.event_date=g.observed_date
           AND left(p.event_time,5)=left(g.observed_time,5)
           AND (CASE WHEN lower(coalesce(p.venue,'')) LIKE '%casa metro%' THEN 'casa-metro'
                     WHEN lower(coalesce(p.venue,'')) LIKE '%teatro metro%' THEN 'teatro-metro'
                     WHEN lower(coalesce(p.venue,'')) LIKE '%teatro argentino%' THEN 'teatro-argentino'
                     WHEN lower(coalesce(p.venue,'')) LIKE '%en eso estamos%' THEN 'en-eso-estamos'
                     ELSE lower(regexp_replace(translate(coalesce(p.venue,''),
                     'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) END)=g.host_key
        ) AS canonical_same_host_clock
 FROM grouped g
)
SELECT title,observed_date,observed_time,mapped_public_source_id,host_key,
       evidence_rows,supporting_rows,unique_detail_urls,specific_rooms,
       room_labels,detail_urls,v1_gate_states,
       canonical_by_original,observation_by_original,
       canonical_by_identity,observation_by_identity,
       other_hosts_same_original,canonical_same_host_clock,
       CASE WHEN other_hosts_same_original>0 THEN 'HOLD_CONFLICTING_HOST_FOR_ORIGINAL'
            WHEN specific_rooms>1 THEN 'HOLD_CONFLICTING_ROOMS'
            WHEN unique_detail_urls>1 THEN 'HOLD_MULTIPLE_INDIVIDUAL_ORIGINALS'
            WHEN canonical_by_original>0 OR canonical_by_identity>0 THEN 'HOLD_CANONICAL_ALREADY_EXISTS'
            WHEN observation_by_original>0 OR observation_by_identity>0 THEN 'HOLD_PUBLIC_OBSERVATION_ALREADY_EXISTS'
            WHEN canonical_same_host_clock>0 THEN 'REVIEW_TITLE_VARIANT_OR_SHARED_VENUE'
            ELSE 'REVIEW_ONE_FUNCTION_PENDING_GATE_AUTHORIZATION' END AS v2_preflight,
       false AS authorized_to_write
FROM checks
ORDER BY observed_date,observed_time,title;