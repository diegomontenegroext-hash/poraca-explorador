"""Four-account daily Instagram pilot using Meta Business Discovery only.

Runs inside the existing Radar 2 schedule (05:27 ART). With no real Meta
credentials the pilot is explicitly NOT_CONFIGURED and performs zero requests.
No HTML profile collection, browser automation, bypass, or new scheduler.
"""
import os
import re
from collector import sha, utc
from instagram import discover
from capabilities import CULTURAL, norm

# Four cultural reference accounts, unchanged across days for a comparable sample.
ACCOUNTS = ("guajira.bar", "lutitravelguide", "escenario40", "circus_ofc")
REQUIRED = ("META_IG_USER_ID", "META_ACCESS_TOKEN", "META_GRAPH_VERSION")
PERMALINK = re.compile(r"https://(?:www\.)?instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?\Z")

def acquire(collector, known_urls):
    """Return concise receipts. Never turn absent credentials into a PASS."""
    report = {"kind": "instagram_official_four_account_pilot",
              "accounts": list(ACCOUNTS), "method": "meta_business_discovery",
              "enabled": False, "queries_sent": 0,
              "new_documents": 0, "new_cultural_candidates": 0,
              "results": []}
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        report.update(status="NOT_CONFIGURED", missing_configuration=missing)
        return report

    report["enabled"] = True
    # Each target is requested once only. Official errors never retry.
    for username in ACCOUNTS:
        official = discover(username)
        report["queries_sent"] += 1
        summary = {"username": username, "status": official.get("status", "UNKNOWN"),
                   "items_returned": len(official.get("posts") or []),
                   "new_documents": 0, "new_candidates": 0,
                   "error_type": official.get("error_type")}
        for post in (official.get("posts") or [])[:12]:
            url = post.get("permalink") or ""
            caption = post.get("caption") or ""
            if not isinstance(url,str) or not PERMALINK.fullmatch(url):
                continue
            if not isinstance(caption,str) or not caption.strip():
                continue
            if url in known_urls or url in collector.docs:
                continue
            fetched_at=utc()
            d={"url":url,"final_url":url,"source":"Instagram",
               "title":"Publicación de @"+username,"text":caption[:16000],
               "fetched_at":fetched_at,"sha256":sha(caption),
               "text_sha256":sha(caption),"acquisition_method":"official_meta_api",
               "content_scope":"caption","profile_username":username,
               "published_at":post.get("timestamp")}
            collector.docs[url]=d
            report["new_documents"] += 1
            summary["new_documents"] += 1
            if CULTURAL.search(norm(caption)):
                key=collector.add(d,d["title"],state="investigable",
                                  evidence=caption,origin_account=username)
                if key:
                    collector.proposals[key].update(
                        kind="document",acquisition_method="official_meta_api",
                        date_basis="post timestamp is not an event date",
                        related_accounts=[])
                    summary["new_candidates"] += 1
                    report["new_cultural_candidates"] += 1
        report["results"].append(summary)
    report["status"] = ("POSTS_ACQUIRED" if report["new_documents"] else
                        "NO_NEW_POSTS_OR_UNAVAILABLE")
    return report
