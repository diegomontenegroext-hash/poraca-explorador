-- Applied under explicit Por Acá reliability mission, 2026-10-30.
-- Project frosty-union-52906378 / br-mute-recipe-b4odj2bl / neondb ONLY.
-- No default privileges, memberships, ownership or write grants.
BEGIN;
DO $$ BEGIN
 IF current_database() <> 'neondb'
 OR current_setting('neon.project_id',true) IS DISTINCT FROM 'frosty-union-52906378'
 OR current_setting('neon.branch_id',true) IS DISTINCT FROM 'br-mute-recipe-b4odj2bl'
 THEN RAISE EXCEPTION 'Wrong operational database'; END IF;
END $$;
GRANT SELECT ON public.radar_v3_source_observations, public.radar_agenda_events
 TO poraca_definitivo_scope;
COMMIT;
-- Readback must use the runner identity, not the owner:
-- BEGIN; SET LOCAL ROLE poraca_definitivo_scope;
-- SELECT current_user, count(*) FROM public.radar_v3_source_observations GROUP BY 1;
-- SELECT count(*) FROM public.radar_agenda_events; ROLLBACK;
