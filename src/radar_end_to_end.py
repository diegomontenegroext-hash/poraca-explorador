"""Contrato de lectura punta a punta: Radar -> observaciones -> canon -> API/Web.

Solo lee la cadena real en Neon. No ejecuta Motor, no crea fuentes ni aprueba
eventos. No presume que READY de Vercel implique contenido listo, ni que
GitHub SUCCESS signifique adquisición/admisión. Fecha local ART.
"""
from __future__ import annotations

SCHEMA = "poraca-radar-end-to-end-v1"
SQL = """
WITH last_run AS (
 SELECT run_id, started_at, status,
        sources_selected, sources_checked
 FROM radar_definitivo.runs
 WHERE finished_at IS NOT NULL
 ORDER BY started_at DESC LIMIT 1
)
SELECT r.run_id,r.status,r.sources_selected,r.sources_checked,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  WHERE l.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date) AS radar_future,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  WHERE l.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
   AND l.evidence_tier LIKE 'primary%'
   AND l.event_time IS NOT NULL AND l.venue IS NOT NULL) AS primary_detail_future,
 (SELECT count(*)::int FROM public.radar_v3_source_observations o
  WHERE o.last_seen_at >= r.started_at) AS editorial_observations_since_run,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date) AS canonical_future,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND e.verification='confirmed') AS confirmed_future,
 (SELECT count(*)::int FROM public.radar_agenda_events e
  WHERE e.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND e.published_at IS NOT NULL) AS published_future,
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences l
  JOIN radar_definitivo.sources s USING(source_id)
  WHERE s.url ~* '^https://[^/]+/(event|events|evento|eventos|entrada|entradas|ticket|tickets)/[^/?#]+/?$'
  AND l.proof_url <> s.url) AS suspect_ticket_crosslinks
FROM last_run r
"""


def assess(row):
    """Separar claramente adquisición, revisión, catálogo y HTTP/SSO.

    No deducir publicación ni lectura web de datos SQL únicamente.
    """
    if row is None:
        return {
            "schema": SCHEMA,
            "status": "NO_COMPLETED_RUN",
            "nextBlockingGate": "radar",
            "runId": None,
            "apiHttp": "NOT_CHECKED",
            "webSso": "NOT_CHECKED",
            "publicationApprovedByRadar": False,
        }
    (run_id, run_status, selected, checked, radar_future, primary_future,
     editorial_since, canonical_future, confirmed_future, published_future,
     suspect_crosslinks) = row
    vals = [max(0, int(v or 0)) for v in (
        selected, checked, radar_future, primary_future, editorial_since,
        canonical_future, confirmed_future, published_future, suspect_crosslinks)]
    (selected, checked, radar_future, primary_future, editorial_since,
     canonical_future, confirmed_future, published_future, suspect_crosslinks) = vals
    if selected != checked or run_status in ("error", "running"):
        gate = "radar_acquisition"
    elif radar_future == 0:
        gate = "discover_future_sessions"
    elif editorial_since == 0:
        gate = "radar_to_editorial_reconciliation"
    elif confirmed_future == 0:
        gate = "editorial_admission"
    else:
        gate = "authenticated_api_and_web_check"
    return {
        "schema": SCHEMA, "status": "DATA_CHAIN_BLOCKED" if
            gate != "authenticated_api_and_web_check" else "HTTP_NOT_VERIFIED",
        "nextBlockingGate": gate, "runId": str(run_id),
        "radarRunStatus": str(run_status),
        "sourcesSelected": selected, "sourcesChecked": checked,
        "radarFutureObservations": radar_future,
        "futurePrimaryWithTimeVenue": primary_future,
        "editorialObservationsTouchedSinceRadarRun": editorial_since,
        "futureCanonical": canonical_future, "futureConfirmed": confirmed_future,
        "futurePublished": published_future,
        "suspectTicketCrosslinks": suspect_crosslinks,
        "apiHttp": "NOT_CHECKED", "webSso": "NOT_CHECKED",
        "publicationApprovedByRadar": False,
        "warning": "Radar staging, historical public observations, canonical editorial "
                   "events, HTTP API and protected web are distinct. These are "
                   "different universes, not a conversion rate or proof of coverage."
    }
