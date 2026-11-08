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
SELECT p.proposal_id,p.title,p.event_date::text event_day,p.event_time,p.venue,
       p.evidence->>'original_url' detail_url
FROM radar2.proposals p JOIN radar2.documents d ON d.url=p.document_url
WHERE p.event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
                      AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date+7
  AND p.evidence->>'kind'='event'
  AND p.review_state NOT IN ('historico','contradictorio')
  AND coalesce(p.evidence->>'duplicate_of','')=''
  AND d.source IN ('Genda','Genda teatro')
  AND p.evidence->>'original_url' ~ '^https://agendalaplata[.]ar/evento/[a-z0-9-]{8,220}$'
  AND coalesce(p.evidence->'primary_source_followup'->>'checkedAt','2000-01-01T00:00:00+00:00')::timestamptz
      < now()-interval '24 hours'
ORDER BY p.event_date,p.event_time NULLS LAST,p.proposal_id
LIMIT 18
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
}
MONTHS = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,
          'junio':6,'julio':7,'agosto':8,'septiembre':9,
          'octubre':10,'noviembre':11,'diciembre':12}
MONTH_NAMES = '|'.join(MONTHS)

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
    for match in re.finditer(r'(?<!\d)(0?[1-9]|[12]\d|3[01])\s+de\s+('+MONTH_NAMES+r')\s+de\s+(20\d{2})(?!\d)',ascii_text):
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
    for row in rows[:max(1,min(int(limit),3))]:
        stats['selected']+=1
        base={'proposalId':row['proposal_id'],'date':row['event_day'],
              'title':row['title'],'venue':row['venue'],
              'secondaryDetailUrl':row['detail_url'],'checkedAt':utc(),
              'runId':collector.run_id,'publicationApproved':False,
              'requiresIndependentEditorialReview':True,
              'reviewerRole':'poraca_editorial_prod',
              'reviewBy':row['event_day']+'T12:00:00-03:00',
              'sourceRole':'secondary_event_detail'}
        detail_url=row['detail_url']
        if not detail_url.startswith('https://agendalaplata.ar/evento/') or not safe_url(detail_url):
            base.update(status='SECONDARY_URL_REJECTED');result.append(base);stats['held']+=1;continue
        d=collector.fetch(detail_url,'Genda secondary detail')
        if not d or d.get('http_status')!=200 or d.get('final_url')!=detail_url:
            base.update(status='SECONDARY_FETCH_BLOCKED');result.append(base);stats['held']+=1;continue
        stats['detailFetched']+=1
        base['secondarySha256']=d['sha256']
        base['secondaryFetchedAt']=d['fetched_at']
        # A valid detail is not enough; prefer an event-specific ticket link.
        links=sorted({u for u in collector.links(d) if ticket_detail(u)})
        if not links:
            base.update(status='NO_EXPLICIT_PRIMARY_EVENT_LINK',
                        reason='Secondary detail has no allowlisted per-event ticket link')
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
  AND EXISTS (SELECT 1 FROM radar2.documents d
    WHERE d.url=x.receipt->>'secondaryDetailUrl'
      AND d.sha256=x.receipt->>'secondarySha256'
      AND d.last_run_id=$2)
  AND (x.receipt->>'primarySha256' IS NULL OR EXISTS (
    SELECT 1 FROM radar2.documents src
    WHERE src.url=x.receipt->>'primaryUrl'
      AND src.sha256=x.receipt->>'primarySha256'
      AND src.last_run_id=$2))
RETURNING p.proposal_id
"""

def stage_followups(conn,run_id,receipts):
    """Stage only if the source documents were persisted in the same run."""
    valid=[r for r in receipts if r.get('secondarySha256')]
    if not valid:return 0
    written=execute(conn,FOLLOWUP_STAGE_SQL,[__import__('json').dumps(valid,ensure_ascii=False),run_id])['rows']
    if len(written)!=len(valid):raise RuntimeError('PRIMARY_FOLLOWUP_SAME_RUN_READBACK_MISMATCH')
    return len(written)
