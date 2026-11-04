#!/usr/bin/env python3
"""O3 last-seven historical replay, side-effect-free. It NEVER changes persisted run status."""
import json
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/"data"/"o3_seven_full_backtest_20261103.json"

def assess(snapshot):
    if snapshot.get("schema")!="poraca-radar-o3-historical-seven-full-v1":
        raise ValueError("O3_REPLAY_SCHEMA")
    rows=snapshot.get("runs")
    if not isinstance(rows,list) or len(rows)!=7:
        raise ValueError("O3_REPLAY_SEVEN")
    ids=[r["id"] for r in rows]
    if len(set(ids))!=7:
        raise ValueError("O3_REPLAY_DUPLICATE")
    persisted=0; counterfactual=0; nonproductive=0; technical_failures=0
    classes={"poraca-health-v1":0,"poraca-health-v2":0}
    for r in rows:
        if r["healthSchema"] not in classes or r["persistedStatus"] not in ("complete","partial","error","failed"):
            raise ValueError("O3_REPLAY_UNKNOWN_STATUS")
        classes[r["healthSchema"]]+=1
        numbers=[r[k] for k in ("selected","checked","ok","indexOnly","failed")]
        if any(type(x) is not int or x<0 for x in numbers) or r["checked"]>r["selected"]:
            raise ValueError("O3_REPLAY_BAD_COUNTERS")
        if r["ok"]+r["indexOnly"]+r["failed"]!=r["checked"]:
            raise ValueError("O3_REPLAY_INCONSISTENT_CHECKS")
        persisted+=int(r["persistedStatus"]=="complete")
        counterfactual+=int(r["selected"]==r["checked"] and r["failed"]==0)
        nonproductive+=r["indexOnly"]
        technical_failures+=r["failed"]
        if r["persistedStatus"]=="complete" and (r["selected"]!=r["checked"] or r["failed"]):
            raise ValueError("O3_REPLAY_FALSE_COMPLETE")
    if not snapshot.get("readOnly") or not snapshot.get("publishedStatusImmutable"):
        raise ValueError("O3_REPLAY_STATE_MUTATION")
    fragile=snapshot["sourcePurpose"]
    noDated={k:v["fetch"] for k,v in fragile.items() if v["withFutureDatedListing"]==0}
    return {"schema":"poraca-o3-retro-diagnostics-v1",
      "fullRuns":7,"persistedComplete":persisted,
      "counterfactualHttpCleanUnderV2":counterfactual,
      "historicalStatusChanged":False,
      "postCutoverCertifiable":False,
      "o3Certified":False,
      "sourceChecksPersisted":sum(r["checked"] for r in rows),
      "sourceIndexOnly":nonproductive,
      "httpFailedChecks":technical_failures,
      "historicalHealthSchemas":classes,
      "fragileWithoutDatedExtraction":noDated,
      "recommendation":"Keep normal daily FULL, do not replay/write history or promote dated yoga/wine from recurring offers."}

def main():
    report=assess(json.loads(PATH.read_text(encoding="utf-8")))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
