-- POR ACÁ · F5 · ORIGINAL INSTITUCIONAL · CONTROLLED ONE-SOURCE REGISTRATION.
-- User authorized continued project implementation. First run QA branch,
-- then one operational branch only, with readback. INSERT-only / idempotent.
-- Source registry is NOT editorial approval, canonical event or auto-publish.
-- No extra cron; only existing natural FULL/incremental schedules.
-- https://biblio.unlp.edu.ar/feria-de-editoriales-noctambula/ original
-- published 2026-11-02, advertises 2026-11-14 19:00-24:00 as FAIR HOURS.
-- The generic importer stages REVIEW ONLY, never an individual timed show.
WITH env AS (
 SELECT current_setting('neon.project_id',true)='frosty-union-52906378'
    AND current_setting('neon.branch_id',true)
       IN ('br-icy-night-b4larkc3','br-mute-recipe-b4odj2bl')
    AS authorized_branch
), params AS (
 SELECT 'rd-web-biblio-unlp-20261103'::text AS source_id,
 'Biblioteca Pública UNLP · programación institucional'::text AS name,
 'https://biblio.unlp.edu.ar/'::text AS url,
 'institutional_program'::text AS source_role,
 'literatura'::text AS circuit
), ins AS (
 INSERT INTO radar_definitivo.sources(
  source_id,name,url,kind,source_role,circuit,priority,
  monitoring_mode,cadence_hours,enabled,next_due_at,
  consecutive_failures,origin,added_at
 )
 SELECT p.source_id,p.name,p.url,'web',p.source_role,p.circuit,60,
   'fetch',48,true,now(),0,'approved_official_source_20261103',now()
 FROM params p CROSS JOIN env e
 WHERE e.authorized_branch
   AND NOT EXISTS(SELECT 1 FROM radar_definitivo.sources s
     WHERE public.poraca_source_host_v1(s.url)=
           public.poraca_source_host_v1(p.url)
       AND s.source_id<>p.source_id)
 ON CONFLICT DO NOTHING
 RETURNING source_id
)
SELECT (SELECT authorized_branch FROM env) AS branch_guard_ok,
 (SELECT count(*)::int FROM ins) AS newly_registered,
 (SELECT count(*)::int FROM radar_definitivo.sources s JOIN params p
   ON s.source_id=p.source_id
   WHERE s.url=p.url AND s.source_role=p.source_role
     AND s.monitoring_mode='fetch' AND s.enabled
     AND s.circuit=p.circuit) AS registered_expected,
 false AS events_approved,false AS original_fetch_claimed,
 false AS f5_certified,
 'NEXT_NATURAL_RUN_MUST_VERIFY_ORIGINAL'::text AS next_gate;