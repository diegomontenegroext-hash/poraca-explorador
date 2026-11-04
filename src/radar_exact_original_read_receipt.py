"""Exact original page read receipts for Radar listings (staging only).

A body digest + parser fields preserve what the collector actually opened.
They are not a signature, independent verification, publication permission,
proof of attendance, or a proof that all fields are correct.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlsplit

_ORIGINAL_ROLES=frozenset({
    "original_venue", "original_venue_program", "original_venue_ticketing",
    "theatre_ticketing", "venue_ticketing",
    "original_institutional", "institutional_program",
    "original_festival_calendar_ics",
})
_INDEX_PATHS=frozenset({"/","/agenda","/cartelera","/cartelera.asp",
                       "/eventos","/actividades","/programacion"})

def attach_exact_original_receipts(items, opened_url, body, status, *,
                                   source_role=None, observed_at=None):
    """Mutate no input rows: attach receipt ONLY to exact document-extracted events.

    Generic indexes/roots, secondary agendas, indirect proof URLs, browsing
    failures and unverified structured JSON never get an original receipt.
    Missing time is always allowed. Opening a page is not editorial attestation.
    """
    result=[dict(x) for x in items]
    if status!=200 or not body or source_role not in _ORIGINAL_ROLES:
        return result
    try:
        p=urlsplit(opened_url)
        if (p.scheme!="https" or not p.hostname or p.username or p.password
            or p.path.rstrip("/").lower() in _INDEX_PATHS):
            return result
    except (TypeError,ValueError):
        return result
    raw=body.encode("utf-8") if isinstance(body,str) else body
    if not isinstance(raw,bytes) or len(raw)<20:
        return result
    read_time=observed_at or datetime.now(timezone.utc).isoformat()
    document_sha=sha256(raw).hexdigest()
    for item in result:
        if item.get("proof_url")!=opened_url:
            continue
        method=str(item.get("method") or "")
        tier=str(item.get("evidence_tier") or "")
        if (not method or "index" in method.lower() or "index" in tier.lower()
            or not tier.startswith("primary_")
            or not isinstance(item.get("title"),str)
            or len(item["title"].strip())<4
            or not isinstance(item.get("event_date"),str)
            or len(item["event_date"])!=10
            or not isinstance(item.get("venue"),str)
            or len(item["venue"].strip())<4):
            continue
        item["_original_read_receipt"]={
            "schema":"radar-exact-original-read-v1",
            "opened_url":opened_url,
            "document_sha256":document_sha,
            "document_bytes":len(raw),
            "observed_at":read_time,
            "http_status":200,
            "method":method,
            "evidence_tier":tier,
            "source_role":source_role,
            "extracted_fields":{
                "program":item["title"],"day":item["event_date"],
                "venue":item["venue"],"time":item.get("event_time")},
            "meaning":"collector_read_and_parsed_not_editorial_approval",
        }
    return result
