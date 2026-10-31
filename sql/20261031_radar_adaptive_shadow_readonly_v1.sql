-- Radar adaptativo: ensayo de selección por rendimiento. SOLAMENTE SELECT.
-- No crea ni elimina datos. Repetible con el catálogo actual; no modifica scheduler.
-- Ventana de 7 días todavía corta: TODOS los modos son hipótesis.
-- Primary evidence != publicación/editorial acceptance; circuit != género evento.
WITH checks_7d AS (
 SELECT source_id,COUNT(*)::int checks,
 COUNT(*) FILTER(WHERE status='ok')::int ok,
 COUNT(*) FILTER(WHERE status='index_only')::int index_only,
 COUNT(*) FILTER(WHERE status='failed')::int failed,
 COALESCE(SUM(details_opened),0)::int details_opened
 FROM radar_definitivo.source_checks
 WHERE checked_at >= now()-interval '7 days'
 GROUP BY source_id
), listings_7d AS (
 SELECT source_id,
 COUNT(*) FILTER(WHERE first_seen_at >= now()-interval '7 days')::int new_observations,
 COUNT(*) FILTER(WHERE first_seen_at >= now()-interval '7 days'
   AND public.poraca_first_party_event_detail_v1(evidence_tier,proof_method,proof_url)
   AND event_time IS NOT NULL AND venue IS NOT NULL)::int primary_new,
 COUNT(*) FILTER(WHERE event_date >=
   (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date)::int future_sessions,
 COUNT(*)::int historic_sessions
 FROM radar_definitivo.listing_occurrences GROUP BY source_id
), facts AS (
 SELECT s.source_id,s.name,s.source_role,s.circuit,s.monitoring_mode,
 s.priority AS existing_priority,s.cadence_hours AS existing_cadence_hours,
 COALESCE(c.checks,0) AS checks_7d,
 COALESCE(c.index_only,0) AS index_only_7d,
 COALESCE(c.failed,0) AS failed_7d,
 COALESCE(c.details_opened,0) AS details_7d,
 COALESCE(l.new_observations,0) AS new_7d,
 COALESCE(l.primary_new,0) AS primary_new_7d,
 COALESCE(l.future_sessions,0) AS future_sessions,
 COALESCE(l.historic_sessions,0) AS historic_sessions
 FROM radar_definitivo.sources s
 LEFT JOIN checks_7d c USING(source_id)
 LEFT JOIN listings_7d l USING(source_id)
 WHERE s.enabled
), proposed AS (
 SELECT *,
 CASE
 WHEN monitoring_mode='discover_only' THEN 'exploracion_indirecta_no_feed'
 WHEN monitoring_mode='review' THEN 'explorar_si_hay_evidencia'
 WHEN primary_new_7d>=2 THEN 'priorizar_original'
 WHEN new_7d>=3 THEN 'reconciliar_agenda_secundaria'
 WHEN checks_7d>=2 AND index_only_7d=checks_7d
   THEN 'diagnosticar_canal_o_valor_institucional'
 WHEN checks_7d>=2 AND new_7d=0
   THEN 'verificar_utilidad_antes_de_reducir'
 ELSE 'exploracion_controlada'
 END AS mode_shadow,
 (LEAST(primary_new_7d,10)*5 + LEAST(new_7d,20)*2
   + LEAST(future_sessions,10)
   - LEAST(index_only_7d,5)*2 - LEAST(failed_7d,5)*3) AS score_shadow
 FROM facts
)
SELECT source_id,name,circuit,monitoring_mode,source_role,
 existing_priority,existing_cadence_hours,checks_7d,index_only_7d,
 details_7d,new_7d,primary_new_7d,future_sessions,historic_sessions,
 mode_shadow,score_shadow,
 CASE WHEN checks_7d<3 THEN 'insuficiente' ELSE 'preliminar' END AS confidence,
 'DRY_RUN_ONLY'::text AS action_state
FROM proposed
ORDER BY CASE WHEN monitoring_mode='fetch' THEN 0
              WHEN monitoring_mode='review' THEN 1 ELSE 2 END,
         score_shadow DESC, existing_priority DESC,source_id
LIMIT 250;
