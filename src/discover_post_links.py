#!/usr/bin/env python3
"""Descubrir enlaces exactos a posts públicos desde medios/agendas culturales.

No abre ni descarga publicaciones Instagram: sólo registra enlaces ya
publicados por webs de terceros. Sin credenciales, sin DB, sin cron.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

PAGES = [
    {"id": "0221-que-hago", "url": "https://www.0221.com.ar/que-hago", "follow": 3},
    {"id": "vive-la-plata-agenda", "url": "https://vivelaplata.com.ar/agenda-cultural-que-hacer-este-finde-en-la-plata-26/", "follow": 0},
    {"id": "casa-metro", "url": "https://casametro.com.ar/", "follow": 0},
    {"id": "genda", "url": "https://agendalaplata.ar/", "follow": 0},
]
MAX_BYTES = 400 * 1024
TIMEOUT_SECONDS = 9
USER_AGENT = "PorAcaExplorador/0.2 (+noncommercial cultural link discovery)"
PERMALINK = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/[A-Za-z0-9_-]+/?",
    re.IGNORECASE,
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def extract_instagram_permalinks(text: str) -> list[str]:
    normal = html.unescape(text).replace("\\/", "/").replace("\\u0026", "&")
    matches = PERMALINK.findall(normal)
    unique = {}
    for m in matches:
        parts = urlparse(m)
        path = parts.path.rstrip("/") + "/"
        unique[f"https://www.instagram.com{path}"] = True
    return list(unique)[:25]


def candidate_article_links(raw_html: str, base_url: str, limit: int) -> list[str]:
    parser = Links()
    parser.feed(raw_html)
    domain = urlparse(base_url).hostname
    candidates = []
    for href in parser.links:
        url = urljoin(base_url, href)
        p = urlparse(url)
        if p.scheme != "https" or p.hostname != domain:
            continue
        if not p.path.startswith(("/que-hago/", "/la-plata/")):
            continue
        if url.rstrip("/") == base_url.rstrip("/") or url in candidates:
            continue
        candidates.append(url)
        if len(candidates) >= limit:
            break
    return candidates


def load(url: str) -> tuple[str | None, int | None, str]:
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            code = resp.status
            ctype = resp.headers.get("Content-Type", "")
            if "html" not in ctype.lower():
                return None, code, "NON_HTML"
            return resp.read(MAX_BYTES).decode("utf-8", errors="replace"), code, "HTML"
    except HTTPError as exc:
        return None, exc.code, "HTTP_ERROR"
    except (URLError, TimeoutError, OSError) as exc:
        return None, None, type(exc).__name__


def run():
    results = []
    discovered = {}
    for source in PAGES:
        html_body, code, status = load(source["url"])
        r = {"source": source["id"], "url": source["url"], "http": code, "result": status, "inspected": 0, "permalinks": []}
        if html_body:
            urls = [source["url"]]
            urls.extend(candidate_article_links(html_body, source["url"], source["follow"]))
            for url in urls:
                content = html_body if url == source["url"] else load(url)[0]
                if not content:
                    continue
                r["inspected"] += 1
                for permalink in extract_instagram_permalinks(content):
                    if permalink not in r["permalinks"]:
                        r["permalinks"].append(permalink)
                        discovered.setdefault(permalink, []).append(url)
        results.append(r)
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_public_sites_links_only",
        "new_post_links_detected": len(discovered),
        "permalinks_and_linking_page": [{"permalink": k, "found_on": v} for k, v in list(discovered.items())[:25]],
        "source_details": results,
        "not_verified_as_new_posts_or_events": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    Path("links-descubiertos.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        lines = ["# Descubrimiento de permalinks Instagram desde agendas", "", "Sin consultas directas a Instagram, sin Neon.", "",
                 "| Sitio | HTTP | Páginas leídas | Permalinks detectados |", "|---|---|---:|---:|"]
        for r in results:
            lines.append(f"| {r['source']} | {r['http'] or '—'} | {r['inspected']} | {len(r['permalinks'])} |")
        lines.append("")
        lines.append(f"**Enlaces distintos detectados: {len(discovered)}.** No son publicaciones nuevas verificadas.")
        with open(summary, "a", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    run()
