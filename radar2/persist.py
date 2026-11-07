#!/usr/bin/env python3
"""Run the collector's restricted Neon writer. Credential file stays outside repo.
Uses the official Neon HTTP SQL endpoint; no dependency or owner credentials.
"""
import json,os,sys,time
from urllib.error import HTTPError,URLError
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

def execute(conn,query,params=()):
 host=urlsplit(conn).hostname
 if not host or not host.endswith('.neon.tech'):raise ValueError('Expected Neon endpoint')
 body=json.dumps({'query':query,'params':list(params)}).encode()
 req=Request('https://'+host+'/sql',data=body,headers={'Content-Type':'application/json','Neon-Connection-String':conn,'Neon-Raw-Text-Output':'true','Neon-Array-Mode':'false'})
 for attempt in range(3):
  try:
   with urlopen(req,timeout=45) as r:return json.load(r)
  except HTTPError as exc:
   if exc.code not in (429,500,502,503,504) or attempt==2:raise
  except (TimeoutError,URLError):
   if attempt==2:raise
  time.sleep(attempt+1)

SQL="""
WITH input AS (SELECT $1::jsonb AS j),
r AS (
 INSERT INTO radar2.runs(run_id,finished_at,summary)
 SELECT j->>'run_id',(j->>'finished_at')::timestamptz,jsonb_build_object('status','completed','documents',jsonb_array_length(j->'documents'),'proposals',jsonb_array_length(j->'proposals'),'checks',j->'checks','collector_sha256',j->>'collector_sha256','processor_sha256',j->>'processor_sha256','reconciliation',j->'reconciliation') FROM input
 ON CONFLICT(run_id) DO UPDATE SET finished_at=excluded.finished_at,summary=excluded.summary RETURNING run_id
),d AS (
 INSERT INTO radar2.documents(url,source,sha256,fetched_at,last_run_id,payload)
 SELECT x->>'url',x->>'source',x->>'sha256',(x->>'fetched_at')::timestamptz,r.run_id,x
 FROM input CROSS JOIN r CROSS JOIN LATERAL jsonb_array_elements(j->'documents') x
 ON CONFLICT(url) DO UPDATE SET sha256=excluded.sha256,fetched_at=excluded.fetched_at,last_run_id=excluded.last_run_id,payload=excluded.payload
 RETURNING url
),p AS (
 INSERT INTO radar2.proposals(proposal_id,document_url,title,event_date,event_time,venue,category,review_state,last_run_id,evidence)
 SELECT x->>'id',x->>'document_url',x->>'title',NULLIF(x->>'date','')::date,x->>'time',x->>'venue',x->>'category',x->>'state',r.run_id,x
 FROM input CROSS JOIN r CROSS JOIN LATERAL jsonb_array_elements(j->'proposals') x
 JOIN d ON d.url=x->>'document_url'
 ON CONFLICT(proposal_id) DO UPDATE SET
 title=excluded.title,event_date=excluded.event_date,event_time=excluded.event_time,venue=excluded.venue,
 category=CASE
  WHEN radar2.proposals.evidence->'category_revision'->>'corrected'=radar2.proposals.category
   AND radar2.proposals.evidence->>'parser_version'=excluded.evidence->>'parser_version'
  THEN radar2.proposals.category
  ELSE excluded.category END,
 review_state=CASE
  WHEN radar2.proposals.review_state='historico'
   AND radar2.proposals.evidence ? 'editorial_exclusion'
  THEN 'historico' ELSE excluded.review_state END,
 last_seen_at=now(),last_run_id=excluded.last_run_id,
 evidence=excluded.evidence
  || CASE WHEN radar2.proposals.evidence->>'known_before_intervention'='true'
     THEN jsonb_build_object('known_before_intervention',true,
       'previous_evidence_url',radar2.proposals.evidence->'previous_evidence_url')
     ELSE '{}'::jsonb END
  || COALESCE((SELECT jsonb_object_agg(k,v)
    FROM jsonb_each(radar2.proposals.evidence) AS preserved(k,v)
    WHERE k IN ('category_revision','territory_revision','editorial_exclusion','exclusion_run_id')
      AND NOT (excluded.evidence ? k)), '{}'::jsonb)
 RETURNING proposal_id
) SELECT (SELECT count(*) FROM d) AS documents_written,(SELECT count(*) FROM p) AS proposals_written
"""
if __name__=='__main__':
 result=json.loads(Path(sys.argv[1]).read_text());conn=json.loads(Path(os.environ['RADAR2_CONNECTION_FILE']).read_text())['url']
 ident=execute(conn,"SELECT current_user AS role,current_setting('neon.project_id',true) AS project,current_setting('neon.branch_id',true) AS branch,has_table_privilege(current_user,'radar2.proposals','INSERT') AS can_write")
 i=ident.get('rows',[{}])[0]
 if i.get('role')!='poraca_radar_limited_prod' or i.get('project')!='frosty-union-52906378' or i.get('branch')!='br-mute-recipe-b4odj2bl' or i.get('can_write') not in ('t',True):raise RuntimeError('LIMITED_WRITER_IDENTITY_FENCE')
 print(json.dumps({'identity':ident,'write':execute(conn,SQL,[json.dumps(result,ensure_ascii=False)])}))
