"""Recover source leads from evidenced historic event relationships.

General-purpose, offline, bounded and READ-ONLY. Never infers new event dates,
mutates source inventory, claims a replacement or gives editorial approval.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

SCHEMA="poraca-circuit-history-recovery-v1"
RELATIONS={"organizer","coorganizer","host","participant","partner","presenter"}
SIGNIFICANCE={"organizer":5,"coorganizer":4,"host":3,"presenter":2,"participant":2,"partner":1}
INACTIVE={"RECENT_YIELD_DROP","SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS","REPEATED_INDEX_ONLY"}

def day(s):
    if not isinstance(s,str) or not re.fullmatch(r"20\d\d-\d\d-\d\d",s):
        raise ValueError("DATE_UNTRUSTED")
    return date.fromisoformat(s)

def proof_url(s):
    if not isinstance(s,str) or len(s)>500:
        return False
    try:
        p=urlsplit(s)
        return (p.scheme=="https" and bool(p.hostname)
                and p.hostname not in ("localhost","127.0.0.1","::1")
                and p.username is None and p.password is None
                and p.port in (None,443))
    except ValueError:
        return False

def reconstruct(packet, as_of):
    """Relate past events to named actors; keep independent future leads separate."""
    today=day(as_of)
    if not isinstance(packet,dict) or packet.get("schema")!=SCHEMA:
        raise ValueError("UNTRUSTED_PACKET")
    hist=packet.get("historical",[])
    future=packet.get("future",[])
    actors=packet.get("actors",[])
    if (not isinstance(hist,list) or not isinstance(future,list)
        or not isinstance(actors,list) or len(hist)>24 or len(future)>24
        or len(actors)>70 or not packet.get("seedSourceId")
        or not packet.get("circuit")):
        raise ValueError("INVALID_BOUNDS")
    index={}
    for actor in actors:
        if not isinstance(actor,dict) or not actor.get("id") or not actor.get("name") or actor["id"] in index:
            raise ValueError("INVALID_ACTOR")
        if actor.get("sourceUrl") is not None and not proof_url(actor["sourceUrl"]):
            raise ValueError("UNVERIFIED_SOURCE_URL")
        index[actor["id"]]={"id":actor["id"],"name":actor["name"],
          "sourceUrl":actor.get("sourceUrl"),"accountHint":actor.get("accountHint"),
          "links":[]}
    for record in hist:
        if not isinstance(record,dict) or day(record["date"])>=today or not proof_url(record.get("evidenceUrl")):
            raise ValueError("HISTORICAL_DATE_OR_SOURCE_INVALID")
        for role in record.get("actors",[]):
            if role.get("id") not in index or role.get("relation") not in RELATIONS:
                raise ValueError("UNSUPPORTED_ACTOR_RELATION")
            index[role["id"]]["links"].append({
                "eventId":record["id"],"relation":role["relation"],
                "evidenceUrl":record["evidenceUrl"],"historicalDate":record["date"]})
    proposals=[]
    for a in index.values():
        if not a["links"]: continue
        evidence=sorted(a["links"],key=lambda e:e["historicalDate"],reverse=True)
        proposals.append({
            "id":a["id"],"name":a["name"],
            "historicalEvidence":evidence,
            "weight":sum(SIGNIFICANCE[e["relation"]] for e in evidence),
            "sourceUrl":a["sourceUrl"],"accountHint":a["accountHint"],
            "nextStep":"CHECK_ACTOR_CONTROLLED_CURRENT_CHANNEL",
            "recentActivityCertified":False,
            "sourceRegistered":False,"publicationApproved":False})
    proposals.sort(key=lambda a:(-a["weight"],a["name"]))
    current=[]
    for item in future:
        if not isinstance(item,dict) or day(item["date"])<today or not proof_url(item.get("evidenceUrl")):
            raise ValueError("FUTURE_DATE_OR_SOURCE_INVALID")
        if (not item.get("title") or not item.get("venue")
            or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",item.get("time",""))
            or item.get("organizerId") not in index):
            raise ValueError("FUTURE_REQUIRES_ACTUAL_FIELDS_AND_ORGANIZER")
        current.append({
            "title":item["title"],"date":item["date"],"time":item["time"],
            "venue":item["venue"],"sourceUrl":item["evidenceUrl"],
            "organizerId":item["organizerId"],
            "relationToSeed":"SAME_CIRCUIT_NOT_ESTABLISHED_ORGANIZER_RELATION",
            "needsLiveCanonicalCollisionCheck":True,
            "publicationApproved":False})
    return {
      "schema":SCHEMA,"circuit":packet["circuit"],
      "seedSourceId":packet["seedSourceId"],
      "historicRecordsExamined":len(hist),"historicalActorCandidates":len(proposals),
      "actorCandidates":proposals,"currentIndependentLeads":current,
      "futureOriginalsFound":len(current),
      "verifiedReplacementSources":0,"sourceWrites":0,"eventWrites":0,
      "publicationApproved":False,
      "status":"HISTORIC_GRAPH_FOR_REVIEW_NOT_AUTOMATIC_RECOVERY",
      "note":"Past co-participation is a discovery clue, not a live publisher or a recurrence."
    }

def inspect_packs(source_rows, as_of, data_dir, max_packs=8):
    """Use the existing yield diagnoses; do not create another fetch or cron."""
    by_id={x["sourceId"]:x for x in source_rows}
    output=[]
    for path in sorted(Path(data_dir).glob("*.json"))[:max_packs]:
        packet=json.loads(path.read_text(encoding="utf-8"))
        seed=by_id.get(packet.get("seedSourceId"))
        if not seed or seed.get("diagnosis") not in INACTIVE or seed.get("circuit")!=packet.get("circuit"):
            continue
        result=reconstruct(packet,as_of)
        result["seedDiagnosis"]=seed["diagnosis"]
        output.append(result)
    return {"schema":"poraca-circuit-history-recovery-batch-v1",
            "cases":output,"coveredSeeds":len(output),
            "autoRegistered":0,"autoPublished":0}
