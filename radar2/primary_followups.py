"""Bounded follow-up from secondary Genda event detail to a specific primary ticket.

This is EVIDENCE COLLECTION, not independent editorial approval. Every
status, including negative or contradictory proof, is preserved for review.
The collector's existing robots/HTTP policy controls all reads.
"""
import re
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit
from collector import norm, utc
from persist import execute
from capabilities import safe_url

CANDIDATES_SQL = """
SELECT * FROM (
SELECT selected.*,row_number() OVER (
 PARTITION BY selected.event_day
 ORDER BY selected.first_seen_at,selected.event_time NULLS LAST,selected.proposal_id
) AS day_slot,
 row_number() OVER(PARTITION BY selected.detail_url ORDER BY selected.event_day,selected.first_seen_at,selected.proposal_id) AS detail_slot
FROM (
SELECT DISTINCT ON (p.event_date,p.evidence->>'original_url')
       p.proposal_id,p.first_seen_at,p.title,p.event_date::text event_day,p.event_time,p.venue,
       p.evidence->>'original_url' detail_url,d.source AS secondary_source
FROM radar2.proposals p JOIN radar2.documents d ON d.url=p.document_url
CROSS JOIN LATERAL (SELECT p.evidence->'primary_source_followup' AS j) receipt
CROSS JOIN LATERAL (SELECT CASE WHEN pg_input_is_valid(receipt.j->>'checkedAt','timestamptz')
 THEN (receipt.j->>'checkedAt')::timestamptz ELSE '2000-01-01T00:00:00+00:00'::timestamptz END AS at) checked
LEFT JOIN radar2.documents detail ON detail.url=p.evidence->>'original_url'
LEFT JOIN radar2.documents primary_doc ON primary_doc.url=receipt.j->>'primaryUrl'
WHERE p.event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
                      AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+14
  AND (p.event_date>(now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
       OR p.event_time IS NULL
       OR p.event_time>to_char((now() AT TIME ZONE 'America/Argentina/Buenos_Aires'),'HH24:MI'))
  AND p.evidence->>'kind'='event'
  AND p.review_state NOT IN ('historico','contradictorio')
  AND coalesce(p.evidence->>'duplicate_of','')=''
  AND coalesce(p.evidence->>'interpretation_superseded_by','')=''
  AND NOT(p.evidence ? 'editorial_exclusion')
  AND coalesce(p.evidence->'territory_resolution'->>'status','')<>'source_stated_outside'
  AND coalesce(p.evidence->>'event_status','') NOT IN ('cancelled','rescheduled_pending_review')
  AND (
    (d.source IN ('Genda','Genda teatro')
      AND p.evidence->>'original_url' ~ '^https://agendalaplata[.]ar/evento/[a-z0-9-]{8,220}$')
    OR (d.source='elevenflow.app'
      AND p.evidence->>'original_url' ~ '^https://elevenflow[.]app/events/[a-z0-9-]{8,220}$')
  )
  -- An observation already bound to a confirmed event does not need another
  -- primary-source search. Require exact receipt or source/date/title/venue.
  AND NOT EXISTS (
   SELECT 1 FROM public.radar_agenda_events a
   WHERE a.event_date=p.event_date AND a.status='scheduled' AND a.verification='confirmed'
    AND (
     EXISTS(SELECT 1 FROM jsonb_array_elements(CASE WHEN jsonb_typeof(a.evidence)='array' THEN a.evidence ELSE '[]'::jsonb END) m
      WHERE m->>'proposalId'=p.proposal_id AND m->>'sourceDocumentSha256'=d.sha256)
     OR (a.source_url IN (p.document_url,p.evidence->>'original_url',receipt.j->>'primaryUrl')
       AND public.poraca_fact_key_v1(a.title)=public.poraca_fact_key_v1(p.title)
       AND length(coalesce(public.poraca_fact_key_v1(p.venue),''))>=4
       AND public.poraca_fact_key_v1(a.venue)=public.poraca_fact_key_v1(p.venue)
       AND a.event_time IS NOT DISTINCT FROM p.event_time)
    )
  )
  -- A unique exact known occurrence is a reconciliation task, not a new
  -- source search. A first-party reported clock is not a verified start.
  AND NOT (
   p.event_time IS NOT NULL AND p.event_time NOT IN ('00:00','23:58','23:59')
   AND length(coalesce(public.poraca_fact_key_v1(p.title),''))>=8
   AND length(coalesce(public.poraca_fact_key_v1(p.venue),''))>=4
   AND 1=(SELECT count(*) FROM public.radar_agenda_events a
    WHERE a.event_date=p.event_date AND a.status='scheduled' AND a.verification='confirmed'
      AND public.poraca_fact_key_v1(a.title)=public.poraca_fact_key_v1(p.title)
      AND public.poraca_fact_key_v1(a.venue)=public.poraca_fact_key_v1(p.venue)
      AND (a.event_time=p.event_time OR (a.event_time IS NULL AND EXISTS(
        SELECT 1 FROM jsonb_array_elements(CASE WHEN jsonb_typeof(a.evidence)='array' THEN a.evidence ELSE '[]'::jsonb END) m
        WHERE m->>'sourceRole'='first_party' AND m->>'url'=a.source_url
          AND m->>'reportedTime'=p.event_time AND m->>'timeStatus'='reported_unverified'
      )))
   )
  )
  -- Reopen immediately only when the occurrence or a stored source version
  -- changes. An unchanged useful receipt is not a daily work item.
  AND (
   receipt.j IS NULL
   OR receipt.j->>'title' IS DISTINCT FROM p.title
   OR receipt.j->>'date' IS DISTINCT FROM p.event_date::text
   OR receipt.j->>'venue' IS DISTINCT FROM p.venue
   OR receipt.j->>'secondaryDetailUrl' IS DISTINCT FROM p.evidence->>'original_url'
   OR (receipt.j ? 'reportedTime' AND receipt.j->>'reportedTime' IS DISTINCT FROM p.event_time)
   OR (detail.sha256 IS NOT NULL AND receipt.j->>'secondarySha256' IS NOT NULL
       AND detail.sha256 IS DISTINCT FROM receipt.j->>'secondarySha256')
   OR (primary_doc.sha256 IS NOT NULL AND receipt.j->>'primarySha256' IS NOT NULL
       AND primary_doc.sha256 IS DISTINCT FROM receipt.j->>'primarySha256')
   OR checked.at < now()-CASE
      WHEN receipt.j->>'status' IN ('PRIMARY_RECEIPT_REVIEW_REQUIRED','NO_EXPLICIT_PRIMARY_EVENT_LINK',
        'ORIGINAL_DATE_CONFLICT','ORIGINAL_DATE_NOT_PROVEN','ORIGINAL_IDENTITY_INCOMPLETE')
       THEN CASE WHEN p.event_date<=(now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+1
                  THEN interval '48 hours' ELSE interval '7 days' END
      ELSE interval '24 hours' END
  )
ORDER BY p.event_date,p.evidence->>'original_url',p.proposal_id
) selected
) ranked
-- One distinct source detail before repeating its other dates, and one dated
-- session per day before a second. This keeps repeated exhibition visiting days
-- from exhausting the eight independent primary checks; no date is deleted.
ORDER BY ranked.detail_slot,ranked.day_slot,ranked.event_day,ranked.first_seen_at,ranked.event_time NULLS LAST,ranked.proposal_id
LIMIT 120
"""

