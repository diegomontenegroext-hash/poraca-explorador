"""Health of existing runs. Acquisition, controls and admission stay distinct."""
from datetime import datetime, timezone, timedelta

CONTROL_NAMES = ("public_observation_aliases", "function_gate_v2", "url_clock_aliases")


def assess(stats):
    selected, checked, success = (int(stats.get(k, 0)) for k in ("selected", "checked", "success"))
    quality = stats.get("evidence_quality", {})
    unavailable = [name for name in CONTROL_NAMES
                   if quality.get(name, {}).get("status") in (None, "unavailable")]
    acquisition = "sin_evidencia_suficiente" if selected == 0 else (
        "correcto" if selected == checked == success else "parcial")
    controls = "bloqueado" if unavailable else "correcto"
    return {"schema": "poraca-health-v1", "acquisition": acquisition,
            "controls": controls, "unavailable_controls": unavailable,
            "overall": "bloqueado" if unavailable else acquisition,
            "sources": {"selected": selected, "checked": checked, "ok": success,
                        "index_only": int(stats.get("index_only", 0)),
                        "failed": max(0, checked-success-int(stats.get("index_only", 0))),
                        "unvisited": max(0, selected-checked)},
            "admission": "not_performed", "api": "not_checked", "web": "not_checked",
            "coverage": "not_measured", "authorized_to_write": False}


def stability(rows, now=None):
    """Observed history only; a young baseline cannot earn a 3/7-day pass.

    rows: started_at, finished_at, status, summary from the existing runs table.
    Gaps > 26h exceed the daily FULL cadence plus tolerance. Omitted incremental
    slots need no fake run; the daily FULL still provides a health sample.
    """
    now = now or datetime.now(timezone.utc)
    def dt(value):
        return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    result = {}
    # Only runs recording this health contract constitute a baseline.
    eligible = [r for r in rows if r.get("summary", {}).get("health", {}).get("schema") == "poraca-health-v1"]
    for days in (3, 7):
        cutoff = now-timedelta(days=days)
        recent = sorted([r for r in eligible if cutoff <= dt(r["started_at"]) <= now], key=lambda r: dt(r["started_at"]))
        baseline = any(dt(r["started_at"]) <= cutoff for r in eligible)
        points = [cutoff]+[dt(r["started_at"]) for r in recent]+[now]
        gaps = any(b-a > timedelta(hours=26) for a, b in zip(points, points[1:]))
        bad = sum(r.get("status") != "complete" or not r.get("finished_at") or
                  r["summary"]["health"].get("overall") != "correcto" for r in recent)
        result[str(days)+"d"] = {"state": "sin_evidencia_suficiente" if not baseline else
                               "degradado" if gaps or bad or not recent else "correcto",
                               "observed_runs": len(recent), "unhealthy_runs": bad,
                               "gap_over_26h": gaps, "baseline_mature": baseline}
    return result
