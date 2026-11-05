-- Same proposal from different agenda documents remains evidenced in staging,
-- but appears once in the private view when title, day, time and venue agree.
CREATE OR REPLACE VIEW radar2.private_discoveries AS
 WITH ranked AS (
 SELECT p.*,d.source,
 row_number() OVER (PARTITION BY lower(regexp_replace(p.title,'[^[:alnum:]]','','g')),p.event_date,p.event_time,lower(regexp_replace(coalesce(p.venue,''),'[^[:alnum:]]','','g')) ORDER BY CASE p.review_state WHEN 'fuente_original' THEN 0 ELSE 1 END,p.first_seen_at,p.proposal_id) AS rn,
 count(*) OVER (PARTITION BY lower(regexp_replace(p.title,'[^[:alnum:]]','','g')),p.event_date,p.event_time,lower(regexp_replace(coalesce(p.venue,''),'[^[:alnum:]]','','g'))) AS source_observations
 FROM radar2.proposals p JOIN radar2.documents d ON d.url=p.document_url
 ) SELECT proposal_id,title,event_date,event_time,venue,category,review_state,
 coalesce(evidence->>'original_url',document_url) AS document_url,source,first_seen_at,last_seen_at,evidence,source_observations
 FROM ranked WHERE rn=1;
