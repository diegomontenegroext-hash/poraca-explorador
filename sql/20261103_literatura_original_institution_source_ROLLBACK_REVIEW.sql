-- POR ACÁ · CONTINGENCY ONLY — DO NOT RUN WITHOUT ACTUAL SOURCE FAILURE.
-- This is a reversible mode change (not DELETE). Do not rewrite history or
-- cancel an in-progress FULL. Requires explicit operational authorization.
WITH preflight AS (
 SELECT current_setting('neon.project_id',true)='frosty-union-52906378'
   AND current_setting('neon.branch_id',true)='br-mute-recipe-b4odj2bl'
   AS prod_branch_ok
), changed AS (
 UPDATE radar_definitivo.sources s SET monitoring_mode='review',
 next_due_at=now()+interval '30 days'
 FROM preflight p WHERE p.prod_branch_ok
 AND s.source_id='rd-web-biblio-unlp-20261103'
 AND s.url='https://biblio.unlp.edu.ar/'
 AND s.source_role='institutional_program'
 AND s.origin='approved_official_source_20261103'
 AND s.monitoring_mode='fetch'
 RETURNING s.source_id,s.monitoring_mode,s.enabled
)
SELECT (SELECT prod_branch_ok FROM preflight) AS branch_guard_ok,
 count(*)::int AS affected,coalesce(jsonb_agg(to_jsonb(changed)),'[]'::jsonb) AS result,
 false AS source_deleted,false AS events_changed
FROM changed;