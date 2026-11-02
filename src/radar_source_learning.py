"""Radar: primera memoria comprobable de rendimiento por fuente.

Medición de CORRIDAS, no de fila permanente `last_run_id`: ese campo solo
conserva la ÚLTIMA corrida y distorsiona el histórico. Sin nuevas tablas,
inserciones, ajustes de prioridades, publicación ni invocación de modelos.
El resultado diagnostica qué método debe revisarse; NO afirma que una fuente
sea irrelevante para la ciudad ni que una estructura haya cambiado.
"""
from __future__ import annotations

SCHEMA = "poraca-source-learning-yield-v1"
SQL = """
WITH outcomes AS (
 SELECT r.run_id,r.started_at, item->>'source_id' AS source_id,
        item->>'status' AS status,
        greatest(0,coalesce((item->>'observed_sessions')::int,0)) AS sessions
 FROM radar_definitivo.runs r
 CROSS JOIN LATERAL jsonb_array_elements(
   CASE WHEN jsonb_typeof(r.summary->'source_outcomes')='array'
        THEN r.summary->'source_outcomes'
        ELSE '[]'::jsonb END) AS item
 WHERE r.finished_at IS NOT NULL AND r.started_at>=now()-interval '30 days'
), ranked AS (
 SELECT *,row_number() OVER(
  PARTITION BY source_id ORDER BY started_at DESC,run_id DESC) AS rn
 FROM outcomes
)
SELECT s.source_id,s.name,s.source_role,s.circuit,s.monitoring_mode,
  count(r.run_id) FILTER(WHERE r.started_at>=now()-interval '7 days')::int AS checks7,
  count(r.run_id) FILTER(WHERE r.started_at>=now()-interval '7 days'
   AND r.status='ok' AND r.sessions=0)::int AS successful_without_session7,
  count(r.run_id) FILTER(WHERE r.started_at>=now()-interval '7 days'
   AND r.status='index_only')::int AS index_only7,
  coalesce(sum(r.sessions) FILTER(WHERE r.started_at>=now()-interval '7 days'),0)::int AS sessions7,
  coalesce(sum(r.sessions),0)::int AS sessions30,
  coalesce(sum(r.sessions) FILTER(WHERE r.rn<=3),0)::int AS latest3,
  coalesce(sum(r.sessions) FILTER(WHERE r.rn BETWEEN 4 AND 10),0)::int AS previous7,
  count(r.run_id) FILTER(WHERE r.rn<=3)::int AS latest3_checks,
  count(r.run_id) FILTER(WHERE r.rn BETWEEN 4 AND 10)::int AS previous7_checks
FROM radar_definitivo.sources s LEFT JOIN ranked r USING(source_id)
WHERE s.enabled
GROUP BY s.source_id,s.name,s.source_role,s.circuit,s.monitoring_mode
ORDER BY s.source_id
"""


# Source roles are declarations, not demonstrated behaviour. This hypothesis
# is used to SORT investigation, never to disable a source or certify events.
REFERENCE_ROLES={
    "original_event_date_check",
    "historical_original_organizer_not_current_venue",
    "official_custodian",
    "official_museum_archive",
    "original_organization_link_hub",
    "community_cooperative_profile",
    "original_editorial_venue",
}
AGENDAS_AND_PROGRAMS={
    "local_press","secondary_agenda","specialized_agenda",
    "institutional_program","first_party_institution",
    "institutional_program_and_community_venue",
    "original_institutional","original_venue","official_ticketing",
    "original_venue_program","original_venue_ticketing",
    "authorized_ticketing","ticketing_primary","theatre_ticketing",
    "original_ticketing","official_festival","original_festival_calendar_ics",
}

def investigation_lane(source_role,monitoring_mode):
    """Conservative, source-role-based triage for persistent zero-yield.

    A static place profile is NOT an error; an agenda with real upcoming
    dates that produces no sessions is. Role is only a queue hint: check the
    actual original before deciding whether the source should change mode.
    """
    if monitoring_mode!="fetch":
        return "OTHER_MODE_NOT_A_DATED_FEED"
    role=(source_role or "").strip().lower()
    if role=="ticketing_blocked":
        return "ACCESS_OR_SCRIPT_BLOCK_REVIEW"
    if role in REFERENCE_ROLES:
        return "REFERENCE_OR_EVIDENCE_REVIEW"
    if role in AGENDAS_AND_PROGRAMS:
        return "POTENTIAL_DATED_FEED_EXTRACTION_GAP"
    return "PURPOSE_REQUIRES_FIRST_PARTY_CHECK"


