"""Bounded Meta Business Discovery: four stable controls plus ten rotating accounts.

Runs inside the existing Radar 2 schedule (05:27 ART). Without valid Meta
credentials the pilot is NOT_CONFIGURED and performs zero requests.
No HTML profile collection, browser automation, bypass, or new scheduler.
"""
import os
import re
from collector import sha, utc
from instagram import discover
from capabilities import CULTURAL, norm
from account_context import preflight

# Four cultural reference accounts, unchanged across days for a comparable sample.
ACCOUNTS = ("guajira.bar", "lutitravelguide", "escenario40", "teatroargentinopba")
REQUIRED = ("META_IG_USER_ID", "META_ACCESS_TOKEN", "META_GRAPH_VERSION")
PERMALINK = re.compile(r"https://(?:www\.)?instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?\Z")

def acquire(collector, known_urls, rotating_accounts=(),include_controls=True,extra_curators=()):
    """Four controls plus at most ten unique users from the persisted daily batch."""
    rotating=[]
    for raw in rotating_accounts:
        username=raw.strip().lower() if isinstance(raw,str) else ""
        if (re.fullmatch(r"[a-z0-9_.]{1,30}",username) and
                (not include_controls or username not in ACCOUNTS) and username not in rotating):
            rotating.append(username)
        if len(rotating)>=10: break
    accounts=(list(ACCOUNTS) if include_controls else [])+rotating
    extra=[]
    for u in extra_curators:
        if isinstance(u,str) and re.fullmatch(r'[a-z0-9_.]{1,30}',u) and u not in accounts:extra.append(u);accounts.append(u)
        if len(extra)>=1:break
    report={"extra_curators":extra,"kind":"instagram_official_rotating_pilot",
              "accounts":accounts,"controls":list(ACCOUNTS) if include_controls else [],
              "rotating_accounts":rotating,"method":"meta_business_discovery",
              "enabled": False, "queries_sent": 0,
              "accounts_eligible": len(accounts), "accounts_successful": 0,
              "accounts_failed": 0, "last_successful_query_at": None,
              "new_documents": 0, "new_cultural_candidates": 0,
              "results": [],
              "account_preflight": [preflight(username) for username in accounts]}
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        report.update(status="NOT_CONFIGURED", missing_configuration=missing)
        return report

    report["enabled"] = True
    # Each target is requested once only. Official errors never retry.
    for username in accounts:
        official = discover(username)
        report["queries_sent"] += 1
        summary = {"username": username, "preflight": preflight(username),
                   "checked_at": official.get("checked_at"),
                   "status": official.get("status", "UNKNOWN"),
                   "items_returned": len(official.get("posts") or []),
                   "new_documents": 0, "new_candidates": 0, "known_documents":0,
                   "latest_publication_at":max((p.get("timestamp") or "" for p in official.get("posts",[])),default=None),
                   "error_type": official.get("error_type"),
                   "http_status": official.get("http_status"),
                   "meta_error_code": official.get("meta_error_code"),
                   "meta_error_subcode": official.get("meta_error_subcode"),
                   "meta_error_type": official.get("meta_error_type")}
        for post in (official.get("posts") or [])[:12]:
            url = post.get("permalink") or ""
            caption = post.get("caption") or ""
            if not isinstance(url,str) or not PERMALINK.fullmatch(url):
                continue
            if not isinstance(caption,str) or not caption.strip():
                continue
            if url in collector.docs:
                continue
            if url in known_urls:summary['known_documents']+=1
            fetched_at=utc()
            d={"url":url,"final_url":url,"source":"Instagram",
               "title":"Publicación de @"+username,"text":caption[:16000],
               "fetched_at":fetched_at,"sha256":sha(caption),
               "text_sha256":sha(caption),"acquisition_method":"official_meta_api",
               "content_scope":"caption","profile_username":username,
               "published_at":post.get("timestamp"),"external_id":post.get("id"),"media_type":post.get("media_type")}
            collector.docs[url]=d
            if getattr(collector,"checkpoint",None):collector.checkpoint(d)
            report["new_documents"] += int(url not in known_urls)
            summary["new_documents"] += int(url not in known_urls)
            if CULTURAL.search(norm(caption)):
                # Use a distinct title per post, not just the profile name.
                first_line=next((re.sub(r"\s+"," ",line).strip()
                                 for line in caption.splitlines() if line.strip()),"")
                title="Instagram @"+username+" · "+(first_line[:110] or url)
                key=collector.add(d,title,state="investigable",
                                  evidence=caption,origin_account=username)
                if key:
                    collector.proposals[key].update(
                        kind="document",acquisition_method="official_meta_api",
                        date_basis="post timestamp is not an event date",
                        related_accounts=[])
                    summary["new_candidates"] += 1
                    report["new_cultural_candidates"] += 1
        summary["operational_status"] = "QUERY_FAILED"
        if summary["status"] in ("MEDIA_RETURNED", "NO_MEDIA_RETURNED"):
            summary["operational_status"] = "POSTS_ACQUIRED" if summary["new_documents"] else "QUERIED_NO_NEW"
        report["results"].append(summary)
        if (summary["meta_error_code"] in (4, 17, 32, 613, 80002, 190)
                or summary["http_status"] == 429):
            report["halt_reason"] = ("META_AUTH" if summary["meta_error_code"] == 190
                                     else "META_RATE_LIMIT")
            break
    report["unattempted_accounts"] = accounts[len(report["results"]):]
    # Do not misreport authentication failure as a quiet day with no posts.
    results = report["results"]
    successful = [r for r in results if r["status"] in ("MEDIA_RETURNED", "NO_MEDIA_RETURNED")]
    report["accounts_successful"] = len(successful)
    report["accounts_failed"] = len(results) - len(successful)
    report["last_successful_query_at"] = max(
        (r["checked_at"] for r in successful if r.get("checked_at")), default=None)
    if not accounts:
        report["status"] = "NOT_DUE"
    elif report.get("halt_reason") == "META_RATE_LIMIT":
        report["status"] = "META_RATE_LIMITED"
    elif any(r.get("meta_error_code") == 190 and
             r.get("meta_error_subcode") == 463 for r in results):
        report["status"] = "META_TOKEN_EXPIRED"
    elif report.get("halt_reason") == "META_AUTH":
        report["status"] = "META_AUTH_ERROR"
    elif report["accounts_failed"]:
        report["status"] = ("PARTIAL_OFFICIAL_API_ERRORS" if successful else "OFFICIAL_API_ERRORS")
    else:
        report["status"] = "POSTS_ACQUIRED" if report["new_documents"] else "QUERIED_NO_NEW"
    return report
