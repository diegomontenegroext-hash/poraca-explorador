-- POR ACA - correction of the actual invariant (not event publication).
-- Existing accepted entity/venue links may refer to unapproved event candidates:
-- their approval means the relation itself is supported, not the event.
-- Only the matched_event_key field is a canonical foreign-reference claim.
-- Therefore disable the too-strict graph-relation trigger installed earlier,
-- and enforce the real invariant for source observations instead.
-- ADDED GUARD + DISABLE WRONG ONE. No user rows modified or deleted.
-- QA branch first; verify 5 cases, then explicitly apply to operational branch.
CREATE OR REPLACE FUNCTION public.poraca_observation_canonical_link_guard_v1()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $func$
BEGIN
  IF NEW.matched_event_key IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM public.radar_agenda_events c
       WHERE c.event_key=NEW.matched_event_key
  ) THEN
      RAISE EXCEPTION 'PORACA_OBSERVATION_MATCHED_EVENT_MISSING_CANONICAL'
          USING ERRCODE='23503',
          HINT='Conservar la observacion y su identidad candidata en original_evidence, sin falso matched_event_key.';
  END IF;
  RETURN NEW;
END;
$func$;

DO $install$
BEGIN
  IF NOT EXISTS (
      SELECT 1 FROM pg_catalog.pg_trigger
       WHERE tgrelid='public.radar_v3_source_observations'::regclass
         AND tgname='poraca_observation_canonical_link_guard_v1'
         AND NOT tgisinternal
  ) THEN
     CREATE TRIGGER poraca_observation_canonical_link_guard_v1
     BEFORE INSERT OR UPDATE OF matched_event_key,reconciliation_state
     ON public.radar_v3_source_observations
     FOR EACH ROW
     EXECUTE FUNCTION public.poraca_observation_canonical_link_guard_v1();
  END IF;
END;
$install$;

-- Prevent regression: relations can be verified independently of a
-- published canonical event; disabling this trigger leaves old data intact.
ALTER TABLE public.poraca_knowledge_relations
  DISABLE TRIGGER poraca_accepted_event_relation_guard_v1;

-- Postconditions: one active observation guard, zero active relation guards.
SELECT (SELECT count(*)::int FROM pg_catalog.pg_trigger
        WHERE tgrelid='public.radar_v3_source_observations'::regclass
          AND tgname='poraca_observation_canonical_link_guard_v1'
          AND tgenabled='O') AS observation_guard,
       (SELECT count(*)::int FROM pg_catalog.pg_trigger
        WHERE tgrelid='public.poraca_knowledge_relations'::regclass
          AND tgname='poraca_accepted_event_relation_guard_v1'
          AND tgenabled='O') AS overrestrictive_relation_guard,
       (SELECT count(*)::int FROM public.radar_v3_source_observations o
        WHERE matched_event_key IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM public.radar_agenda_events c
                          WHERE c.event_key=o.matched_event_key)) AS missing_canonical_matches,
       (SELECT count(*)::int FROM public.poraca_knowledge_relations) AS relation_count,
       (SELECT count(*)::int FROM public.radar_v3_source_observations) AS observation_count;
