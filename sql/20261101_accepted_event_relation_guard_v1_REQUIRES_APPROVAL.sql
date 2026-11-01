-- POR ACA / Canonical relation integrity / v1 / 2026-11-01.
-- PREPARED ONLY: requires administrator authorization before applying in QA,
-- negative tests, and explicit production cutover. Do NOT run as Radar.
-- Does not delete, edit, admit or publish any existing rows.
-- Existing accepted dangling relations remain P0 and must be reconciled separately.
-- Only a reviewed relation whose subject is an existing canonical event can
-- become accepted. Research relations can remain proposal/disputed/retracted.
-- Source keys are never inferred; the canonical reference is checked in DB.
CREATE OR REPLACE FUNCTION public.poraca_accepted_event_relation_guard_v1()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $guard$
BEGIN
    IF NEW.review_state='accepted'
       AND NEW.subject_kind='event'
       AND NOT EXISTS (
           SELECT 1 FROM public.radar_agenda_events c
           WHERE c.event_key=NEW.subject_id
       ) THEN
      RAISE EXCEPTION 'PORACA_ACCEPTED_EVENT_RELATION_MISSING_CANONICAL'
        USING ERRCODE='23503',
        HINT='Conservar la evidencia como propuesta; admitir solo despues de crear o reconciliar el evento canonico autorizado.';
    END IF;
    RETURN NEW;
END;
$guard$;

DO $install$
BEGIN
  IF NOT EXISTS (
      SELECT 1 FROM pg_catalog.pg_trigger t
      WHERE t.tgrelid='public.poraca_knowledge_relations'::regclass
        AND t.tgname='poraca_accepted_event_relation_guard_v1'
        AND NOT t.tgisinternal
  ) THEN
    CREATE TRIGGER poraca_accepted_event_relation_guard_v1
    BEFORE INSERT OR UPDATE OF review_state, subject_kind, subject_id
    ON public.poraca_knowledge_relations
    FOR EACH ROW
    EXECUTE FUNCTION public.poraca_accepted_event_relation_guard_v1();
  END IF;
END;
$install$;

-- Readback after approved application. Expect one enabled trigger.
SELECT tgname,tgenabled,pg_get_triggerdef(t.oid) AS definition
FROM pg_catalog.pg_trigger t
WHERE t.tgrelid='public.poraca_knowledge_relations'::regclass
  AND t.tgname='poraca_accepted_event_relation_guard_v1'
  AND NOT t.tgisinternal;
