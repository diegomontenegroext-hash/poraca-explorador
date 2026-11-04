"""Review-only capture of an admitted ORIGINAL source's own landing page.

A crawled original may be a dated ticket detail or a multi-venue cultural
cycle. HTTP 200 is proof that a URL was opened, NOT evidence of confirmed
attendance, dates, organizer identity, or permission to publish. The output
reuses Radar's existing candidate/evidence schema and preserves its scope.
This module never fetches, inserts, accepts or publishes by itself.
"""
from __future__ import annotations

from urllib.parse import urlsplit

_ALLOWED_SOURCE_ROLES = frozenset({
    "first_party_organizer", "first_party_ticketing",
    "original_cycle", "original_ticketing",
    "original_venue", "original_project", "institutional_program",
})

def root_review_candidate(source, root, page, http_status, make_candidate):
    """Return 0 or 1 unverified root candidates, never a canonical event."""
    if not isinstance(source, dict) or source.get("source_role") not in _ALLOWED_SOURCE_ROLES:
        return []
    if page is None or http_status != 200:
        return []
    try:
        parsed = urlsplit(root)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password):
            return []
    except (TypeError, ValueError):
        return []
    source_id = source.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        return []
    item = make_candidate(root, source_id, "first_party_original_opened", page, http_status)
    if not item or item.get("original_url") != root:
        return []
    item["evidence"].update({
        "root_original_review": True,
        "admission": "UNVERIFIED_ORIGINAL_NEEDS_EDITORIAL_REVIEW",
        "source_root": root,
        "linked_from": root,
        "detail_opened": True,
        "source_type": source["source_role"],
        "auto_publish": False,
        "auto_accept": False,
    })
    if source['source_role'] in ('original_venue','original_project','institutional_program'):
        # A meaningful first-party place/project description is knowledge
        # even without a future event. It remains a proposal, not freshness.
        metadata=getattr(page,'meta',{})
        description=metadata.get('og:description') or metadata.get('description') or ''
        if len(description.strip())<40 or (getattr(page,'title','') or '').lower() in ('site unavailable','instagram','inicio'):
            return []
        item['evidence']['identity_review']={'state':'review_only',
            'description':description[:500], 'current_program_verified':False}
        if not item.get('event_date'):
            item['kind']='cultural_identity_index'
            item['event_time']=None
    if source["source_role"] == "original_cycle":
        # A distributed circuit is not one concert at every named bookstore.
        # Even a JSON-LD Event is reviewed as a cycle without a single venue.
        item["kind"] = "cultural_cycle_index"
        item["event_date"] = None
        item["event_time"] = None
        item["venue"] = None
        item["organizer"] = None
        item["evidence"]["not_an_atomic_event"] = True
        item["evidence"]["structured_event_found"] = False
        item["evidence"].pop("cultural_signals_v1", None)
    return [item]


def suppress_unverified_cycle_root_sessions(listings, root, root_candidates):
    """Keep dated children with their own proof; drop fake atomic root Event.

    Multi-venue cycle roots often expose a JSON-LD Event whose location is
    merely 'all independent bookstores'. That is not a verified individual
    session. This applies by semantic candidate kind, not by URL or domain.
    """
    if not isinstance(listings, list):
        return listings
    cycle=any(isinstance(item,dict) and item.get("kind")=="cultural_cycle_index"
              and item.get("original_url")==root
              and item.get("evidence",{}).get("not_an_atomic_event") is True
              for item in (root_candidates or []))
    if not cycle:
        return listings
    return [item for item in listings
            if not (isinstance(item,dict) and item.get("proof_url")==root)]
