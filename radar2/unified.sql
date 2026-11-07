-- Additive contract v1. Originals and old endpoints are retained.
CREATE TABLE IF NOT EXISTS radar2.document_versions (
 url text NOT NULL, sha256 text NOT NULL, payload jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(url,sha256)
);
CREATE TABLE IF NOT EXISTS radar2.proposal_versions (
 proposal_id text NOT NULL, evidence_hash text NOT NULL, payload jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(proposal_id,evidence_hash)
);
INSERT INTO radar2.document_versions(url,sha256,payload) SELECT url,sha256,payload FROM radar2.documents ON CONFLICT DO NOTHING;
INSERT INTO radar2.proposal_versions(proposal_id,evidence_hash,payload) SELECT proposal_id,md5(to_jsonb(p)::text),to_jsonb(p) FROM radar2.proposals p ON CONFLICT DO NOTHING;
CREATE OR REPLACE FUNCTION radar2.preserve_version_v1() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,radar2 AS $$
BEGIN
 IF TG_TABLE_NAME='documents' THEN
  INSERT INTO radar2.document_versions(url,sha256,payload) VALUES(NEW.url,NEW.sha256,NEW.payload) ON CONFLICT DO NOTHING;
 ELSE
  INSERT INTO radar2.proposal_versions(proposal_id,evidence_hash,payload) VALUES(NEW.proposal_id,md5(to_jsonb(NEW)::text),to_jsonb(NEW)) ON CONFLICT DO NOTHING;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE TRIGGER preserve_document_v1 AFTER INSERT OR UPDATE ON radar2.documents FOR EACH ROW EXECUTE FUNCTION radar2.preserve_version_v1();
CREATE OR REPLACE TRIGGER preserve_proposal_v1 AFTER INSERT OR UPDATE ON radar2.proposals FOR EACH ROW EXECUTE FUNCTION radar2.preserve_version_v1();
CREATE OR REPLACE VIEW radar2.contract_v1 AS
WITH visible AS MATERIALIZED (SELECT * FROM radar2.private_discoveries)
SELECT 'document:'||d.url id,'documents' resource,jsonb_build_object(
 'id','document:'||d.url,'url',d.url,'source',d.source,'published_at',d.payload->>'published_at',
 'acquired_at',d.first_seen_at,'observed_at',d.fetched_at,'version',d.sha256,'original',d.payload,
 'stage','document_observation') data FROM radar2.documents d
UNION ALL
SELECT 'proposal:'||p.proposal_id,'proposals',jsonb_build_object(
 'id','proposal:'||p.proposal_id,'title',p.title,'document_id','document:'||p.document_url,
 'date',p.event_date,'time',p.event_time,'timezone','America/Argentina/Buenos_Aires',
 'venue',p.venue,'category',p.category,'state',p.review_state,'evidence',p.evidence,
 'stage','cultural_candidate','publication_approved',false) FROM radar2.proposals p
UNION ALL
SELECT 'occurrence:'||p.proposal_id,'occurrences',jsonb_build_object(
 'id','occurrence:'||p.proposal_id,'event_id','event:'||coalesce(p.evidence->>'event_identity_key',p.proposal_id),
 'announced_date',p.evidence->'announced_date','announced_time',p.evidence->'announced_time',
 'date_resolution',CASE WHEN p.evidence->'ambiguities' ? 'midnight_calendar_day_requires_review' THEN 'announced_day_requires_midnight_review' ELSE 'resolved' END,
 'date',CASE WHEN p.evidence->'ambiguities' ? 'midnight_calendar_day_requires_review' THEN NULL ELSE p.event_date END,'time',p.event_time,'timezone','America/Argentina/Buenos_Aires',
 'event_status',coalesce(p.evidence->>'event_status','scheduled_pending_review'),
 'time_precision',CASE WHEN p.event_time IS NULL THEN 'unknown' ELSE 'minute' END,
 'venue',p.venue,'state',p.review_state,'stage','structured_unapproved_event',
 'evidence',p.evidence,'publication_approved',false) FROM visible p
