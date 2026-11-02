"""Recovery planner: sources by circuit, not speculative channel substitutions.

Uses the already-read 7/30d per-run evidence: a HTTP 200 with no dated
session is not productivity. A related-circuit source is NOT proof that it
replaced a disappeared original or reflects the same venue/organizer.
No network, writes, ranking changes, or automated publication.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlsplit


# Regional coverage is more than a city-center address. Historic neighbors
# (Berisso / Ensenada / Gonnet / City Bell) are valid candidates for validation.
# Still no claim their current accounts actually publish dated events.
LOCAL_CIRCUIT_AREAS={"La Plata","Gorina","Gonnet","City Bell","Berisso",
                     "Ensenada","Tolosa","Los Hornos","Abasto"}

def is_local_future_original(record,today):
    """A local ORGANIZER is not proof of a local EVENT.

    Requires the exact source's future date/time/venue plus an explicit,
    independently checked locality for the EVENT itself.
    """
    if not isinstance(record,dict) or not isinstance(today,date):
        return False
    if record.get("kind")!="upcoming_original":
        return False
    url=record.get("url")
    if not isinstance(url,str):
        return False
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    ev=record.get("event")
    if not isinstance(ev,dict) or ev.get("locality") not in LOCAL_CIRCUIT_AREAS:
        return False
    if (not ev.get("time") or not ev.get("venue")
            or ev.get("date")!=record.get("date")):
        return False
    try:
        if date.fromisoformat(record["date"])<today:
            return False
    except (TypeError,ValueError,KeyError):
        return False
    # The EVENT'S verified venue governs territorial relevance. A visiting
    # artist, touring producer or national organizer can advertise a valid
    # event in La Plata. The organizer's headquarters is neither required
    # nor enough to establish event locality.
    proof=ev.get("localityProof")
    return isinstance(proof,str) and bool(proof.strip())


def reconstruct_historical_network(evidence,circuit,today,limit=10):
    """Follow old named participants to new local channels, never to publication."""
    if not isinstance(today,date):
        raise ValueError("Local date required")
    found={}
    for record in list(evidence)[:300]:
        if not isinstance(record,dict) or record.get("circuit")!=circuit:
            continue
        original=record.get("url") or ""
        parsed=urlsplit(original)
        if parsed.scheme!="https" or not parsed.hostname:
            continue
        try:
            day=date.fromisoformat(record["date"])
        except (ValueError,TypeError,KeyError):
            continue
        kind=record.get("kind")
        if kind not in ("historical","historical_secondary","upcoming_original"):
            continue
        is_future=is_local_future_original(record,today)
        for target in record.get("targets",[])[:30]:
            if not isinstance(target,dict) or not target.get("id") or not target.get("name"):
                continue
            profile=target.get("url")
            if profile and (urlsplit(profile).scheme!="https" or not urlsplit(profile).hostname):
                continue
            key=str(target["id"])
            item=found.setdefault(key,{
                "targetId":key,"name":target["name"],
                "relationshipRole":target.get("role"),"channelUrl":profile,
                "accountHint":target.get("accountHint"),
                "locality":target.get("locality"),"historicalProofUrls":[],
                "upcomingOriginals":[],"autoRegistered":False,
                "publicationApproved":False})
            if (kind in ("historical","historical_secondary") or day<today) and original not in item["historicalProofUrls"]:
                item["historicalProofUrls"].append(original)
            if is_future and not any(x["url"]==original for x in item["upcomingOriginals"]):
                ev=record.get("event") or {}
                if ev.get("date")==record["date"] and ev.get("time") and ev.get("venue"):
                    item["upcomingOriginals"].append({
                        "title":record.get("title"),"date":record["date"],
                        "time":ev["time"],"venue":ev["venue"],"url":original,
                        "status":"UNVERIFIED_FOR_PORACA"})
    for item in found.values():
        local=item["locality"] in LOCAL_CIRCUIT_AREAS
        item["reviewPriority"]=(
            "VERIFY_UPCOMING_ORIGINAL" if item["upcomingOriginals"] else
            "FIND_CURRENT_LOCAL_PROGRAM" if local else
            "RELATED_PARTNER_NOT_LOCAL_FEED")
    def role_priority(item):
        role=str(item.get("relationshipRole") or "").lower()
        # Event organizers control future notices more often than participants.
        # This is only an investigation order, never a source reliability claim.
        if "organizer" in role:return 0
        if "host" in role or "venue" in role:return 1
        if "participant" in role:return 2
        return 3
    return sorted(found.values(),key=lambda x:(
        {"VERIFY_UPCOMING_ORIGINAL":0,"FIND_CURRENT_LOCAL_PROGRAM":1,
         "RELATED_PARTNER_NOT_LOCAL_FEED":2}[x["reviewPriority"]],
        role_priority(x),
        -len(x["historicalProofUrls"]),x["targetId"]))[:max(0,min(limit,30))]


def discover_directory_review_leads(evidence,circuit,today,limit=3):
    """National/regional calendars can reveal channels, NEVER local events.

    A directory dated for November is not evidence that any specific shop in
    La Plata participates. It stays in a separate review queue until a
    participant's local identity and original dated activity are verified.
    """
    if not isinstance(today,date):
        raise ValueError("Local date required")
    leads=[]
    seen=set()
    for record in list(evidence)[:300]:
        if not isinstance(record,dict) or record.get("kind")!="upcoming_directory":
            continue
        if record.get("circuit")!=circuit or record.get("localParticipantVerified") is not False:
            continue
        url=record.get("url")
        if not isinstance(url,str) or len(url)>1500:
            continue
        parsed=urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
            continue
        try:
            event_date=date.fromisoformat(record["date"])
        except (ValueError,TypeError,KeyError):
            continue
        if event_date<today or url in seen:
            continue
        if record.get("directoryScope") not in ("AR_nationwide","regional_unverified"):
            continue
        if not record.get("dateEvidenceUrl"):
            continue
        proof=urlsplit(record["dateEvidenceUrl"])
        if proof.scheme!="https" or not proof.hostname:
            continue
        seen.add(url)
        leads.append({
            "title":str(record.get("title") or "")[:140],
            "date":event_date.isoformat(),"directoryUrl":url,
            "dateEvidenceUrl":record["dateEvidenceUrl"],
            "directoryScope":record["directoryScope"],
            "localParticipantVerified":False,
            "localEventDetected":False,"autoRegistered":False,
            "publicationApproved":False,
            "requiredReview":"VERIFY_LOCAL_PARTICIPANT_AND_ORIGINAL_DATED_ACTIVITY",
            "sourcePurpose":"PARTICIPANT_DISCOVERY_INDEX_NOT_EVENT_FEED"
        })
    return sorted(leads,key=lambda x:(x["date"],x["directoryUrl"]))[:max(0,min(limit,10))]


TRIGGERS={"RECENT_YIELD_DROP","SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS",
          "REPEATED_INDEX_ONLY"}


def plan(rows,limit=12,historical_evidence=(),today=None):
    # rows are from radar_source_learning.classify, not merely DB inventory
    records=[dict(x) for x in rows]
    productive=[x for x in records if
                x.get("monitoringMode")=="fetch" and
                x.get("observedSessions7d",0)>0 and
                x.get("diagnosis")=="DATED_SESSIONS_OBSERVED"]
    failing=[x for x in records if x.get("monitoringMode")=="fetch" and
             x.get("diagnosis") in TRIGGERS]
    productive_circuits={str(x.get("circuit") or "") for x in productive}
    # An evidence-backed UPCOMING local original from a circuit with no
    # productive feed deserves review before a generic index-only page.
    # This prioritizes investigation only; it never changes ingest sources.
    future_circuits=set()
    if today is not None:
        for record in historical_evidence:
            if is_local_future_original(record,today):
                future_circuits.add(str(record.get("circuit") or ""))
    failing.sort(key=lambda x:(
        0 if x.get("circuit") in future_circuits and
             x.get("circuit") not in productive_circuits else 1,
        0 if x["diagnosis"]=="RECENT_YIELD_DROP" else 1,
        0 if x.get("circuit") not in productive_circuits else 1,
        -int(x.get("checks7d",0)),str(x.get("sourceId"))))
    # Count real, reported 7-day dated yields by independent fetch source.
    # These are UNAPPROVED sightings, not proof of source quality or coverage
    # of a whole cultural circuit. Discovery-only and review channels never
    # count as a productive extraction channel.
    circuit_rows={}
    for item in records:
        circuit=str(item.get("circuit") or "").strip()
        if not circuit or item.get("monitoringMode")!="fetch":
            continue
        aggregate=circuit_rows.setdefault(circuit,{"fetchIds":set(),
            "yieldIds":set(),"zeroYieldIds":set()})
        source_id=str(item.get("sourceId") or "").strip()
        if not source_id:
            continue
        aggregate["fetchIds"].add(source_id)
        if (item.get("diagnosis")=="DATED_SESSIONS_OBSERVED"
                and int(item.get("observedSessions7d") or 0)>0):
            aggregate["yieldIds"].add(source_id)
        else:
            aggregate["zeroYieldIds"].add(source_id)
    # A verified future original discovered through historical research
    # reveals a coverage hole even if the circuit has NO fetch source at all.
    # Do not register it as a source, observation or approved event.
    for circuit in future_circuits:
        if circuit:
            circuit_rows.setdefault(circuit,{"fetchIds":set(),
                "yieldIds":set(),"zeroYieldIds":set()})
    circuit_resilience=[]
    for circuit,counts in circuit_rows.items():
        reported=len(counts["yieldIds"])
        gate=("NO_REPORTED_DATED_YIELD" if reported==0 else
              "SINGLE_REPORTED_YIELD_CHANNEL" if reported==1 else
              "MULTIPLE_REPORTED_YIELD_CHANNELS_NOT_CERTIFIED")
        circuit_resilience.append({
            "circuit":circuit,
            "fetchSources":len(counts["fetchIds"]),
            "futureOriginalResearchHint":circuit in future_circuits,
            "reportedDatedYieldSources7d":reported,
            "fetchSourcesWithoutReportedDatedYield7d":len(
                counts["fetchIds"]-counts["yieldIds"]),
            "sourceResilienceGate":gate,
            "independentOrganizerVerified":False,
            "resilienceCertified":False,
            "minimumTargetChannels":2,
            "interpretation":"Reported sessions may duplicate; original links, "
                             "organizer independence and admission remain untested."
        })
    circuit_resilience.sort(key=lambda x:(
        x["reportedDatedYieldSources7d"],x["circuit"]))
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
            "historicalNetworkCandidates":reconstruct_historical_network(
                historical_evidence,circuit,today) if today is not None else [],
            "directoryReviewCandidates":discover_directory_review_leads(
                historical_evidence,circuit,today) if today is not None else [],
            "selfHealConfirmed":False,"sourceDisabled":False
        })
    return {"schema":"poraca-source-recovery-plan-v1",
            "sourcesNeedingRecovery":len(failing),
            "shown":len(actions),"actions":actions,
            "strategy":"SHADOW_RECOMMENDATIONS_ONLY",
            "confirmedReplacements":0,
            "circuitResilience":circuit_resilience,
            "circuitsWithoutReportedDatedYield":sum(
                x["reportedDatedYieldSources7d"]==0 for x in circuit_resilience),
            "circuitsWithOneReportedYieldChannel":sum(
                x["reportedDatedYieldSources7d"]==1 for x in circuit_resilience),
            "resilienceCertification":"NOT_CERTIFIED_REQUIRES_INDEPENDENT_ORIGINALS",
            "uncoveredCases":sum(not a["alternativeCoverageSources"] for a in actions),
            "note":"Cobertura alternativa en mismo circuito NO es reemplazo "
                   "verificado del canal de una entidad. Sin visita nueva al "
                   "original no hay confirmación de recuperación."}
