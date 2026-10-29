#!/usr/bin/env python3
"""RADAR DEFINITIVO 0.2 — ingesta reversible a Neon y cursor por fuente.

Escribe SOLO al schema radar_definitivo; nunca acepta ni publica eventos.
Instagram: solo permalinks publicos encontrados en fuentes web; perfiles
catalogados como 'discover_only' no son scrapeados ni se leen Stories.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone, date, timedelta
import hashlib
import json
import os
import re
import sys
import time
import uuid
from urllib.parse import urlparse, urljoin, urlsplit, urlunsplit, quote, parse_qsl, urlencode
from zoneinfo import ZoneInfo

from radar_parallel import (
    clean_link, compact, discover_links, WORDS, LOCAL_DETAIL,
    exact_instagram, fetch, make_candidate, parse_html, structured_event,
)
from radar_agenda_adapters import extract_listings, special_links, tidy
from radar_evidence_quality import summarize as summarize_evidence_quality
from radar_gate_alias_preflight import SQL as SHADOW_ALIAS_SQL, summarize as summarize_aliases
from radar_function_gate_review import query as function_review_sql, summarize as summarize_function_review
from instagram_seed_inbox import choose_seed_sources, public_instagram_metadata
from radar_genda_browser import render_date_pages, validated_date_pages, render_argentino_event_pages, render_alpedo_date_pages

SCHEMA = "radar_definitivo"
EXPECTED_LAB_DB = "poraca_explorador"
EXPECTED_LAB_ROLE = "poraca_explorador_writer"
EXPECTED_OPERATIVE_DB = "neondb"
EXPECTED_OPERATIVE_LOGIN = "poraca_definitivo_ingest"
EXPECTED_OPERATIVE_SCOPE = "poraca_definitivo_scope"
MAX_SOURCES_FULL = 75
MAX_SOURCES_INCREMENTAL = 45
MAX_DETAILS_FULL = 6
MAX_DETAILS_INCREMENTAL = 4
MAX_REQUESTS = 360
MAX_INSTAGRAM = 24
MAX_SECONDS = 24 * 60
MAX_DOMAIN_REQUESTS = 26
MAX_EMBEDDED_PER_DETAIL = 3
MIN_SOURCE_DELAY_SECONDS = 0.2
MIN_INSTAGRAM_INTERVAL_SECONDS = 4.0
MAX_DISCOVERY_LINKS = 100

class Budget:
    def __init__(self, seconds=MAX_SECONDS):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.total = 0
        self.instagram = 0
        self.last_instagram_request = None
        self.by_host = Counter()
        self.blocked_hosts = set()

    def can_fetch(self, url):
        try:
            p = urlparse(url)
            host = p.hostname or ""
            if p.scheme != "https" or not host:
                return False
            if time.monotonic() >= self.deadline or self.total >= MAX_REQUESTS:
                return False
            if host in self.blocked_hosts or self.by_host[host] >= MAX_DOMAIN_REQUESTS:
                return False
            if exact_instagram(url) and self.instagram >= MAX_INSTAGRAM:
                return False
            return True
        except ValueError:
            return False

    def request(self, url):
        if not self.can_fetch(url):
            return None, None, "BUDGET_OR_DOMAIN_LIMIT"
        host = urlparse(url).hostname
        self.total += 1
        self.by_host[host] += 1
        if exact_instagram(url):
            self.instagram += 1
            if self.last_instagram_request is not None:
                pause = MIN_INSTAGRAM_INTERVAL_SECONDS - (time.monotonic()-self.last_instagram_request)
                if pause>0 and pause<self.remaining():
                    time.sleep(pause)
            self.last_instagram_request=time.monotonic()
        if MIN_SOURCE_DELAY_SECONDS:
            time.sleep(MIN_SOURCE_DELAY_SECONDS)
        status, body, error = fetch(url)
        if status == 429:
            self.blocked_hosts.add(host)
        return status, body, error

    def remaining(self):
        return max(0, int(self.deadline - time.monotonic()))


def isolated_connection():
    # Automatic cutover only when the operator supplies a dedicated secret.
    # Until then Github continues experimental ingestion and is explicit about target.
    operational = bool(os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL"))
    value = (os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL") if operational
             else os.getenv("NEON_EXPLORADOR_DATABASE_URL",""))
    if not value:
        raise RuntimeError("Missing configured Neon secret")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install psycopg[binary]") from exc
    conn = psycopg.connect(value, connect_timeout=12)
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(),session_user,to_regclass('radar_definitivo.sources')")
        db,login,table=cur.fetchone()
        expected_db = EXPECTED_OPERATIVE_DB if operational else EXPECTED_LAB_DB
        expected_login = EXPECTED_OPERATIVE_LOGIN if operational else EXPECTED_LAB_ROLE
        if db != expected_db or login != expected_login or table is None:
            conn.close()
            raise RuntimeError("Isolation guard: database/role/schema mismatch")
        if operational:
            cur.execute("SET ROLE poraca_definitivo_scope")
            cur.execute("SELECT current_user,has_table_privilege(current_user,'public.radar_agenda_events','INSERT')")
            scoped_role,can_publish=cur.fetchone()
            if scoped_role != EXPECTED_OPERATIVE_SCOPE or can_publish:
                conn.close()
                raise RuntimeError("Scope guard: operational role has unexpected publish privileges")
    conn.commit()
    print("TARGET "+("OPERATIONAL_STAGING_NEONDB" if operational else
                     "EXPERIMENTAL_PORACA_EXPLORADOR"),flush=True)
    return conn


def choose_sources(conn, mode):
    where = ("enabled AND monitoring_mode='fetch'" if mode == "full" else
             "enabled AND monitoring_mode='fetch' AND next_due_at<=now()")
    with conn.cursor() as cur:
        cur.execute(f"""SELECT source_id,name,url,source_role,priority,cadence_hours,
                        consecutive_failures FROM radar_definitivo.sources
                        WHERE {where}
                        ORDER BY last_checked_at ASC NULLS FIRST, priority DESC,source_id
                        LIMIT %s""", (MAX_SOURCES_FULL if mode=="full" else MAX_SOURCES_INCREMENTAL,))
        sources=[dict(source_id=a,name=b,url=c,source_role=d,priority=e,
                     cadence_hours=f,consecutive_failures=g,seed_urls=[])
                 for a,b,c,d,e,f,g in cur.fetchall()]
        # The frozen canonical baseline is used as a WATCHLIST of ORIGINAL URLs
        # only. It is never copied into observations and cannot make a match.
        # The actual original page must still be opened by this run.
        if os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL"):
            for src in sources:
                host=urlparse(src["url"]).hostname or ""
                root=src["url"]
                # Avoid duplicate watches of mirrored organizer URLs.
                if "lumenartis.org" in host and "/proximos-eventos" not in root:
                    continue
                if "teatrometrolp.com.ar" in host and "/entradas/cartelera/" not in root:
                    continue
                patterns=(
                    ["https://www.alternativateatral.com/obra%"] if "alternativateatral.com" in host else
                    ["https://casametro.com.ar/evento/%"] if "casametro.com.ar" in host else
                    ["https://www.teatrometrolp.com.ar/entrada/%"] if "teatrometrolp.com.ar" in host else
                    ["https://teatroargentino.gba.gob.ar/meet/%"] if "teatroargentino.gba.gob.ar" in host else
                    ["https://lumenartis.org/?p=%"] if "lumenartis.org" in host else
                    []
                )
                if not patterns: continue
                cur.execute("""WITH watchlist AS (
                         SELECT baseline_url AS url, min(event_date) next_date,
                                min(CASE
                                   WHEN parity_state='original_date_time_match_venue_hold' THEN 0
                                   WHEN parity_state='not_recovered' THEN 1
                                   WHEN parity_state='source_date_match_time_hold' THEN 2
                                   ELSE 3 END) gap_priority
                         FROM radar_definitivo.baseline_event_parity_checked_v3
                         WHERE event_date>=current_date-interval '7 days'
                           AND event_date<=current_date+interval '80 days'
                           AND baseline_url LIKE ANY(%s)
                         GROUP BY baseline_url
                       )
                       SELECT w.url FROM watchlist w
                       LEFT JOIN radar_definitivo.candidates c ON c.url=w.url
                       ORDER BY w.gap_priority ASC,
                                c.last_seen_at ASC NULLS FIRST,
                                w.next_date ASC,w.url ASC LIMIT %s""",
                     (patterns,MAX_DETAILS_FULL if mode=="full" else MAX_DETAILS_INCREMENTAL))
                src["seed_urls"]=[row[0] for row in cur.fetchall() if row[0]]
        return sources


def safe_public_link(raw,base):
    """Resolve complete public URLs, preserving only safe agenda date parameters."""
    try:
        url=urljoin(base,raw.strip())
        p=urlsplit(url)
        if p.scheme!="https" or not p.hostname or p.username or p.password:
            return None
        if p.port not in (None,443):
            return None
        if p.hostname in {"localhost","127.0.0.1","0.0.0.0","::1"} or p.hostname.endswith(".local"):
            return None
        path=quote(p.path or "/",safe="/%:@+~,-")
        q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True)
            if k in {"fecha","date","month","year","p","post_type"} and len(v)<=16]
        canonical=urlunsplit(("https",p.hostname.lower(),path,urlencode(q),""))
        return canonical if len(canonical)<=1400 else None
    except (ValueError,UnicodeError):
        return None


def links_from_page(body, page, url):
    """Preserve links and date parameters; never treat profile roots as Instagram posts."""
    seen=set()
    out=[]
    hostname=urlparse(url).hostname
    # Original anchor links, not a fixed first-18 excerpt from the pilot.
    for href,label in page.links[:900]:
        target=safe_public_link(href,url)
        if not target or target in seen or target.rstrip("/")==url.rstrip("/"):
            continue
        p=urlparse(target)
        parts=[x.casefold() for x in p.path.strip("/").split("/") if x]
        if not exact_instagram(target) and (
            any(x in {"categoria","categoría","categorias","tag","tags","recintos",
                      "page","pagina","página","lista","archivo","author","wp-content"} for x in parts)
            or any(target.lower().endswith(ext) for ext in (".jpg",".jpeg",".png",".webp",".pdf",".svg",".mp4"))):
            continue
        if exact_instagram(target) or (
            p.hostname==hostname and (LOCAL_DETAIL.search(p.path) or
            (WORDS.search(label or "") and len(parts)>=2))):
            seen.add(target)
            out.append((target,label))
            if len(out)>=MAX_DISCOVERY_LINKS:
                break
    # Permalinks from source HTML, including embeds or scripts.
    for target,label in discover_links(body,page,url):
        normalized=safe_public_link(target,url)
        if normalized and exact_instagram(normalized) and normalized not in seen:
            out.append((normalized,label))
            seen.add(normalized)
    return sorted(out,key=lambda item:(not exact_instagram(item[0]),item[0]))


def curator_multi_plan_preview(caption):
    """Non-canonical line-level leads from a curated multi-plan caption.

    A curator may mention venues, artists and menus in one reel. This only
    records literal fragments and account handles. It never proposes an
    approved event, a parsed date/time, venue identity or organizer role.
    """
    if not isinstance(caption,str) or len(caption)>40000:
        return None
    weekdays=r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
    plans=[]
    anchor_days=set()
    for raw_line in caption.splitlines()[:120]:
        line=tidy(raw_line).strip('"')
        if len(line)<12 or len(line)>800:
            continue
        handles=list(dict.fromkeys(re.findall(r"@([A-Za-z0-9._]{2,40})",line)))
        if not handles:
            continue
        # No interpretation of roles, format or implied calendar date.
        literal=re.match(r"^"+weekdays+r"\b",line,re.I)
        if literal:
            anchor_days.add(literal.group(0).casefold())
        plans.append({"position":len(plans)+1,"fragment":line,
                      "mentioned_accounts":handles,
                      "literal_weekday":literal.group(0).casefold() if literal else None})
        if len(plans)>=25:
            break
    # Reject a normal post with collaborator tags rather than a multi-day agenda.
    if len(plans)<3 or len(anchor_days)<2:
        return None
    return {"state":"review_only","classification":"curatorial_multiplan_caption",
            "plan_lead_count":len(plans),"event_count":0,
            "original_confirmation_required":True,
            "source_not_organizer":True,
            "date_or_venue_inferred":False,
            "leads":plans}


def scan_exact_instagram_seeds(source, budget):
    """Leer exclusivamente permalinks aportados, NUNCA el perfil de origen."""
    check = dict(source_id=source["source_id"], http_status=None, status="failed",
                 error_type="EXACT_PERMALINK_ONLY_PROFILE_NOT_SCANNED",
                 details_opened=0, links_found=0, _listings=[], _seed_only=True)
    candidates = []
    for post in source["seed_urls"]:
        if not budget.can_fetch(post):
            break
        status, body, error = budget.request(post)
        check["http_status"] = status
        if not body:
            check["error_type"] = error or "PERMALINK_UNAVAILABLE"
            if status == 429:
                break
            continue
        detail = parse_html(body)
        candidate = make_candidate(post, source["source_id"], "shared_exact_permalink", detail, status)
        candidate["evidence"].update({
            "radar": "definitivo", "source_root": source["url"],
            "seeded_permalink": True, "seed_method": "shared_public_exact_url",
            "profile_not_scanned": True,
            "claimed_account": source["account"],
            "attribution_status": "requires_original_check",
        })
        # El resumen visible del candidato tiene limite; mantener el texto
        # disponible para poder separar varios anuncios con rigor posterior.
        full_meta = public_instagram_metadata(body)
        caption = full_meta.get("description") or full_meta.get("og:description") or ""
        if caption:
            candidate["evidence"]["public_caption_text"] = caption
            if source.get("source_role")=="curadora":
                multi=curator_multi_plan_preview(caption)
                if multi:
                    candidate["evidence"]["multi_plan_review"] = multi
        candidate["evidence"]["public_caption_extraction"] = "html_meta_full_v2"
        claimed_url = full_meta.get("og:url") or full_meta.get("canonical_url")
        candidate["evidence"]["metadata_source_url"] = claimed_url
        if claimed_url:
            p = urlsplit(claimed_url)
            account = source["account"].lower()
            pieces = [s.lower() for s in p.path.strip("/").split("/")]
            if (p.hostname in {"instagram.com", "www.instagram.com"}
                and len(pieces) >= 3 and pieces[0] == account
                and pieces[1] in {"reel", "p"}):
                candidate["evidence"]["attribution_status"] = "public_url_account_matched"
        image_url = extract_og_image(body, post)
        if image_url:
            candidate["evidence"]["og_image_url"] = image_url
        candidates.append(candidate)
        check["details_opened"] += 1
        check["status"] = "ok"
    return check, candidates


def scan_source(source,budget,mode):
    if source.get("seed_only"):
        return scan_exact_instagram_seeds(source,budget)
    root=source["url"]
    status,body,error=budget.request(root)
    check=dict(source_id=source["source_id"],http_status=status,
               status="ok" if body else "failed", error_type=error,
               details_opened=0, links_found=0)
    if body is None:
        return check,[]
    page=parse_html(body)
    # Source-specific evidence, including multiple sessions per theatre work.
    check["_listings"]=extract_listings(body,root)
    links=special_links(root,page)+[(u,"baseline_watchlist_original") for u in source.get("seed_urls",[])]
    links+=links_from_page(body,page,root)
    links=list(dict(((u,lab),None) for u,lab in links).keys())
    check["links_found"]=len(links)
    if not links and not check["_listings"]:
        check["status"]="index_only"
    max_details=MAX_DETAILS_FULL if mode=="full" else MAX_DETAILS_INCREMENTAL
    candidates=[]
    known=set()
    for url,label in links[:max_details]:
        if not budget.can_fetch(url):
            break
        stat,data,detail_error=budget.request(url)
        detail=parse_html(data) if data else None
        if detail:
            check["details_opened"]+=1
            check["_listings"].extend(extract_listings(data,url))
        record=make_candidate(url,source["source_id"],label,detail,stat)
        record["evidence"]["radar"]="definitivo"
        record["evidence"]["source_root"]=root
        record["evidence"]["baseline_watchlist"]=label=="baseline_watchlist_original"
        record["evidence"]["linked_from"]=root
        if data:
            image_url=extract_og_image(data,url)
            if image_url:
                record["evidence"]["og_image_url"]=image_url
        if detail_error:
            record["evidence"]["detail_error"]=detail_error
        candidates.append(record)
        known.add(url)
        if stat==429:
            continue
        if data and not exact_instagram(url):
            embedded=links_from_page(data,detail,url)
            for post,label2 in embedded:
                if not exact_instagram(post) or post in known:
                    continue
                if sum(1 for c in candidates if c["evidence"].get("linked_from")==url)>=MAX_EMBEDDED_PER_DETAIL:
                    break
                if not budget.can_fetch(post):
                    break
                pstat,pbody,perror=budget.request(post)
                ppage=parse_html(pbody) if pbody else None
                candidate=make_candidate(post,source["source_id"],label2,ppage,pstat)
                candidate["evidence"]["radar"]="definitivo"
                candidate["evidence"]["linked_from"]=url
                if pbody:
                    image_url=extract_og_image(pbody,post)
                    if image_url:
                        candidate["evidence"]["og_image_url"]=image_url
                if perror:
                    candidate["evidence"]["detail_error"]=perror
                candidates.append(candidate)
                known.add(post)
                if pstat==429:
                    break
    # Some official Teatro Argentino details are hydrated after initial HTML.
    # Only render explicit /meet/<id> URLs already discovered or in the
    # historical WATCHLIST, and only if the HTTP parser found no session.
    if urlparse(root).hostname=="teatroargentino.gba.gob.ar":
        missed=[]
        for url,_ in links[:max_details]:
            if urlparse(url).hostname!="teatroargentino.gba.gob.ar":
                continue
            if any(x["proof_url"]==url for x in check["_listings"]):
                continue
            if budget.can_fetch(url):
                missed.append(url)
        if missed and budget.remaining()>50:
            missed=missed[:3]
            budget.total+=len(missed)
            budget.by_host[urlparse(root).hostname]+=len(missed)
            pages,reason=render_argentino_event_pages(
                missed,max_seconds=min(65,budget.remaining()-8))
            for u,markup in pages.items():
                check["_listings"].extend(extract_listings(markup,u))
            for u,markup in pages.items():
                plain=re.sub(r"\s+"," ",re.sub(r"<[^>]*>"," ",markup))
                m=re.search(r"Fecha\s+del\s+evento",plain,re.I)
                sample=plain[m.start():m.start()+140] if m else ""
                print(json.dumps({"adapter":"argentino_date_diagnostic",
                    "url_id":u.rsplit("/",1)[-1],
                    "date_fragment":sample,
                    "date_regex_match":bool(re.search(
                      r"Fecha\s+del\s+evento\s+[0-3]?\d/[01]?\d/20\d{2}\s+\d\d:\d\d",
                      plain,re.I)),
                    "caption_p_tags":sum("|" in t for t in
                       re.findall(r"<p\b[^>]*>(.*?)</p\s*>",markup,re.I|re.S))},
                    ensure_ascii=False),flush=True)
            print(json.dumps({"source":source["source_id"],
                  "adapter":"argentino_browser",
                  "pages":len(pages),"sessions":len(check["_listings"]),
                  "pages_with_event_label":sum(bool(re.search(r"Fecha\s+del\s+evento",
                       re.sub(r"<[^>]*>"," ",markup),re.I)) for markup in pages.values()),
                  "pages_with_caption_pipe":sum("|" in markup for markup in pages.values()),
                  "markup_sizes":[len(m) for m in pages.values()],
                  "error":reason}),flush=True)
    # Genda may return only a JS shell to the HTTP client. Use one bounded
    # browser session solely for missing Genda date-page observations.
    if urlparse(root).hostname in ("agendalaplata.ar","www.agendalaplata.ar"):
        selected=validated_date_pages([u for u,_ in links])
        observed={item["proof_url"] for item in check["_listings"]
                  if item.get("method")=="genda_dated_listing"}
        missing=[u for u in selected if u not in observed and budget.can_fetch(u)]
        if missing and budget.remaining()>50:
            budget.total+=len(missing)
            budget.by_host[urlparse(root).hostname]+=len(missing)
            rendered,reason=render_date_pages(missing,max_seconds=min(65,budget.remaining()-8))
            for u,markup in rendered.items():
                check["_listings"].extend(extract_listings(markup,u))
            check["_genda_render_pages"]=len(rendered)
            if not check["_listings"]:
                check["error_type"]=reason or ("GENDA_NO_SESSIONS_AFTER_RENDER_"+
                                        str(len(rendered))+"_PAGES")
                check["status"]="index_only"
            print(json.dumps({"source":source["source_id"],"adapter":"genda_browser",
                 "browser_pages":len(rendered),
                 "visible_clock_lines":sum(len(re.findall(r"\b\d{1,2}:\d{2}\s*hs\b",
                                             content,re.I)) for content in rendered.values()),
                 "sessions":len(check["_listings"]),
                 "error":reason}),flush=True)
    # Alpedó serves an HTML shell to plain HTTP clients: source_checks
    # often show index_only:200 and 0 links. An extra generic menu link
    # must NOT silently disable the bounded Chromium fallback. A bounded Chromium
    # session reads date pages already supported by the official web UI.
    # Unlike Genda, Alpedó has many museum opening-hour ranges; the parser
    # deliberately excludes those and all data stays SECONDARY.
    if (urlparse(root).hostname in ("alpedo.ar","www.alpedo.ar")
        and urlparse(root).path=="/" and not check["_listings"]
        and budget.remaining()>55 and budget.total+3<=MAX_REQUESTS):
        day=datetime.now(timezone.utc).astimezone(
            ZoneInfo("America/Argentina/Buenos_Aires")).date()
        count=3 if mode=="full" else 2
        date_urls=["https://alpedo.ar/?fecha="+(day+timedelta(days=i)).isoformat()
                   for i in range(count)]
        rendered,reason=render_alpedo_date_pages(
            date_urls,max_seconds=min(70,budget.remaining()-8))
        budget.total+=len(rendered)
        budget.by_host["alpedo.ar"]+=len(rendered)
        for u,markup in rendered.items():
            check["_listings"].extend(extract_listings(markup,u))
        check["details_opened"]+=len(rendered)
        check["_alpedo_render_pages"]=len(rendered)
        if check["_listings"]:
            check["status"]="ok"
        elif reason:
            check["error_type"]=reason
        print(json.dumps({"source":source["source_id"],"adapter":"alpedo_browser",
            "pages":len(rendered),"secondary_sessions":len(check["_listings"]),
            "error":reason}),flush=True)
    return check,candidates


def extract_og_image(body,base_url):
    # Reference only: do not download or publish an image.
    import html
    tags=re.findall(r"<meta\b[^>]*>",body[:200_000],flags=re.I)
    for tag in tags:
        if not re.search(r"(?:property|name)\s*=\s*['\"]og:image['\"]",tag,re.I):
            continue
        match=re.search(r"content\s*=\s*['\"]([^'\"]+)['\"]",tag,re.I)
        if match:
            try:
                target=urlsplit(urljoin(base_url,html.unescape(match.group(1))))
                if (target.scheme=="https" and target.hostname and not target.username
                    and not target.password and target.port in (None,443)
                    and len(target.geturl())<=2400):
                    return urlunsplit(("https",target.netloc.lower(),target.path,
                                      target.query,""))
            except ValueError:
                continue
    return None


def credible_occurrence(candidate):
    """Structural observation, not an accepted event."""
    if not candidate.get("event_date") or not candidate["evidence"].get("structured_event_found"):
        return None
    if candidate.get("kind") not in {"event_detail","news_article"}:
        return None
    if not candidate["evidence"].get("detail_opened"):
        return None
    try:
        event_day=date.fromisoformat(candidate["event_date"])
    except (ValueError,TypeError):
        return None
    today=datetime.now(timezone.utc).date()
    if not today-timedelta(days=14)<=event_day<=today+timedelta(days=365):
        return None
    title=compact(candidate.get("title") or "",180)
    if len(title)<8 or title.lower() in {"casa metro la plata","inicio","cartelera"}:
        return None
    return event_day


def classify_category(title):
    """Pista de disciplina de un anuncio, NO género ni estado editorial.

    staging.category es nullable: un título genérico no prueba «comunidad».
    «Taller/curso» son FORMATO, no disciplina; el contrato de publicación
    decide luego las facetas del evento y la identidad por fuente original.
    Vocabulario compatible con Por Acá (semantic-boundary-contract-v1).
    """
    t=(title or "").casefold()
    # La disciplina explícita gana sobre «taller» o «clase» del mismo título.
    for cat,words in [("cine",("cine","película","film","proyección")),
                      ("ceramica",("cerámica","ceramica","alfarería","alfareria")),
                      ("yoga",("yoga",)),
                      ("teatro",("teatro","obra","función","escena")),
                      ("musica",("recital","concierto","música","show","banda")),
                      ("danza",("danza","milonga","tango","baile")),
                      ("artes",("exposición","muestra","galería"))]:
        if any(w in t for w in words):
            return cat
    # No volver a emitir «arte»/«formacion» heredados ni asumir comunidad.
    return None


def entity_for(source_id,name,entity_type,url,origin):
    label=compact(name,180)
    if len(label)<3:
        return None
    canonical=re.sub(r"\s+"," ",label.casefold()).strip()
    key=hashlib.sha256((entity_type+"|"+canonical).encode("utf-8")).hexdigest()
    return dict(entity_key=key, name=label, entity_type=entity_type,
                profile_url=url,source_id=source_id,evidence={
                    "method":origin,"not_verified":True})


def save_source_result(conn,run_id,source,check,candidates):
    new_candidates=0
    entity_new=0
    with conn.cursor() as cur:
        # Each listing item is a separate event session, even when a daily
        # agenda has no per-event permalink. No invented source URLs.
        for item in check.get("_listings",[]):
            signature="|".join((source["source_id"],item["title"].casefold(),
                     item["event_date"],item.get("event_time") or "",
                     (item.get("venue") or "").casefold(),item["proof_url"]))
            listing_key=hashlib.sha256(signature.encode("utf-8")).hexdigest()
            cur.execute("""INSERT INTO radar_definitivo.listing_occurrences(
              listing_key,source_id,title,event_date,event_time,venue,
              proof_url,proof_method,evidence_tier,first_run_id,last_run_id)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
              ON CONFLICT(listing_key) DO UPDATE SET
                 last_seen_at=now(),seen_count=radar_definitivo.listing_occurrences.seen_count+1,
                 last_run_id=EXCLUDED.last_run_id""",
                 (listing_key,source["source_id"],item["title"],
                  item["event_date"],item.get("event_time"),item.get("venue"),
                  item["proof_url"],item["method"],item["evidence_tier"],run_id,run_id))
        for c in candidates:
            cur.execute(
                """INSERT INTO radar_definitivo.candidates
                (candidate_key,url,kind,title,summary,event_date,event_time,venue,
                 organizer,source_role,evidence)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT(url) DO NOTHING RETURNING candidate_key""",
                (c["candidate_key"],c["original_url"],c["kind"],c["title"],
                 c["summary"],c["event_date"],c["event_time"],c["venue"],
                 c["organizer"],source["source_role"],json.dumps(c["evidence"])))
            if cur.fetchone():
                new_candidates+=1
            else:
                # Previously COALESCE(event_time,new_time) permanently froze
                # the FIRST JSON-LD clock (including UTC misread as ART).
                # Only a newly OPENED structured original can revise it.
                # Keep the prior date/time in evidence for audit; never
                # overwrite with a label, snippet or secondary guess.
                clock_from_original=bool(
                    c["evidence"].get("structured_event_found")
                    and c["evidence"].get("detail_opened")
                    and c.get("event_date") and c.get("event_time"))
                cur.execute("""UPDATE radar_definitivo.candidates
                  SET seen_count=seen_count+1,last_seen_at=now(),
                      title=CASE WHEN %s::text IS NOT NULL AND %s::text<>'' THEN %s ELSE title END,
                      summary=CASE WHEN %s::text IS NOT NULL AND %s::text<>'' THEN %s ELSE summary END,
                      event_date=CASE WHEN %s::boolean THEN %s::date
                                      ELSE COALESCE(event_date,%s::date) END,
                      event_time=CASE WHEN %s::boolean THEN %s::text
                                      ELSE COALESCE(event_time,%s::text) END,
                      venue=COALESCE(venue,%s::text),
                      organizer=COALESCE(organizer,%s::text),
                      evidence=CASE WHEN %s::boolean THEN
                        coalesce(evidence,'{}'::jsonb) ||
                        (CASE WHEN %s::boolean AND event_time IS DISTINCT FROM %s::text
                          THEN jsonb_build_object('previousEventTime',event_time,
                            'previousEventDate',event_date,'eventTimeRecheckedAt',now())
                          ELSE '{}'::jsonb END) || %s::jsonb
                        ELSE evidence END
                  WHERE url=%s""",
                    (c["title"],c["title"],c["title"],
                     c["summary"],c["summary"],c["summary"],
                     clock_from_original,c["event_date"],c["event_date"],
                     clock_from_original,c["event_time"],c["event_time"],
                     c["venue"],c["organizer"],
                     bool(c["evidence"].get("detail_opened")),
                     clock_from_original,c["event_time"],
                     json.dumps(c["evidence"]),c["original_url"]))
            source_page=c["evidence"].get("linked_from") or source["url"]
            edge_key=hashlib.sha256((source["source_id"]+"|"+source_page+"|"+c["original_url"]).encode("utf-8")).hexdigest()
            cur.execute("""INSERT INTO radar_definitivo.link_edges
               (edge_key,source_id,from_url,to_url,relation,evidence)
               VALUES(%s,%s,%s,%s,%s,%s::jsonb)
               ON CONFLICT(edge_key) DO UPDATE SET last_seen_at=now()""",
               (edge_key,source["source_id"],source_page,c["original_url"],
                ("seeded_exact_permalink" if c["evidence"].get("seeded_permalink")
                 else "original_instagram_permalink" if exact_instagram(c["original_url"])
                 else "detail"),
                json.dumps({"runId":run_id,"http":c["evidence"].get("detail_http")})))
            image_url=c["evidence"].get("og_image_url")
            if image_url:
                media_key=hashlib.sha256((c["candidate_key"]+"|"+image_url).encode()).hexdigest()
                cur.execute("""INSERT INTO radar_definitivo.media_references
                   (media_key,candidate_key,media_url,origin_url)
                   VALUES(%s,%s,%s,%s)
                   ON CONFLICT(media_key) DO NOTHING""",
                   (media_key,c["candidate_key"],image_url,c["original_url"]))
            when=credible_occurrence(c)
            if when:
                occurrence_key=hashlib.sha256((c["candidate_key"]+"|"+str(when)+"|"+(c.get("event_time") or "")).encode()).hexdigest()
                cur.execute("""INSERT INTO radar_definitivo.event_occurrences
                  (occurrence_key,candidate_key,event_date,event_time,venue,organizer,
                   category,first_party_evidence,proof_url,proof_method)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                  ON CONFLICT(occurrence_key) DO UPDATE SET last_seen_at=now()""",
                  (occurrence_key,c["candidate_key"],when,c.get("event_time"),c.get("venue"),
                   c.get("organizer"),classify_category(c.get("title")),False,
                   c["original_url"],"public_jsonld_event_unverified"))
            cur.execute("""INSERT INTO radar_definitivo.candidate_sources(candidate_key,source_id)
                      VALUES (%s,%s) ON CONFLICT(candidate_key,source_id)
                      DO UPDATE SET last_seen_at=now()""",
                        (c["candidate_key"],source["source_id"]))
            # New artists/venues ONLY when source explicitly offers named structured Event.
            if (os.getenv("RADAR_ENABLE_ENTITY_PROPOSALS","false").lower()=="true"
                and c["evidence"].get("structured_event_found")):
                for typ,val in (("venue",c["venue"]),("organizer",c["organizer"])):
                    ent=entity_for(source["source_id"],val or "",typ,c["original_url"],
                                   "event_jsonld_original")
                    if ent:
                        cur.execute("""INSERT INTO radar_definitivo.entities(
                           entity_key,name,entity_type,profile_url,source_id,evidence)
                           VALUES(%s,%s,%s,%s,%s,%s::jsonb)
                           ON CONFLICT(entity_key) DO NOTHING RETURNING entity_key""",
                            (ent["entity_key"],ent["name"],ent["entity_type"],
                             ent["profile_url"],ent["source_id"],json.dumps(ent["evidence"])))
                        if cur.fetchone():
                            entity_new+=1
        cur.execute("""INSERT INTO radar_definitivo.source_checks(
           run_id,source_id,http_status,status,details_opened,links_found,error_type)
           VALUES(%s,%s,%s,%s,%s,%s,%s)""",
           (run_id,source["source_id"],check["http_status"],
            check["status"],check["details_opened"],check["links_found"],check["error_type"]))
        fail=source["consecutive_failures"]+1 if check["status"]=="failed" else 0
        cadence=(min(12,source["cadence_hours"]) if check["status"]=="index_only" else
                 source["cadence_hours"] if not fail else min(48,2**min(5,fail)))
        if not check.get("_seed_only"):
            cur.execute("""UPDATE radar_definitivo.sources
               SET last_checked_at=now(),last_status=%s,
                   consecutive_failures=%s,next_due_at=now()+(%s*interval '1 hour')
               WHERE source_id=%s""",
               (check["status"]+":"+str(check["http_status"] or check["error_type"]),
                fail,cadence,source["source_id"]))
        # Commit per source: crash/retry preserves already discovered data.
    conn.commit()
    return new_candidates,entity_new


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["full","incremental"],default="incremental")
    args=p.parse_args()
    try:
        conn=isolated_connection()
    except Exception as exc:
        print("CONFIG_ERROR: "+type(exc).__name__+" (check DB/role/secret)",file=sys.stderr)
        return 2
    budget=Budget()
    run_id="definitivo-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6]
    stats=dict(selected=0,checked=0,success=0,index_only=0,urls=0,candidates=0,new=0,entities=0,listings=0)
    try:
        sources=choose_sources(conn,args.mode)
        # Buzon pequeño de permalinks exactos: no implica monitorizar perfiles.
        sources.extend(choose_seed_sources(conn))
        stats["seed_accounts"]=sum(1 for s in sources if s.get("seed_only"))
        stats["selected"]=len(sources)
        with conn.cursor() as cur:
            # Historic runner aborts should never appear as still-running forever.
            cur.execute("""UPDATE radar_definitivo.runs SET status='interrupted',
                 finished_at=now(),summary=summary || '{"stopReason":"stale_previous_run"}'::jsonb
                 WHERE status='running' AND started_at<now()-interval '55 minutes'""")
            cur.execute("""INSERT INTO radar_definitivo.runs(run_id,mode,sources_selected)
                           VALUES(%s,%s,%s)""",
                        (run_id,args.mode,len(sources)))
        conn.commit()
        for source in sources:
            if budget.remaining()<12 or budget.total>=MAX_REQUESTS:
                print("BUDGET_STOP: keeping unvisited sources pending",flush=True)
                break
            try:
                check,candidates=scan_source(source,budget,args.mode)
                new,entities=save_source_result(conn,run_id,source,check,candidates)
            except Exception as exc:
                conn.rollback()
                print("SOURCE_ERROR "+source["source_id"]+" "+type(exc).__name__,file=sys.stderr)
                # Failure of one source must not abort remaining scans.
                check=dict(status="failed",http_status=None,error_type=type(exc).__name__,details_opened=0,links_found=0)
                try:
                    save_source_result(conn,run_id,source,check,[])
                except Exception as inner:
                    conn.rollback()
                    print("PERSISTENCE_ERROR "+type(inner).__name__,file=sys.stderr)
                    raise
                candidates=[];new=0;entities=0
            stats["checked"]+=1
            stats["success"]+=int(check["status"]=="ok")
            stats["index_only"]+=int(check["status"]=="index_only")
            stats["urls"]+=check["links_found"]
            stats["candidates"]+=len(candidates)
            stats["new"]+=new
            stats["entities"]+=entities
            stats["listings"]+=len(check.get("_listings",[]))
            # Live persisted acknowledgement after EVERY source, including index-only/errors.
            with conn.cursor() as cur:
                cur.execute("""UPDATE radar_definitivo.runs SET
                  sources_checked=%s,sources_success=%s,urls_discovered=%s,
                  candidates_seen=%s,candidates_new=%s,entities_new=%s,
                  summary=jsonb_build_object('phase','running','lastSource',%s::text,
                    'httpRequests',%s::integer,'instagramRequests',%s::integer,'target',%s::text)
                  WHERE run_id=%s""",
                    (stats["checked"],stats["success"],stats["urls"],
                     stats["candidates"],stats["new"],stats["entities"],
                     source["source_id"],budget.total,budget.instagram,
                     "operational_neondb_staging" if os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL")
                     else "experimental_poraca_explorador",run_id))
            conn.commit()
            print(json.dumps({"source":source["source_id"],"status":check["status"],
                              "http":check["http_status"],"links":check["links_found"],
                              "candidates":len(candidates),"new":new,
                              "details":check["details_opened"],"listings":len(check.get("_listings",[])),
                              "error":check["error_type"],
                              "exact_permalink_only":bool(check.get("_seed_only"))},
                             ensure_ascii=False),flush=True)
        # Separate new records created BY THIS run from repeated sightings.
        # Do not confuse previously harvested URLs/occurrences with new work.
        with conn.cursor() as cur:
            cur.execute("""SELECT count(*) FROM radar_definitivo.listing_occurrences
                           WHERE first_run_id=%s""",(run_id,))
            stats["new_listings"]=cur.fetchone()[0]
        # Existing rows only: one bounded read to expose duplicates and unsafe
        # historical venues after each normal run; not an ingest or a new task.
        try:
            with conn.cursor() as cur:
                cur.execute("""SELECT source_id,title,event_date::text,event_time,
                                     venue,proof_url,evidence_tier
                               FROM radar_definitivo.listing_occurrences
                               ORDER BY last_seen_at DESC LIMIT 5000""")
                qa_rows=cur.fetchall()
            stats["evidence_quality"]=summarize_evidence_quality(qa_rows)
        except Exception as exc:
            conn.rollback()
            stats["evidence_quality"]={"status":"unavailable",
                                       "reason":type(exc).__name__}
        # Shadow collision check: not a replacement for the ingestion gate.
        # Source-specific category and detail URLs can refer to ONE existing
        # public observation, despite an exact-URL count of zero.
        try:
            with conn.cursor() as cur:
                cur.execute(SHADOW_ALIAS_SQL)
                aliases=cur.fetchall()
            stats["evidence_quality"]["public_observation_aliases"]=summarize_aliases(aliases)
        except Exception as exc:
            conn.rollback()
            stats["evidence_quality"]["public_observation_aliases"]={
                "status":"unavailable","reason":type(exc).__name__,
                "authorized_to_write":False}
        # P0 function identity v2: a third bounded read-only preflight.
        # Never applies an admission, even when a candidate has one original.
        try:
            with conn.cursor() as cur:
                cur.execute(function_review_sql())
                review_rows=cur.fetchall()
            stats["evidence_quality"]["function_gate_v2"]=summarize_function_review(review_rows)
        except Exception as exc:
            conn.rollback()
            stats["evidence_quality"]["function_gate_v2"]={
                "status":"unavailable","reason":type(exc).__name__,
                "authorized_to_write":False}
        state=("complete" if stats["checked"]==stats["selected"] and
               stats["checked"]==stats["success"] else "partial")
        info=dict(**stats,mode=args.mode,
                  target="operational_neondb_staging" if os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL")
                  else "experimental_poraca_explorador",
                  requests=budget.total,instagram_requests=budget.instagram,
                  remaining_seconds=budget.remaining(),notes="all candidates unverified")
        with conn.cursor() as cur:
            cur.execute("""UPDATE radar_definitivo.runs SET finished_at=now(),
                          status=%s,sources_checked=%s,sources_success=%s,
                          urls_discovered=%s,candidates_new=%s,candidates_seen=%s,
                          entities_new=%s,summary=%s::jsonb WHERE run_id=%s""",
                        (state,stats["checked"],stats["success"],stats["urls"],
                         stats["new"],stats["candidates"],stats["entities"],
                         json.dumps(info),run_id))
        conn.commit()
        print("DEFINITIVO_RESULT "+json.dumps({"run_id":run_id,"status":state,**info},ensure_ascii=False),flush=True)
        out=os.getenv("GITHUB_STEP_SUMMARY")
        if out:
            with open(out,"a",encoding="utf-8") as f:
                f.write("# Radar Definitivo - "+args.mode+"\n\n")
                f.write("| Fuentes seleccionadas | Revisadas | Accesibles | Funciones leídas | Funciones **nuevas** | Enlaces hallados | Candidatos URL nuevos | IG exactos consultados |\n"
                        "|---:|---:|---:|---:|---:|---:|---:|---:|\n")
                f.write(f"| {stats['selected']} | {stats['checked']} | {stats['success']} | "
                        f"{stats['listings']} | {stats['new_listings']} | {stats['urls']} | {stats['new']} | {budget.instagram} |\n\n")
                f.write("Diagnóstico de duplicaciones y sedes (solo lectura): "
                        +json.dumps(stats.get("evidence_quality",{}),ensure_ascii=False)+"\\n\\n")
                f.write(f"Permalinks IG exactos: {stats['seed_accounts']} cuentas en buzon; "
                        "NO equivale a revisar feeds. Candidatos sin aceptar.\\n")
        return 0 if (stats["checked"]>0 or not sources) else 1
    except Exception as exc:
        conn.rollback()
        try:
            with conn.cursor() as cur:
                cur.execute("""UPDATE radar_definitivo.runs SET status='error',
                      finished_at=now(),summary=%s::jsonb WHERE run_id=%s""",
                            (json.dumps({"error":type(exc).__name__,**stats}),run_id))
            conn.commit()
        except Exception:
            conn.rollback()
        print("RADAR_FATAL "+type(exc).__name__,file=sys.stderr)
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
