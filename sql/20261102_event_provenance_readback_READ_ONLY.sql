-- POR ACÁ / Contrato de procedencia: SELECT-only después de aplicar migración.
-- No confirma que una función haya ocurrido ni reemplaza el recibo editorial.
SELECT count(*)::int AS all_events,
  count(*) FILTER(WHERE source_url_primary_correlated)::int AS correlated_sources,
  count(*) FILTER(WHERE first_party_supports_start)::int AS supported_starts,
  count(*) FILTER(WHERE first_party_supports_venue)::int AS supported_venues
FROM public.poraca_event_field_evidence_quality_v1;

SELECT event_key,verification,release_quality_gate,
       source_url_primary_correlated,first_party_supports_start,
       first_party_supports_venue,publication_policy
FROM public.poraca_event_release_readiness_v2
WHERE event_key IN
 ('noches-capitales-babasonicos-2026-11-14',
  'opera-carmen-sanchez-viamonte-2026-11-07',
  'cultural-98eea4dade88fd2fbfdc4b1a360ad2cf',
  'cultural-6cf2d79cf70eac4e4006881207f111f2')
ORDER BY event_key;