WHERE p.event_date IS NOT NULL AND coalesce(p.evidence->>'kind','event') IN ('event','program')
UNION ALL
SELECT 'event:'||coalesce(p.evidence->>'event_identity_key',p.proposal_id),'events',jsonb_build_object(
 'id','event:'||coalesce(p.evidence->>'event_identity_key',p.proposal_id),'title',min(p.title),'category',min(p.category),
 'occurrence_ids',jsonb_agg('occurrence:'||p.proposal_id ORDER BY p.event_date,p.event_time,p.proposal_id),
 'document_ids',jsonb_agg(DISTINCT 'document:'||p.document_url),
 'work',CASE WHEN min(p.evidence->>'work_identity_key') IS NOT NULL THEN jsonb_build_object(
   'id','work:'||min(p.evidence->>'work_identity_key'),'title',min(p.title),
   'identity_status','document_scoped_work_pending_review') ELSE NULL END,
 'stage','structured_unapproved_event','state',min(p.review_state),'publication_approved',false,
 'identity_policy',coalesce(min(p.evidence->>'identity_scope'),'conservative_per_occurrence_pending_work_identity_review'))
FROM visible p
WHERE p.event_date IS NOT NULL AND coalesce(p.evidence->>'kind','event') IN ('event','program')
GROUP BY coalesce(p.evidence->>'event_identity_key',p.proposal_id)
UNION ALL
SELECT 'entity:'||n.key,CASE WHEN n.value->>'role'='venue' THEN 'places' ELSE 'actors' END,
 n.value || jsonb_build_object('id','entity:'||n.key,'stage','identified_name_candidate',
 'identity_status','pending_identity_review','verified',false)
FROM radar2.runs r CROSS JOIN LATERAL jsonb_each(coalesce(r.summary->'nodes','{}')) n
WHERE r.run_id='radar2-cultural-memory-state-v1' AND NOT n.value ? 'alias_of'
UNION ALL
SELECT 'relation:'||n.key,'relationships',n.value || jsonb_build_object(
 'id','relation:'||n.key,'verified',false,'original_subject',n.value->>'subject',
 'subject',CASE WHEN representative.proposal_id IS NOT NULL THEN 'event:'||coalesce(representative.event_identity_key,representative.proposal_id) ELSE NULL END,
 'object','entity:'||coalesce(r.summary->'nodes'->(n.value->>'object')->>'alias_of',n.value->>'object'),
 'reference_state',CASE WHEN representative.proposal_id IS NOT NULL THEN 'resolved' ELSE 'pending_event_identity_review' END)
FROM radar2.runs r CROSS JOIN LATERAL jsonb_each(coalesce(r.summary->'relationships','{}')) n
LEFT JOIN radar2.proposals p ON p.proposal_id=substring(n.value->>'subject' from 7)
LEFT JOIN LATERAL (
 SELECT q.proposal_id,q.evidence->>'event_identity_key' event_identity_key FROM visible q
 WHERE q.event_date IS NOT NULL AND coalesce(q.evidence->>'kind','event') IN ('event','program') AND
 (q.proposal_id=coalesce(p.evidence->>'duplicate_of',p.proposal_id) OR
 (q.title=p.title AND q.event_date=p.event_date AND q.event_time IS NOT DISTINCT FROM p.event_time AND q.venue IS NOT DISTINCT FROM p.venue))
 ORDER BY q.proposal_id LIMIT 1
) representative ON true
WHERE r.run_id='radar2-cultural-memory-state-v1' AND n.value->>'status'<>'superseded_by_reconciliation'
UNION ALL
SELECT 'source:'||d.source,'sources',jsonb_build_object('id','source:'||d.source,'name',d.source,
 'document_count',count(*),'last_observed_at',max(d.fetched_at),'identity_status','observed_source')
FROM radar2.documents d GROUP BY d.source
UNION ALL
SELECT 'account:'||n.key,'accounts',n.value || jsonb_build_object('id','account:'||n.key)
FROM radar2.runs r CROSS JOIN LATERAL jsonb_each(coalesce(r.summary->'accounts','{}')) n
WHERE r.run_id='radar2-instagram-rotation-state-v1'
UNION ALL
SELECT 'run:'||run_id,'runs',summary || jsonb_build_object('id','run:'||run_id,'finished_at',finished_at)
FROM radar2.runs WHERE summary->>'status'<>'control_state';
GRANT SELECT ON radar2.contract_v1 TO poraca_motor_qa,poraca_radar_limited_prod;
GRANT SELECT ON radar2.document_versions,radar2.proposal_versions TO poraca_radar_limited_prod;
