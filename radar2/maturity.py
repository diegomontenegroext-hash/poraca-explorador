"""Safe reprocessing of preserved captions. No acquisition, schedule or canon writes."""
import json,os,argparse,tempfile
from pathlib import Path
from collector import Collector,utc,sha
from caption import interpret,VERSION
from reconcile import reconcile
from capabilities import enrich_graph,persist_graph,carry_forward
from persist import execute,SQL

ROOT=Path(__file__).resolve().parent.parent
RETIRE="""UPDATE radar2.proposals p SET review_state='historico',
evidence=evidence || jsonb_build_object('interpretation_superseded_by',$1::text)
WHERE p.document_url IN (SELECT jsonb_array_elements_text($2::jsonb))
AND p.evidence->>'acquisition_method'='official_meta_api'
AND coalesce(p.evidence->>'parser_version','')<>$3
AND coalesce(p.evidence->>'interpretation_superseded_by','')=''
RETURNING proposal_id"""

def retire_interpretations(conn,result):
 urls=sorted({p['document_url'] for p in result['proposals'] if p.get('parser_version')==VERSION})
 return execute(conn,RETIRE,[result['run_id'],json.dumps(urls),VERSION])['rows'] if urls else []

def build(documents,baseline,run_id,out):
 c=Collector(out);c.run_id=run_id;accounts=json.loads((ROOT/'radar2/accounts.json').read_text())
 for d in documents:
  if d.get('acquisition_method')!='official_meta_api':continue
  c.docs[d['url']]=d;interpret(c,d,accounts)
 r=c.save();r=reconcile(r,baseline);r=carry_forward(r,baseline);graph=enrich_graph(r,baseline)
 return r,graph

def replay(conn,run_id):
 identity=execute(conn,"SELECT current_user role,current_setting('neon.project_id',true) project,current_setting('neon.branch_id',true) branch")['rows'][0]
 if identity!={'role':'poraca_radar_limited_prod','project':'frosty-union-52906378','branch':'br-mute-recipe-b4odj2bl'}:raise ValueError('LIMITED_WRITER_IDENTITY_FENCE')
 rows=execute(conn,"SELECT payload FROM radar2.documents WHERE payload->>'acquisition_method'='official_meta_api' ORDER BY url")['rows']
 docs=[json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload'] for r in rows]
 old=execute(conn,"SELECT proposal_id,title,to_char(event_date,'YYYY-MM-DD') event_date,event_time,venue,document_url,evidence FROM radar2.proposals WHERE coalesce(evidence->>'interpretation_superseded_by','')='' ORDER BY first_seen_at,proposal_id")['rows']
 with tempfile.TemporaryDirectory() as tmp:
  result,graph=build(docs,old,run_id,tmp)
  result['finished_at']=utc();write=execute(conn,SQL,[json.dumps(result,ensure_ascii=False)])['rows'][0]
  execute(conn,"UPDATE radar2.runs SET summary=summary || jsonb_build_object('status','postprocessing') WHERE run_id=$1",[run_id])
  try:
   retired=retire_interpretations(conn,result);memory=persist_graph(conn,run_id,graph)
  except Exception:
   execute(conn,"UPDATE radar2.runs SET summary=summary || jsonb_build_object('status','failed_postprocessing') WHERE run_id=$1",[run_id]);raise
  report={'status':'completed','run_id':run_id,'parser':VERSION,'documents':len(docs),'proposals':len(result['proposals']),'write':write,'retired_previous_interpretations':len(retired),'memory':memory,'acquisition_requests':0,'publication_approved':False}
  execute(conn,"UPDATE radar2.runs SET summary=summary || $2::jsonb WHERE run_id=$1",[run_id,json.dumps(report)])
  return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--out',required=True);args=p.parse_args()
 conn=json.loads(Path(os.environ['RADAR2_CONNECTION_FILE']).read_text())['url']
 report=replay(conn,args.run_id);Path(args.out).write_text(json.dumps(report,indent=2));print(json.dumps(report))
