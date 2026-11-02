-- POR ACA - Correct false linkage states without promoting any event.
-- Apply to existing QA branch first. Production only after exact readback and
-- explicit authorization. Maintains evidence and historical event keys in JSON.
-- Distinguishes confirmed entity/venue from a published canonical event.
-- Does not touch relation review decisions, canonical events, or history rows.
-- One-time known cohort of 5; zero is safe idempotent replay.
DO $reconcile$
DECLARE n_before integer; n_updated integer;
BEGIN
  SELECT count(*)::int INTO n_before
  FROM public.radar_v3_source_observations o
  WHERE o.reconciliation_state='reconciled_linked'
    AND o.matched_event_key IS NOT NULL
    AND o.original_evidence#>>'{reconciliation_v1,publication_approved}'='false'
    AND o.original_evidence#>>'{reconciliation_v1,canonical_target}'=o.matched_event_key
    AND o.original_evidence->'reconciliation_v2' IS NULL
    AND NOT EXISTS (SELECT 1 FROM public.radar_agenda_events c
                    WHERE c.event_key=o.matched_event_key);
  IF n_before NOT IN (0,5) THEN
    RAISE EXCEPTION 'PORACA_UNEXPECTED_UNPUBLISHED_LINK_COHORT_%', n_before
      USING ERRCODE='check_violation';
  END IF;
  UPDATE public.radar_v3_source_observations o
  SET reconciliation_state='observed_unverified',
      matched_event_key=NULL,
      original_evidence=jsonb_set(o.original_evidence,'{reconciliation_v2}',
        jsonb_build_object('action','RECLASSIFY_UNPUBLISHED_CANONICAL_LINK',
          'previous_event_key',o.matched_event_key,
          'previous_reconciliation_state',o.reconciliation_state,
          'publication_approved',false,
          'reason','prior candidate key was not an existing approved canonical',
          'corrected_at',now()),true)
  WHERE o.reconciliation_state='reconciled_linked'
    AND o.matched_event_key IS NOT NULL
    AND o.original_evidence#>>'{reconciliation_v1,publication_approved}'='false'
    AND o.original_evidence#>>'{reconciliation_v1,canonical_target}'=o.matched_event_key
    AND o.original_evidence->'reconciliation_v2' IS NULL
    AND NOT EXISTS (SELECT 1 FROM public.radar_agenda_events c
                    WHERE c.event_key=o.matched_event_key);
  GET DIAGNOSTICS n_updated=ROW_COUNT;
  IF n_updated<>n_before THEN
    RAISE EXCEPTION 'PORACA_UNEXPECTED_RECLASSIFICATION_COUNT_%_%',
                    n_before,n_updated USING ERRCODE='check_violation';
  END IF;
END $reconcile$;

-- Readback: no false canon link, 5 recoverable original identities, no
-- accepted relation altered. Cross-check baseline counters independently.
SELECT (SELECT count(*)::int FROM public.radar_v3_source_observations
        WHERE original_evidence->'reconciliation_v2'->>'action'=
              'RECLASSIFY_UNPUBLISHED_CANONICAL_LINK') AS preserved_corrections,
       (SELECT count(*)::int FROM public.radar_v3_source_observations o
        WHERE o.matched_event_key IS NOT NULL AND NOT EXISTS
          (SELECT 1 FROM public.radar_agenda_events c WHERE c.event_key=o.matched_event_key)
       ) AS remaining_missing_canonical_matches,
       (SELECT count(*)::int FROM public.radar_v3_source_observations) AS observations_total,
       (SELECT count(*)::int FROM public.poraca_knowledge_relations) AS relations_total,
       (SELECT count(*)::int FROM public.radar_agenda_events) AS canonicals_total;
