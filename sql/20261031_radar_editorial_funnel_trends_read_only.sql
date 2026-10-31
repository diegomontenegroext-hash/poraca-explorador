-- POR ACA / Compare successful post-run editorial funnel snapshots.
-- Read-only; no Neon write, no new cron, no claims of editorial approvals.
-- Historical runs without this report stay 'not_measured', NEVER zero.
WITH measured AS (
 SELECT r.run_id,r.mode,r.status,r.finished_at,
        r.summary->'editorial_funnel_v1' AS funnel,
        r.summary->'editorial_funnel_v1'->'counts' AS counts
 FROM radar_definitivo.runs r
 WHERE r.finished_at IS NOT NULL
   AND r.summary ? 'editorial_funnel_v1'
 ORDER BY r.finished_at DESC
 LIMIT 21
), timeline AS (
 SELECT m.*,
        LAG((m.counts->>'publishedCanonicalSnapshot')::int)
          OVER(ORDER BY m.finished_at) AS previous_canonical_published
 FROM measured m
), by_circuit AS (
 SELECT t.run_id,t.finished_at,r.value->>'rubro' AS rubro,
        r.value->>'label' AS label,
        (r.value->>'distinctDetected')::int detected,
        (r.value->>'new')::int new_occurrences,
        (r.value->>'seenAgain')::int revisited,
        (r.value->>'possibleDuplicates')::int possible_duplicates,
        (r.value->>'pendingEditorial')::int pending,
        (r.value->>'completePrimaryEvidence')::int first_party_ready,
        (r.value->>'matchedPublished')::int matched_published,
        (r.value->>'venueNamesMentioned')::int venue_names
 FROM measured t
 CROSS JOIN LATERAL jsonb_array_elements(t.funnel->'byRubro') r(value)
)
SELECT jsonb_build_object(
 'schema','poraca-radar-editorial-funnel-trend-read-only-v1',
 'runsMeasured',(SELECT count(*) FROM measured),
 'latestRun',(SELECT run_id FROM measured ORDER BY finished_at DESC LIMIT 1),
 'timeline',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'runId',run_id,'at',finished_at,'mode',mode,'status',status,
   'detected',counts->'distinctDetected',
   'new',counts->'new',
   'revisited',counts->'seenAgain',
   'possibleDuplicates',counts->'possibleDuplicates',
   'pendingEditorial',counts->'pendingEditorial',
   'primaryEvidence',counts->'completePrimaryEvidence',
   'matchedPublished',counts->'matchedPublished',
   'venueNames',counts->'venueNamesMentioned',
   'totalConfirmedPublished',counts->'publishedCanonicalSnapshot',
   'changeInPublishedInventory',
     CASE WHEN previous_canonical_published IS NULL THEN NULL
     ELSE (counts->>'publishedCanonicalSnapshot')::int-previous_canonical_published END
 ) ORDER BY finished_at DESC),'[]'::jsonb) FROM timeline),
 'byRubro',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'runId',run_id,'rubro',rubro,'label',label,
   'detected',detected,'new',new_occurrences,'revisited',revisited,
   'possibleDuplicates',possible_duplicates,'pending',pending,
   'primaryEvidence',first_party_ready,'matchedPublished',matched_published,
   'venueNames',venue_names
 ) ORDER BY finished_at DESC,rubro),'[]'::jsonb) FROM by_circuit),
 'limits',jsonb_build_array(
   'La reobservación NO es duplicado',
   'Prueba primaria completa NO es aprobación editorial',
   'La publicación confirmada requiere vínculo a catálogo, no la provoca Radar',
   'El delta de publicaciones es inventario entre cortes, NO autoría de esta corrida',
   'El rubro corresponde al circuito de la fuente; 47 fuentes fetch carecían de etiqueta',
   'Ninguna corrida por sí sola demuestra cobertura exhaustiva de la ciudad'
 ),'readOnly',true
) result;