"""Bounded Meta Business Discovery: 20 official requests maximum per run.

Runs inside the existing Radar 2 schedule (FULL and incrementals). Without valid Meta
credentials the pilot is NOT_CONFIGURED and performs zero requests.
No HTML profile collection, browser automation, bypass, or new scheduler.
"""
import json
import os
import re
from urllib.parse import parse_qsl, urlsplit
from datetime import datetime, timedelta, timezone
from collector import sha, utc
from instagram import discover
from capabilities import CULTURAL, norm
from account_context import preflight

# Four cultural reference accounts, unchanged across days for a comparable sample.
ACCOUNTS = ("guajira.bar", "lutitravelguide", "escenario40", "teatroargentinopba")
REQUIRED = ("META_IG_USER_ID", "META_ACCESS_TOKEN", "META_GRAPH_VERSION")
PERMALINK = re.compile(r"https://(?:www\.)?instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?\Z")

def media_references(post):
    """Keep temporary image renditions only, never a video URL or API credentials."""
    children = post.get("children")
    album = post.get("media_type") == "CAROUSEL_ALBUM"
    items = children.get("data") if album and isinstance(children, dict) else []
    items = list(items) if isinstance(items, list) else []
    if not album or not items:
        items = [post]
    leads = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = item.get("media_type")
        field = {"IMAGE": "media_url", "VIDEO": "thumbnail_url", "CAROUSEL_ALBUM": "media_url"}.get(kind)
        url = item.get(field)
        if not isinstance(url, str) or len(url) > 4096:
            continue
        try:
            parts = urlsplit(url)
            if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
                    or parts.port or not parts.hostname.endswith((".cdninstagram.com", ".fbcdn.net"))
                    or any(k.lower() in ("access_token", "appsecret_proof") for k, _ in parse_qsl(parts.query))):
                continue
        except ValueError:
            continue
        if any(ref["url"] == url for ref in leads):
            continue
        leads.append({"media_id": item.get("id") or post.get("id"), "url": url,
                      "role": "reel_cover" if field == "thumbnail_url" else "publication_image",
                      "origin": "meta_business_discovery", "temporary": True})
        if len(leads) == 3:
            break
    return leads

def publication_age_bucket(timestamp, checked_at):
    """Distinguish newly found old posts from truly recent posts; no inferred dates."""
    try:
        published = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        checked = datetime.fromisoformat(str(checked_at).replace("Z", "+00:00"))
        if published.tzinfo is None or checked.tzinfo is None:
            return "unknown"
        lag = checked - published
        if lag < -timedelta(minutes=5):
            return "unknown"
        return "recent_7d" if lag <= timedelta(days=7) else "backfill_older_7d"
    except (TypeError, ValueError, OverflowError):
        return "unknown"

def acquire(collector, known_urls, rotating_accounts=(),include_controls=True,extra_curators=()):
    """At most 20 official queries total, including controls and extra curators."""
    controls=list(ACCOUNTS) if include_controls else []
    rotating_cap=max(0,20-len(controls))
    rotating=[]
    for raw in rotating_accounts:
        username=raw.strip().lower() if isinstance(raw,str) else ""
        if (re.fullmatch(r"[a-z0-9_.]{1,30}",username) and
                (not include_controls or username not in ACCOUNTS) and username not in rotating):
            rotating.append(username)
        if len(rotating)>=rotating_cap: break
    accounts=controls+rotating
    extra=[]
    for u in extra_curators:
        if (len(accounts)<20 and isinstance(u,str) and
                re.fullmatch(r'[a-z0-9_.]{1,30}',u) and u not in accounts):
            extra.append(u);accounts.append(u)
        if len(extra)>=1:break
    report={"extra_curators":extra,"kind":"instagram_official_rotating_pilot",
              "accounts":accounts,"controls":list(ACCOUNTS) if include_controls else [],
              "rotating_accounts":rotating,"method":"meta_business_discovery",
              "enabled": False, "queries_sent": 0,
              "accounts_eligible": len(accounts), "accounts_successful": 0,
              "accounts_failed": 0, "last_successful_query_at": None,
              "new_documents": 0, "new_cultural_candidates": 0,
              "new_recent_documents_7d": 0, "new_backfill_documents_older_7d": 0,
              "new_documents_date_unknown": 0,
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
                   "new_recent_documents_7d":0, "new_backfill_documents_older_7d":0,
                   "new_documents_date_unknown":0,
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
            leads = media_references(post)
            if not isinstance(caption,str) or (not caption.strip() and not leads):
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
            d["media_leads_v1"] = leads
            d["media_status"] = "temporary_references" if leads else "not_returned"
            if leads:
                identities = [(ref["media_id"], ref["role"]) for ref in leads]
                d["sha256"] = sha(json.dumps([caption, post.get("timestamp"), identities], ensure_ascii=False))
            collector.docs[url]=d
            if getattr(collector,"checkpoint",None):collector.checkpoint(d)
            if url not in known_urls:
                report["new_documents"] += 1
                summary["new_documents"] += 1
                # This classifier is informational only: never filters receipts,
                # changes event dates, or approves a cultural event for publishing.
                age = publication_age_bucket(post.get("timestamp"), official.get("checked_at") or fetched_at)
                counter = {"recent_7d":"new_recent_documents_7d",
                           "backfill_older_7d":"new_backfill_documents_older_7d",
                           "unknown":"new_documents_date_unknown"}[age]
                report[counter] += 1
                summary[counter] += 1
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
