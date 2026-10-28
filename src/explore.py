#!/usr/bin/env python3
"""Explorador Por Acá 0.1: prueba manual, sin escrituras ni credenciales."""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

SOURCES = [
    {"id": "centro-arte-unlp", "kind": "web_oficial", "url": "https://www.centrodearte.unlp.edu.ar/"},
    {"id": "casa-metro", "kind": "web_oficial", "url": "https://casametro.com.ar/"},
    {"id": "la-plata-tango", "kind": "web_oficial", "url": "https://laplatatango.com.ar/agenda/lista/"},
    {"id": "alpedo", "kind": "agenda", "url": "https://alpedo.ar/"},
    {"id": "0221-que-hago", "kind": "agenda", "url": "https://www.0221.com.ar/que-hago"},
    {"id": "genda", "kind": "agenda", "url": "https://agendalaplata.ar/"},
    {"id": "instagram-cineselect", "kind": "instagram", "url": "https://www.instagram.com/cineselect/"},
    {"id": "instagram-cineecoselect", "kind": "instagram", "url": "https://www.instagram.com/cineecoselect/"},
    {"id": "instagram-casa52", "kind": "instagram", "url": "https://www.instagram.com/casa52casa/"},
]
TIMEOUT = 10
MAX_BYTES = 400 * 1024
USER_AGENT = "PorAcaExplorador/0.1 (+noncommercial public research; manual)"
KEYWORDS = re.compile(
    r"agenda|evento|funci[oó]n|taller|m[uú]sica|muestra|teatro|cine|entrada|"
    r"concierto|recital|festival|octubre|noviembre|2026|programaci[oó]n",
    re.IGNORECASE,
)


def clean(value: str, limit: int = 130) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()[:limit]


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.heading: list[str] = []
        self.links: list[dict[str, str]] = []
        self.description = ""
        self._active: str | None = None
        self._text: list[str] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta" and (attributes.get("name") or "").lower() == "description":
            self.description = clean(attributes.get("content") or "", 220)
        if tag in ("title", "h1", "h2", "h3") and self._active is None:
            self._active, self._text = tag, []
        if tag == "a" and self._href is None:
            self._href = attributes.get("href")
            self._link_text = []

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._text.append(data)
        if self._href is not None:
            self._link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._active:
            value = clean(" ".join(self._text))
            if tag == "title" and not self.title:
                self.title = value
            elif value and tag in ("h1", "h2", "h3") and len(self.heading) < 8:
                self.heading.append(value)
            self._active, self._text = None, []
        if tag == "a" and self._href is not None:
            label = clean(" ".join(self._link_text))
            if KEYWORDS.search(label + " " + self._href) and len(self.links) < 5:
                self.links.append({"text": label, "href": self._href[:300]})
            self._href, self._link_text = None, []


def extract(html_text: str, base_url: str) -> dict:
    parser = PageParser()
    parser.feed(html_text)
    return {
        "page_title": parser.title,
        "description": parser.description,
        "headings": parser.heading,
        "candidate_links_unverified": [
            {"label": link["text"], "url": urljoin(base_url, link["href"])}
            for link in parser.links
        ],
    }


def probe(source: dict[str, str]) -> dict:
    result = dict(source)
    request = Request(
        source["url"],
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            result["status_http"] = response.status
            content_type = response.headers.get("Content-Type", "")
            result["content_type"] = content_type[:90]
            if "html" not in content_type.lower():
                result["result"] = "NON_HTML"
                return result
            body = response.read(MAX_BYTES + 1)
            result["truncated"] = len(body) > MAX_BYTES
            page = body[:MAX_BYTES].decode("utf-8", errors="replace")
            result.update(extract(page, response.geturl()))
            if source["kind"] == "instagram":
                result["result"] = "HTML_RECIBIDO_POSTS_NO_VERIFICADOS"
                result["candidate_links_unverified"] = []
            else:
                result["result"] = "HTML_LEIDO_PISTAS_SIN_VERIFICAR"
    except HTTPError as exc:
        result["status_http"] = exc.code
        result["result"] = "ACCESO_RESTRINGIDO" if exc.code in (401, 403, 429) else "ERROR_HTTP"
    except (URLError, TimeoutError, OSError) as exc:
        result["result"] = "ERROR_RED_O_TIMEOUT"
        result["error_type"] = type(exc).__name__
    except Exception as exc:
        result["result"] = "ERROR_LECTURA"
        result["error_type"] = type(exc).__name__
    return result


def markdown_cell(text: str) -> str:
    return clean(text, 80).replace("|", "/").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    results = [probe(source) for source in SOURCES]
    output = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "manual_read_only_no_neon",
        "sources": results,
    }
    Path("resultado-exploracion.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        rows = [
            "# Por Acá · Prueba de fuentes",
            "",
            "Prueba sin credenciales, sin cambios a Neon, sin captación automática de eventos.",
            "",
            "| Fuente | Estado HTTP | Lectura | Título | Pistas |",
            "|---|---|---|---|---:|",
        ]
        for r in results:
            rows.append(
                "| " + markdown_cell(r["id"])
                + " | " + str(r.get("status_http", "—"))
                + " | " + markdown_cell(r["result"])
                + " | " + markdown_cell(r.get("page_title", ""))
                + " | " + str(len(r.get("candidate_links_unverified", []))) + " |"
            )
        rows.extend([
            "",
            "> **Advertencia:** HTTP 200 no demuestra acceso a posts de Instagram. "
            "Las pistas HTML no constituyen eventos ni fuentes originales validadas.",
        ])
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
