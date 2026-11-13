"""Selective recovery of saved compound originals, inside the existing runner."""
import json,tempfile
from pathlib import Path
from compound import classify,interpret,VERSION
from marked_program import VERSION as MARKED_VERSION
from collector import Collector,utc
from persist import execute,SQL
from reconcile import reconcile
from capabilities import enrich_graph,persist_graph,carry_forward,supplement_representatives

ROOT=Path(__file__).resolve().parent.parent

def retire(conn,result):
 urls=sorted({p['document_url'] for p in result['proposals'] if p.get('parser_version') in (VERSION,MARKED_VERSION)})
 if not urls:return []
 ids=[p['id'] for p in result['proposals'] if p.get('parser_version') in (VERSION,MARKED_VERSION)]
 return execute(conn,"""UPDATE radar2.proposals p SET review_state='historico',evidence=evidence || jsonb_build_object('interpretation_superseded_by',$1::text)
 WHERE document_url IN (SELECT jsonb_array_elements_text($2::jsonb))
 AND proposal_id NOT IN (SELECT jsonb_array_elements_text($3::jsonb))
 AND coalesce(evidence->>'interpretation_superseded_by','')=''
 RETURNING proposal_id""",[result['run_id'],json.dumps(urls),json.dumps(ids)])['rows']

def recover(conn,run_id,urls=None):
 accounts=json.loads((ROOT/'radar2/accounts.json').read_text())
 rows=execute(conn,'SELECT payload FROM radar2.documents WHERE ($1::jsonb IS NULL OR url IN (SELECT jsonb_array_elements_text($1::jsonb))) ORDER BY url',[json.dumps(urls) if urls is not None else None])['rows']
 docs=[json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload'] for r in rows]
 docs=[d for d in docs if classify(d,accounts)['compound'] and d.get('published_at') and not any(str(item.get('@type','')).endswith('Event') for item in d.get('structured_items',[]))]
 docs.sort(key=lambda d:(classify(d,accounts)['shape']!='bullet_schedule',d['url']))
 baseline=execute(conn,"SELECT proposal_id,title,to_char(event_date,'YYYY-MM-DD') event_date,event_time,venue,document_url,evidence FROM radar2.proposals WHERE coalesce(evidence->>'interpretation_superseded_by','')='' ORDER BY first_seen_at,proposal_id")['rows']
 with tempfile.TemporaryDirectory() as tmp:
  c=Collector(tmp);c.run_id=run_id;c.baseline=baseline;matrix=[]
  for d in docs:
   c.docs[d['url']]=d
   ps=interpret(c,d,accounts,baseline+list(c.proposals.values()))
   previous=[p for p in baseline if p['document_url']==d['url']]
   matrix.append({'before_observations':len(previous),'before_dated':sum(bool(p.get('event_date')) for p in previous),'url':d['url'],'source':d['source'],'type':d['document_type'],'activities':len(ps or []),'complete':sum(bool(p['date'] and p['time'] and p['venue']) for p in ps or []),'ambiguous':sum(bool(p.get('ambiguities') or p.get('missing_fields')) for p in ps or [])})
  result=reconcile(c.save(),baseline);result=carry_forward(result,baseline);graph=enrich_graph(result,baseline)
  write=execute(conn,SQL,[json.dumps(result,ensure_ascii=False)])['rows'][0]
  execute(conn,"UPDATE radar2.runs SET summary=summary || jsonb_build_object('status','postprocessing') WHERE run_id=$1",[run_id])
  old=retire(conn,result);supplement_representatives(conn,result);memory=persist_graph(conn,run_id,graph)
  rows=execute(conn,'SELECT proposal_id,document_url,title,event_date::text,event_time,venue,evidence FROM radar2.proposals WHERE last_run_id=$1 ORDER BY proposal_id',[run_id])['rows']
  if len(rows)!=int(write['proposals_written']):raise RuntimeError('COMPOUND_READBACK_MISMATCH')
  summary={'status':'completed','parser':VERSION,'mode':'selective_compound_recovery','run_id':run_id,'documents':len(docs),'proposals':len(result['proposals']),'retired':len(old),'aliases':len(result.get('reconciliation',[])),'memory':memory,'matrix':matrix,'readback_count':len(rows),'acquisition_requests':0,'publication_approved':False}
  execute(conn,'UPDATE radar2.runs SET summary=summary || $2::jsonb WHERE run_id=$1',[run_id,json.dumps(summary,ensure_ascii=False)])
  return summary