# Ticket detail only. Plateanet /teatro/13 is a theatre CATALOG, not
# proof of a specific session. Unknown destinations are not blindly crawled.
TICKETING_PATHS = {
    'www.passline.com': r'^/eventos/[a-z0-9-]{5,160}/?$',
    'passline.com': r'^/eventos/[a-z0-9-]{5,160}/?$',
    'www.casualpass.net': r'^/e/[a-z0-9-]{4,160}/?$',
    'casualpass.net': r'^/e/[a-z0-9-]{4,160}/?$',
    'catpass.net': r'^/eventos/[a-z0-9-]{5,180}/?$',
    'www.catpass.net': r'^/eventos/[a-z0-9-]{5,180}/?$',
    'wearebombo.com': r'^/eventos/[a-z0-9-]{5,180}/?$',
    'centralticket.net': r'^/event/[a-z0-9-]{4,160}/?$',
    'www.centralticket.net': r'^/event/[a-z0-9-]{4,160}/?$',
}
MONTHS = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,
          'junio':6,'julio':7,'agosto':8,'septiembre':9,
          'octubre':10,'noviembre':11,'diciembre':12}
MONTHS.update({'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,
               'jul':7,'ago':8,'sep':9,'sept':9,'oct':10,'nov':11,'dic':12})
MONTH_NAMES = '|'.join(sorted(MONTHS,key=len,reverse=True))

