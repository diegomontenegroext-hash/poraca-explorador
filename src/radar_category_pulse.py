#!/usr/bin/env python3
"""Post-run category pulse, read-only: no new scheduler, ingestion, or approvals."""
import json, os, sys, unicodedata
from pathlib import Path

SCHEMA="poraca-radar-category-pulse-v1"
LABELS={"teatro":"Teatro","musica":"Música","cine":"Cine","artes":"Artes y exposiciones",
"literatura":"Literatura","festival":"Festivales","yoga":"Yoga","ceramica":"Cerámica",
"danza":"Danza","fiestas":"Fiestas","taller":"Talleres","naturaleza":"Naturaleza",
"comunidad":"Comunidad","otras":"Otras / por clasificar"}
ALIASES={
"teatro":"teatro","teatro musical":"teatro","stand up":"teatro","teatro stand up":"teatro",
"musica":"musica","music":"musica","cine":"cine","artes":"artes","arte":"artes",
"exposicion":"artes","muestra":"artes","museo":"artes","literatura":"literatura",
"libros":"literatura","festival":"festival","festivales":"festival","feria":"festival",
"yoga":"yoga","ceramica":"ceramica","danza":"danza","milonga":"danza",
"clase_tango":"danza","fiesta":"fiestas","fiestas":"fiestas","noche":"fiestas",
"taller":"taller","formacion":"taller","naturaleza":"naturaleza","ecologia":"naturaleza",
"comunidad":"comunidad","cultura":"comunidad","infantil":"comunidad","ciencia":"comunidad"}

CANONICAL_SQL="""
SELECT category,COUNT(*)::int,
COUNT(*) FILTER(WHERE status='scheduled' AND verification='confirmed' AND
event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+14)::int,
COUNT(*) FILTER(WHERE status='scheduled' AND verification='confirmed' AND
event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+45)::int,
COUNT(*) FILTER(WHERE first_seen_at>=now()-interval '7 days')::int,
COUNT(*) FILTER(WHERE updated_at>=now()-interval '24 hours')::int
FROM public.radar_agenda_events GROUP BY category
"""
OBS_SQL="""
SELECT observed_category,COUNT(*)::int,
COUNT(*) FILTER(WHERE first_seen_at>=now()-interval '7 days')::int
FROM public.radar_v3_source_observations
WHERE observed_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+45
AND matched_event_key IS NULL AND reconciliation_state IN
('observed_unverified','reconciled_new_candidate','reconciled_pending_evidence')
GROUP BY observed_category
"""

# Source status is inventory from prior runs, NOT a health result of this run.
SOURCE_MODES_SQL="""
SELECT monitoring_mode,COUNT(*)::int,
COUNT(*) FILTER(WHERE last_status LIKE 'index_only%')::int,
COUNT(*) FILTER(WHERE last_status LIKE 'failed%')::int
FROM radar_definitivo.sources WHERE enabled=true GROUP BY monitoring_mode
"""
# These are editorial leads. An event URL and date are not admission.
REVIEW_QUEUE_SQL="""
WITH pending AS (
 SELECT observed_category,observed_title,observed_date,observed_time,
 observed_venue,source_event_url,origin_source_id,
 ROW_NUMBER() OVER(PARTITION BY lower(coalesce(observed_category,''))
   ORDER BY observed_date,first_seen_at DESC,source_event_url) AS rank_in_category
 FROM public.radar_v3_source_observations
 WHERE observed_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
 AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+45
 AND matched_event_key IS NULL
 AND reconciliation_state IN ('observed_unverified','reconciled_new_candidate',
                              'reconciled_pending_evidence')
 AND source_event_url LIKE 'https://%'
)
SELECT observed_category,observed_title,observed_date,observed_time,
 observed_venue,source_event_url,origin_source_id FROM pending
WHERE rank_in_category<=3 ORDER BY observed_date,observed_category LIMIT 80
"""

def review_queue(rows, max_total=14, max_per_category=2):
    """Small candidate queue, explicitly unapproved, links checked for safety."""
    import re
    from urllib.parse import urlsplit
    picked=[];seen=set();per_category={}
    for raw,title,day,clock,venue,url,source in rows:
        rubro=category_of(raw)
        if per_category.get(rubro,0)>=max_per_category or len(picked)>=max_total:
            continue
        if not isinstance(title,str) or not 3<=len(title.strip())<=240:
            continue
        if not isinstance(url,str) or len(url)>1500 or re.search(r"[\s<>]",url):
            continue
        try:
            link=urlsplit(url)
            if link.scheme!="https" or not link.hostname or link.username or link.password or link.port not in (None,443):
                continue
        except ValueError:
            continue
        value=day.isoformat() if hasattr(day,"isoformat") else str(day)[:10]
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",value):
            continue
        key=(rubro,value,str(clock or ""),title.strip().casefold(),url)
        if key in seen:
            continue
        seen.add(key);per_category[rubro]=per_category.get(rubro,0)+1
        picked.append({"category":rubro,"date":value,"time":str(clock or "")[:5],
                       "title":title.strip()[:140],"venue":str(venue or "")[:100],
                       "url":url,"sourceId":str(source or "")[:120],
                       "reviewState":"UNAPPROVED_ORIGINAL_DETAIL_REVIEW",
                       "publicationApproved":False})
    return picked

def source_mode_counts(rows):
    """Status measures the last persisted source check, not today's execution."""
    return {str(mode):{"enabled":int(count or 0),
            "lastIndexOnly":int(index_only or 0),"lastFailed":int(failed or 0)}
            for mode,count,index_only,failed in rows}

def safe_cell(value):
    import re
    return re.sub(r"[\r\n|<>\[\]]"," ",str(value or "")).strip()[:180]

