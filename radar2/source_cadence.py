"""Cadence derives from source class/yield; it never creates another schedule."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from persist import execute

def media_due(conn):
 at=datetime.now(timezone.utc);local=at.astimezone(ZoneInfo('America/Argentina/Buenos_Aires'))
 if local.weekday() not in (3,4,5,6):return False
 rows=execute(conn,"SELECT min(fetched_at)::text last_checked FROM radar2.documents WHERE url IN ('https://www.eldia.com/espectaculos','https://www.0221.com.ar/que-hago')")['rows']
 last=rows[0].get('last_checked') if rows else None
 return not last or (at-datetime.fromisoformat(last)).total_seconds()>=(8 if local.weekday() in (3,4) else 12)*3600

def curator_due(conn,excluded=()):
 """At most one productive curator supplement; fair ten-account batch remains intact."""
 import json
 local=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires'))
 if local.weekday() not in (2,3,4):return []
 rows=execute(conn,"""SELECT evidence->>'origin_account' username,count(*) useful
 FROM radar2.proposals WHERE evidence->>'source_role'='curator' AND event_date>=(now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
 AND coalesce(evidence->>'duplicate_of','')='' AND coalesce(evidence->>'interpretation_superseded_by','')=''
 AND evidence->>'kind'='event' GROUP BY 1 ORDER BY useful DESC,username LIMIT 30""")['rows']
 from rotation import read
 state=read(conn)
 for row in rows:
  u=row['username']
  if not u or u in excluded or u not in state['accounts'] or int(row['useful'])<2:continue
  account=state['accounts'][u]
  last=account.get('curator_last_checked_at') or account.get('official_last_result',{}).get('checked_at')
  if not last or (datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()>=8*3600:return [u]
 return []

def record_curator_checks(conn,usernames,results,run_id):
 from rotation import read,cas
 at=datetime.now(timezone.utc).isoformat()
 for _ in range(4):
  state=read(conn);version=state['version']
  for u in usernames:
   result=next((r for r in results if r.get('username')==u),None)
   if not result:continue
   state['accounts'][u]['curator_last_checked_at']=at
   state['accounts'][u]['curator_last_result']={k:result.get(k) for k in ('status','new_documents','items_returned','meta_error_code')}
   state['accounts'][u]['curator_last_result']['run_id']=run_id
  if cas(conn,state,version):return
 raise RuntimeError('CURATOR_CADENCE_CAS_RETRY_LATER')


# Date-sensitive, bounded re-check of *existing* documents inside the already
# scheduled incremental. Does not create new cron, source identity or publication.
URGENT_REFRESH_SQL="""
SELECT p.document_url AS url,max(d.source) AS source,
       min(p.event_date)::text AS first_event_date,
       max(d.fetched_at)::text AS last_fetched,
       bool_or(
         (d.source='festival.freezer.com.ar'
          AND p.document_url='https://festival.freezer.com.ar/2026/programacion/')
         OR (d.source='www.passline.com'
          AND p.document_url ~ '^https://www[.]passline[.]com/eventos/[a-z0-9-]{5,160}$')
       ) AS priority_original
FROM radar2.proposals p
JOIN radar2.documents d ON d.url=p.document_url
WHERE p.event_date BETWEEN (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date
  AND (now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date + 7
  AND p.review_state<>'historico'
  AND p.evidence->>'kind'='event'
  AND d.source NOT IN ('Instagram','Genda','Genda teatro','El Día','0221')
  AND p.document_url ~ '^https://'
  AND (
    (
      (
       (d.source='festival.freezer.com.ar'
        AND p.document_url='https://festival.freezer.com.ar/2026/programacion/')
       OR (d.source='www.passline.com'
        AND p.document_url ~ '^https://www[.]passline[.]com/eventos/[a-z0-9-]{5,160}$')
      )
      AND d.fetched_at<now()-interval '36 hours'
    )
    OR (
      p.event_date<=(now() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date + 2
      AND p.last_seen_at<now()-interval '24 hours'
      AND d.fetched_at<now()-interval '12 hours'
    )
  )
GROUP BY p.document_url
ORDER BY priority_original DESC,min(p.event_date),max(d.fetched_at),p.document_url
LIMIT 18
"""

def urgent_source_rechecks(conn,limit=3):
 """At most one URL per origin and three total; originals have 36h cooldown.

 Preserve the existing fetch robots/permission checks and never turn a
 successful HTTP fetch into independent editorial confirmation.
 """
 from urllib.parse import urlsplit
 from capabilities import safe_url
 rows=execute(conn,URGENT_REFRESH_SQL)['rows']
 selected=[];hosts=set()
 for row in rows:
  url=str(row.get('url') or '')
  parts=urlsplit(url)
  host=(parts.hostname or '').lower()
  if parts.scheme!='https' or not host or parts.username or parts.password or not safe_url(url):continue
  if host in hosts or host.endswith('.instagram.com') or host=='instagram.com':continue
  if host in ('localhost','127.0.0.1') or host.endswith('.local'):continue
  source=str(row.get('source') or '').strip()
  if not source:continue
  selected.append({'url':url,'source':source,'first_event_date':row.get('first_event_date')})
  hosts.add(host)
  if len(selected)>=max(1,min(int(limit),3)):break
 return selected