def social_profile_leads(urls,limit=4):
    """Only outbound public Instagram profile URLs in the already-read secondary HTML.
    These are unverified editorial leads, NOT primary event receipts or approvals.
    """
    leads=set()
    reserved={'p','reel','reels','stories','explore','accounts','tv','direct',
              'about','developer','legal','static','graphql','instagram'}
    for url in urls:
        try:
            u=urlsplit(str(url))
            if u.scheme!='https' or u.username or u.password or u.port not in (None,443):
                continue
            if (u.hostname or '').lower() not in ('instagram.com','www.instagram.com'):
                continue
            handle=u.path.strip('/')
            if not re.fullmatch(r'[A-Za-z0-9._]{2,30}',handle) or handle.lower() in reserved:
                continue
            leads.add('https://www.instagram.com/'+handle.lower()+'/')
        except (ValueError,TypeError):
            continue
    return sorted(leads)[:max(0,min(int(limit),4))]

def secondary_detail(url):
    try:
        p=urlsplit(url)
        if p.scheme!='https' or p.username or p.password or p.query or p.fragment:
            return False
        return bool(
            ((p.hostname or '').lower()=='agendalaplata.ar' and
             re.fullmatch(r'/evento/[a-z0-9-]{8,220}',p.path,re.I))
            or ((p.hostname or '').lower()=='elevenflow.app' and
                re.fullmatch(r'/events/[a-z0-9-]{8,220}',p.path,re.I)))
    except ValueError:
        return False

def ticket_detail(url):
    try:
        p=urlsplit(url)
        return (p.scheme=='https' and not p.username and not p.password
                and p.port in (None,443)
                and bool(re.fullmatch(TICKETING_PATHS.get((p.hostname or '').lower(),r'(?!)'),p.path,re.I))
                and not p.query and not p.fragment)
    except ValueError:
        return False

def dates_in(text):
    """Explicit year is mandatory: a day/month without a year is not proof."""
    found=set()
    for match in re.finditer(r'(?<!\d)(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])(?!\d)',text):
        try:found.add(date(*map(int,match.groups())).isoformat())
        except ValueError:pass
    for match in re.finditer(r'(?<!\d)(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})(?!\d)',text):
        d,m,y=map(int,match.groups())
        try:found.add(date(y,m,d).isoformat())
        except ValueError:pass
    ascii_text=norm(text)
    for match in re.finditer(r'(?<!\d)(0?[1-9]|[12]\d|3[01])\s+de\s+('+MONTH_NAMES+r')\s+(?:de\s+)?(20\d{2})(?!\d)',ascii_text):
        d,m,y=match.groups()
        try:found.add(date(int(y),MONTHS[m],int(d)).isoformat())
        except ValueError:pass
    return sorted(found)

def compact_key(text):
    return re.sub(r'[^a-z0-9]','',norm(text))

def classify_ticket(row,doc):
    """No machine claim of first-party approval; evidence-level triage only."""
    if not doc or doc.get('http_status')!=200 or doc.get('final_url')!=doc.get('url'):
        return 'ORIGINAL_FETCH_NOT_VERIFIED',[]
    dates=dates_in(doc.get('text',''))
    if dates and row['event_day'] not in dates:
        return 'ORIGINAL_DATE_CONFLICT',[]
    if not dates:return 'ORIGINAL_DATE_NOT_PROVEN',[]
    source_key=compact_key(doc.get('text',''))
    expected_title=compact_key(row.get('title'))
    expected_venue=compact_key(row.get('venue'))
    fields=['date']
    if expected_title and expected_title in source_key:fields.append('title')
    if expected_venue and expected_venue in source_key:fields.append('venue')
    if all(x in fields for x in ('title','date','venue')):
        return 'PRIMARY_RECEIPT_REVIEW_REQUIRED',fields
    return 'ORIGINAL_IDENTITY_INCOMPLETE',fields

