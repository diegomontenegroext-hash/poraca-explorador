"""Conservative reconciliation against the previous inventory and current run.
No rows removed: duplicates retain their evidence and point to a visible proposal.
"""
import json,re,sys
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit
from collector import norm

def venue_name(x):
 s=norm(x or '')
 return s.replace('sede ','').replace('club argentino juvenil','argentino juvenil').replace('sede argentino juvenil club','argentino juvenil').replace('escenario40','escenario 40')
def title_name(t,v):
 s=norm(t or '');v=venue_name(v)
 if v:s=s.replace(' en '+v,'')
 s=re.sub(r'\s+\d{1,2}\s+(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)(?:iembre|ubre)?(?:\s+20\d{2})?$','',s)
 s=re.sub(r'\s+en la plata$','',s)
 return s.strip()
def reconcile(result,baseline):
 baseline=[p for p in baseline if not ((json.loads(p['evidence']) if isinstance(p.get('evidence'),str) else p.get('evidence') or {}).get('duplicate_of'))]
 old=[dict(p,date=(p.get('event_date') or '')[:10] or None,time=p.get('event_time'),id=p.get('proposal_id'),kind='event' if p.get('event_date') else 'document') for p in baseline]
 def priority(p):return (0 if p.get('source')=='www.passline.com' else 1,p.get('document_url',''),p['id'])
 known=list(old);decisions=[]
 for p in sorted(result['proposals'],key=priority):
  p.pop('duplicate_of',None)
  if p.get('acquisition_method','').startswith('genda_'):continue
  if p.get('kind')!='event' or not p.get('date'):continue
  matched=None
  for q in known:
   if p['id']==q['id']:continue
   if p['date']!=q.get('date') or p.get('time')!=q.get('time'):continue
   a=venue_name(p.get('venue'));b=venue_name(q.get('venue'))
   if not a or not b or not(a==b or a.startswith(b) or b.startswith(a)):continue
   t=title_name(p['title'],p.get('venue'));u=title_name(q['title'],q.get('venue'))
   score=SequenceMatcher(None,t,u).ratio()
   if t==u or score>=.88 or (min(len(t),len(u))>16 and (t in u or u in t)):
    matched=q;break
   # Same named wine fair at same host/time, preserving both source labels.
   if ('vino' in t or 'feria' in t) and ('vino' in u or 'feria' in u) and ('argentino juvenil' in a):matched=q;break
  if matched:
   p['duplicate_of']=matched.get('duplicate_of') or matched['id']
   decisions.append({'id':p['id'],'duplicate_of':p['duplicate_of'],'reason':'matching date, hour, venue and equivalent cultural title','title':p['title']})
  else:known.append(p)
 result['reconciliation']=decisions
 return result

def mark_previous_knowledge(result,legacy):
 for p in result['proposals']:
  if not p.get('date') or not p.get('discovery'):continue
  title=title_name(p['title'],p.get('venue'));place=venue_name(p.get('venue'))
  for q in legacy:
   if p['date']!=(q.get('event_date') or '')[:10] or p.get('time')!=q.get('event_time'):continue
   other=title_name(q['title'],q.get('venue'));room=venue_name(q.get('venue'))
   if len(title)>7 and (title==other or title in other or other in title) and (not place or not room or place in room or room in place):
    p['known_before_intervention']=True;p['previous_evidence_url']=q.get('proof_url');break
  if p.get('origin_account')=='circus_ofc':p['known_before_intervention']=True
 return result

if __name__=='__main__':
 file=Path(sys.argv[1]);r=json.loads(file.read_text());baseline=json.loads(Path(sys.argv[2]).read_text());r=reconcile(r,baseline)
 if len(sys.argv)>3:r=mark_previous_knowledge(r,json.loads(Path(sys.argv[3]).read_text()))
 file.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({'observations':len(r['proposals']),'aliases':len(r['reconciliation']),'new_visible_candidates':sum(p.get('kind')=='event' and not p.get('duplicate_of') and p.get('discovery') is not None for p in r['proposals'])}))
