#!/usr/bin/env python3
"""RADAR -> Neon -> PRIVATE API data-contract probe; independent of historical P0.

No ingestion, UPDATE, cron or editorial approval. Distinguishes an actual
direct Radar feed from the older public editorial observation queue.
API HTTP/SSO require a separate protected Vercel probe.
"""
from __future__ import annotations
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "poraca-radar-direct-read-contract-v2"
IDENTITY_SQL = """
SELECT current_database(),session_user,current_user,
 current_setting('neon.project_id',true),
 current_setting('neon.branch_id',true),
 has_function_privilege(current_user,'public.poraca_radar_direct_discoveries_v2(date,date,text,text)','EXECUTE'),
 has_table_privilege(current_user,'public.radar_agenda_events','INSERT,UPDATE,DELETE,TRUNCATE')
"""
DAY_SQL = "SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date"
FEED_SQL = """
SELECT observation_id,title,date,"time",venue,category,source_url,
       origin_url,last_seen_at,source_label
FROM public.poraca_radar_direct_discoveries_v2(%s::date,%s::date,%s::text,%s::text)
"""
OVERLAP_SQL = """
SELECT count(*)::int FROM public.radar_agenda_events e
JOIN unnest(%s::date[],%s::text[],%s::text[]) v(event_date,event_time,source_url)
 ON e.event_date=v.event_date
 AND left(coalesce(e.event_time,''),5)=v.event_time
 AND e.source_url=v.source_url
"""
LAST_RUN_SQL = """
SELECT run_id,mode,status,started_at,finished_at,sources_checked,sources_success
FROM radar_definitivo.runs
WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1
"""

EXPECTED = ("neondb", "poraca_definitivo_ingest", "poraca_definitivo_scope",
            "frosty-union-52906378", "br-mute-recipe-b4odj2bl", True, False)
ID_RE = re.compile(r"^radar-[a-f0-9]{32}$")
DATE_RE = re.compile(r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}$")
TIME_RE = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


def safe_https(value):
    if not isinstance(value, str) or len(value) > 1600:
        return False
    try:
        x = urlsplit(value)
        return (x.scheme == "https" and bool(x.hostname)
                and not x.username and not x.password
                and x.port in (None, 443) and not re.search(r"[\s<>]", value))
    except ValueError:
        return False


def collect_pages(fetch, day, max_pages=50):
    """Get all eligible sessions, never treating a 48-row page as the whole feed."""
    collected = []
    after = (None, None, None)
    seen_keys = set()
    for index in range(max_pages):
        rows = fetch(day, *after)
        if len(rows) > 49:
            raise ValueError("RADAR_PAGE_EXCEEDED_LIMIT")
        selected = rows[:48]
        collected.extend(selected)
        if len(rows) <= 48:
            return collected, index + 1
        if len(selected) != 48:
            raise ValueError("RADAR_PAGE_INVALID")
        last = selected[-1]
        after = (date.fromisoformat(last[2]), last[3], last[0])
        if after in seen_keys:
            raise ValueError("RADAR_PAGE_CURSOR_LOOP")
        seen_keys.add(after)
    raise ValueError("RADAR_PAGINATION_LIMIT_EXCEEDED")