def follow_secondary(conn,collector,limit=3):
    """Return only justified, bounded receipts to stage in the SAME Radar run."""
    rows=execute(conn,CANDIDATES_SQL)['rows']
    result=[];stats={'selected':0,'detailFetched':0,'primaryFetched':0,
                     'readyForReview':0,'conflicts':0,'held':0}
    for row in rows[:max(1,min(int(limit),8))]:
        stats['selected']+=1
        base={'proposalId':row['proposal_id'],'date':row['event_day'],
              'title':row['title'],'venue':row['venue'],'reportedTime':row.get('event_time'),
              'receiptPolicy':'version_aware_followup_v2',
              'secondaryDetailUrl':row['detail_url'],'checkedAt':utc(),
              'runId':collector.run_id,'publicationApproved':False,
              'requiresIndependentEditorialReview':True,
              'reviewerRole':'poraca_editorial_prod',
              'reviewBy':row['event_day']+'T08:00:00-03:00',
              'sourceRole':'secondary_event_detail',
              'secondaryPublisher':row.get('secondary_source')}
        detail_url=row['detail_url']
        if not secondary_detail(detail_url) or not safe_url(detail_url):
            base.update(status='SECONDARY_URL_REJECTED');result.append(base);stats['held']+=1;continue
        d=collector.fetch(detail_url,'Secondary event detail · '+str(row.get('secondary_source','unknown')))
        if not d or d.get('http_status')!=200 or d.get('final_url')!=detail_url:
            base.update(status='SECONDARY_FETCH_BLOCKED');result.append(base);stats['held']+=1;continue
        stats['detailFetched']+=1
        base['secondarySha256']=d['sha256']
        base['secondaryFetchedAt']=d['fetched_at']
        # A valid detail is not enough; prefer an event-specific ticket link.
        outbound=collector.links(d)
        links=sorted({u for u in outbound if ticket_detail(u)})
        # Do not request social platforms here. An explicit profile in Genda
        # helps editorial follow-up but cannot validate a dated performance.
        profile_leads=social_profile_leads(outbound)
        if not links:
            base.update(status='NO_EXPLICIT_PRIMARY_EVENT_LINK',
                        reason='Secondary detail has no allowlisted per-event ticket link',
                        socialProfileLeads=profile_leads,
                        socialLeadRole='unverified_public_profile_link_not_original_evidence')
            result.append(base);stats['held']+=1;continue
        original=links[0]
        base['primaryUrl']=original
        base['sourceRole']='ticketing_candidate_not_editorial_approval'
        if not safe_url(original):
            base.update(status='PRIMARY_URL_UNSAFE');result.append(base);stats['held']+=1;continue
        proof=collector.fetch(original,'Ticketing original candidate',detail_url)
        if not proof or proof.get('http_status')!=200 or proof.get('final_url')!=original:
            base.update(status='PRIMARY_FETCH_BLOCKED')
            result.append(base);stats['held']+=1;continue
        stats['primaryFetched']+=1
        base.update(primarySha256=proof['sha256'],primaryFetchedAt=proof['fetched_at'],
                    primaryHttpStatus=200,originalFields=[])
        status,fields=classify_ticket(row,proof)
        base.update(status=status,originalFields=fields)
        if status=='PRIMARY_RECEIPT_REVIEW_REQUIRED':stats['readyForReview']+=1
        elif status=='ORIGINAL_DATE_CONFLICT':stats['conflicts']+=1
        else:stats['held']+=1
        result.append(base)
    collector.source_followups.extend(result)
    return stats

# Run after existing atomic collector write. The limited role can update
# radar2.proposals, but has no canonical agenda write permission.
# A dated secondary row is never upgraded to a first-party proposal.
FOLLOWUP_STAGE_SQL = """
WITH x AS (SELECT value AS receipt FROM jsonb_array_elements($1::jsonb))
UPDATE radar2.proposals p
SET evidence=p.evidence || jsonb_build_object('primary_source_followup',x.receipt)
FROM x
WHERE p.proposal_id=x.receipt->>'proposalId'
  AND p.event_date::text=x.receipt->>'date'
  AND p.evidence->>'original_url'=x.receipt->>'secondaryDetailUrl'
  AND p.evidence->>'kind'='event'
  AND (x.receipt->>'secondarySha256' IS NULL OR EXISTS (
    SELECT 1 FROM radar2.documents d
    WHERE d.url=x.receipt->>'secondaryDetailUrl'
      AND d.sha256=x.receipt->>'secondarySha256'
      AND d.last_run_id=$2))
  AND (x.receipt->>'primarySha256' IS NULL OR EXISTS (
    SELECT 1 FROM radar2.documents src
    WHERE src.url=x.receipt->>'primaryUrl'
      AND src.sha256=x.receipt->>'primarySha256'
      AND src.last_run_id=$2))
RETURNING p.proposal_id
"""

def stage_followups(conn,run_id,receipts):
    """Stage only if the source documents were persisted in the same run."""
    if not receipts:return 0
    written=execute(conn,FOLLOWUP_STAGE_SQL,[__import__('json').dumps(receipts,ensure_ascii=False),run_id])['rows']
    if len(written)!=len(receipts):raise RuntimeError('PRIMARY_FOLLOWUP_SAME_RUN_READBACK_MISMATCH')
    return len(written)
