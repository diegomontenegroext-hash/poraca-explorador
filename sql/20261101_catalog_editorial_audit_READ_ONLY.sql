-- POR ACA · Asepsia editorial del catálogo, auditoría no destructiva, 2026-11-01.
-- No son PASS/FAIL universales. Los contadores miden colas de revisión;
-- jamás convierten falta de evidencia en baja del lugar ni en publicación.
-- Ejecutar SOLO en Neon operacional br-mute-recipe-b4odj2bl / neondb.
WITH today AS (
 SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS d
),
canonical_duplicate_groups AS (
 SELECT event_date,event_time,lower(btrim(title)) title,
        lower(btrim(venue)) venue,count(*)::int n
 FROM public.radar_agenda_events
 GROUP BY 1,2,3,4 HAVING count(*)>1
), exact_pairs AS (
 SELECT a.event_key a_key,b.event_key b_key
 FROM public.radar_agenda_events a JOIN public.radar_agenda_events b
 ON a.event_key < b.event_key
 AND a.event_date=b.event_date
 AND a.event_time IS NOT DISTINCT FROM b.event_time
 AND lower(trim(a.title))=lower(trim(b.title))
 AND lower(trim(a.venue))=lower(trim(b.venue))
 AND a.source_url=b.source_url
), directory_base AS (
 SELECT e.entity_id FROM public.poraca_knowledge_entities e
 WHERE e.editorial_state='approved_public' AND e.merged_into_id IS NULL
 AND e.entity_kind IN ('venue','project','collective','cycle','school')
 AND e.lifecycle_state NOT IN ('closed_confirmed','merged_duplicate')
 AND e.official_url LIKE 'https://%'
 AND EXISTS (
   SELECT 1 FROM public.poraca_knowledge_assertions a
   WHERE a.entity_id=e.entity_id AND a.review_state='accepted'
   AND a.evidence_tier IN ('first_party','official','institutional')
   AND a.predicate IN ('descripcion','primary_topic','principal_actividad',
     'identidad_del_canal','direccion','ubicacion')
   AND (a.fact_valid_until IS NULL OR a.fact_valid_until>now())
   AND a.evidence_url LIKE 'https://%'
 )
), metrics AS (
 SELECT 'event_canonical_total' AS metric,(SELECT count(*) FROM public.radar_agenda_events)::int AS amount, 'inventory' AS disposition
 UNION ALL SELECT 'event_historical',(SELECT count(*) FROM public.radar_agenda_events WHERE event_date<(SELECT d FROM today))::int,'retain_history'
 UNION ALL SELECT 'event_historical_still_scheduled',(SELECT count(*) FROM public.radar_agenda_events WHERE event_date<(SELECT d FROM today) AND status='scheduled')::int,'presentation_policy_review'
 UNION ALL SELECT 'event_upcoming_unconfirmed',(SELECT count(*) FROM public.radar_agenda_events WHERE event_date>=(SELECT d FROM today) AND verification='to_verify')::int,'validate_individually'
 UNION ALL SELECT 'event_upcoming_release_holds',(SELECT count(*) FROM public.poraca_event_release_readiness_v2 WHERE first_program_day>=(SELECT d FROM today) AND release_quality_gate<>'structurally_reviewed_needs_independent_publication_gate')::int,'review_evidence_not_auto_publish'
 UNION ALL SELECT 'event_exact_duplicate_groups',(SELECT count(*) FROM canonical_duplicate_groups)::int,'review_identity_preserve_history'
 UNION ALL SELECT 'event_exact_duplicate_excess_rows',(SELECT coalesce(sum(n-1),0) FROM canonical_duplicate_groups)::int,'review_identity_preserve_history'
 UNION ALL SELECT 'event_unresolved_exact_duplicate_pairs',(SELECT count(*) FROM exact_pairs p WHERE NOT EXISTS (SELECT 1 FROM public.poraca_event_identity_resolutions_v1 r WHERE r.decision='duplicate_alias' AND ((r.alias_event_key=p.a_key AND r.canonical_event_key=p.b_key) OR (r.alias_event_key=p.b_key AND r.canonical_event_key=p.a_key))))::int,'zero_required_before_publication'
 UNION ALL SELECT 'entities_total',(SELECT count(*) FROM public.poraca_knowledge_entities)::int,'inventory'
 UNION ALL SELECT 'entities_approved',(SELECT count(*) FROM public.poraca_knowledge_entities WHERE editorial_state='approved_public')::int,'inventory'
 UNION ALL SELECT 'entities_internal',(SELECT count(*) FROM public.poraca_knowledge_entities WHERE editorial_state='verified_internal')::int,'retain_research'
 UNION ALL SELECT 'entities_candidate',(SELECT count(*) FROM public.poraca_knowledge_entities WHERE editorial_state='candidate')::int,'retain_research'
 UNION ALL SELECT 'entities_approved_no_activity_date',(SELECT count(*) FROM public.poraca_knowledge_entities WHERE editorial_state='approved_public' AND last_verified_activity_at IS NULL)::int,'verify_activity_by_priority'
 UNION ALL SELECT 'entities_web_mini_eligible',(SELECT count(*) FROM directory_base)::int,'compare_private_directory'
 UNION ALL SELECT 'entities_mini_identity_with_dossier_hold',(SELECT count(*) FROM directory_base d JOIN public.poraca_verified_public_entity_handoff_v1 h USING(entity_id) WHERE h.web_handoff_state='visibility_conflict_hold')::int,'resolve_policy_conflict'
 UNION ALL SELECT 'entities_full_dossier_holds',(SELECT count(*) FROM public.poraca_verified_public_entity_handoff_v1 WHERE web_handoff_state='visibility_conflict_hold')::int,'resolve_policy_conflict'
 UNION ALL SELECT 'staging_unreviewed_listings',(SELECT count(*) FROM radar_definitivo.listing_occurrences WHERE review_state='observed_unverified')::int,'candidate_not_event'
 UNION ALL SELECT 'staging_potential_duplicate_groups',(SELECT count(*) FROM radar_definitivo.possible_duplicate_events)::int,'review_sessions_not_merge_by_title'
)
SELECT metric,amount,disposition,'no_data_writes' AS contract
FROM metrics ORDER BY metric;