def assess(rows, day, canonical_overlap, last_run):
    """Certify read-path properties only, never freshness of every source."""
    seen = set()
    problems = Counter()
    categories = Counter()
    distinct_urls = set()
    refreshed = 0
    for item in rows:
        (rid, title, when, clock, venue, category, url, origin, seen_at,
         source_label) = item
        if not isinstance(rid, str) or not ID_RE.fullmatch(rid):
            problems["bad_identity"] += 1
        elif rid in seen:
            problems["duplicate_identity"] += 1
        seen.add(rid)
        if not isinstance(when, str) or not DATE_RE.fullmatch(when) or when < str(day):
            problems["expired_or_bad_date"] += 1
        if not isinstance(clock, str) or not TIME_RE.fullmatch(clock):
            problems["bad_time"] += 1
        if not isinstance(title, str) or len(title.strip()) < 4 or len(title) > 180:
            problems["bad_title"] += 1
        if not isinstance(venue, str) or len(venue.strip()) < 4:
            problems["bad_venue"] += 1
        if not safe_https(url) or url != origin:
            problems["bad_original"] += 1
        else:
            distinct_urls.add(url)
        if not source_label:
            problems["no_attributed_source"] += 1
        categories[category or "sin_clasificar"] += 1
        if (last_run and isinstance(seen_at, datetime)
                and isinstance(last_run[3], datetime)
                and seen_at >= last_run[3]):
            refreshed += 1
    if canonical_overlap:
        problems["already_in_canonical"] += int(canonical_overlap)
    if not rows:
        problems["no_radar_discoveries"] += 1
    status = ("DIRECT_RADAR_NEON_READ_PASS_API_HTTP_SEPARATE" if not problems
              else "DIRECT_RADAR_NEON_READ_FAIL")
    return {
        "schema": SCHEMA, "status": status,
        "dayArgentina": str(day), "readOnly": True, "autoPublished": False,
        "visibleUnverified": len(rows), "distinctSourceUrls": len(distinct_urls),
        "categories": dict(sorted(categories.items())),
        "lastRadarRunId": str(last_run[0]) if last_run else None,
        "lastRadarRunStatus": str(last_run[2]) if last_run else None,
        "lastRadarRunSourcesChecked": int(last_run[5] or 0) if last_run else 0,
        "lastRadarRunSourcesSuccessful": int(last_run[6] or 0) if last_run else 0,
        "directResultsTouchedSinceLastRun": refreshed,
        "canonicalDuplicatesByDateTimeOriginal": int(canonical_overlap),
        "problems": dict(sorted(problems.items())),
        "apiHttp": "NOT_CHECKED", "browserSso": "NOT_CHECKED",
        "learning": "SOURCE_YIELD_DIAGNOSTICS_NOT_AUTOMATIC_SELF_IMPROVEMENT",
        "interpretation": ("Each API page displays at most 48 discoveries, but the "
                           "certifier traverses all Radar pages. Source success "
                           "does not certify every advertised event.")
    }


def read(url):
    import psycopg
    with psycopg.connect(url, connect_timeout=12) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cur.execute(IDENTITY_SQL)
                identity = cur.fetchone()
                if identity != EXPECTED:
                    raise RuntimeError("RADAR_DIRECT_READ_IDENTITY_MISMATCH")
                cur.execute(DAY_SQL)
                day = cur.fetchone()[0]
                def fetch_page(on_day, after_date, after_time, after_id):
                    cur.execute(FEED_SQL, (on_day, after_date, after_time, after_id))
                    return cur.fetchall()

                rows, pages = collect_pages(fetch_page, day)
                cur.execute(OVERLAP_SQL, (
                    [r[2] for r in rows], [r[3] for r in rows],
                    [r[6] for r in rows],
                ))
                overlaps = cur.fetchone()[0]
                cur.execute(LAST_RUN_SQL)
                last_run = cur.fetchone()
    report = assess(rows, day, overlaps, last_run)
    report['pagesTraversed'] = pages
    return report


def main():
    url = os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL")
    if not url:
        print("::error::RADAR_DIRECT_PROBE_SECRET_MISSING", file=sys.stderr)
        return 2
    try:
        report = read(url)
        print("PORACA_RADAR_DIRECT_PROBE " + json.dumps(report, ensure_ascii=False))
        summary = os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with Path(summary).open("a", encoding="utf-8") as out:
                out.write("\n### Radar → Neon → API: lectura directa, no aprobación\n\n")
                out.write("| Puerta | Resultado |\n|---|---|\n")
                out.write("| Integridad de consulta directa | {} |\n".format(report["status"]))
                out.write("| Anuncios elegibles en todas las páginas | {} |\n".format(report["visibleUnverified"]))
                out.write("| Páginas Radar recorridas | {} |\n".format(report["pagesTraversed"]))
                out.write("| URLs originales distintas | {} |\n".format(report["distinctSourceUrls"]))
                out.write("| Casos tocados desde última corrida | {} |\n".format(report["directResultsTouchedSinceLastRun"]))
                out.write("| Conflictos con eventos canónicos | {} |\n".format(report["canonicalDuplicatesByDateTimeOriginal"]))
                out.write("| Circuitos visibles | {} |\n\n".format(
                    ", ".join("{}:{}".format(k, v) for k, v in report["categories"].items())))
                out.write("**API HTTP y navegador SSO no verificados en esta lectura SQL.** "
                          "La integridad canónica histórica se evalúa en otro control; "
                          "una falla de esa deuda no invalida esta lectura directa.\n")
        if report["status"] != "DIRECT_RADAR_NEON_READ_PASS_API_HTTP_SEPARATE":
            print("::error::RADAR_DIRECT_READ_CONTRACT_FAILED", file=sys.stderr)
            return 2
        return 0
    except Exception as exc:
        print("::error::RADAR_DIRECT_PROBE_UNAVAILABLE " + type(exc).__name__,
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
