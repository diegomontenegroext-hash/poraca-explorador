-- POR ACA / READY GATES V1 | 2026-11-01 | SOLO SELECT.
-- Ejecucion: rama Neon OPERATIVA br-mute-recipe-b4odj2bl, base neondb.
-- No instala objetos, no publica, no repara recibos, no ejecuta Radar.
-- Estados por puerta independientes: PASS / PARTIAL / FAIL / NOT_CHECKED.
-- No usar un PASS de lectura como certificacion de API HTTP, SSO ni admision editorial.
WITH latest AS (
  SELECT run_id,mode,status,started_at,finished_at,sources_selected,sources_checked,summary
  FROM radar_definitivo.runs
  WHERE finished_at IS NOT NULL
  ORDER BY finished_at DESC LIMIT 1
),
checks AS (
  SELECT count(*)::int AS checked,
   count(*) FILTER (WHERE status='ok')::int AS ok,
   count(*) FILTER (WHERE status='index_only')::int AS index_only,
   count(*) FILTER (WHERE status NOT IN ('ok','index_only'))::int AS other
  FROM radar_definitivo.source_checks
  WHERE run_id=(SELECT run_id FROM latest)
),
inventory AS (
  SELECT count(*) FILTER (WHERE enabled AND monitoring_mode='fetch')::int AS fetch_enabled,
   count(*) FILTER (WHERE enabled AND monitoring_mode='discover_only')::int AS discover_only,
   count(*) FILTER (WHERE enabled AND monitoring_mode='review')::int AS review_only,
   count(*) FILTER (WHERE enabled AND monitoring_mode='fetch'
      AND (circuit IS NULL OR trim(circuit)=''))::int AS fetch_no_circuit
  FROM radar_definitivo.sources
),
future AS (
  SELECT count(*)::int AS future_staging,
   count(*) FILTER (WHERE coalesce(event_time,'') <> ''
     AND coalesce(venue,'') <> '' AND coalesce(proof_url,'') LIKE 'https://%'
     AND evidence_tier LIKE 'primary_%')::int AS primary_structured_leads
  FROM radar_definitivo.listing_occurrences
  WHERE event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
),
attestation AS (SELECT public.poraca_e2e_integrity_attestation_v1() AS a),
-- Expected historical IDs from independent published acceptance acts.
-- This detects lost checkpoints PLUS lost canon; not an automatic restore.
reference_ledger AS (
 SELECT baseline.event_key,baseline.act_ref,(e.event_key IS NOT NULL) AS preserved
 FROM (VALUES
  ('freezer-brindis-inauguracion-ciudad-de-gatos-2026-11-05',
   'docs/PLAN_EXCELENCIA_BACKLOG_UNICO_20261030.md / 31-10 E2E HTTP'),
  ('cultural-66d110c1850ad58739385baf263c0519',
   'docs/PILOTO_EL_ANIMO_20261101_ADMISION_20261030.md')
 ) AS baseline(event_key,act_ref)
 LEFT JOIN public.radar_agenda_events e ON e.event_key=baseline.event_key
), historical_canaries AS (
 SELECT count(*)::int baseline_count,
   count(*) FILTER (WHERE NOT preserved)::int missing_count,
   coalesce(jsonb_agg(jsonb_build_object('eventKey',event_key,'actRef',act_ref))
      FILTER (WHERE NOT preserved),'[]'::jsonb) AS missing_ids
 FROM reference_ledger
),
identity_key_guard AS (
 SELECT count(*)::int AS active_guard
 FROM pg_catalog.pg_trigger
 WHERE tgrelid='public.radar_agenda_events'::regclass
 AND tgname='poraca_canonical_event_key_immutable_v1'
 AND NOT tgisinternal AND tgenabled='O'
),
security AS (
 SELECT pg_has_role('poraca_definitivo_ingest','neon_superuser','member') AS ingest_elevated,
        pg_has_role('poraca_explorador_writer','neon_superuser','member') AS writer_elevated
),
ctx AS (
 SELECT l.*, c.checked AS check_rows,c.ok,c.index_only,c.other,
    i.fetch_enabled,i.discover_only,i.review_only,i.fetch_no_circuit,
    f.future_staging,f.primary_structured_leads,
    a.a AS integrity,s.ingest_elevated,s.writer_elevated,
    g.baseline_count,g.missing_count,g.missing_ids,k.active_guard
 FROM latest l CROSS JOIN checks c CROSS JOIN inventory i CROSS JOIN future f
 CROSS JOIN attestation a CROSS JOIN security s CROSS JOIN historical_canaries g CROSS JOIN identity_key_guard k
)
SELECT g.ord,g.gate,g.state,g.evidence,g.acceptance,g.next_action
FROM ctx x CROSS JOIN LATERAL (VALUES
(1,'ORCHESTRATION',
 CASE WHEN x.finished_at >= now()-interval '26 hours' THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('runId',x.run_id,'mode',x.mode,'finishedAt',x.finished_at),
 'Existe corrida ordinaria reciente; no prueba estabilidad de 3/7 dias',
 'Mantener tarea unica 05 FULL, 13/21 condicionadas; no lanzar FULL de compensacion'),
(2,'RADAR_RECEIPT',
 CASE WHEN x.sources_selected>0 AND x.sources_checked=x.sources_selected
 AND x.check_rows=x.sources_checked THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('selected',x.sources_selected,'checked',x.sources_checked,'checkRows',x.check_rows,'status',x.status),
 'Todas las fuentes seleccionadas tienen recibo de comprobacion en el run',
 'Corregir solo faltantes comprobados; PASS no implica extraccion'),
(3,'SOURCE_YIELD',
 CASE WHEN x.other>0 OR x.index_only>0 THEN 'PARTIAL'
      WHEN x.ok=x.sources_selected AND x.ok>0 THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('ok',x.ok,'indexOnly',x.index_only,'other',x.other,
 'fetchEnabled',x.fetch_enabled,'discoverOnly',x.discover_only,'reviewOnly',x.review_only),
 'Medir agenda fechada por fuente elegible, separada de indice/entidad/regular',
 'Triar indices por proposito y priorizar El Dia, Teatro Cerca, UNLP, vinos, yoga y talleres'),
(4,'RUN_FUNNEL',
 CASE WHEN (x.summary->'editorial_funnel_v1'->'counts'->>'distinctDetected') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('new',x.summary->'editorial_funnel_v1'->'counts'->'new',
 'seenAgain',x.summary->'editorial_funnel_v1'->'counts'->'seenAgain',
 'potentialDuplicates',x.summary->'editorial_funnel_v1'->'counts'->'possibleDuplicates',
 'originalsComplete',x.summary->'editorial_funnel_v1'->'counts'->'completePrimaryEvidence'),
 'Embudo guardado para el run y conteos separados de aprobacion',
 'Revisar originales individuales priorizados y posibles colisiones sin fusionar horarios'),
(5,'EDITORIAL_ADMISSION',
 'PARTIAL',
 jsonb_build_object('futureStaging',x.future_staging,'primaryStructuredLeads',x.primary_structured_leads,
 'confirmedFuture',x.integrity->'confirmedScheduledFuture','autoPublished',false),
 'Lotes solo con original puntual, horario, sede aprobada, autorizacion y readback idempotente',
 'Preparar lote pequeno de expedientes; no insertar masivamente ni convertir indices en funciones'),
(6,'CANONICAL_INTEGRITY',
 CASE WHEN (x.integrity->>'missingAcceptedReceipts')::int=0
 AND (x.integrity->>'orphanedObservationLinks')::int=0
 AND (x.integrity->>'orphanAcceptedEventRelations')::int=0
 AND (x.integrity->>'missingApprovedEventIds')::int=0
 AND (x.integrity->>'protectionTriggers')::int>=2
 AND x.integrity->>'checkpointSurvivalGuard'='true'
 AND x.baseline_count=2 AND x.missing_count=0 AND x.active_guard=1 THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('decision',x.integrity->'decision',
 'missingReceipts',x.integrity->'missingAcceptedReceipts',
 'orphanedObservations',x.integrity->'orphanedObservationLinks',
 'orphanedAcceptedRelations',x.integrity->'orphanAcceptedEventRelations',
 'missingApprovedIds',x.integrity->'missingApprovedEventIds',
 'guards',x.integrity->'protectionTriggers',
 'eventKeyImmutableTriggerEnabled',x.active_guard,
 'independentHistoricalCanariesExpected',x.baseline_count,
 'independentHistoricalCanariesMissing',x.missing_count,
 'independentHistoricalMissingIds',x.missing_ids),
 'Sin huerfanos, DELETE/TRUNCATE+event_key UPDATE guard activos y 2 canarios conservados',
 'Resolver 5/18/33 y canario Freezer ausente, sin publicar ni fabricar identidades'),
(7,'DIRECT_RADAR_AND_API_HTTP',
 'NOT_CHECKED',
 jsonb_build_object('databaseEvidence','La corrida no certifica HTTP autenticado','httpApi',x.integrity->'httpApi'),
 'Prueba separada de paginacion + API HTTP sobre SHA y datos actuales',
 'Verificar via Vercel autenticado; no inferir HTTP PASS por SELECT de Neon'),
(8,'WEB_SSO_UX',
 'NOT_CHECKED',
 jsonb_build_object('webSso',x.integrity->'webSso'),
 'Chromium autentico 7 perfiles, viewport y capturas sobre SHA exacto',
 'Ejecutar QA estandar #30 sin desactivar SSO; si entorno bloqueado registrar BLOCKED'),
(9,'COVERAGE_BY_CIRCUIT',
 'PARTIAL',
 jsonb_build_object('fetchWithoutCircuit',x.fetch_no_circuit,
 'knownCircuitNotEventGenre',true),
 'Denominador representativo por disciplina y control de fuente primaria',
 'Medir yoga, ceramica, vinos, under, teatro, artes y talleres sin inventar cobertura'),
(10,'LEAST_PRIVILEGE',
 CASE WHEN x.ingest_elevated OR x.writer_elevated THEN 'FAIL' ELSE 'PASS' END,
 jsonb_build_object('ingestNeonSuperuserMember',x.ingest_elevated,
 'writerNeonSuperuserMember',x.writer_elevated),
 'Credenciales operativas sin pertenencia a rol privilegiado ni DDL; ensayar migracion en clon',
 'P0 A17: preparar rol de minimo privilegio y cutover con rollback; no cambiar secretos a ciegas'),
(11,'STABILITY',
 CASE WHEN x.summary->'stability'->'3d'->>'state'='healthy'
 AND x.summary->'stability'->'7d'->>'state'='healthy' THEN 'PASS' ELSE 'PARTIAL' END,
 jsonb_build_object('last3d',x.summary->'stability'->'3d',
                    'last7d',x.summary->'stability'->'7d'),
 'Series completas de 3 y 7 dias sin perdida/duplicacion de calendario',
 'Observar corridas ordinarias con misma consulta; no simular periodos')
) AS g(ord,gate,state,evidence,acceptance,next_action)
ORDER BY g.ord;