"""Compare a separately observed visible inventory, never the parser's output."""
import csv,json,sys
from collections import Counter
from pathlib import Path
from collector import norm
out=Path(sys.argv[1]);result=json.loads((out/'result.json').read_text())
ref=list(csv.DictReader(Path('radar2/evidence/genda-reference.tsv').open(),delimiter='\t'))
rows=[];daily=[]
for day in ['2026-11-04','2026-11-05','2026-11-06','2026-11-07','2026-11-08','2026-11-09','2026-11-10']:
 expected=[x for x in ref if x['date']==day];actual=[x for x in result['proposals'] if x['source']=='Genda' and x['date']==day]
 matches=errors=misses=0
 for x in expected:
  found=[p for p in actual if p['source_id']==x['id']]
  ok=len(found)==1 and norm(found[0]['title'])==norm(x['title']) and found[0]['time']==x['time'] and norm(found[0]['venue'])==norm(x.get('venue',''))
  matches+=ok;misses+=not found;errors+=bool(found) and not ok
  rows.append({'date':day,'id':x['id'],'title':x['title'],'expected_time':x['time'],'actual':found,'correct':ok})
 daily.append({'date':day,'visible':len(expected),'recovered':len(actual),'correct':matches,'missing':misses,'duplicates':sum(v-1 for v in Counter(p['source_id'] for p in actual).values()),'errors':errors})
report={'reference_method':'Independent cloud browser DOM, visible cards, 2026-11-05T01:18-01:19Z; Saturday inspected again after initial render was incomplete. Not supplied to collector. Includes completed Nov4 cards; excludes cross-day recommendations. Nov9 no cards.','daily':daily,'items':rows,'recall':sum(x['correct'] for x in daily)/len(ref)}
(out/'benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'daily':daily,'recall':report['recall']},ensure_ascii=False))
