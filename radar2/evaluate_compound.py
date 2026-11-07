import json,tempfile
from pathlib import Path
from collector import Collector
from compound import interpret,permanent_recommendations

def evaluate(cases,accounts,baseline):
 results=[]
 with tempfile.TemporaryDirectory() as tmp:
  for case in cases:
   d=case['document'];c=Collector(tmp);ps=interpret(c,d,accounts,baseline)
   if ps is None:ps=permanent_recommendations(c,d,accounts) or []
   samples=[]
   for title,day,hour,venue in case['expected']['samples']:
    matches=[p for p in ps if p['title']==title and p['date']==day and p['time']==hour]
    samples.append({'expected':[title,day,hour,venue],'matched':bool(matches),'venue_exact':any(p['venue']==venue for p in matches)})
   results.append({'url':d['url'],'expected_activities':case['expected']['events'],'dated_events':sum(p.get('kind') in ('event','program') for p in ps),'all_candidates':len(ps),'samples':samples,'proposals':[{'title':p['title'],'date':p['date'],'time':p['time'],'venue':p['venue'],'kind':p.get('kind'),'ambiguities':p.get('ambiguities')} for p in ps]})
 return {'annotation':'agent_labeled_reserved_partial_field_labels_no_human_validation','certified':False,'cases':results}

if __name__=='__main__':
 import sys
 corpus=json.loads(Path('radar2/evidence/compound-reserved-20261107.json').read_text());accounts=json.loads(Path('radar2/accounts.json').read_text());baseline=json.loads(Path(sys.argv[1]).read_text())
 result=evaluate(corpus['cases'],accounts,baseline)
 Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps([{k:v for k,v in c.items() if k!='proposals'} for c in result['cases']],ensure_ascii=False))
