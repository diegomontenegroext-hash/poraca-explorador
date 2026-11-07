-- Keep deduplication for agenda/event records; official Instagram media must
-- remain individually visible even when titles/dates/venues repeat.
-- Non-destructive, same column names/types, preserves existing grants.
CREATE OR REPLACE VIEW radar2.private_discoveries AS
 WITH ranked AS (
         SELECT p.proposal_id,
            p.document_url,
            p.title,
            p.event_date,
            p.event_time,
            p.venue,
            p.category,
            p.review_state,
            p.first_seen_at,
            p.last_seen_at,
            p.last_run_id,
            p.evidence,
            d.source,
            row_number() OVER (PARTITION BY (CASE WHEN p.evidence->>'acquisition_method'='official_meta_api' THEN p.proposal_id ELSE lower(regexp_replace(p.title, '[^[:alnum:]]'::text, ''::text, 'g'::text)) END), p.event_date, p.event_time, (lower(regexp_replace(COALESCE(p.venue, ''::text), '[^[:alnum:]]'::text, ''::text, 'g'::text))) ORDER BY (
                CASE p.review_state
                    WHEN 'fuente_original'::text THEN 0
                    ELSE 1
                END), p.first_seen_at, p.proposal_id) AS rn,
            count(*) OVER (PARTITION BY (CASE WHEN p.evidence->>'acquisition_method'='official_meta_api' THEN p.proposal_id ELSE lower(regexp_replace(p.title, '[^[:alnum:]]'::text, ''::text, 'g'::text)) END), p.event_date, p.event_time, (lower(regexp_replace(COALESCE(p.venue, ''::text), '[^[:alnum:]]'::text, ''::text, 'g'::text)))) AS source_observations
           FROM radar2.proposals p
             JOIN radar2.documents d ON d.url = p.document_url
          WHERE COALESCE(p.evidence ->> 'duplicate_of'::text, ''::text) = ''::text
        )
 SELECT proposal_id,
    title,
    event_date,
    event_time,
    venue,
    category,
    review_state,
    COALESCE(evidence ->> 'original_url'::text, document_url) AS document_url,
    source,
    first_seen_at,
    last_seen_at,
    evidence,
    source_observations
   FROM ranked
  WHERE rn = 1;;
