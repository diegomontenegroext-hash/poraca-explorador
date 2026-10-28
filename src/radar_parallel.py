#!/usr/bin/env python3
"""Por Acá: Radar paralelo V0.1.

Recolecta sólo páginas públicas; escribe pistas NO verificadas en la
base Neon poraca_explorador. Nunca accede a neondb ni a la web privada.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

DB_NAME = "poraca_explorador"
DB_ROLE = "poraca_explorador_writer"
MAX_BODY = 450_000
REQUEST_TIMEOUT = 10
MAX_SOURCES = 20
MAX_DETAILS_FULL = 9
MAX_DETAILS_INCREMENTAL = 4
MAX_RUNTIME_SECONDS = 18 * 60
USER_AGENT = "PorAcaExplorador/0.1 (+public noncommercial cultural links; contact via repository)"
INSTAGRAM = re.compile(
    r"^/(?:[A-Za-z0-9_.]+/)?(p|reel)/([A-Za-z0-9_-]+)/?$",
    re.IGNORECASE,
)
WORDS = re.compile(
    r"concierto|festival|recital|estreno|funci[oó]n|muestra|taller|evento|"
    r"feria|cartelera|exposici[oó]n|milonga|programaci[oó]n|cine|teatro|"
    r"cultural|presenta|funciones|agenda",
    re.IGNORECASE,
)
LOCAL_DETAIL = re.compile(r"/(?:evento/[^/]+|eventos/[^/]+|"
    r"que-hago/[^/]+-n\d+|la-plata/[^/]+-n\d+|"
    r"agenda/[^/?]+/[^/?]+|espectaculos/[^/]+|cartelera/[^/]+)", re.IGNORECASE)
FALLBACK = [
    {"source_id": "src-0221", "url": "https://www.0221.com.ar/que-hago", "kind": "media"},
    {"source_id": "src-genda", "url": "https://agendalaplata.ar/", "kind": "agenda"},
    {"source_id": "src-alpedo", "url": "https://alpedo.ar/", "kind": "agenda"},
    {"source_id": "src-casa-metro", "url": "https://casametro.com.ar/cartelera/", "kind": "organizer"},
    {"source_id": "src-vive-la-plata", "url": "https://vivelaplata.com.ar/", "kind": "media"},
    {"source_id": "src-la-plata-tango", "url": "https://laplatatango.com.ar/agenda/lista/", "kind": "organizer"},
]


def compact(text: str, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()[:limit]


def exact_instagram(url: str) -> bool:
    p = urlparse(url)
    return (p.scheme == "https" and p.hostname in ("www.instagram.com", "instagram.com")
            and bool(INSTAGRAM.fullmatch(p.path)))


def clean_link(href: str, base_url: str) -> str | None:
    try:
        u = urlparse(urljoin(base_url, html.unescape(href).replace("\\/", "/")))
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            return None
        return f"{u.scheme}://{u.netloc.lower()}{quote(u.path.rstrip('/') + '/', safe='/%:@+~')}"
    except ValueError:
        return None


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[tuple[str, str]] = []
        self.jsonld: list[str] = []
        self._field = None
        self._text: list[str] = []
        self._anchor_href = None
        self._anchor: list[str] = []
        self._ld = False
        self._json: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key in {"og:title", "og:description", "description", "article:published_time"}:
                self.meta[key] = compact(a.get("content") or "", 500)
        elif tag == "title":
            self._field = "title"
            self._text = []
        elif tag == "a":
            self._anchor_href = a.get("href")
            self._anchor = []
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld = True
            self._json = []

    def handle_data(self, text):
        if self._field:
            self._text.append(text)
        if self._anchor_href:
            self._anchor.append(text)
        if self._ld:
            self._json.append(text)

    def handle_endtag(self, tag):
        if tag == "title" and self._field == "title":
            self.title = compact(" ".join(self._text))
            self._field = None
        if tag == "a":
            if self._anchor_href:
                self.links.append((self._anchor_href, compact(" ".join(self._anchor))))
            self._anchor_href = None
            self._anchor = []
        if tag == "script" and self._ld:
            self.jsonld.append("".join(self._json)[:100_000])
            self._ld = False

def parse_html(body: str) -> Parser:
    p = Parser()
    p.feed(body)
    return p


def structured_event(page: Parser) -> dict:
    """Read explicit schema.org event roles, never infer a performer from title."""
    def name_of(value):
        if isinstance(value,dict):
            return compact(value.get("name") or "",180)
        if isinstance(value,str):
            return compact(value,180)
        return ""

    for script in page.jsonld[:10]:
        try:
            item = json.loads(script)
        except (json.JSONDecodeError, ValueError):
            continue
        queue = item if isinstance(item, list) else [item]
        steps = 0
        while queue and steps < 160:
            steps += 1
            node = queue.pop(0)
            if not isinstance(node, dict):
                continue
            typ = node.get("@type", "")
            values = typ if isinstance(typ,list) else [typ]
            is_event = any(isinstance(t,str) and
                t.rsplit("/",1)[-1].casefold() in (
                    "event","musicevent","theaterevent","danceevent",
                    "festivalevent","festival","visualartsevent",
                    "educationevent","screeningevent","comedyEvent".casefold())
                for t in values)
            if is_event:
                date_value = node.get("startDate","")
                loc = node.get("location")
                org = node.get("organizer")
                if isinstance(loc, list):
                    loc = next((n for n in loc if isinstance(n,(dict,str))),None)
                if isinstance(org, list):
                    org = next((n for n in org if isinstance(n,(dict,str))),None)
                performers = []
                performer_data = node.get("performer") or node.get("performers") or []
                if not isinstance(performer_data,list):
                    performer_data = [performer_data]
                generic_role_placeholders = {
                    "organization","person","musicgroup","performinggroup",
                    "performingartist","performer","artist","group",
                    "unknown","unspecified","null","na","tbd",
                    "artista","organizacion",
                }
                for performer in performer_data[:12]:
                    value = name_of(performer)
                    # Some ticketing pages misuse a schema TYPE token
                    # (e.g. the literal "Organization") as performer.name.
                    # It is not an artist and must never become a node lead.
                    normalized = re.sub(r"[^a-z]","",value.casefold())
                    if (3 <= len(value) <= 180
                        and normalized not in generic_role_placeholders
                        and value not in performers):
                        performers.append(value)
                return {
                    "name": compact(str(node.get("name") or "")),
                    "date": str(date_value)[:40] if date_value else None,
                    "venue": name_of(loc) or None,
                    "organizer": name_of(org) or None,
                    "performers": performers[:8],
                }
            graph = node.get("@graph")
            if isinstance(graph,list):
                queue.extend(graph[:30])
            elif isinstance(graph,dict):
                queue.append(graph)
    return {}

def iso_event_fields(date_value: str | None) -> tuple[str | None, str | None]:
    """Convert absolute schema.org timestamps to LOCAL Argentina event time.

    Date-only starts retain unknown hours. Offset-naive timestamps remain
    wall-clock values and require independent confirmation; Z/+HH:MM inputs
    represent instants and must be converted to America/Argentina/Buenos_Aires.
    Never parse by truncating at 'T' as that makes UTC 23:30 look like 23:30 ART.
    """
    if not isinstance(date_value,str):
        return None,None
    raw=date_value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}",raw):
        try:return datetime.strptime(raw,"%Y-%m-%d").date().isoformat(),None
        except ValueError:return None,None
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"
        r"(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:?\d{2})?",raw,re.I):
        return None,None
    try:
        parsed=datetime.fromisoformat(raw.replace("Z","+00:00").replace("z","+00:00"))
        if parsed.tzinfo is not None:
            parsed=parsed.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
    except ValueError:
        return None,None
    return parsed.date().isoformat(),parsed.strftime("%H:%M")


def fetch(url: str) -> tuple[int | None, str | None, str | None]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            if "html" not in response.headers.get("Content-Type", "").lower():
                return response.status, None, "NON_HTML"
            data = response.read(MAX_BODY)
            return response.status, data.decode("utf-8", errors="replace"), None
    except HTTPError as err:
        return err.code, None, "RATE_LIMIT" if err.code == 429 else "HTTP_ERROR"
    except (URLError, TimeoutError, OSError, UnicodeError, ValueError) as err:
        return None, None, type(err).__name__


def discover_links(body: str, page: Parser, base_url: str) -> list[tuple[str, str]]:
    host = urlparse(base_url).hostname
    results: dict[str, str] = {}
    raw = html.unescape(body).replace("\\/", "/")
    permalink = re.compile(
        r"https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/[A-Za-z0-9_-]+/?",
        re.IGNORECASE,
    )
    for match in permalink.findall(raw)[:20]:
        cleaned = clean_link(match.replace("http://", "https://"), base_url)
        if cleaned and exact_instagram(cleaned):
            results[cleaned] = "instagram permalink"
    for href, title in page.links[:400]:
        u = clean_link(href, base_url)
        if not u or u in results or u.rstrip("/") == base_url.rstrip("/"):
            continue
        parsed = urlparse(u)
        segments = [unquote(part).lower() for part in parsed.path.strip("/").split("/") if part]
        # Las paginas de categorias, etiquetas y paginacion NO son eventos.
        if not exact_instagram(u) and (
            any(part in {"categoria", "categoría", "category", "categorias", "recintos", "tag", "tags",
                         "page", "pagina", "página", "lista", "wp-content", "author", "archivo"} for part in segments)
            or (segments and segments[-1] in {"agenda", "eventos", "clases",
                "teatro", "musica", "cine", "exposiciones", "cartelera"})
        ):
            continue
        if exact_instagram(u):
            results[u] = title
        elif parsed.hostname == host and (LOCAL_DETAIL.search(parsed.path) or
                                           (WORDS.search(title) and
                                            len(parsed.path.strip("/").split("/")) >= 2)):
            if "/wp-content/" in parsed.path or parsed.path.lower().endswith((".png/", ".jpg/", ".webp/", ".pdf/")):
                continue
            results[u] = title
        if len(results) >= 30:
            break
    return list(results.items())[:18]


def make_candidate(url: str, source_id: str, label: str, detail: Parser | None,
                   http_status: int | None) -> dict:
    inst = exact_instagram(url)
    kind = ("instagram_reel" if "/reel/" in url else "instagram_post") if inst else (
        "news_article" if "/que-hago/" in url or "/la-plata/" in url else "event_detail"
    )
    event = structured_event(detail) if detail else {}
    date, time = iso_event_fields(event.get("date"))
    title = compact(event.get("name") or ((detail.meta.get("og:title") or detail.title) if detail else label))
    summary = compact((detail.meta.get("og:description") or detail.meta.get("description") or "")
                      if detail else "", 380)
    evidence = {
        "method": "public_html_read_only",
        "source_id": source_id,
        "detail_http": http_status,
        "detail_opened": detail is not None,
        "structured_event_found": bool(event),
        "metadata_keys": sorted(detail.meta) if detail else [],
        "announced_only": True,
    }
    if event:
        # These are explicit JSON-LD ROLE labels, not inferred from title,
        # locality, a venue's page or popularity. Some sites assert no
        # cultural role at all; do not manufacture an empty "lead".
        signal_artists = event.get("performers",[])
        signal_organizers = [event["organizer"]] if event.get("organizer") else []
        signal_venues = [event["venue"]] if event.get("venue") else []
        if signal_artists or signal_organizers or signal_venues:
            evidence["cultural_signals_v1"] = {
                "status": "lead_unverified",
                "origin": "schema_org_event_on_opened_page",
                "artists": signal_artists,
                "organizers": signal_organizers,
                "venues": signal_venues,
            }
    return {
        "candidate_key": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        "original_url": url, "kind": kind, "title": title or None,
        "summary": summary or None, "event_date": date, "event_time": time,
        "organizer": event.get("organizer"), "venue": event.get("venue"),
        "source_id": source_id, "evidence": evidence,
    }


def scan_source(source: dict, max_details: int = MAX_DETAILS_INCREMENTAL,
                deadline: float | None = None) -> tuple[dict, list[dict]]:
    source_id, url = source["source_id"], source["url"]
    status, body, error = fetch(url)
    check = {"source_id": source_id, "http_status": status, "error_type": error,
             "pages_opened": 1 if body is not None else 0, "status": "ok" if body else "failed"}
    if body is None:
        check["discovered_links"] = 0
        return check, []
    parsed = parse_html(body)
    links = discover_links(body, parsed, url)
    candidates = []
    # El primer nivel privilegia posts exactos e ítems, nunca categorías.
    ordered = sorted(links, key=lambda item: (not exact_instagram(item[0]),))
    for link, label in ordered[:max_details]:
        if deadline is not None and time.monotonic() >= deadline:
            break
        detail_status, detail_body, detail_err = fetch(link)
        detail = parse_html(detail_body) if detail_body else None
        if detail:
            check["pages_opened"] += 1
        candidate = make_candidate(link, source_id, label, detail, detail_status)
        if detail_err:
            candidate["evidence"]["detail_error"] = detail_err
        candidates.append(candidate)
        if detail_status == 429:
            break
        # Segundo nivel: posts exactos publicados dentro de notas/carteleras.
        # No se accede al feed, y se limita a dos enlaces por nota.
        if detail_body and not exact_instagram(link) and len(candidates) < max_details + 3:
            embedded = [x for x, _ in discover_links(detail_body, detail, link) if exact_instagram(x)]
            for permalink in embedded[:2]:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                if any(existing["original_url"] == permalink for existing in candidates):
                    continue
                post_status, post_body, post_error = fetch(permalink)
                post_page = parse_html(post_body) if post_body else None
                post = make_candidate(permalink, source_id, "Enlace exacto desde la nota", post_page, post_status)
                post["evidence"]["linked_from"] = link
                if post_error:
                    post["evidence"]["detail_error"] = post_error
                candidates.append(post)
                if post_status == 429:
                    break
        if len(candidates) >= max_details + 3:
            break
    check["discovered_links"] = len(links)
    return check, candidates


def save_check(conn, run_id: str, source: dict, check: dict, candidates: list[dict]) -> int:
    new_count = 0
    with conn.cursor() as cur:
        for c in candidates:
            cur.execute(
                """INSERT INTO candidates(candidate_key,original_url,kind,title,summary,event_date,event_time,
                       organizer,venue,evidence,first_source_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                   ON CONFLICT(original_url) DO NOTHING RETURNING candidate_key""",
                (c["candidate_key"],c["original_url"],c["kind"],c["title"],c["summary"],
                 c["event_date"],c["event_time"],c["organizer"],c["venue"],
                 json.dumps(c["evidence"]),c["source_id"]),
            )
            if cur.fetchone():
                new_count += 1
            else:
                cur.execute("""UPDATE candidates SET last_seen_at=now(), seen_count=seen_count+1,
                        title=CASE WHEN %s::text IS NOT NULL AND %s::text <> '' THEN %s::text ELSE title END,
                        summary=CASE WHEN %s::text IS NOT NULL AND %s::text <> '' THEN %s::text ELSE summary END,
                        event_date=COALESCE(event_date,%s::date), event_time=COALESCE(event_time,%s::text),
                        organizer=COALESCE(organizer,%s),venue=COALESCE(venue,%s),
                        evidence=CASE WHEN %s THEN evidence || %s::jsonb ELSE evidence END
                        WHERE original_url=%s""",
                    (c["title"],c["title"],c["title"],c["summary"],c["summary"],c["summary"],
                     c["event_date"],c["event_time"],c["organizer"],c["venue"],
                     bool(c["evidence"].get("detail_opened")),json.dumps(c["evidence"]),c["original_url"]))
        cur.execute(
            """INSERT INTO source_checks(run_id,source_id,status,http_status,pages_opened,
                discovered_links,error_type) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (run_id,source["source_id"],check["status"],check["http_status"],
             check["pages_opened"],check["discovered_links"],check["error_type"]),
        )
        cadence = source["cadence_hours"] if check["status"] == "ok" else min(6,source["cadence_hours"])
        cur.execute(
            """UPDATE sources SET last_checked_at=now(),next_due_at=now()+(%s*interval '1 hour'),
                last_access_result=%s WHERE source_id=%s""",
            (cadence,check["status"]+((":"+str(check["http_status"])) if check["http_status"] else ""),
             source["source_id"]),
        )
    conn.commit()
    return new_count


