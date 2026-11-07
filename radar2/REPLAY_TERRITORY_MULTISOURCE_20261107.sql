-- Radar 2 · one-time, guarded and versioned backfill for 99 structured events from 11 non-Eventbrite sources.
-- Run only on frosty-union-52906378 / br-mute-recipe-b4odj2bl / neondb.
-- Preserves original documents, proposal identities, dates, titles, venues and editorial review_state.
-- An observed source locality is NOT independent geographical verification nor editorial approval.
WITH source_rows AS (
 SELECT p.proposal_id,p.title,p.event_date,p.venue,p.document_url,
 p.evidence->>'original_url' AS original_url,
 (p.evidence ? 'territory_resolution') AS prior,
 d.source,((p.evidence->>'evidence')::jsonb)->'location' AS loc
 FROM radar2.proposals p
 JOIN radar2.documents d ON d.url=p.document_url
 WHERE p.evidence->>'kind'='event'
 AND p.event_date>=DATE '2026-11-07'
 AND d.source<>'www.eventbrite.com.ar'
 AND left(trim(p.evidence->>'evidence'),1)='{'
 AND p.evidence->>'evidence' LIKE '%"location"%'
),
fields AS (
 SELECT *,loc->'address'->>'addressLocality' AS locality,
 loc->'address'->>'addressRegion' AS region,
 loc->'address'->>'addressCountry' AS country,
 loc->'address'->>'postalCode' AS postal,
 loc->>'name' AS source_venue,
 loc->'geo'->>'latitude' AS lat,
 loc->'geo'->>'longitude' AS lng
 FROM source_rows
),
signalled AS (
 SELECT *,
 (lower(coalesce(region,''))='caba'
  OR lower(coalesce(region,'')) LIKE '%aut%noma%') AS region_caba,
 (coalesce(postal,'') ~ '^C1[0-9]{3}') AS postal_caba,
 CASE WHEN coalesce(lat,'') ~ '^-?[0-9]+(\\.[0-9]+)?$'
           AND coalesce(lng,'') ~ '^-?[0-9]+(\\.[0-9]+)?$'
  THEN lat::numeric BETWEEN -34.67 AND -34.54
       AND lng::numeric BETWEEN -58.53 AND -58.34
  ELSE FALSE END AS geo_caba
 FROM fields
),
labelled AS (
 SELECT *,
 CASE WHEN lower(trim(coalesce(locality,'')))='la plata'
  AND NOT region_caba AND NOT postal_caba AND NOT geo_caba
  THEN 'source_stated_local' ELSE 'pending' END AS territory_status,
 CASE WHEN lower(trim(coalesce(locality,'')))='la plata'
  AND (region_caba OR postal_caba OR geo_caba)
  THEN 'conflicting_structured_location'
 WHEN lower(trim(coalesce(locality,'')))='la plata'
  THEN 'jsonld_address_locality'
 ELSE 'insufficient_or_conflicting_structured_location' END AS territory_basis
 FROM signalled
),
guard AS (
 SELECT count(*) AS n,
 count(*) FILTER(WHERE territory_status='source_stated_local') AS local_n,
 count(*) FILTER(WHERE territory_status='pending') AS pending_n,
 count(*) FILTER(WHERE territory_basis='conflicting_structured_location') AS conflicts,
 count(*) FILTER(WHERE prior) AS already,
 count(*) FILTER(WHERE venue IS DISTINCT FROM source_venue) AS venue_mismatch,
 count(*) FILTER(WHERE original_url !~ '^https://[^ ]+$') AS invalid_url,
 count(*) FILTER(WHERE country NOT IN ('','AR','Argentina') AND country IS NOT NULL) AS foreign_country,
 count(DISTINCT source) AS source_count
 FROM labelled
),
changed AS (
 UPDATE radar2.proposals p
 SET evidence=p.evidence || jsonb_build_object(
  'territory_resolution',jsonb_build_object(
   'version','territory-jsonld-v1',
   'status',l.territory_status,
   'locality',l.locality,
   'region',l.region,
   'postal_code',l.postal,
   'country',l.country,
   'venue',l.source_venue,
   'source_url',l.original_url,
   'basis',l.territory_basis,
   'area',CASE WHEN l.territory_status='source_stated_local'
      THEN 'La Plata y alrededores' ELSE NULL END,
   'original_preserved',true,
   'editorial_approved',false),
  'territory_revision',jsonb_build_object(
   'version','territory-jsonld-v1',
   'previous','unclassified',
   'basis','primary_event_jsonld_location_not_search_page',
   'source_document',l.document_url,
   'original_url',l.original_url,
   'recorded_at',clock_timestamp(),
   'original_preserved',true,
   'editorial_approved',false))
 FROM labelled l,guard g
 WHERE g.n=99 AND g.local_n=89 AND g.pending_n=10
 AND g.conflicts=3 AND g.already=0 AND g.venue_mismatch=0
 AND g.invalid_url=0 AND g.foreign_country=0 AND g.source_count=11
 AND p.proposal_id=l.proposal_id
 AND p.title=l.title
 AND p.venue IS NOT DISTINCT FROM l.venue
 AND p.event_date=l.event_date
 AND p.document_url=l.document_url
 AND p.evidence->>'original_url'=l.original_url
 AND p.evidence->>'kind'='event'
 AND NOT (p.evidence ? 'territory_resolution')
 RETURNING p.proposal_id,
 p.evidence->'territory_resolution'->>'status' AS status,
 p.evidence->'territory_resolution'->>'basis' AS basis
)
SELECT count(*)::int AS updated,
 count(*) FILTER(WHERE status='source_stated_local')::int AS local,
 count(*) FILTER(WHERE status='pending')::int AS pending,
 count(*) FILTER(WHERE basis='conflicting_structured_location')::int AS contradictions
FROM changed;