-- POR ACÁ / Última FULL: rendimiento FECHADO por circuito (no HTTP solamente).
-- Neon branch OPERATIVA: br-mute-recipe-b4odj2bl / neondb.
-- SOLO SELECT. No evento publicado ni independencia de organizadores inferida.
WITH last_full AS (
  SELECT run_id,started_at,finished_at,summary
  FROM radar_definitivo.runs
  WHERE mode='full' AND finished_at IS NOT NULL
  ORDER BY started_at DESC LIMIT 1
), receipts AS (
  SELECT l.run_id,item->>'source_id' AS source_id,
    item->>'status' AS outcome_status,
    GREATEST(0,COALESCE((item->>'observed_sessions')::int,0)) AS reported_sessions
  FROM last_full l CROSS JOIN LATERAL jsonb_array_elements(
    CASE WHEN jsonb_typeof(l.summary->'source_outcomes')='array'
         THEN l.summary->'source_outcomes' ELSE '[]'::jsonb END) item
), counted AS (
  SELECT s.circuit,COUNT(DISTINCT s.source_id)::int AS fetch_sources,
    COUNT(DISTINCT s.source_id) FILTER(WHERE r.outcome_status='ok')::int AS transport_ok_sources,
    COUNT(DISTINCT s.source_id) FILTER(WHERE r.reported_sessions>0)::int AS reported_yield_sources,
    COALESCE(SUM(r.reported_sessions),0)::int AS reported_sightings_not_unique_events
  FROM receipts r JOIN radar_definitivo.sources s ON s.source_id=r.source_id
  WHERE s.enabled AND s.monitoring_mode='fetch'
  GROUP BY s.circuit
)
SELECT (SELECT run_id FROM last_full) AS measured_run,
       circuit,fetch_sources,transport_ok_sources,reported_yield_sources,
       reported_sightings_not_unique_events,
       CASE WHEN reported_yield_sources=0 THEN 'NO_REPORTED_DATED_YIELD'
            WHEN reported_yield_sources=1 THEN 'SINGLE_REPORTED_YIELD_CHANNEL'
            ELSE 'MULTIPLE_REPORTED_YIELD_CHANNELS_NOT_CERTIFIED'
       END AS source_gate,
       false AS independent_organizers_verified,
       false AS resilience_certified
FROM counted ORDER BY reported_yield_sources ASC,circuit;
