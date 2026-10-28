#!/usr/bin/env python3
"""Comparación controlada de URL exacta Instagram (/p/, /reel/).

No se usa login, scraping privado, proxies, ni APIs de Meta para extracción.
Al recibir un 429, se detiene toda consulta adicional a Instagram.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SOURCES = [
    {
        "id": "juntada-gamer-post-historico",
        "url": "https://www.instagram.com/p/DeHOPiJRwNi/",
        "historical_result": "13/10: texto de anuncio, fecha, sede y og:image, segun auditoria interna",
    },
    {
        "id": "feria-libro-reel-historico",
        "url": "https://www.instagram.com/reel/DeIP5x6RTRH/",
        "historical_result": "13/10: texto y vista previa de reel, no reproduccion de video",
    },
    {
        "id": "malisia-post-historico",
        "url": "https://www.instagram.com/malisialibros/p/DeW_6noxGOx/",
        "historical_result": "11/10: post exacto referenciado en Radar, verificacion previa no equivale a acceso actual",
    },
]
MAX_BYTES = 256 * 1024
TIMEOUT_SECONDS = 10
USER_AGENT = "PorAcaExplorador/0.2 (+noncommercial public research; one-time diagnostic)"


def valid_exact_url(url: str) -> bool:
    u = urlparse(url)
    return (
        u.scheme == "https"
        and u.hostname in ("www.instagram.com", "instagram.com")
        and bool(re.fullmatch(r"/(?:[^/]+/)?(?:p|reel)/[A-Za-z0-9_-]+/?", u.path))
    )


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.canonical = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta":
            key = d.get("property") or d.get("name")
            if key in ("og:title", "og:description", "og:image", "article:published_time", "description"):
                self.meta[key] = bool(d.get("content"))
        if tag == "link" and d.get("rel") == "canonical":
            self.canonical = d.get("href") or ""


def evaluate_html(raw_html: str, original_url: str) -> dict:
    parser = MetaParser()
    parser.feed(raw_html)
    shortcode = urlparse(original_url).path.rstrip("/").split("/")[-1]
    canon = parser.canonical
    canonical_matches = shortcode in urlparse(canon).path.split("/") if canon else False
    return {
        "fields_present": sorted(k for k, v in parser.meta.items() if v),
        "canonical_matches_shortcode": canonical_matches,
        "potential_post_metadata": canonical_matches and (
            parser.meta.get("og:description", False) or parser.meta.get("description", False)
        ),
    }


def probe(source: dict) -> dict:
    if not valid_exact_url(source["url"]):
        raise ValueError("Only exact public Instagram /p/ or /reel/ URLs are allowed")
    r = {"id": source["id"], "url": source["url"]}
    req = Request(source["url"], headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            r["http_status"] = resp.status
            typ = resp.headers.get("Content-Type", "")
            if "html" not in typ.lower():
                r["result"] = "NON_HTML"
                return r
            content = resp.read(MAX_BYTES + 1)
            r["truncated"] = len(content) > MAX_BYTES
            r.update(evaluate_html(content[:MAX_BYTES].decode("utf-8", errors="replace"), source["url"]))
            r["result"] = (
                "METADATA_CANDIDATA_NO_VALIDADA"
                if r["potential_post_metadata"]
                else "HTML_SIN_PRUEBA_DE_POST"
            )
    except HTTPError as exc:
        r["http_status"] = exc.code
        r["result"] = "RATE_LIMIT_STOP" if exc.code == 429 else "HTTP_RESTRICTED_OR_ERROR"
    except (URLError, TimeoutError, OSError) as exc:
        r["result"] = "NETWORK_OR_TIMEOUT"
        r["error_type"] = type(exc).__name__
    return r


def main():
    results = []
    for idx, source in enumerate(SOURCES):
        result = probe(source)
        results.append(result)
        if result["result"] == "RATE_LIMIT_STOP":
            for remaining in SOURCES[idx + 1:]:
                results.append({
                    "id": remaining["id"],
                    "url": remaining["url"],
                    "result": "NOT_ATTEMPTED_AFTER_429",
                })
            break
    result = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "one_time_exact_permalink_read_only",
        "historical_comparator": "docs/INSTAGRAM_FUENTES_Y_FLYERS_V1.md (Por Aca privado)",
        "no_stories": True,
        "no_neon_writes": True,
        "records": results,
    }
    Path("instagram-exact-result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        rows = [
            "# Instagram: comparación de publicaciones exactas",
            "",
            "No se accede a Stories ni se usan cuentas, tokens, API de extracción o proxies.",
            "",
            "| ID | HTTP | Resultado | Metadatos presentes |",
            "|---|---|---|---|",
        ]
        for item in results:
            rows.append("| " + item["id"] + " | "
                        + str(item.get("http_status", "—")) + " | "
                        + item["result"] + " | "
                        + ", ".join(item.get("fields_present", [])) + " |")
        rows += [
            "",
            "**Importante:** HTML o metadatos no prueban por sí solos texto completo, fecha/hora/sede de un evento.",
            "La prueba se detiene inmediatamente si Instagram devuelve HTTP 429.",
        ]
        with open(summary_path, "a", encoding="utf-8") as out:
            out.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