def db_connect():
    url = os.environ.get("NEON_EXPLORADOR_DATABASE_URL", "")
    if not url:
        raise RuntimeError("NEON_EXPLORADOR_DATABASE_URL missing: add GitHub Actions repository secret")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install dependency psycopg[binary] for database writes") from exc
    conn = psycopg.connect(url, connect_timeout=12)
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(),current_user")
        database_name, role_name = cur.fetchone()
    if database_name != DB_NAME or role_name != DB_ROLE:
        conn.close()
        raise RuntimeError("Connection refused: database/role is not isolated Radar parallel target")
    return conn


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry-run", "write"], default="dry-run")
    parser.add_argument("--scope", choices=["full", "incremental"], default="incremental")
    args = parser.parse_args()
    deadline = time.monotonic() + MAX_RUNTIME_SECONDS
    max_details = MAX_DETAILS_FULL if args.scope == "full" else MAX_DETAILS_INCREMENTAL
    run_id = "explorador-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    conn = None
    if args.mode == "write":
        try:
            conn = db_connect()
        except Exception as exc:
            print("CONFIG_ERROR: "+str(exc), file=sys.stderr)
            return 2
        with conn.cursor() as cur:
            if args.scope == "full":
                cur.execute("""SELECT source_id,url,kind,cadence_hours FROM sources
                               WHERE enabled
                               ORDER BY last_checked_at NULLS FIRST, source_id LIMIT %s""",
                            (MAX_SOURCES,))
            else:
                cur.execute("""SELECT source_id,url,kind,cadence_hours FROM sources
                               WHERE enabled AND next_due_at<=now()
                               ORDER BY next_due_at,source_id LIMIT %s""",
                            (MAX_SOURCES,))
            rowset = cur.fetchall()
            sources = [dict(source_id=a,url=b,kind=c,cadence_hours=d) for a,b,c,d in rowset]
            cur.execute("INSERT INTO radar_runs(run_id) VALUES (%s)",(run_id,))
        conn.commit()
    else:
        sources = [dict(source_id=s["source_id"],url=s["url"],kind=s["kind"],
                        cadence_hours=24) for s in FALLBACK]
    count, good, seen, new = 0, 0, 0, 0
    try:
        for source in sources:
            if time.monotonic() >= deadline:
                print("RUN_BUDGET_EXHAUSTED: remaining sources remain due", file=sys.stderr)
                break
            check, candidates = scan_source(source,max_details=max_details,deadline=deadline)
            count += 1
            good += int(check["status"] == "ok")
            seen += len(candidates)
            if conn:
                new += save_check(conn,run_id,source,check,candidates)
            print(json.dumps({"source":source["source_id"], "http":check["http_status"],
                              "status":check["status"],"pages":check["pages_opened"],
                              "links_found":check["discovered_links"],
                              "error_type":check["error_type"],
                              "candidates":len(candidates),"sample_urls":[x["original_url"] for x in candidates[:2]]},
                             ensure_ascii=False))
        status = "completed" if good == count and count == len(sources) else "partial"
        if conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE radar_runs SET finished_at=now(),status=%s,sources_attempted=%s,
                    sources_success=%s,candidates_seen=%s,candidates_new=%s,note=%s
                    WHERE run_id=%s""",
                    (status,count,good,seen,new,
                     ("NO_SOURCES_DUE:" if count == 0 else "SCOPE_"+args.scope.upper()+":")
                     + " Candidates remain unverified, not accepted events",run_id))
            conn.commit()
        result = {"run_id":run_id,"mode":args.mode,"scope":args.scope,"status":status,
                  "sources_selected":len(sources),"sources_attempted":count,
                  "sources_success":good,"candidates_seen":seen,"candidates_new":new,
                  "database_written":bool(conn)}
        print("RADAR_RESULT "+json.dumps(result,ensure_ascii=False))
        summary = os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary,"a",encoding="utf-8") as f:
                f.write("# Radar paralelo · "+run_id+"\n\n")
                f.write("| Modo | Estado | Fuentes | Accesibles | Candidatos vistos | Nuevos en Neon |\n"
                        "|---|---|---:|---:|---:|---:|\n")
                f.write(f"| {args.mode}/{args.scope} | {status} | {count} | {good} | {seen} | {new} |\n\n")
                f.write("Los candidatos no son eventos verificados ni datos publicados en la web.\n")
        return 0 if (not sources or good) else 1
    except Exception as exc:
        if conn:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute("""UPDATE radar_runs SET finished_at=now(),status='error',note=%s
                               WHERE run_id=%s""",(type(exc).__name__,run_id))
            conn.commit()
        print("RADAR_ERROR "+type(exc).__name__,file=sys.stderr)
        return 1
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
