-- POR ACÁ · QA DE CAMBIO DE PROPÓSITO / REQUIERE APROBACIÓN PARA PROD.
-- Cambia SOLO el modo de consulta de UN origen archivístico con alternativa
-- institucional del MISMO nodo comprobada; no modifica enabled, URL ni historia.
-- Aplicación controlada: revisar manualmente los IDs del CTE target antes de
-- ejecutar en cualquier rama. No ejecutar el script en modo automático.
WITH target(source_id,entity_id,alternative_id) AS (
 VALUES ('rd-web-2f6489bc'::text,
         'museo-pettoruti'::text,
         'rd-web-88482c94'::text)
), approved AS (
 SELECT s.source_id,s.monitoring_mode AS previous_mode,s.name,
        t.entity_id,t.alternative_id
 FROM target t
 JOIN radar_definitivo.sources s ON s.source_id=t.source_id
 JOIN radar_definitivo.sources a ON a.source_id=t.alternative_id
 JOIN public.poraca_knowledge_entities e ON e.entity_id=t.entity_id
 WHERE s.enabled AND s.monitoring_mode='fetch'
   AND s.source_role IN ('official_museum_archive',
     'historical_original_organizer_not_current_venue','official_custodian')
   AND a.enabled AND a.monitoring_mode='fetch'
   AND a.source_role IN ('original_institutional','first_party_institution',
                         'institutional_program')
   AND e.editorial_state='approved_public' AND e.merged_into_id IS NULL
   AND public.poraca_source_host_v1(a.url)=
       public.poraca_source_host_v1(e.official_url)
   AND NOT EXISTS(SELECT 1 FROM radar_definitivo.listing_occurrences l
     WHERE l.source_id=s.source_id
       AND l.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date)
   AND (SELECT count(*) FROM radar_definitivo.source_checks c
     WHERE c.source_id=s.source_id AND c.status='index_only'
       AND c.checked_at>=now()-interval '7 days')>=3
), changed AS (
 UPDATE radar_definitivo.sources s SET monitoring_mode='discover_only'
 FROM approved a WHERE s.source_id=a.source_id
 RETURNING s.source_id,s.name,s.monitoring_mode
)
SELECT c.source_id,c.name,c.monitoring_mode,a.previous_mode,a.entity_id,
       a.alternative_id,'RECLASSIFIED_SOURCE_NOT_RUN_STATUS'::text AS decision
FROM changed c JOIN approved a USING(source_id);