-- Certificación punta a punta de la cadena real: SELECT, sin modificaciones.
-- Reconstruir el resultado de la última corrida, no confundir staging/editorial.
-- Datos adaptados por zona America/Argentina/Buenos_Aires.
WITH latest AS (
 SELECT run_id,started_at,finished_at,status,sources_selected,sources_checked,
        summary->'health'->>'overall' AS health
 FROM radar_definitivo.runs ORDER BY started_at DESC LIMIT 1
)
SELECT latest.run_id,latest.status AS radar_status,latest.health,
 latest.finished_at IS NOT NULL AS run_finished,
 latest.sources_selected AS selected_sources,
 latest.sources_checked AS checked_sources,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  WHERE l.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date) AS future_staging,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  WHERE l.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND l.evidence_tier LIKE 'primary%'
  AND l.event_time IS NOT NULL AND l.venue IS NOT NULL) AS future_primary_complete,
 (SELECT count(*)::int FROM public.radar_v3_source_observations o
  WHERE o.last_seen_at >= latest.started_at) AS editorial_touched_since_run,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date) AS future_canonical,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND e.verification='confirmed') AS future_confirmed,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND e.published_at IS NOT NULL) AS future_published,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  JOIN radar_definitivo.sources s USING(source_id)
  WHERE s.url ~* '^https://[^/]+/(event|events|evento|eventos|entrada|entradas|ticket|tickets)/[^/?#]+/?$'
  AND l.proof_url <> s.url) AS suspect_crosslinks,
 (SELECT count(*)::int FROM radar_definitivo.sources s
  WHERE s.enabled AND s.monitoring_mode='fetch' AND
  (coalesce(s.circuit,'') ~* 'deport|recrea' OR
   s.url ILIKE '%deportes.unlp.edu.ar%' OR
   s.name ~* 'deport|recreaci|rugby|futbol|hockey|tenis|patin|basquet|judo|kayak')) AS active_sports_sources,
 (SELECT count(*)::int FROM radar_definitivo.sources WHERE enabled AND monitoring_mode='discover_only') AS indirect_source_inventory,
 (SELECT count(*)::int FROM radar_definitivo.runs WHERE finished_at IS NULL) AS currently_running,
 (SELECT count(*)::int FROM radar_archive_20261031.listing_occurrences) AS archived_original_listings,
 (SELECT count(*)::int FROM radar_archive_20261031.radar_agenda_events_future) AS archived_original_future_catalog
FROM latest;
