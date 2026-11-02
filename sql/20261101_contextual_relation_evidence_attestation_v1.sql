-- POR ACA / Context-only relation evidence attestation, not event publication.
-- Additive SECURITY DEFINER count-only audit. No source rows or secret values exposed.
-- QA + operational branch only; scoped Radar role receives EXECUTE, not SELECT.
-- Accepted relation evidence != approved canonical public event.
CREATE OR REPLACE FUNCTION public.poraca_contextual_relation_evidence_attestation_v1()
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path TO pg_catalog, public, pg_temp
AS $fn$
DECLARE v_result jsonb;
BEGIN
 IF current_database()<>'neondb'
   OR current_setting('neon.project_id',true)<>'frosty-union-52906378'
   OR current_setting('neon.branch_id',true) NOT IN
     ('br-mute-recipe-b4odj2bl','br-icy-night-b4larkc3') THEN
    RAISE EXCEPTION 'PORACA_CONTEXT_AUDIT_WRONG_DATABASE_SCOPE';
 END IF;
 WITH missing_subject AS (
   SELECT r.subject_id,r.object_kind,r.object_id,r.predicate,
          r.evidence_url,r.reviewed_by,r.reviewed_at
   FROM public.poraca_knowledge_relations r
   WHERE r.subject_kind='event' AND r.review_state='accepted'
   AND NOT EXISTS (SELECT 1 FROM public.radar_agenda_events e
                   WHERE e.event_key=r.subject_id)
 ), stats AS (
   SELECT count(*)::int AS context_only_accepted,
     count(DISTINCT subject_id)::int AS context_only_event_keys,
     count(*) FILTER(WHERE evidence_url NOT LIKE 'https://%'
       OR evidence_url IS NULL OR NULLIF(btrim(reviewed_by),'') IS NULL
       OR reviewed_at IS NULL)::int AS context_missing_provenance,
     count(*) FILTER(WHERE predicate NOT IN
       ('hosted_at','organized_by','part_of_cycle','announced_by',
        'performed_by','directed_by','written_by','produced_by',
        'discovered_by','same_as_candidate','based_at','inside','teaches_at'))::int
       AS context_unsupported_predicate,
     count(*) FILTER(WHERE object_kind='event' AND NOT EXISTS
       (SELECT 1 FROM public.radar_agenda_events e
        WHERE e.event_key=object_id))::int AS context_invalid_canonical_object
   FROM missing_subject
 ), object_check AS (
   SELECT count(*)::int AS accepted_missing_event_objects
   FROM public.poraca_knowledge_relations r
   WHERE r.review_state='accepted' AND r.object_kind='event'
     AND NOT EXISTS (SELECT 1 FROM public.radar_agenda_events e
                      WHERE e.event_key=r.object_id)
 )
 SELECT jsonb_build_object(
    'schema','poraca-context-relations-v1',
    'database',current_database(),
    'branchId',current_setting('neon.branch_id',true),
    'contextOnlyAccepted',s.context_only_accepted,
    'contextOnlyEventKeys',s.context_only_event_keys,
    'contextMissingProvenance',s.context_missing_provenance,
    'contextUnsupportedPredicate',s.context_unsupported_predicate,
    'acceptedMissingEventObjects',o.accepted_missing_event_objects,
    'scope','documented_context_not_publication',
    'writesPerformed',false
 ) INTO v_result FROM stats s CROSS JOIN object_check o;
 RETURN v_result;
END;
$fn$;

REVOKE ALL ON FUNCTION public.poraca_contextual_relation_evidence_attestation_v1()
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.poraca_contextual_relation_evidence_attestation_v1()
  TO poraca_definitivo_scope;

-- Run readback as limited role after installation. Do not interpret
-- this function alone as an E2E certification.
SELECT public.poraca_contextual_relation_evidence_attestation_v1();
