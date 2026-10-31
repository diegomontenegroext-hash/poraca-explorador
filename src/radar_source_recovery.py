"""Recovery planner: sources by circuit, not speculative channel substitutions.

Uses the already-read 7/30d per-run evidence: a HTTP 200 with no dated
session is not productivity. A related-circuit source is NOT proof that it
replaced a disappeared original or reflects the same venue/organizer.
No network, writes, ranking changes, or automated publication.
"""
from __future__ import annotations

TRIGGERS={"RECENT_YIELD_DROP","SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS",
          "REPEATED_INDEX_ONLY"}


def plan(rows,limit=12):
    # rows are from radar_source_learning.classify, not merely DB inventory
    records=[dict(x) for x in rows]
    productive=[x for x in records if
                x.get("monitoringMode")=="fetch" and
                x.get("observedSessions7d",0)>0 and
                x.get("diagnosis")=="DATED_SESSIONS_OBSERVED"]
    failing=[x for x in records if x.get("monitoringMode")=="fetch" and
             x.get("diagnosis") in TRIGGERS]
    failing.sort(key=lambda x:(
        0 if x["diagnosis"]=="RECENT_YIELD_DROP" else 1,
        -int(x.get("checks7d",0)),str(x.get("sourceId"))))
    actions=[]
    for source in failing[:limit]:
        circuit=str(source.get("circuit") or "")
        # Same circuit or multi-scene channels; never infer same organization.
        alternatives=[x for x in productive if x.get("sourceId")!=source.get("sourceId")
                      and (circuit and x.get("circuit")==circuit)]
        alternatives.sort(key=lambda x:(-int(x.get("observedSessions7d",0)),
                                        str(x.get("sourceId"))))
        suggestions=[{
             "sourceId":x["sourceId"],"name":x.get("sourceName"),
             "observedSessions7d":x.get("observedSessions7d",0),
             "reason":"ALTERNATE_COVERAGE_IN_SAME_CIRCUIT_NOT_SAME_ORGANIZER"
            } for x in alternatives[:3]]
        actions.append({
            "sourceId":source["sourceId"],"name":source.get("sourceName"),
            "circuit":circuit,"observedSessions7d":source.get("observedSessions7d",0),
            "diagnosis":source["diagnosis"],"last7Checks":source.get("checks7d",0),
            "alternativeCoverageSources":suggestions,
            "requiredRecoveryTest":"REOPEN_REAL_SOURCE_THEN_VALIDATE_EXACT_ORIGINAL",
            "recommendation":("TEST_ALTERNATE_CHANNELS_WITHIN_CIRCUIT"
                              if suggestions else "DISCOVER_NEW_VERIFIABLE_CHANNEL"),
            "selfHealConfirmed":False,"sourceDisabled":False
        })
    return {"schema":"poraca-source-recovery-plan-v1",
            "sourcesNeedingRecovery":len(failing),
            "shown":len(actions),"actions":actions,
            "strategy":"SHADOW_RECOMMENDATIONS_ONLY",
            "confirmedReplacements":0,
            "uncoveredCases":sum(not a["alternativeCoverageSources"] for a in actions),
            "note":"Cobertura alternativa en mismo circuito NO es reemplazo "
                   "verificado del canal de una entidad. Sin visita nueva al "
                   "original no hay confirmación de recuperación."}
