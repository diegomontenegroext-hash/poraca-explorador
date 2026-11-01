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
security AS (
 SELECT pg_has_role('poraca_definitivo_ingest','neon_superuser','member') AS ingest_elevated,
        pg_has_role('poraca_explorador_writer','neon_superuser','member') AS writer_elevated
),
ctx AS (
 SELECT l.*, c.checked AS check_rows,c.ok,c.index_only,c.other,
    i.fetch_enabled,i.discover_only,i.review_only,i.fetch_no_circuit,
    f.future_staging,f.primary_structured_leads,
    a.a AS integrity,s.ingest_elevated,s.writer_elevated
 FROM latest l CROSS JOIN checks c CROSS JOIN inventory i CROSS JOIN future f
 CROSS JOIN attestation a CROSS JOIN security s
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
 AND x.integrity->>'checkpointSurvivalGuard'='true' THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('decision',x.integrity->'decision',
 'missingReceipts',x.integrity->'missingAcceptedReceipts',
 'orphanedObservations',x.integrity->'orphanedObservationLinks',
 'orphanedAcceptedRelations',x.integrity->'orphanAcceptedEventRelations',
 'missingApprovedIds',x.integrity->'missingApprovedEventIds',
 'guards',x.integrity->'protectionTriggers'),
 '0 recibos/observaciones/relaciones aceptadas huerfanas, guardas activas',
 'Triage de 5/18/33 por clase, sin fabricar canones ni borrar evidencia'),
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