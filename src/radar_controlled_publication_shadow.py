"""Por Acá: deterministic controlled-publication preflight (PURE / SHADOW ONLY).

No connections, network, SQL, state, side effects, or publication. This is a
decision proposal for a separate authorized editorial writer that does not
yet exist; the production writer v1 remains intact.
"""
from __future__ import annotations
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import json
from urllib.parse import urlsplit

POLICY_PATH=Path(__file__).resolve().parents[1]/"data"/"controlled_auto_publication_policy_v1.json"
POLICY=json.loads(POLICY_PATH.read_text(encoding="utf-8"))

def _url_exact(url: object) -> bool:
    if not isinstance(url,str): return False
    try:
        p=urlsplit(url)
    except ValueError:
        return False
    if p.scheme!="https" or not p.hostname or p.username or p.password: return False
    # An Instagram account or a home page is not proof of one scheduled event.
    if p.hostname.lower() in ("instagram.com","www.instagram.com"):
        return p.path.strip("/").startswith(("p/","reel/")) and len(p.path.strip("/").split("/"))>=2
    return p.path not in ("","/") or bool(p.query or p.fragment)

def _valid_day(day: object) -> date | None:
    if not isinstance(day,str) or len(day)!=10: return None
    try: return date.fromisoformat(day)
    except ValueError: return None

def evaluate(candidate: dict, *, today: date, now: datetime, policy: dict=POLICY) -> dict:
    """Return reviewable outcome; writeAuthorized is ALWAYS false, even on PASS."""
    if policy.get("mode")!="SHADOW_ONLY" or policy.get("productionEnabled") is not False:
        raise ValueError("PRODUCTION_GATE_DISABLED_IN_THIS_MODULE")
    if not isinstance(candidate,dict): raise ValueError("CANDIDATE_NOT_OBJECT")
    event=candidate.get("event") or {}
    original=candidate.get("original") or {}
    source=candidate.get("source") or {}
    identity=candidate.get("identity") or {}
    integrity=candidate.get("integrity") or {}
    result={"decision":"REVIEW","reasons":[],"writeAuthorized":False,
            "publicationApproved":False,"clockRequired":False,
            "suggestedTime":None,"proposedEventKey":None,"policy":policy["schema"]}
    def stop(kind: str, reason: str) -> dict:
        result["decision"]=kind
        result["reasons"]=[reason]
        return result
    if not isinstance(event,dict) or not isinstance(original,dict) or not isinstance(source,dict) or not isinstance(identity,dict) or not isinstance(integrity,dict):
        return stop("REVIEW","INVALID_RECORD")
    if integrity.get("prior_hold") or integrity.get("source_date_conflict") or integrity.get("venue_conflict"):
        return stop("REVIEW","PRIOR_HOLD_OR_FACT_CONFLICT")
    if event.get("status") in ("cancelled","ended") or integrity.get("cancelled_original"):
        return stop("DISCARD","CANCELLED_OR_ENDED")
    if event.get("accessory_only") or original.get("accessory_ticket"):
        return stop("DISCARD","NOT_A_SEPARATE_EVENT")
    day=_valid_day(event.get("program_day"))
    if day is None: return stop("SKIP","PROGRAM_DAY_NOT_VERIFIED")
    if (day-today).days<0: return stop("DISCARD","HISTORICAL_EVENT")
    if (day-today).days>policy["maxFutureDays"]:
        return stop("SKIP","OUTSIDE_ADMISSION_WINDOW")
    title=event.get("program") or ""
    venue=event.get("venue") or ""
    if not isinstance(title,str) or len(title.strip())<4 or not isinstance(venue,str) or len(venue.strip())<4:
        return stop("SKIP","PROGRAM_OR_VENUE_UNCLEAR")
    if event.get("location_in_scope") is not True:
        return stop("SKIP","LOCATION_NOT_CONFIRMED_LOCAL")
    if source.get("enabled") is not True or source.get("registered") is not True:
        return stop("SKIP","SOURCE_NOT_REGISTERED_AND_ENABLED")
    if source.get("role") not in policy["sourceRoles"] or original.get("primary_source") is not True:
        return stop("SKIP","NOT_AN_AUTHORIZED_ORIGINAL")
    if original.get("exact_announcement") is not True or not _url_exact(original.get("url")):
        return stop("SKIP","ORIGINAL_ANNOUNCEMENT_NOT_SPECIFIC")
    asserted=set(original.get("supports",[]))
    if not set(policy["originalEvidenceMinimum"]).issubset(asserted):
        return stop("SKIP","ORIGINAL_DOES_NOT_SUPPORT_DAY_PROGRAM_VENUE")
    if original.get("day_matches") is not True or original.get("program_matches") is not True or original.get("venue_matches") is not True:
        return stop("REVIEW","ORIGINAL_FIELDS_DISAGREE")
    if identity.get("approved_venue_matches")==0:
        return stop("SKIP","VENUE_IDENTITY_NOT_YET_VALIDATED")
    if identity.get("approved_venue_matches")!=1 or not identity.get("approved_venue_id"):
        return stop("REVIEW","VENUE_IDENTITY_AMBIGUOUS")
    if integrity.get("different_event_same_url_day") or integrity.get("multiple_distinct_sessions"):
        return stop("REVIEW","MULTIPLE_EVENTS_OR_SESSIONS_NEED_REVIEW")
    if integrity.get("candidate_variants") not in (None,0,1):
        return stop("REVIEW","AMBIGUOUS_PROGRAM_VARIANTS")
    if integrity.get("canonical_same_event_count",0)>1:
        return stop("REVIEW","MULTIPLE_CANONICAL_IDENTITIES")
    if integrity.get("canonical_same_event_count")==1:
        if integrity.get("same_identity_original_confirmed") is True:
            return stop("LINK_EXISTING_SHADOW","IDEMPOTENT_EXISTING_CANONICAL")
        return stop("REVIEW","EXISTING_CANONICAL_DIFFERENT_FACTS")
    if integrity.get("canonical_same_event_count") != 0:
        return stop("REVIEW","CANONICAL_COLLISION_NOT_CHECKED")
    if integrity.get("collision_check_complete") is not True:
        return stop("REVIEW","COLLISION_SEARCH_NOT_PROVEN")
    if now.tzinfo is None: raise ValueError("NOW_NEEDS_TIMEZONE")
    checked=original.get("checked_at")
    if not isinstance(checked,str): return stop("SKIP","ORIGINAL_RECHECK_REQUIRED")
    try: timestamp=datetime.fromisoformat(checked.replace("Z","+00:00"))
    except ValueError: return stop("SKIP","ORIGINAL_RECHECK_REQUIRED")
    if timestamp.tzinfo is None or not timedelta()<=now.astimezone(timezone.utc)-timestamp.astimezone(timezone.utc)<=timedelta(hours=policy["maxEvidenceAgeHours"]):
        return stop("SKIP","ORIGINAL_RECHECK_REQUIRED")
    result["decision"]="AUTO_ELIGIBLE_SHADOW"
    result["reasons"]=["ORIGINAL_DAY_PROGRAM_VENUE_IDENTITY_PROVEN"]
    result["suggestedTime"]=event.get("time") if isinstance(event.get("time"),str) and event.get("time_kind")=="original_verified" else None
    return result
