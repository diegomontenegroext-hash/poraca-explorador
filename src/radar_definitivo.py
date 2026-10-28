#!/usr/bin/env python3
"""RADAR DEFINITIVO 0.1 — motor autonomo con Neon experimental y cursor por fuente.

No es aceptador canonico, no escribe en neondb, no publica eventos.
Instagram: solo permalinks publicos encontrados en fuentes web; perfiles
catalogados como 'discover_only' no son scrapeados ni se leen Stories.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
import time
import uuid
from urllib.parse import urlparse

from radar_parallel import (
    DB_NAME, DB_ROLE, clean_link, compact, discover_links,
    exact_instagram, fetch, make_candidate, parse_html, structured_event,
)

SCHEMA = "radar_definitivo"
MAX_SOURCES = 36
MAX_DETAILS_FULL = 8
MAX_DETAILS_INCREMENTAL = 4
MAX_REQUESTS = 200
MAX_INSTAGRAM = 18
MAX_SECONDS = 19 * 60
MAX_DOMAIN_REQUESTS = 24
MAX_EMBEDDED_PER_DETAIL = 2
MIN_SOURCE_DELAY_SECONDS = 0.15

class Budget:
    def __init__(self, seconds=MAX_SECONDS):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.total = 0
        self.instagram = 0
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
        if MIN_SOURCE_DELAY_SECONDS:
            time.sleep(MIN_SOURCE_DELAY_SECONDS)
        status, body, error = fetch(url)
        if status == 429:
            self.blocked_hosts.add(host)
        return status, body, error

    def remaining(self):
        return max(0, int(self.deadline - time.monotonic()))


def isolated_connection():
    value = os.environ.get("NEON_EXPLORADOR_DATABASE_URL", "")
    if not value:
        raise RuntimeError("Missing NEON_EXPLORADOR_DATABASE_URL repository secret")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install psycopg[binary]") from exc
    conn = psycopg.connect(value, connect_timeout=12)
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(),current_user,to_regclass('radar_definitivo.sources')")
        db,role,table=cur.fetchone()
    if db != DB_NAME or role != DB_ROLE or table is None:
        conn.close()
        raise RuntimeError("Isolation guard: wrong DB, role or missing radar_definitivo schema")
    return conn


def choose_sources(conn, mode):
    where = ("enabled AND monitoring_mode='fetch'" if mode == "full" else
             "enabled AND monitoring_mode='fetch' AND next_due_at<=now()")
    with conn.cursor() as cur:
        cur.execute(f"""SELECT source_id,name,url,source_role,priority,cadence_hours,
                        consecutive_failures FROM radar_definitivo.sources
                        WHERE {where}
                        ORDER BY last_checked_at ASC NULLS FIRST, priority DESC,source_id
                        LIMIT %s""", (MAX_SOURCES,))
        return [dict(source_id=a,name=b,url=c,source_role=d,priority=e,
                     cadence_hours=f,consecutive_failures=g)
                for a,b,c,d,e,f,g in cur.fetchall()]


def links_from_page(body, page, url):
    """Candidate URL discovery restricted to original source links, no profile scraping."""
    links = discover_links(body,page,url)
    seen = set()
    out = []
    for href,label in links:
        if href in seen:
            continue
        if not exact_instagram(href):
            parts = urlparse(href).path.lower().split("/")
            if any(p in {"categoria","categoría","categorias","tag","tags","recintos",
                         "page","pagina","página","lista","archivo","author"}
                   for p in parts):
                continue
        seen.add(href)
        out.append((href,label))
    return sorted(out,key=lambda item:(not exact_instagram(item[0]),item[0]))


def scan_source(source,budget,mode):
    root=source["url"]
    status,body,error=budget.request(root)
    check=dict(source_id=source["source_id"],http_status=status,
               status="ok" if body else "failed", error_type=error,
               details_opened=0, links_found=0)
    if body is None:
        return check,[]
    page=parse_html(body)
    links=links_from_page(body,page,root)
    check["links_found"]=len(links)
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
        record=make_candidate(url,source["source_id"],label,detail,stat)
        record["evidence"]["radar"]="definitivo"
        record["evidence"]["source_root"]=root
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
                if perror:
                    candidate["evidence"]["detail_error"]=perror
                candidates.append(candidate)
                known.add(post)
                if pstat==429:
                    break
    return check,candidates


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
                cur.execute("""UPDATE radar_definitivo.candidates
                  SET seen_count=seen_count+1,last_seen_at=now(),
                      title=CASE WHEN %s::text IS NOT NULL AND %s::text<>'' THEN %s ELSE title END,
                      summary=CASE WHEN %s::text IS NOT NULL AND %s::text<>'' THEN %s ELSE summary END,
                      event_date=COALESCE(event_date,%s::date),
                      event_time=COALESCE(event_time,%s::text),
                      venue=COALESCE(venue,%s::text),
                      organizer=COALESCE(organizer,%s::text),
                      evidence=CASE WHEN %s::boolean
                         THEN evidence || %s::jsonb ELSE evidence END
                  WHERE url=%s""",
                    (c["title"],c["title"],c["title"],
                     c["summary"],c["summary"],c["summary"],
                     c["event_date"],c["event_time"],c["venue"],c["organizer"],
                     bool(c["evidence"].get("detail_opened")),
                     json.dumps(c["evidence"]),c["original_url"]))
            cur.execute("""INSERT INTO radar_definitivo.candidate_sources(candidate_key,source_id)
                      VALUES (%s,%s) ON CONFLICT(candidate_key,source_id)
                      DO UPDATE SET last_seen_at=now()""",
                        (c["candidate_key"],source["source_id"]))
            # New artists/venues ONLY when source explicitly offers named structured Event.
            if c["evidence"].get("structured_event_found"):
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
        fail=source["consecutive_failures"]+1 if check["status"]!="ok" else 0
        cadence=source["cadence_hours"] if not fail else min(48,2**min(5,fail))
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
        print("CONFIG_ERROR: "+str(exc),file=sys.stderr)
        return 2
    budget=Budget()
    run_id="definitivo-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6]
    stats=dict(selected=0,checked=0,success=0,urls=0,candidates=0,new=0,entities=0)
    try:
        sources=choose_sources(conn,args.mode)
        stats["selected"]=len(sources)
        with conn.cursor() as cur:
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
            stats["urls"]+=check["links_found"]
            stats["candidates"]+=len(candidates)
            stats["new"]+=new
            stats["entities"]+=entities
            print(json.dumps({"source":source["source_id"],"status":check["status"],
                              "http":check["http_status"],"links":check["links_found"],
                              "candidates":len(candidates),"new":new,
                              "details":check["details_opened"],"error":check["error_type"]},
                             ensure_ascii=False),flush=True)
        state=("complete" if stats["checked"]==stats["selected"] and
               stats["checked"]==stats["success"] else "partial")
        info=dict(**stats,mode=args.mode,requests=budget.total,instagram_requests=budget.instagram,
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
                f.write("| Fuentes seleccionadas | Revisadas | Accesibles | Enlaces hallados | Candidatos nuevos | IG exactos consultados |\n"
                        "|---:|---:|---:|---:|---:|---:|\n")
                f.write(f"| {stats['selected']} | {stats['checked']} | {stats['success']} | "
                        f"{stats['urls']} | {stats['new']} | {budget.instagram} |\n\n")
                f.write("Las fuentes IG catalogadas NO se consultan por perfil. Todos los candidatos quedan pendientes.\n")
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
