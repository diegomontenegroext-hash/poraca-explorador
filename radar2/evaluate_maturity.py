"""Frozen reserved set scoring: multiset occurrences, never date-set accuracy.
Reports unmatched slots, exact date/time joint accuracy and unknown fields.
Agent labels do not become independent human truth by being held out.
"""
import json,sys,tempfile,importlib.util
from collections import Counter
from pathlib import Path
from collector import Collector
from caption import interpret

def score(cases,parser,accounts):
 tp=fp=fn=complete=predicted=0;details=[]
 with tempfile.TemporaryDirectory() as tmp:
  for case in cases:
   c=Collector(tmp);ps=parser(c,case['document'],accounts)
   gold=Counter((x['date'],x['time']) for x in case['expected_occurrences'])
   got=Counter((p['date'],p['time']) for p in ps)
   a=sum((gold&got).values());b=sum((got-gold).values());e=sum((gold-got).values())
   tp+=a;fp+=b;fn+=e;predicted+=len(ps)
   complete+=sum(bool(p.get('date') and p.get('time') and p.get('venue')) for p in ps)
   details.append({'url':case['document']['url'],'tp':a,'fp':b,'fn':e,'expected':list(gold.elements()),'extracted':list(got.elements()),'titles':[p['title'] for p in ps]})
 return {'tp':tp,'fp':fp,'fn':fn,'joint_date_time_precision':tp/(tp+fp) if tp+fp else None,'joint_date_time_recall':tp/(tp+fn) if tp+fn else None,'date_time_venue_complete':complete,'predicted':predicted,'cases':details}

if __name__=='__main__':
 cases=json.loads(Path('radar2/evidence/maturity-reserved-20261107.json').read_text())['cases'];accounts=json.loads(Path('radar2/accounts.json').read_text())
 spec=importlib.util.spec_from_file_location('caption_previous',sys.argv[1]);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 out={'annotation':'agent_labeled_reserved_before_implementation_not_independent_human_validation','before':score(cases,old.interpret,accounts),'after':score(cases,interpret,accounts),'certification':False,'unmeasured':['independent human field labels','representative festival recall','actor identity precision','title accuracy across entire corpus']}
 Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:{a:b for a,b in v.items() if a!='cases'} if isinstance(v,dict) else v for k,v in out.items()}))
