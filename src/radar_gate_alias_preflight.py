"""Read-only shadow protection against duplicate observations behind URL aliases.

The current gate counts existing observations by *exact source_event_url*.
A category listing and an official /evento/ page may instead describe the
same performance. This module reports probable collisions but NEVER changes
the underlying gate, approval state or canonical data.
"""
import re

SQL = """WITH candidates AS (
 SELECT m.observation_id,m.observed_title,m.observed_date,m.observed_time,
        m.observed_venue,m.source_event_url,m.mapped_public_source_id,
        m.gate_decision,m.existing_observation_count,
        lower(regexp_replace(translate(coalesce(m.observed_title,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) title_key,
        lower(regexp_replace(translate(coalesce(m.observed_venue,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) venue_key
 FROM radar_definitivo.motor_ingest_gate_v1 m
 WHERE m.existing_observation_count=0 AND m.observed_date IS NOT NULL
   AND m.observed_time IS NOT NULL AND m.mapped_public_source_id IS NOT NULL
), existing AS (
 SELECT o.observation_id,o.origin_source_id,o.observed_title,o.observed_date,
        o.observed_time,o.observed_venue,o.source_event_url,
        coalesce(o.original_evidence::text,'') LIKE '%DO_NOT_APPROVE%' AS editorial_hold,
        lower(regexp_replace(translate(coalesce(o.observed_title,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) title_key,
        lower(regexp_replace(translate(coalesce(o.observed_venue,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) venue_key
 FROM public.radar_v3_source_observations o
)
SELECT c.observation_id,c.gate_decision,e.observation_id AS public_observation_id,
       c.observed_title,c.observed_date::text,c.observed_time,
       c.source_event_url,e.source_event_url AS existing_original_url,
       e.observed_venue AS existing_venue,
       CASE WHEN e.editorial_hold THEN 'HOLD_EDITORIAL_DO_NOT_APPROVE'
            WHEN c.venue_key=e.venue_key OR strpos(c.venue_key,e.venue_key)>0
                 OR strpos(e.venue_key,c.venue_key)>0
            THEN 'REVIEW_EXISTING_OBSERVATION_DO_NOT_INSERT'
            ELSE 'HOLD_VENUE_OR_ROOM_IDENTITY_REVIEW' END AS safe_next_step
FROM candidates c JOIN existing e
ON c.observed_date=e.observed_date
AND left(c.observed_time,5)=left(e.observed_time,5)
AND c.title_key=e.title_key
AND length(c.title_key)>=10
-- Source and venue mismatches are a reason to REVIEW, never proof of novelty.
-- Room compatibility is not an automatic merge: same title can fill two rooms.
ORDER BY c.observed_date,c.observed_time,c.observation_id
LIMIT 600"""

def summarize(rows):
    """Only candidate aliases for human preflight, never a write decision."""
    observed=set()
    groups={}
    samples=[]
    # Material editorial holds take precedence over historical secondary matches.
    prioritized=sorted(rows,key=lambda r:(
        not (len(r)>9 and r[9]=="HOLD_EDITORIAL_DO_NOT_APPROVE"),
        r[1]!="REVIEW_ORIGINAL_BEFORE_ANY_INSERT"))
    for row in prioritized:
        candidate,decision,public_id,title,day,hour,*urls=row[:8]
        observed.add(public_id)
        groups.setdefault(decision,set()).add(candidate)
        if len(samples)<8:
            samples.append({"title":str(title),"date":str(day),"time":str(hour),
                            "gate_decision":str(decision),
                            "public_observation_id":str(public_id),
                            "safe_next_step":str(row[9]) if len(row)>9 else "REVIEW_EXISTING_OBSERVATION_DO_NOT_INSERT"})
    return {"status":"read_only_alias_suspicions",
            "matched_gate_rows":sum(len(items) for items in groups.values()),
            "distinct_public_observations":len(observed),
            "review_original_already_present":len(groups.get(
                "REVIEW_ORIGINAL_BEFORE_ANY_INSERT",set())),
            "by_gate":{key:len(value) for key,value in sorted(groups.items())},
            "editorial_holds":sum(1 for r in rows if len(r)>9 and r[9]=="HOLD_EDITORIAL_DO_NOT_APPROVE"),
            "samples":samples,
            "authorized_to_write":False,
            "note":"URL aliases and compatible venues: potential matches, not automated joins."}
