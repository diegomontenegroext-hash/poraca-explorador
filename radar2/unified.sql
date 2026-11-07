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
 'id','occurrence:'||p.proposal_id,'event_id','event:'||p.proposal_id,
 'date',p.event_date,'time',p.event_time,'timezone','America/Argentina/Buenos_Aires',
 'time_precision',CASE WHEN p.event_time IS NULL THEN 'unknown' ELSE 'minute' END,
 'venue',p.venue,'state',p.review_state,'stage','structured_unapproved_event',
 'evidence',p.evidence,'publication_approved',false) FROM radar2.private_discoveries p
WHERE p.event_date IS NOT NULL AND coalesce(p.evidence->>'kind','event') IN ('event','program')
UNION ALL
SELECT 'event:'||p.proposal_id,'events',jsonb_build_object(
 'id','event:'||p.proposal_id,'title',p.title,'category',p.category,
 'occurrence_ids',jsonb_build_array('occurrence:'||p.proposal_id),
 'document_ids',coalesce((SELECT jsonb_agg(DISTINCT 'document:'||q.document_url) FROM radar2.proposals q
 WHERE q.proposal_id=p.proposal_id OR q.evidence->>'duplicate_of'=p.proposal_id),jsonb_build_array('document:'||p.document_url)),
 'stage','structured_unapproved_event','state',p.review_state,'publication_approved',false,
 'identity_policy','conservative_per_occurrence_pending_work_identity_review') FROM radar2.private_discoveries p
WHERE p.event_date IS NOT NULL AND coalesce(p.evidence->>'kind','event') IN ('event','program')
UNION ALL
SELECT 'entity:'||n.key,CASE WHEN n.value->>'role'='venue' THEN 'places' ELSE 'actors' END,
 n.value || jsonb_build_object('id','entity:'||n.key,'stage','identified_name_candidate',
 'identity_status','pending_identity_review','verified',false)
FROM radar2.runs r CROSS JOIN LATERAL jsonb_each(coalesce(r.summary->'nodes','{}')) n
WHERE r.run_id='radar2-cultural-memory-state-v1' AND NOT n.value ? 'alias_of'
UNION ALL
SELECT 'relation:'||n.key,'relationships',n.value || jsonb_build_object('id','relation:'||n.key,'verified',false)
FROM radar2.runs r CROSS JOIN LATERAL jsonb_each(coalesce(r.summary->'relationships','{}')) n
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
