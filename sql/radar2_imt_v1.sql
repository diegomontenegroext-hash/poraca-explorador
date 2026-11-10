-- IMT v1.0: 5 dimensions * 3 equal gates. Score = 10 * PASS / 15.
-- NOT CHECKED earns zero and stays visible. This is evidence coverage, not uptime.
-- READ ONLY. Evaluate on the production branch. A receipt is fresh for 24 h.
-- External gates require independent evidence; SQL alone never upgrades them.
WITH last_full AS (
 SELECT run_id,finished_at,summary AS s FROM radar2.runs
 WHERE run_id LIKE 'radar2-ghdaily-%' AND summary->>'mode'='full'
 ORDER BY finished_at DESC LIMIT 1
), base AS (
 SELECT f.*, now()-finished_at <= interval '24 hours' AS fresh
 FROM (VALUES(1)) anchor(n) LEFT JOIN last_full f ON true
), links AS (
 SELECT count(*) AS proposals,count(d.url) AS linked
 FROM radar2.proposals p LEFT JOIN radar2.documents d ON d.url=p.document_url
), gates AS (
 SELECT b.run_id,b.finished_at,g.* FROM base b CROSS JOIN links
 CROSS JOIN LATERAL (VALUES
 ('R1','21 scheduled slots in 7 complete local days correlated to successful GitHub jobs and receipts',NULL::boolean),
 ('R2','Three consecutive healthy natural cycles after repair',NULL::boolean),
 ('R3','Fresh full receipt within 24 hours',b.fresh),
 ('A1','Fresh FULL discovery phase has a successful terminal status',CASE WHEN b.fresh THEN CASE WHEN s#>>'{source_discovery,status}'='phase_failed' THEN false WHEN s#>>'{source_discovery,status}' IN ('completed','success') THEN true END END),
 ('A2','Fresh FULL has new official Meta documents',CASE WHEN b.fresh AND s#>>'{instagram_official_pilot,method}'='meta_business_discovery' THEN EXISTS(SELECT FROM jsonb_array_elements(s#>'{instagram_official_pilot,results}') r WHERE (r->>'new_documents')::int>0) END),
 ('A3','Unavailable source recovered at next eligible attempt with useful document',NULL::boolean),
 ('I1','Every current proposal joins an existing document',CASE WHEN proposals>0 THEN linked=proposals END),
 ('I2','Fresh FULL readback complete and both positive counts match',CASE WHEN b.fresh THEN s#>>'{neon_readback,status}'='completed' AND (s->>'documents')::int>0 AND (s->>'proposals')::int>0 AND s->>'documents'=s#>>'{neon_readback,documents}' AND s->>'proposals'=s#>>'{neon_readback,proposals}' END),
 ('I3','Replay of interrupted attempt preserves document versions and canonical state',NULL::boolean),
 ('V1','Natural watcher observed and classified a failure before Neon',NULL::boolean),
 ('V2','Fresh FULL gives individual reasons for every check error',CASE WHEN b.fresh AND (s->>'checks_errors')::int>0 THEN (s->>'checks_errors')::int=(SELECT count(*) FROM jsonb_array_elements(s->'checks') c WHERE length(c->>'error')>0) END),
 ('V3','Natural recovery followed by matching API readback',NULL::boolean),
 ('S1','Fresh FULL inspected valid Meta credential with both expiries beyond 14 days',CASE WHEN b.fresh AND s#>>'{credential_health,inspection_status}'='INSPECTED' THEN (s#>>'{credential_health,is_valid}')::boolean AND (s#>>'{credential_health,expires_at}')::timestamptz>now()+interval '14 days' AND (s#>>'{credential_health,data_access_expires_at}')::timestamptz>now()+interval '14 days' END),
 ('S2','No elevated attributes on inventoried current and legacy Radar roles',CASE WHEN (SELECT count(*) FROM pg_roles WHERE rolname IN ('poraca_radar_limited_prod','poraca_explorador_writer','poraca_definitivo_ingest'))=3 THEN NOT EXISTS(SELECT FROM pg_roles WHERE rolname IN ('poraca_radar_limited_prod','poraca_explorador_writer','poraca_definitivo_ingest') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls)) END),
 ('S3','Seven days reconciled billable minutes and requests against approved budget, no duplicate dispatcher',NULL::boolean)
 ) g(id,criterion,result)
)
SELECT id,criterion,CASE WHEN result THEN 'PASS' WHEN NOT result THEN 'FAIL' ELSE 'NOT CHECKED' END AS state,
 run_id AS latest_full, finished_at AS receipt_at,now() AS measured_at,
 round(10.0*count(*) FILTER(WHERE result) OVER()/15,2) AS imt_v1
FROM gates ORDER BY id;
