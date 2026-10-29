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
        lower(regexp_replace(translate(coalesce(o.observed_title,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) title_key,
        lower(regexp_replace(translate(coalesce(o.observed_venue,''),
          'ÁÉÍÓÚÜÑáéíóúüñ','AEIOUUNaeiouun'),'[^a-zA-Z0-9]+','','g')) venue_key
 FROM public.radar_v3_source_observations o
)
SELECT c.observation_id,c.gate_decision,e.observation_id AS public_observation_id,
       c.observed_title,c.observed_date::text,c.observed_time,
       c.source_event_url,e.source_event_url AS existing_original_url
FROM candidates c JOIN existing e
ON c.mapped_public_source_id=e.origin_source_id
AND c.observed_date=e.observed_date
AND left(c.observed_time,5)=left(e.observed_time,5)
AND c.title_key=e.title_key
AND length(c.title_key)>=10
AND length(c.venue_key)>=6 AND length(e.venue_key)>=6
AND (c.venue_key=e.venue_key OR strpos(c.venue_key,e.venue_key)>0
     OR strpos(e.venue_key,c.venue_key)>0)
ORDER BY c.observed_date,c.observed_time,c.observation_id
LIMIT 600"""

def summarize(rows):
    """Only candidate aliases for human preflight, never a write decision."""
    observed=set()
    groups={}
    samples=[]
    for row in rows:
        candidate,decision,public_id,title,day,hour,*urls=row
        observed.add(public_id)
        groups.setdefault(decision,set()).add(candidate)
        if len(samples)<8:
            samples.append({"title":str(title),"date":str(day),"time":str(hour),
                            "gate_decision":str(decision),
                            "public_observation_id":str(public_id)})
    return {"status":"read_only_alias_suspicions",
            "matched_gate_rows":sum(len(items) for items in groups.values()),
            "distinct_public_observations":len(observed),
            "review_original_already_present":len(groups.get(
                "REVIEW_ORIGINAL_BEFORE_ANY_INSERT",set())),
            "by_gate":{key:len(value) for key,value in sorted(groups.items())},
            "samples":samples,
            "authorized_to_write":False,
            "note":"URL aliases and compatible venues: potential matches, not automated joins."}
