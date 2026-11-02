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
last_full AS (
  SELECT run_id,finished_at,sources_selected,sources_checked,status
  FROM radar_definitivo.runs
  WHERE finished_at IS NOT NULL AND mode='full'
  ORDER BY finished_at DESC LIMIT 1
),
full_checks AS (
  -- Only fetch mode counts toward acquisition health. discover_only seeds are
  -- extra scheduled probes: not event-yield sources and not a transport failure.
  SELECT count(*) FILTER(WHERE s.monitoring_mode='fetch')::int AS checked,
   count(*) FILTER(WHERE s.monitoring_mode='fetch' AND sc.status='ok')::int AS ok,
   count(*) FILTER(WHERE s.monitoring_mode='fetch' AND sc.status='index_only')::int AS index_only,
   count(*) FILTER(WHERE s.monitoring_mode='fetch' AND
     (sc.status NOT IN ('ok','index_only') OR coalesce(sc.error_type,'')<>''
      OR sc.http_status NOT BETWEEN 200 AND 299))::int AS other,
   count(*) FILTER(WHERE s.monitoring_mode='discover_only'
     AND sc.status='ok' AND sc.http_status BETWEEN 200 AND 299)::int AS supplemental
  FROM radar_definitivo.source_checks sc
  LEFT JOIN radar_definitivo.sources s ON s.source_id=sc.source_id
  WHERE sc.run_id=(SELECT run_id FROM last_full)
),
checks AS (
  SELECT count(*)::int AS checked,
   count(*) FILTER (WHERE status='ok')::int AS ok,
   count(*) FILTER (WHERE status='index_only')::int AS index_only,
   count(*) FILTER (WHERE status NOT IN ('ok','index_only')
      OR coalesce(error_type,'')<>'' OR http_status NOT BETWEEN 200 AND 299)::int AS other
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
attestation AS (SELECT public.poraca_e2e_integrity_attestation_v1() AS a,
 public.poraca_contextual_relation_evidence_attestation_v1() AS context_audit),
-- Positive proof of the approved editorial path, independent of historical P0.
-- Presence of a receipt alone does not justify admitting any new candidate.
admission_proof AS (
 SELECT count(*) FILTER (WHERE verification='confirmed'
          AND status IN ('scheduled','rescheduled')
          AND event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
          AND source_url LIKE 'https://%'
          AND jsonb_typeof(evidence)='array'
          AND evidence <> '[]'::jsonb)::int AS confirmed_future_with_evidence,
        count(*) FILTER (WHERE verification='confirmed'
          AND (source_url NOT LIKE 'https://%'
               OR jsonb_typeof(evidence)<>'array'
               OR evidence='[]'::jsonb))::int AS confirmed_missing_evidence
 FROM public.radar_agenda_events
),
-- Inventory and run receipts by circuit, not an unsupported census of
-- every activity in La Plata. Missing categories remain observable gaps.
circuit_checks AS (
 SELECT count(*)::int AS fetch_rows,
        count(DISTINCT NULLIF(btrim(s.circuit),''))::int AS circuits_mapped,
        count(*) FILTER (WHERE s.circuit IS NULL OR btrim(s.circuit)='')::int AS fetch_without_circuit,
        count(*) FILTER (WHERE sc.source_id IS NULL)::int AS fetch_unchecked,
        count(*) FILTER (WHERE sc.source_id IS NOT NULL AND
          (sc.status NOT IN ('ok','index_only') OR coalesce(sc.error_type,'')<>''
            OR sc.http_status NOT BETWEEN 200 AND 299))::int AS fetch_errors,
        count(*) FILTER (WHERE sc.status='ok')::int AS yield_eligible_checks,
        count(*) FILTER (WHERE sc.status='index_only')::int AS index_only_checks
 FROM radar_definitivo.sources s
 LEFT JOIN radar_definitivo.source_checks sc
   ON sc.source_id=s.source_id
      AND sc.run_id=(SELECT run_id FROM last_full)
 WHERE s.enabled AND s.monitoring_mode='fetch'
),
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
-- Independent baseline of 133 hashed canonical event IDs, captured in Git.
-- A deleted canon remains a FAIL even if its acceptance receipt also vanishes.
survival_hashes(event_hash) AS (
 VALUES
  ('0040c1adb16ae1b212c30f18c40c0051'),
  ('0050cce70dac5af0aacca6b87192714d'),
  ('0297ce4dbaf54a40025f8d839bea5c79'),
  ('03f56efc6ac31020a44a34e5a9e5dec3'),
  ('088f00997af9d8b2700edbd101584dbb'),
  ('08b696117134b438b30a6bc861ea258d'),
  ('0a12d6c1bf3ebbcfb85242ced7137aab'),
  ('0a2fabd4debf7d4ce60aeac3d9d235c2'),
  ('0a3a708882044c4ef15b78e420c7217f'),
  ('0a92db65c81aca18150781f2db407cea'),
  ('0b979ecac40418e8756c8cbb7270b259'),
  ('0bdf0d2d168aa957f9bc695bb4cca08a'),
  ('0cc1b1be51d1d048430b0d037b9ef0ae'),
  ('0d0c6e94b50517402eaf706d092b75b1'),
  ('0ea1ceccb597a6362ea22819807aca14'),
  ('12690f48ce86629757b2528d27421dd1'),
  ('1292ea1bea5589b4c7a3a25fa8b22d2a'),
  ('13659bc779de25dfb1118b2d75af1f31'),
  ('1387fd87f82fc0cd8590a2ceec4b685b'),
  ('19d34a5c600b08f9a30208d70c44fc43'),
  ('1b4c05f895a5cecb0096a03fa1244fa7'),
  ('21ed4daccb0637af835d8ed2693ae48e'),
  ('233cd29be805dc7e47ada07613753e55'),
  ('24c79955385115f0f1543c83a1cb9ed3'),
  ('27480f1df265068a594dafeca9710370'),
  ('28d2efe336f39c1f24fa558238fcc4b7'),
  ('2b4d203585f8bbd321c01443b12e20c3'),
  ('2e3f0cb19624c7eec2fdfa4cb8b9789c'),
  ('3137ba2af6aec230ebcd1b444cf97698'),
  ('3546d803baa4a9bd856207c3efed0219'),
  ('35e1ebc63242181a0ccc2c83079114e1'),
  ('396a0064fc2db22369898a59e2bd81dd'),
  ('3ded497570c692a629bbf2207c0eb7be'),
  ('3eaba7e130af05c8c586a2d554835b81'),
  ('3fb480ef82195481b590a0665e575d43'),
  ('40744ed33efc03b5fdf64f4364f8af00'),
  ('436f3bafc771588661ea5776d4d43045'),
  ('4474257dd5faa66b588e424d2e2509a5'),
  ('49e35d536cf505ca1dd5e78874a99476'),
  ('4b843a74fb0f3772c545f6318700a052'),
  ('4d0c84aa62adab61ef1b6508bc6bce02'),
  ('51cabe56b73ad97e78b76b567814bf9a'),
  ('52b19b8ea1f75652fa84c2481d74ce03'),
  ('53e2073b2e6082746ad0cf8794c7f6cd'),
  ('53eb10e2a64939d8499d063e153e27df'),
  ('55ce7bae200942ae774c492d21d6690a'),
  ('55e19042b0c54a432e93d00e31a01dc5'),
  ('59ceda21ec207c57b7ecc1de0300b51c'),
  ('5b755b5d3d28482db3d14acb64e4b468'),
  ('5bd7f6c45b8a3739a0d7dc5650fbda48'),
  ('5e9cf80b72960bce405c99e109133ca1'),
  ('5eb63aacb189fec4673d619a73e45b8c'),
  ('5f56b49ebb8392b55bf460217376181e'),
  ('65de43accceddc0b2f83f8488d2a33d9'),
  ('68f060457633aff69a99620ea0bfd500'),
  ('69835dac89bba4c6ae7f91691dee9f0a'),
  ('69e746d8c461cf44f5c0773721daa248'),
  ('6a19bd20687c6532f529edd7453eedc4'),
  ('6d15bc7d5840395323d12e5fa8eab046'),
  ('6f94675ab1d831104e843273a320c73f'),
  ('705d487aed60cbb2f965b593f3d29831'),
  ('715848005bbb3b1fb6c36b174fad2073'),
  ('7313079f9bc1a851c4be3fe35841b205'),
  ('738f9177864443d9b3e623aa093ada46'),
  ('775c40c625f1ffbe92c1816db0464c51'),
  ('785a918119cd0a510bd0bbb6670caef0'),
  ('7a9c770999358bebc47ff6c148aae403'),
  ('7e67cbb2b370f5bb05f9d9787a519b80'),
  ('7e81adb4cb832221e428e5191708e8c3'),
  ('7f3c5c2f40e3bae7622d6032f77a600e'),
  ('7f67a7f638a967abff29cb0882d985a6'),
  ('7fe99fe7dff9d5c418aaf03067180563'),
  ('89ccac74e80dfa1e052df7577f2c0dea'),
  ('89eab099ccfc84f88f44f6cc62086bb4'),
  ('8bb8c6626983669576267afbbc77dc8d'),
  ('8ca2a9ca42ba87433dbbfbd3be3c3c26'),
  ('902304f13b7156ac46e26b8aba69363e'),
  ('90537ebe608b58f0fa74c43cd9a3c2e2'),
  ('92907b7ff324ffe7464ca6bb6a0e7516'),
  ('930963570e5417b16b829b77ebb12df6'),
  ('99234509747fc46eee7cd14f8c9fb69e'),
  ('998388a0e917b8163b2af512e0331374'),
  ('9bd9509aaee1a82c62b01cd071d1eb1f'),
  ('a05e436c60a221438b42748491c23a30'),
  ('a0948d8ae04424bb7c0c1b989fa2d556'),
  ('a20648afe64c5e3a500c022e7e8008a6'),
  ('a4d332827db1fbb06e75d2f90f61d3ef'),
  ('a562ec26320605cd870cd98a585ed101'),
  ('a72982245e3f1e1d028bbc0433168e08'),
  ('acdbab1c961c13247b595ce35614d83f'),
  ('ad05095318c1f158f7b801267bb7c0d3'),
  ('ae785f9186a4fde9a6c9189b390fc7d2'),
  ('b0fb235ca193c851cb8782b3d49de72d'),
  ('b1a1731c120c1e682275d39ee7bb5400'),
  ('b468a1bb587d6b608713c45df02b54b9'),
  ('b5f7bcb223b4177f29234d82f4067d8c'),
  ('b7af1ad35ec3e87044df8746e2337172'),
  ('b7f2e7ea6dcb9e266dbe914d99905a7b'),
  ('b863faa5058b33b4838e390d15c4ccc0'),
  ('ba31c248be9c2abe3a1c12e1ef20c197'),
  ('bad050fcdf0c1fbb5457f7b35f1fc7bc'),
  ('bae2f2f11435dacd8419cd336bfa414a'),
  ('c2148abe9cf64a4d9bf371c50da63939'),
  ('c3f19df57f65c3289165abbd55f8486a'),
  ('c74660c3e3ccdbad37ac2984351cec65'),
  ('c8128304defdd3d2bec323bddb2c9036'),
  ('c8b44b2fc54a59b035feb5d626814031'),
  ('ca1c5a048244b682092e776f7eb62381'),
  ('ca66e4f5cad4405dc91f130719ea7436'),
  ('cb19678e2484ac14d559934b53cc0ca3'),
  ('d07d5383320cd64fdb9dfd520383ea95'),
  ('d3c9b4ddb8386d1ad1c08b74fdb8c3d0'),
  ('d4b7de301452eeae991501e85e5d298d'),
  ('d7177142ca92f2c0d9983f8d87e4cfb2'),
  ('dbc9f1698175b499e2e13266dd83cd68'),
  ('dca3f4b466bca7a19c1fddb14b8cbfe3'),
  ('dd3d0c7a850dc19ecb5bd57cf2c40141'),
  ('de41f471d04cba7d02e5ca4aab6e773b'),
  ('de827d3490206b863bcc0063092b9e93'),
  ('dfad2ccb5891fb02f074868420c5949a'),
  ('dfd8aaa5dd6127ffe8e6bdbdc5515fb0'),
  ('e028b877884fd672be4eacab9752f7cd'),
  ('e5c82182f49e2aa3780c97be05d7a9c1'),
  ('e6f4eebc71b97ab3fc8a50b77e3c9451'),
  ('e87627643aeeca612677a5295c16ba1b'),
  ('ebcf1d4e0aed0063f026f98bdf209497'),
  ('f0b6444d4c6cc25f7737ab935030c6c1'),
  ('f144433b0143feb6531a033087b39419'),
  ('f416ac41f1bc07269b3bd45ebcb991d6'),
  ('f4ec203f88d34afaaf3036548ebefc13'),
  ('f72625edd53c7c1eca77e40c632df55c'),
  ('fb524d933f58b76ba4560565ceca373d'),
  ('feb7804aca44fcd80cb4b1974f9dbfd8')
), survival_missing AS (
 SELECT count(*)::int AS lost_count
 FROM survival_hashes b
 WHERE NOT EXISTS(SELECT 1 FROM public.radar_agenda_events e
   WHERE md5(e.event_key)=b.event_hash)
),
identity_key_guard AS (
 SELECT count(*)::int AS active_guard
 FROM pg_catalog.pg_trigger
 WHERE tgrelid='public.radar_agenda_events'::regclass
 AND tgname='poraca_canonical_event_key_immutable_v1'
 AND NOT tgisinternal AND tgenabled='O'
),
security AS (
 -- Identity of the CURRENT Radar ingestion credential is also asserted by the
 -- workflow secret binding + run provenance; SQL alone cannot read GitHub secrets.
 -- This query separately checks grants of the deployed limited role and the
 -- residual privilege risk from LEGACY logins (still real until retired).
 SELECT pg_has_role('poraca_definitivo_ingest','neon_superuser','member') AS ingest_elevated,
        pg_has_role('poraca_explorador_writer','neon_superuser','member') AS writer_elevated,
        EXISTS (
          SELECT 1 FROM pg_catalog.pg_roles r
          WHERE r.rolname='poraca_radar_limited_prod'
            AND r.rolcanlogin AND NOT r.rolsuper
            AND NOT r.rolcreatedb AND NOT r.rolcreaterole
            AND NOT pg_has_role(r.rolname,'neon_superuser','member')
            AND has_table_privilege(r.rolname,'radar_definitivo.runs','INSERT,UPDATE')
            AND has_table_privilege(r.rolname,'radar_definitivo.listing_occurrences','INSERT,UPDATE')
            AND NOT has_table_privilege(r.rolname,'public.radar_agenda_events','INSERT,UPDATE,DELETE,TRUNCATE')
        ) AS limited_scope_verified
),
ctx AS (
 SELECT l.*, c.checked AS check_rows,c.ok,c.index_only,c.other,
    i.fetch_enabled,i.discover_only,i.review_only,i.fetch_no_circuit,
    f.future_staging,f.primary_structured_leads,
    ap.confirmed_future_with_evidence,ap.confirmed_missing_evidence,
    cc.fetch_rows,cc.circuits_mapped,cc.fetch_without_circuit,
    cc.fetch_unchecked,cc.fetch_errors,cc.yield_eligible_checks,cc.index_only_checks,
    a.a AS integrity,a.context_audit AS context_audit,
    s.ingest_elevated,s.writer_elevated,s.limited_scope_verified,
    g.baseline_count,g.missing_count,g.missing_ids,k.active_guard,m.lost_count,fc.checked AS full_checked,fc.ok AS full_ok,
    fc.index_only AS full_index_only,fc.other AS full_other,
    fc.supplemental AS full_supplemental,
    lf.run_id AS last_full_run_id,lf.sources_selected AS full_sources_selected,
    lf.sources_checked AS full_sources_checked,lf.finished_at AS full_finished_at
 FROM latest l CROSS JOIN checks c CROSS JOIN inventory i CROSS JOIN future f
 CROSS JOIN admission_proof ap CROSS JOIN circuit_checks cc
 CROSS JOIN attestation a CROSS JOIN security s CROSS JOIN historical_canaries g CROSS JOIN identity_key_guard k CROSS JOIN survival_missing m CROSS JOIN last_full lf CROSS JOIN full_checks fc
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
(3,'SOURCE_FETCH_HEALTH',
 -- Only source transport and check completeness; yield is separate gate 9.
 CASE WHEN x.full_sources_selected>0
        AND x.full_checked=x.fetch_enabled
        AND x.full_checked+x.full_supplemental=x.full_sources_selected
        AND x.full_sources_checked=x.full_sources_selected
        AND x.full_other=0 THEN 'PASS'
      WHEN x.full_checked=0 THEN 'FAIL'
      ELSE 'PARTIAL' END,
 jsonb_build_object('latestRunId',x.run_id,'latestOk',x.ok,
 'lastFullRunId',x.last_full_run_id,'lastFullAt',x.full_finished_at,
 'lastFullSelected',x.full_sources_selected,'lastFullCheckRows',x.full_checked,
 'lastFullOk',x.full_ok,'lastFullIndexOnly',x.full_index_only,
 'lastFullOther',x.full_other,'lastFullSupplemental',x.full_supplemental,
 'fetchEnabled',x.fetch_enabled,
 'discoverOnly',x.discover_only,'reviewOnly',x.review_only),
 'Todas las fuentes seleccionadas revisadas sin errores HTTP/operativos; index_only no prueba produccion de eventos',
 'El rendimiento por circuito sigue en COVERAGE_BY_CIRCUIT y nunca se infiere de HTTP 200'),
(4,'RUN_FUNNEL',
 CASE WHEN (x.summary->'editorial_funnel_v1'->'counts'->>'distinctDetected') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('new',x.summary->'editorial_funnel_v1'->'counts'->'new',
 'seenAgain',x.summary->'editorial_funnel_v1'->'counts'->'seenAgain',
 'potentialDuplicates',x.summary->'editorial_funnel_v1'->'counts'->'possibleDuplicates',
 'originalsComplete',x.summary->'editorial_funnel_v1'->'counts'->'completePrimaryEvidence'),
 'Embudo guardado para el run y conteos separados de aprobacion',
 'Revisar originales individuales priorizados y posibles colisiones sin fusionar horarios'),
(5,'EDITORIAL_ADMISSION',
 CASE WHEN (x.integrity->>'acceptedReceipts')::int > 0
        AND (x.integrity->>'missingAcceptedReceipts')::int=0
        AND x.confirmed_future_with_evidence>0
        AND x.confirmed_missing_evidence=0 THEN 'PASS'
      ELSE 'PARTIAL' END,
 jsonb_build_object('futureStaging',x.future_staging,'primaryStructuredLeads',x.primary_structured_leads,
 'acceptedReceipts',x.integrity->'acceptedReceipts',
 'missingAcceptedReceipts',x.integrity->'missingAcceptedReceipts',
 'confirmedFutureWithEvidence',x.confirmed_future_with_evidence,
 'confirmedMissingEvidence',x.confirmed_missing_evidence,
 'autoPublicationAuthorized',false,'historicalIntegritySeparatelyChecked',true),
 'Ruta de admision probada con recibos, canon futuro confirmado y evidencia; no acredita integridad historica ni autoriza autopublicacion',
 'Si no hay recibos o evidencia valida, preparar un expediente individual con revision y readback; nunca publicar masivamente'),
(6,'CANONICAL_INTEGRITY',
 CASE WHEN (x.integrity->>'missingAcceptedReceipts')::int=0
 AND (x.integrity->>'orphanedObservationLinks')::int=0
 AND (x.integrity->>'missingApprovedEventIds')::int=0
 AND (x.integrity->>'orphanAcceptedEventRelations')::int=0
 AND (x.integrity->>'missingAcceptedRelationEventIds')::int=0
 AND (SELECT count(*) FROM pg_catalog.pg_trigger
      WHERE tgrelid='public.poraca_knowledge_relations'::regclass
      AND tgname='poraca_accepted_event_relation_guard_v1'
      AND tgenabled='O' AND NOT tgisinternal)=1
 AND x.context_audit->>'schema'='poraca-context-relations-v1'
 AND x.context_audit->>'branchId'='br-mute-recipe-b4odj2bl'
 AND x.context_audit->>'scope'='documented_context_not_publication'
 AND x.context_audit->>'writesPerformed'='false'
 AND (x.context_audit->>'contextOnlyAccepted')::int =
     (x.integrity->>'orphanAcceptedEventRelations')::int
 AND (x.context_audit->>'contextOnlyEventKeys')::int =
     (x.integrity->>'missingAcceptedRelationEventIds')::int
 AND (x.context_audit->>'contextMissingProvenance')::int=0
 AND (x.context_audit->>'contextUnsupportedPredicate')::int=0
 AND (x.context_audit->>'acceptedMissingEventObjects')::int=0
 AND (x.integrity->>'protectionTriggers')::int>=2
 AND x.integrity->>'checkpointSurvivalGuard'='true'
 AND x.baseline_count=2 AND x.missing_count=0 AND x.active_guard=1
 AND x.lost_count=0 THEN 'PASS' ELSE 'FAIL' END,
 jsonb_build_object('auditScope','CANONICAL_SURVIVAL_AND_CONTEXTUAL_RELATION_RECONCILIATION',
 'missingReceipts',x.integrity->'missingAcceptedReceipts',
 'orphanedObservations',x.integrity->'orphanedObservationLinks',
 'contextOnlyAcceptedRelations',x.integrity->'orphanAcceptedEventRelations',
 'contextOnlyEventKeys',x.integrity->'missingAcceptedRelationEventIds',
 'contextEvidenceAudit',x.context_audit,
 'legacyV1Decision',x.integrity->'decision',
 'missingApprovedIds',x.integrity->'missingApprovedEventIds',
 'guards',x.integrity->'protectionTriggers',
 'eventKeyImmutableTriggerEnabled',x.active_guard,
 'acceptedEventRelationGuardEnabled',(SELECT count(*) FROM pg_catalog.pg_trigger
   WHERE tgrelid='public.poraca_knowledge_relations'::regclass
   AND tgname='poraca_accepted_event_relation_guard_v1'
   AND tgenabled='O' AND NOT tgisinternal),
 'baselineCanonicalIdsExpected',133,
 'baselineCanonicalIdsMissing',x.lost_count,
 'independentHistoricalCanariesExpected',x.baseline_count,
 'independentHistoricalCanariesMissing',x.missing_count,
 'independentHistoricalMissingIds',x.missing_ids),
 'Sin enlaces canonicos falsos ni recibos perdidos; hechos contextuales con fuente/revision, tres protecciones y 133 IDs historicos preservados',
 'Conservar el contexto antes de publicacion; nunca generar sesiones para cerrar cifras'),
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
 CASE WHEN x.fetch_rows=0 OR x.circuits_mapped=0 THEN 'FAIL'
      WHEN x.fetch_without_circuit=0 AND x.fetch_unchecked=0 AND x.fetch_errors=0
       AND x.fetch_rows=x.full_sources_selected THEN 'PASS'
      ELSE 'PARTIAL' END,
 jsonb_build_object('fetchSources',x.fetch_rows,
 'circuitsMapped',x.circuits_mapped,
 'fetchWithoutCircuit',x.fetch_without_circuit,
 'fetchUncheckedInLastFull',x.fetch_unchecked,
 'fetchErrorsInLastFull',x.fetch_errors,
 'yieldEligibleChecks',x.yield_eligible_checks,
 'indexOnlyChecks',x.index_only_checks,
 'cityActivityExhaustiveness','not_measured',
 'sourceRosterCoverageOnly',true),
 'Inventario fetch clasificado por circuito y consultado en FULL sin errores; NO prueba exhaustividad cultural ni eventos por rubro',
 'Clasificar fuentes faltantes y medir por separado yoga, talleres, vinos y musica under segun evidencia de actividad o entidad, sin funciones ficticias'),
(10,'LEAST_PRIVILEGE',
 -- Preserve FAIL for active credential misconfiguration OR lingering legacy
 -- elevated identities. A working limited ingestion does not erase old risk.
 CASE WHEN NOT x.limited_scope_verified OR x.ingest_elevated OR x.writer_elevated
      THEN 'FAIL' ELSE 'PASS' END,
 jsonb_build_object(
 'limitedRadarLogin','poraca_radar_limited_prod',
 'limitedRoleGrantsSafe',x.limited_scope_verified,
 'activeRunCredential','VERIFY_FROM_GITHUB_WORKFLOW_AND_RUN_SEPARATELY',
 'legacyIngestNeonSuperuserMember',x.ingest_elevated,
 'legacyWriterNeonSuperuserMember',x.writer_elevated,
 'residualLegacyPrivilegeRisk',(x.ingest_elevated OR x.writer_elevated)),
 'Credencial limitada validada por rol y corrida; evaluar por separado los dos logins legacy elevados',
 'Mantener FAIL hasta retirar privilegios legacy de forma administrada; verificar dependencias, reversion y recibos de staging'),
(11,'STABILITY',
 CASE WHEN x.summary->'stability'->'3d'->>'state'='correcto'
 AND x.summary->'stability'->'7d'->>'state'='correcto' THEN 'PASS' ELSE 'PARTIAL' END,
 jsonb_build_object('last3d',x.summary->'stability'->'3d',
                    'last7d',x.summary->'stability'->'7d'),
 'Series completas de 3 y 7 dias sin perdida/duplicacion de calendario',
 'Observar corridas ordinarias con misma consulta; no simular periodos')
) AS g(ord,gate,state,evidence,acceptance,next_action)
ORDER BY g.ord;