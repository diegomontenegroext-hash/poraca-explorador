"""Pre-admisión de las funciones Radar, sin escribir ni aprobar información.

Agrupa observaciones candidatas por título + fecha + horario (la sede puede
diferir y se trata como conflicto). Monitores sobre el MISMO enlace no
equivalen a corroboración independiente. Toda decisión sigue siendo humana
o de un flujo editorial expresamente autorizado.
"""
from __future__ import annotations

SCHEMA="poraca-radar-editorial-preview-v1"

SQL=r"""
WITH eligible AS (
 SELECT l.listing_key,l.source_id,l.title,l.event_date,l.event_time,
        l.venue,l.proof_url,l.proof_method,l.evidence_tier,l.last_seen_at,
        s.name AS source_name,
        lower(regexp_replace(btrim(l.title),'\s+',' ','g')) AS title_key
 FROM radar_definitivo.listing_occurrences l
 JOIN radar_definitivo.sources s USING(source_id)
 WHERE l.event_date >= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
   AND l.event_date <= (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date + 21
   AND l.event_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'
   AND nullif(btrim(l.venue),'') IS NOT NULL
   AND length(btrim(l.title)) >= 4
   AND l.evidence_tier IN (
       'primary_venue','primary_ticket_listing','primary_program',
       'primary_program_ics','primary_structured_page')
   AND NOT EXISTS (
      SELECT 1 FROM radar_archive_20261031.bootstrap_crosslink_listings a
      WHERE a.listing_key=l.listing_key)
),
bundled AS (
 SELECT title_key,event_date,event_time,
        count(DISTINCT listing_key)::int AS raw_observations,
        count(DISTINCT source_id)::int AS monitors,
        count(DISTINCT proof_url)::int AS different_proofs,
        count(DISTINCT lower(btrim(venue)))::int AS venue_variants
 FROM eligible
 GROUP BY title_key,event_date,event_time
),
ranked AS (
 SELECT e.*,b.raw_observations,b.monitors,b.different_proofs,b.venue_variants,
        row_number() OVER(PARTITION BY e.title_key,e.event_date,e.event_time
          ORDER BY CASE e.evidence_tier
            WHEN 'primary_venue' THEN 0
            WHEN 'primary_program_ics' THEN 1
            WHEN 'primary_ticket_listing' THEN 2
            WHEN 'primary_structured_page' THEN 3
            ELSE 4 END,
          CASE WHEN e.proof_method ILIKE '%category_card%' THEN 1 ELSE 0 END,
          e.last_seen_at DESC,e.listing_key) AS choice
 FROM eligible e
 JOIN bundled b USING(title_key,event_date,event_time)
)
SELECT event_date,event_time,title,venue,proof_url,proof_method,evidence_tier,
       source_name,monitors,raw_observations,different_proofs,venue_variants,
       CASE
          WHEN venue_variants>1 THEN 'HOLD_VENUE_IDENTITY_VARIANTS'
          WHEN different_proofs>1 THEN 'REVIEW_MULTIPLE_PROOF_URLS'
          ELSE 'REVIEW_ORIGINAL_EVENT'
       END AS review_gate
FROM ranked WHERE choice=1
ORDER BY event_date,event_time,title LIMIT 300
"""


def summarize(rows):
    seen={"HOLD_VENUE_IDENTITY_VARIANTS":0,
          "REVIEW_MULTIPLE_PROOF_URLS":0,"REVIEW_ORIGINAL_EVENT":0}
    items=[]
    for row in rows:
        (day,clock,title,venue,proof,method,tier,source,
         monitors,observations,different_proofs,venue_variants,gate)=row
        if gate not in seen:
            raise ValueError("Unrecognized review gate")
        seen[gate]+=1
        items.append({"day":str(day),"time":clock,"title":title,
             "venue":venue,"proofUrl":proof,"proofMethod":method,
             "evidenceTier":tier,"source":source,"monitors":int(monitors),
             "observations":int(observations),
             "differentProofUrls":int(different_proofs),
             "venueVariants":int(venue_variants),"reviewGate":gate,
             "canonWriteApproved":False,"publicationApproved":False})
    return {"schema":SCHEMA,"reviewGroups":len(items),"gates":seen,
            "sample":items[:12],
            "independentCorroborationsVerified":0,
            "editorialObservationsWritten":0,
            "canonWriteApproved":False,"publicationApproved":False,
            "state":"READ_ONLY_QUEUE_NOT_EDITORIAL_HANDOFF",
            "note":"Una vista de revisión no es una admisión. Múltiples monitores "
                   "del mismo enlace NO constituyen originales independientes; "
                   "títulos repetidos requieren cotejo antes de deduplicar."}