def classify(row):
    """Read-only diagnosis, grounded in 7/30d per-run outcomes."""
    (source_id,name,role,circuit,mode,checks,successful_empty,index_only,
     sessions7,sessions30,latest3,previous7,latest3_checks,previous7_checks)=row
    (checks,successful_empty,index_only,sessions7,sessions30,latest3,previous7,
     latest3_checks,previous7_checks)=(
        max(0,int(x or 0)) for x in
        (checks,successful_empty,index_only,sessions7,sessions30,latest3,
         previous7,latest3_checks,previous7_checks))
    if mode!="fetch":
        diagnosis="PRESERVE_DISCOVERY_OR_REVIEW_ROLE"
        suggestion="No exigir al canal indirecto sesiones fechadas"
    elif checks>=3 and latest3_checks==3 and latest3==0 and previous7_checks>=2 and previous7>0:
        diagnosis="RECENT_YIELD_DROP"
        suggestion="Examinar formato, canal y fecha; probar estrategia alternativa"
    elif checks>=3 and successful_empty>=3 and sessions7==0:
        diagnosis="SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS"
        suggestion="Auditar método de lectura, no declarar fuente inútil"
    elif checks>=3 and index_only>=3 and sessions7==0:
        diagnosis="REPEATED_INDEX_ONLY"
        suggestion="Verificar si es una institución sin agenda o un canal cambiado"
    elif sessions7>0:
        diagnosis="DATED_SESSIONS_OBSERVED"
        suggestion="Medir originalidad, duplicación y valor marginal antes de priorizar"
    elif checks==0:
        diagnosis="NOT_RECENTLY_OBSERVED"
        suggestion="Reservar exploración de acuerdo con cobertura y prioridad"
    else:
        diagnosis="INSUFFICIENT_SIGNAL"
        suggestion="Seguir observando; no modificar reputación por pocas visitas"
    return {
        "sourceId":source_id, "sourceName":name, "sourceRole":role or "unknown",
        "sourcePurposeHypothesis":investigation_lane(role,mode),
        "sourcePurposeCertified":False, "sourceModeChanged":False,
        "circuit":circuit or "sin_circuito", "monitoringMode":mode,
        "checks7d":checks, "httpOkWithoutSessions7d":successful_empty,
        "indexOnly7d":index_only, "observedSessions7d":sessions7,
        "observedSessions30d":sessions30, "latest3Sessions":latest3,
        "previous7Sessions":previous7, "diagnosis":diagnosis,
        "suggestedInvestigation":suggestion,
        "autoPriorityChanged":False, "autoEntityRemoved":False,
        "evidenceClass":"per_run_reported_sessions_unapproved",
    }


def summarize(rows):
    items=[classify(row) for row in rows]
    counts={}
    for item in items:
        key=item["diagnosis"]
        counts[key]=counts.get(key,0)+1
    high_priority=[x for x in items if x["diagnosis"] in (
        "RECENT_YIELD_DROP","SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS",
        "REPEATED_INDEX_ONLY")]
    lane_rank={"POTENTIAL_DATED_FEED_EXTRACTION_GAP":0,
               "ACCESS_OR_SCRIPT_BLOCK_REVIEW":1,
               "PURPOSE_REQUIRES_FIRST_PARTY_CHECK":2,
               "REFERENCE_OR_EVIDENCE_REVIEW":3}
    high_priority.sort(key=lambda x:(
        {"RECENT_YIELD_DROP":0,"SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS":1,
         "REPEATED_INDEX_ONLY":2}[x["diagnosis"]],
        lane_rank.get(x["sourcePurposeHypothesis"],4),
        -x["httpOkWithoutSessions7d"],-x["checks7d"],str(x["sourceId"])))
    triage_counts={}
    for item in high_priority:
        lane=item["sourcePurposeHypothesis"]
        triage_counts[lane]=triage_counts.get(lane,0)+1
    return {"schema":SCHEMA,"sourceCount":len(items),"diagnosisCounts":counts,
            "priorityReview":high_priority[:12],
            "sourcesWithRecentDatedSessions":sum(
                1 for x in items if x["observedSessions7d"]>0),
            "persistentZeroYieldByPurposeHypothesis":triage_counts,
            "sourceModeChanges":0,
            "learningState":"DIAGNOSTIC_ONLY",
            "warning":"HTTP OK no implica funciones; sesiones observadas no equivalen "
                      "a eventos distintos ni confirmados. Cambios de formato "
                      "requieren evidencia de la página. No modificar prioridades "
                      "por reinicio del staging o solo por volumen."}
