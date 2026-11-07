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
