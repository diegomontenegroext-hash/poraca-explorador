#!/usr/bin/env python3
"""Por Acá: evidence-bounded per-run editorial intake, inside EXISTING Radar post-run pulse.

Only touches radar_definitivo.runs.summary.editorial_funnel_v1. Never writes to
sources, candidates, occurrences, public events or editorial approvals.
Run-level link reads are snapshotted immediately because last_run_id is mutable.
"""
from collections import Counter, defaultdict
import json

SCHEMA="poraca-radar-run-editorial-funnel-v1"
LABELS={
    "teatro":"Teatro","musica":"Música","teatro_y_musica":"Teatro y música (mixto)",
    "arte_y_cultura":"Arte y cultura","artes":"Arte y cultura","vinos":"Vinos",
    "ceramica":"Cerámica","yoga":"Yoga","fiestas":"Fiestas","danza":"Danza",
    "cine":"Cine","literatura":"Literatura","talleres":"Talleres",
    "general":"Agenda general","unclassified":"Sin clasificar"
}
RUN_SQL="""
SELECT r.run_id,r.mode,r.status,r.started_at,r.finished_at,r.sources_selected,
 r.sources_checked,r.summary->>'listings',r.summary->>'new_listings',
 r.summary->>'new',r.summary->>'candidates'
FROM radar_definitivo.runs r WHERE r.finished_at IS NOT NULL
 AND r.status IN ('complete','partial')
 ORDER BY r.finished_at DESC LIMIT 1
"""
FACTS_SQL="""
SELECT l.listing_key,l.source_id,l.title,l.event_date,l.event_time,l.venue,
 l.proof_url,l.first_run_id,coalesce(nullif(s.circuit,''),'unclassified') AS circuit,
 public.poraca_fact_key_v1(l.title) norm_title,
 public.poraca_fact_key_v1(l.venue) norm_venue,
 public.poraca_first_party_event_detail_v1(l.evidence_tier,l.proof_method,l.proof_url)
   AS first_party_dated_original,
 (SELECT e.event_key FROM public.radar_agenda_events e
  WHERE e.event_date=l.event_date
    AND e.event_time IS NOT DISTINCT FROM l.event_time
    AND e.status='scheduled' AND e.verification='confirmed'
    AND e.published_at IS NOT NULL
    AND (e.evidence->0->>'listingKey'=l.listing_key
      OR (e.source_url=l.proof_url
       AND public.poraca_fact_key_v1(e.title)=public.poraca_fact_key_v1(l.title)
       AND public.poraca_fact_key_v1(e.venue)=public.poraca_fact_key_v1(l.venue)))
  ORDER BY e.event_key LIMIT 1) AS confirmed_published_match
FROM radar_definitivo.listing_occurrences l
JOIN radar_definitivo.sources s ON s.source_id=l.source_id
WHERE l.last_run_id=%s
ORDER BY l.listing_key
"""
CHECKS_SQL="""
SELECT status,count(*)::int FROM radar_definitivo.source_checks
WHERE run_id=%s GROUP BY status
"""
SNAPSHOT_SQL="""
SELECT
 (SELECT count(*)::int FROM public.radar_agenda_events
   WHERE status='scheduled' AND verification='confirmed' AND published_at IS NOT NULL),
 (SELECT count(*)::int FROM public.radar_agenda_events),
 (SELECT count(*)::int FROM radar_definitivo.listing_occurrences),
 (SELECT count(*)::int FROM public.radar_v3_source_observations)
"""
# This UPDATE can only be performed by the scoped ingestion role; the regular
# website's read-only role cannot mutate the run summary or publish anything.
PERSIST_SQL="""
UPDATE radar_definitivo.runs
SET summary=jsonb_set(summary,'{editorial_funnel_v1}',%s::jsonb,true)
WHERE run_id=%s AND finished_at IS NOT NULL
 AND status IN ('complete','partial')
 AND NOT (summary ? 'editorial_funnel_v1')
RETURNING run_id
"""

def asint(value):
    return int(value or 0)

def category(circuit):
    key=str(circuit or "").strip().lower()
    return key if key in LABELS else "unclassified"

def blank_counts():
    return dict(distinctDetected=0,new=0,seenAgain=0,
        possibleDuplicates=0,pendingEditorial=0,
        completePrimaryEvidence=0,matchedPublished=0,
        venueNamesMentioned=0,missingTime=0,missingVenue=0)

