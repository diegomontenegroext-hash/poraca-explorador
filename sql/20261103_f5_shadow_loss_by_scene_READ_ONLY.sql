-- F5 / 2026-11-03 / READ ONLY · SHADOW source loss, NOT an actual outage.
-- Source independence = distinct source root hostname (not distinct source IDs).
-- Full recovery means remaining PRECISE first-party sessions; source index
-- alone is a LEAD, never a confirmed recovered event or an original receipt.
-- No actual source is disabled, no job triggered, no review or publication.
WITH params AS (
 SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today,
        now()-interval '7 days' AS from_time
), source_ok AS (
 SELECT c.source_id,count(*)::int AS ok_checks
 FROM radar_definitivo.source_checks c CROSS JOIN params p
 WHERE c.checked_at>=p.from_time AND c.status='ok'
   AND c.http_status BETWEEN 200 AND 299
 GROUP BY c.source_id
), observed AS (
 SELECT s.circuit,s.source_id,public.poraca_source_host_v1(s.url) AS source_root,
   l.title,l.event_date,l.event_time,l.venue,l.proof_url,
   public.poraca_first_party_event_detail_v1(
     l.evidence_tier,l.proof_method,l.proof_url) AS precise
 FROM radar_definitivo.sources s JOIN source_ok ok USING(source_id)
 JOIN radar_definitivo.listing_occurrences l USING(source_id)
 CROSS JOIN params p
 WHERE s.enabled AND s.monitoring_mode='fetch' AND s.circuit IS NOT NULL
   AND s.circuit<>''
   AND l.event_date BETWEEN p.today AND p.today+45
   AND l.last_seen_at>=p.from_time
   AND l.proof_url LIKE 'https://%'
   AND nullif(btrim(l.title),'') IS NOT NULL
   AND public.poraca_source_host_v1(s.url)<>''
), host_coverage AS (
 SELECT circuit,source_root,
   count(DISTINCT concat_ws('|',lower(btrim(title)),event_date::text,
     left(coalesce(event_time,''),5),proof_url))::int AS dated_leads,
   count(DISTINCT concat_ws('|',lower(btrim(title)),event_date::text,
     left(coalesce(event_time,''),5),proof_url)) FILTER(
     WHERE precise AND event_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'
       AND nullif(btrim(venue),'') IS NOT NULL)::int AS precise_sessions,
   min(proof_url) FILTER(WHERE precise AND event_time ~
       '^([01][0-9]|2[0-3]):[0-5][0-9]$'
       AND nullif(btrim(venue),'') IS NOT NULL) AS precise_proof,
   min(proof_url) AS example_lead,
   string_agg(DISTINCT source_id,',') AS source_ids
 FROM observed GROUP BY circuit,source_root
), ranked AS (
 SELECT *,row_number() OVER(PARTITION BY circuit
   ORDER BY precise_sessions DESC,dated_leads DESC,source_root) AS position
 FROM host_coverage
), outage AS (
 SELECT circuit,source_root AS removed_root,precise_sessions AS removed_precise,
   dated_leads AS removed_leads,precise_proof AS removed_proof
 FROM ranked WHERE position=1
), fallback AS (
 SELECT circuit,count(*)::int AS remaining_domains,
   count(*) FILTER(WHERE precise_sessions>0)::int AS remaining_precise_domains,
   sum(precise_sessions)::int AS remaining_precise_sessions,
   sum(dated_leads)::int AS remaining_dated_leads,
   jsonb_agg(jsonb_build_object('root',source_root,'sourceIds',source_ids,
     'precise',precise_sessions,'datedLeads',dated_leads,
     'proof',coalesce(precise_proof,example_lead))
     ORDER BY precise_sessions DESC,dated_leads DESC,source_root) AS alternatives
 FROM ranked WHERE position>1 GROUP BY circuit
)
SELECT o.circuit,o.removed_root,o.removed_precise,o.removed_leads,
  o.removed_proof,coalesce(f.remaining_domains,0) AS remaining_domains,
  coalesce(f.remaining_precise_domains,0) AS remaining_precise_domains,
  coalesce(f.remaining_precise_sessions,0) AS remaining_precise_sessions,
  coalesce(f.remaining_dated_leads,0) AS remaining_dated_leads,
  coalesce(f.alternatives,'[]'::jsonb) AS alternatives,
  CASE WHEN o.removed_precise>0 AND coalesce(f.remaining_precise_domains,0)>0
       THEN 'SHADOW_PRECISE_COVERAGE_REMAINS'
       WHEN coalesce(f.remaining_dated_leads,0)>0
       THEN 'SHADOW_LEADS_ONLY_NOT_ORIGINAL_RECOVERY'
       ELSE 'SHADOW_NO_CONTINUITY'
  END AS simulated_result,
  false AS actual_outage_verified,
  false AS same_event_recovered,
  false AS editorial_approved,
  false AS f5_certified
FROM outage o LEFT JOIN fallback f USING(circuit)
ORDER BY circuit;