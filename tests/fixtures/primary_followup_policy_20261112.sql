-- Deterministic candidate selection regression. Read-only synthetic rows, no ingestion.
WITH cases(id,day,title,st,checked,secondary_hash,actual_hash,primary_hash,actual_primary,territory,excluded) AS (
 VALUES
 ('unchanged_ready','2026-11-20'::date,'Ready program','PRIMARY_RECEIPT_REVIEW_REQUIRED','2026-11-11T14:00:00Z','s1','s1','p1','p1','source_stated_local',false),
 ('changed_detail','2026-11-20','Changed detail','NO_EXPLICIT_PRIMARY_EVENT_LINK','2026-11-12T17:00:00Z','s1','s2',null,null,'source_stated_local',false),
 ('changed_primary','2026-11-20','Changed primary','PRIMARY_RECEIPT_REVIEW_REQUIRED','2026-11-12T17:00:00Z','s1','s1','p1','p2','source_stated_local',false),
 ('blocked_retry','2026-11-20','Blocked original','PRIMARY_FETCH_BLOCKED','2026-11-11T14:00:00Z','s1','s1',null,null,'source_stated_local',false),
 ('no_receipt','2026-11-20','New original',null,null,null,'s1',null,null,'source_stated_local',false),
 ('canonical','2026-11-20','Canonical concert',null,null,null,'s1',null,null,'source_stated_local',false),
 ('outside','2026-11-20','Outside event',null,null,null,'s1',null,null,'source_stated_outside',false),
 ('excluded','2026-11-20','Excluded event',null,null,null,'s1',null,null,'source_stated_local',true),
 ('stale_no_link','2026-11-20','Old no link','NO_EXPLICIT_PRIMARY_EVENT_LINK','2026-11-04T14:00:00Z','s1','s1',null,null,'source_stated_local',false),
 ('unchanged_conflict','2026-11-20','Conflict event','ORIGINAL_DATE_CONFLICT','2026-11-10T14:00:00Z','s1','s1','p1','p1','source_stated_local',false),
 ('near_recheck','2026-11-13','Near show','NO_EXPLICIT_PRIMARY_EVENT_LINK','2026-11-10T14:00:00Z','s1','s1',null,null,'source_stated_local',false),
 ('bad_timestamp','2026-11-20','Bad timestamp','NO_EXPLICIT_PRIMARY_EVENT_LINK','invalid','s1','s1',null,null,'source_stated_local',false)
), raw AS (
 SELECT *, 'https://agendalaplata.ar/evento/fixture-'||replace(id,'_','-') AS detail,'https://tickets.example.org/event/'||id AS primary_url
 FROM cases
), proposals AS (
 SELECT id AS proposal_id,'https://agendalaplata.ar/?fecha='||day AS document_url,title,day AS event_date,'21:00'::text AS event_time,'Venue local'::text AS venue,'observado_agenda'::text AS review_state,'2026-11-01'::timestamptz AS first_seen_at,
 jsonb_strip_nulls(jsonb_build_object('kind','event','original_url',detail,'territory_resolution',jsonb_build_object('status',territory),'editorial_exclusion',CASE WHEN excluded THEN 'excluded' END,
  'primary_source_followup',CASE WHEN st IS NOT NULL THEN jsonb_build_object('status',st,'checkedAt',checked,'title',title,'date',day::text,'venue','Venue local','secondaryDetailUrl',detail,'secondarySha256',secondary_hash,'primaryUrl',primary_url,'primarySha256',primary_hash) END)) AS evidence
 FROM raw
), documents AS (
 SELECT DISTINCT 'https://agendalaplata.ar/?fecha='||day AS url,'Genda'::text AS source,'listing'::text AS sha256 FROM raw
 UNION ALL SELECT detail,'Secondary',actual_hash FROM raw
 UNION ALL SELECT primary_url,'Ticket',actual_primary FROM raw WHERE actual_primary IS NOT NULL
), events AS (
 SELECT 'Canonical concert'::text AS title,'2026-11-20'::date AS event_date,NULL::text AS event_time,'Venue local'::text AS venue,'https://example.org/original'::text AS source_url,'scheduled'::text AS status,'confirmed'::text AS verification,
 '[{"sourceRole":"first_party","url":"https://example.org/original","reportedTime":"21:00","timeStatus":"reported_unverified"}]'::jsonb AS evidence
), actual AS (
SELECT * FROM (
SELECT selected.*,row_number() OVER (
 PARTITION BY selected.event_day
 ORDER BY selected.first_seen_at,selected.event_time NULLS LAST,selected.proposal_id
) AS day_slot,
 row_number() OVER(PARTITION BY selected.detail_url ORDER BY selected.event_day,selected.first_seen_at,selected.proposal_id) AS detail_slot
FROM (
SELECT DISTINCT ON (p.event_date,p.evidence->>'original_url')
       p.proposal_id,p.first_seen_at,p.title,p.event_date::text event_day,p.event_time,p.venue,
       p.evidence->>'original_url' detail_url,d.source AS secondary_source
FROM proposals p JOIN documents d ON d.url=p.document_url
CROSS JOIN LATERAL (SELECT p.evidence->'primary_source_followup' AS j) receipt
CROSS JOIN LATERAL (SELECT CASE WHEN pg_input_is_valid(receipt.j->>'checkedAt','timestamptz')
 THEN (receipt.j->>'checkedAt')::timestamptz ELSE '2000-01-01T00:00:00+00:00'::timestamptz END AS at) checked
LEFT JOIN documents detail ON detail.url=p.evidence->>'original_url'
LEFT JOIN documents primary_doc ON primary_doc.url=receipt.j->>'primaryUrl'
WHERE p.event_date BETWEEN ('2026-11-12T18:00:00Z'::timestamptz AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
                      AND ('2026-11-12T18:00:00Z'::timestamptz AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+14
  AND (p.event_date>('2026-11-12T18:00:00Z'::timestamptz AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
       OR p.event_time IS NULL
       OR p.event_time>to_char(('2026-11-12T18:00:00Z'::timestamptz AT TIME ZONE 'America/Argentina/Buenos_Aires'),'HH24:MI'))
  AND p.evidence->>'kind'='event'
  AND p.review_state NOT IN ('historico','contradictorio')
  AND coalesce(p.evidence->>'duplicate_of','')=''
  AND coalesce(p.evidence->>'interpretation_superseded_by','')=''
  AND NOT(p.evidence ? 'editorial_exclusion')
  AND coalesce(p.evidence->'territory_resolution'->>'status','')<>'source_stated_outside'
  AND coalesce(p.evidence->>'event_status','') NOT IN ('cancelled','rescheduled_pending_review')
  AND (
    (d.source IN ('Genda','Genda teatro')
      AND p.evidence->>'original_url' ~ '^https://agendalaplata[.]ar/evento/[a-z0-9-]{8,220}$')
    OR (d.source='elevenflow.app'
      AND p.evidence->>'original_url' ~ '^https://elevenflow[.]app/events/[a-z0-9-]{8,220}$')
  )
  -- An observation already bound to a confirmed event does not need another
  -- primary-source search. Require exact receipt or source/date/title/venue.
  AND NOT EXISTS (
   SELECT 1 FROM events a
   WHERE a.event_date=p.event_date AND a.status='scheduled' AND a.verification='confirmed'
    AND (
     EXISTS(SELECT 1 FROM jsonb_array_elements(CASE WHEN jsonb_typeof(a.evidence)='array' THEN a.evidence ELSE '[]'::jsonb END) m
      WHERE m->>'proposalId'=p.proposal_id AND m->>'sourceDocumentSha256'=d.sha256)
     OR (a.source_url IN (p.document_url,p.evidence->>'original_url',receipt.j->>'primaryUrl')
       AND public.poraca_fact_key_v1(a.title)=public.poraca_fact_key_v1(p.title)
       AND length(coalesce(public.poraca_fact_key_v1(p.venue),''))>=4
       AND public.poraca_fact_key_v1(a.venue)=public.poraca_fact_key_v1(p.venue)
       AND a.event_time IS NOT DISTINCT FROM p.event_time)
    )
  )
  -- A unique exact known occurrence is a reconciliation task, not a new
  -- source search. A first-party reported clock is not a verified start.
  AND NOT (
   p.event_time IS NOT NULL AND p.event_time NOT IN ('00:00','23:58','23:59')
   AND length(coalesce(public.poraca_fact_key_v1(p.title),''))>=8
   AND length(coalesce(public.poraca_fact_key_v1(p.venue),''))>=4
   AND 1=(SELECT count(*) FROM events a
    WHERE a.event_date=p.event_date AND a.status='scheduled' AND a.verification='confirmed'
      AND public.poraca_fact_key_v1(a.title)=public.poraca_fact_key_v1(p.title)
      AND public.poraca_fact_key_v1(a.venue)=public.poraca_fact_key_v1(p.venue)
      AND (a.event_time=p.event_time OR (a.event_time IS NULL AND EXISTS(
        SELECT 1 FROM jsonb_array_elements(CASE WHEN jsonb_typeof(a.evidence)='array' THEN a.evidence ELSE '[]'::jsonb END) m
        WHERE m->>'sourceRole'='first_party' AND m->>'url'=a.source_url
          AND m->>'reportedTime'=p.event_time AND m->>'timeStatus'='reported_unverified'
      )))
   )
  )
  -- Reopen immediately only when the occurrence or a stored source version
  -- changes. An unchanged useful receipt is not a daily work item.
  AND (
   receipt.j IS NULL
   OR receipt.j->>'title' IS DISTINCT FROM p.title
   OR receipt.j->>'date' IS DISTINCT FROM p.event_date::text
   OR receipt.j->>'venue' IS DISTINCT FROM p.venue
   OR receipt.j->>'secondaryDetailUrl' IS DISTINCT FROM p.evidence->>'original_url'
   OR (receipt.j ? 'reportedTime' AND receipt.j->>'reportedTime' IS DISTINCT FROM p.event_time)
   OR (detail.sha256 IS NOT NULL AND receipt.j->>'secondarySha256' IS NOT NULL
       AND detail.sha256 IS DISTINCT FROM receipt.j->>'secondarySha256')
   OR (primary_doc.sha256 IS NOT NULL AND receipt.j->>'primarySha256' IS NOT NULL
       AND primary_doc.sha256 IS DISTINCT FROM receipt.j->>'primarySha256')
   OR checked.at < '2026-11-12T18:00:00Z'::timestamptz-CASE
      WHEN receipt.j->>'status' IN ('PRIMARY_RECEIPT_REVIEW_REQUIRED','NO_EXPLICIT_PRIMARY_EVENT_LINK',
        'ORIGINAL_DATE_CONFLICT','ORIGINAL_DATE_NOT_PROVEN','ORIGINAL_IDENTITY_INCOMPLETE')
       THEN CASE WHEN p.event_date<=('2026-11-12T18:00:00Z'::timestamptz AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+1
                  THEN interval '48 hours' ELSE interval '7 days' END
      ELSE interval '24 hours' END
  )
ORDER BY p.event_date,p.evidence->>'original_url',p.proposal_id
) selected
) ranked
-- One distinct source detail before repeating its other dates, and one dated
-- session per day before a second. This keeps repeated exhibition visiting days
-- from exhausting the eight independent primary checks; no date is deleted.
ORDER BY ranked.detail_slot,ranked.day_slot,ranked.event_day,ranked.first_seen_at,ranked.event_time NULLS LAST,ranked.proposal_id
LIMIT 120
)
SELECT array_agg(proposal_id ORDER BY proposal_id) AS actual,
 array_agg(proposal_id ORDER BY proposal_id)=ARRAY['bad_timestamp','blocked_retry','changed_detail','changed_primary','near_recheck','no_receipt','stale_no_link']::text[] AS pass
FROM actual;