def calculate(run,rows,checks,snapshot):
    """Only facts TOUCHED by this run, not every old lead in the database."""
    (rid,mode,status,started,ended,selected,checked,
     parsed_total,parsed_new,url_new,url_seen)=run
    grouped=defaultdict(list)
    unique_venues=defaultdict(set)
    cross_venue=set()
    for row in rows:
        (key,source,title,day,clock,venue,url,first,circuit,
         norm_title,norm_venue,primary,published)=row
        rubro=category(circuit)
        grouped[rubro].append(row)
        if norm_venue:
            unique_venues[rubro].add(norm_venue)
            cross_venue.add(norm_venue)
    by=[]
    summary=blank_counts()
    duplicate_global=set()
    published_global=set()
    for rubro in sorted(grouped):
        facts=grouped[rubro]
        counts=blank_counts()
        collisions=Counter()
        pubs=set()
        for row in facts:
            (key,source,title,day,clock,venue,url,first,circ,
             norm_title,norm_venue,primary,published)=row
            counts["distinctDetected"]+=1
            counts["new"]+=int(first==rid)
            counts["seenAgain"]+=int(first!=rid)
            counts["missingTime"]+=int(not clock)
            counts["missingVenue"]+=int(not norm_venue)
            ready=bool(primary and clock and norm_venue)
            counts["completePrimaryEvidence"]+=int(ready)
            counts["pendingEditorial"]+=int(not published)
            if published:
                pubs.add(published)
                published_global.add(published)
            if norm_title and norm_venue and clock:
                # Same title + venue + day + clock across source records is a
                # suspected duplicate, never automatically a merge approval.
                collision=(norm_title,str(day),clock,norm_venue)
                collisions[collision]+=1
                duplicate_global.add((collision,key))
        counts["matchedPublished"]=len(pubs)
        counts["possibleDuplicates"]=sum(n-1 for n in collisions.values() if n>1)
        counts["venueNamesMentioned"]=len(unique_venues[rubro])
        for field in summary:
            if field not in ("venueNamesMentioned","matchedPublished","possibleDuplicates"):
                summary[field]+=counts[field]
        by.append({"rubro":rubro,"label":LABELS[rubro],**counts})
    summary["venueNamesMentioned"]=len(cross_venue)
    summary["matchedPublished"]=len(published_global)
    # A venue may be mentioned under multiple source circuits; title + day +
    # clock + venue is the fact identity, regardless of evidence source.
    collisions=Counter()
    for facts in grouped.values():
        for row in facts:
            norm_title,norm_venue=row[10],row[11]
            if norm_title and norm_venue and row[4]:
                collisions[(norm_title,str(row[3]),row[4],norm_venue)]+=1
    summary["possibleDuplicates"]=sum(n-1 for n in collisions.values() if n>1)
    summary["urlCandidatesNew"]=asint(url_new)
    summary["urlCandidatesSeen"]=asint(url_seen)
    summary["parsedListingReads"]=asint(parsed_total)
    summary["parsedNewListingReads"]=asint(parsed_new)
    summary["publishedNewThisRun"]=None  # Editorial approvals are not Radar writes.
    summary["newPlacesApprovedThisRun"]=None  # No place-approval history per run.
    summary["publishedCanonicalSnapshot"]=asint(snapshot[0])
    summary["allCanonicalSnapshot"]=asint(snapshot[1])
    summary["stagingSnapshot"]=asint(snapshot[2])
    summary["olderObservationsSnapshot"]=asint(snapshot[3])
    report={"schema":SCHEMA,"runId":rid,"mode":mode,"radarStatus":status,
        "startedAt":started.isoformat(),"finishedAt":ended.isoformat(),
        "sourceSelected":asint(selected),"sourceChecked":asint(checked),
        "sourceChecks":dict(sorted(checks.items())),
        "counts":summary,"byRubro":by,
        "scope":"run_id_last_touched_occurrences_plus_current_approved_catalogue_snapshot",
        "unit":"distinct listing keys touched by this run; source circuit is NOT per-event genre",
        "validationRule":"completePrimaryEvidence means dated first-party original with clock and venue, NOT editorial approval",
        "repeatRule":"seenAgain is re-observation across runs, NOT a duplicate",
        "duplicateRule":"possibleDuplicates shares normalized title/date/time/venue; review required, separate showtimes remain separate",
        "publicationRule":"matchedPublished joins an exact confirmed published catalogue event; NOT newly published by Radar",
        "placeRule":"venueNamesMentioned counts distinct names, NOT approved venue entities",
        "cannotClaim":["citywide coverage","automatic editorial validation",
                       "new editorial publications attributed to this Radar run",
                       "deduplication accuracy without manual review"],
        "autoPublished":False}
    if summary["distinctDetected"]!=summary["new"]+summary["seenAgain"]:
        raise ValueError("FUNNEL_RUN_PARTITION_INVARIANT")
    if summary["pendingEditorial"]+summary["matchedPublished"]>summary["distinctDetected"]+len(published_global):
        raise ValueError("FUNNEL_PUBLICATION_INVARIANT")
    return report

def read(cur):
    cur.execute(RUN_SQL)
    run=cur.fetchone()
    if not run:
        raise RuntimeError("FUNNEL_NO_COMPLETED_RUN")
    run_id=run[0]
    cur.execute(FACTS_SQL,(run_id,))
    facts=cur.fetchall()
    cur.execute(CHECKS_SQL,(run_id,))
    checks=dict(cur.fetchall())
    cur.execute(SNAPSHOT_SQL)
    snapshot=cur.fetchone()
    return calculate(run,facts,checks,snapshot)

def persist(database_url,report):
    """One read-to-write handoff, bounded to a completed run.summary JSON key."""
    import psycopg
    with psycopg.connect(database_url,connect_timeout=12) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE poraca_definitivo_scope")
                cur.execute("""SELECT current_database(),session_user,current_user,
                  current_setting('neon.project_id',true),
                  current_setting('neon.branch_id',true),
                  has_table_privilege(current_user,'radar_definitivo.runs','UPDATE'),
                  has_table_privilege(current_user,'public.radar_agenda_events','INSERT,UPDATE,DELETE,TRUNCATE')""")
                if cur.fetchone()!=("neondb","poraca_definitivo_ingest",
                    "poraca_definitivo_scope","frosty-union-52906378",
                    "br-mute-recipe-b4odj2bl",True,False):
                    raise RuntimeError("FUNNEL_SCOPE_OR_WRITE_BOUNDARY_MISMATCH")
                cur.execute(PERSIST_SQL,(json.dumps(report,ensure_ascii=False),report["runId"]))
                if cur.fetchone() is None:
                    # Retry safe: no rewrites of a historical report.
                    cur.execute("""SELECT summary->'editorial_funnel_v1'
                      FROM radar_definitivo.runs WHERE run_id=%s""",(report["runId"],))
                    previous=cur.fetchone()
                    if not previous or previous[0]!=report:
                        raise RuntimeError("FUNNEL_ALREADY_SAVED_OR_RACE")
                    return "already_saved_identical"
    return "persisted_one_run_summary"