def category_of(value):
    if not isinstance(value,str):return "otras"
    norm="".join(c for c in unicodedata.normalize("NFD",value.strip().lower())
                 if unicodedata.category(c)!="Mn")
    return ALIASES.get(norm,"otras")

def summarize(canon,observations,today):
    rows={key:dict(rubro=key,label=label,historical=0,confirmedNext15=0,
      confirmedNext46=0,newCanonical7d=0,recordsTouched24h=0,
      pendingObservations46=0,newPendingObservations7d=0)
      for key,label in LABELS.items()}
    for category,history,n15,n46,added,touched in canon:
        row=rows[category_of(category)]
        for key,n in [("historical",history),("confirmedNext15",n15),
                      ("confirmedNext46",n46),("newCanonical7d",added),
                      ("recordsTouched24h",touched)]:
            row[key]+=int(n or 0)
    for category,pending,new in observations:
        row=rows[category_of(category)]
        row["pendingObservations46"]+=int(pending or 0)
        row["newPendingObservations7d"]+=int(new or 0)
    items=list(rows.values())
    return {"schema":SCHEMA,"todayArgentina":str(today),
      "totalCanonical":sum(x["historical"] for x in items),
      "totalConfirmedNext15":sum(x["confirmedNext15"] for x in items),
      "totalPendingObservations46":sum(x["pendingObservations46"] for x in items),
      "categories":items,
      "warning":"Pending observations are not distinct verified events; updated_at alone does not prove changed content; no dated yoga/ceramics function does not mean no regular offers.",
      "publicationApproved":False}

def fetch(url):
    import psycopg
    with psycopg.connect(url,connect_timeout=12) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cur.execute("""SELECT current_database(),session_user,current_user,
                  current_setting('neon.project_id',true),
                  current_setting('neon.branch_id',true),
                  has_table_privilege(current_user,'public.radar_agenda_events','SELECT'),
                  has_table_privilege(current_user,'public.radar_v3_source_observations','SELECT'),
                  has_table_privilege(current_user,'radar_definitivo.sources','SELECT'),
                  has_table_privilege(current_user,'public.radar_agenda_events','INSERT,UPDATE,DELETE,TRUNCATE')""")
                identity=cur.fetchone()
                expected=("neondb","poraca_definitivo_ingest","poraca_definitivo_scope",
                          "frosty-union-52906378","br-mute-recipe-b4odj2bl",True,True,True,False)
                if identity!=expected:raise RuntimeError("PULSE_DB_READ_ONLY_IDENTITY_MISMATCH")
                cur.execute("SELECT (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date")
                today=cur.fetchone()[0]
                cur.execute(CANONICAL_SQL);canonical=cur.fetchall()
                cur.execute(OBS_SQL);observations=cur.fetchall()
                cur.execute(SOURCE_MODES_SQL);source_rows=cur.fetchall()
                cur.execute(REVIEW_QUEUE_SQL);candidate_rows=cur.fetchall()
    report=summarize(canonical,observations,today)
    report["sourceModesPreviousCheck"]=source_mode_counts(source_rows)
    report["editorialReviewQueue"]=review_queue(candidate_rows)
    return report

def main():
    if not os.getenv("NEON_RADAR_OPERATIONAL_DATABASE_URL"):
        print("::error::PULSE_NEON_SECRET_MISSING",file=sys.stderr);return 1
    try:
        report=fetch(os.environ["NEON_RADAR_OPERATIONAL_DATABASE_URL"])
        print("RADAR_CATEGORY_PULSE "+json.dumps(report,ensure_ascii=False),flush=True)
        path=os.environ.get("GITHUB_STEP_SUMMARY")
        if path:
            with Path(path).open("a",encoding="utf-8") as out:
                out.write("\n## Por Acá: evolución por disciplina (lectura)\n\n")
                out.write("Canónicos: **{}** · próximos confirmados ≤15 días: **{}** · observaciones pendientes ≤46 días: **{}**.\n\n".format(
                    report["totalCanonical"],report["totalConfirmedNext15"],report["totalPendingObservations46"]))
                out.write("| Rubro | Confirmados ≤15 días | Nuevos canónicos 7 días | Observaciones pendientes ≤46 días |\n|---|---:|---:|---:|\n")
                for row in report["categories"]:
                    out.write("| {label} | {confirmedNext15} | {newCanonical7d} | {pendingObservations46} |\n".format(**row))
                out.write("\nObservaciones no son eventos aprobados; 0 funciones fechadas no equivale a ausencia de ofertas regulares. No se escriben datos.\n")
                out.write("\n### Cobertura de fuentes habilitadas (último check conocido)\n\n")
                out.write("| Modalidad | Fuentes | Índices sin detalle | Último check fallido |\n|---|---:|---:|---:|\n")
                for mode,count in sorted(report["sourceModesPreviousCheck"].items()):
                    out.write("| {} | {} | {} | {} |\n".format(safe_cell(mode),count["enabled"],count["lastIndexOnly"],count["lastFailed"]))
                out.write("\n### Próximas pistas a revisar · NO APROBADAS\n\n")
                out.write("Los enlaces siguientes son material para revisión editorial, no funciones confirmadas. La fuente individual y su horario se deben verificar nuevamente.\n\n")
                for item in report["editorialReviewQueue"]:
                    out.write("- **{}** · {} {} · {} · fuente: <{}>\n".format(
                        safe_cell(LABELS.get(item["category"],item["category"])),item["date"],
                        safe_cell(item["time"]),safe_cell(item["title"]),item["url"]))
                if not report["editorialReviewQueue"]:
                    out.write("Sin detalles originales pendientes en esta ventana.\n")
        return 0
    except Exception as exc:
        print("::error::RADAR_CATEGORY_PULSE_UNAVAILABLE "+type(exc).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
