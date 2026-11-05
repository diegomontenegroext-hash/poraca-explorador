"""Re-extract current saved originals after a parsing correction, without fetches."""
import json,sys
from pathlib import Path
from collector import Collector
from extract import extract_document
from reconcile import reconcile
path=Path(sys.argv[1]);r=json.loads(path.read_text());c=Collector(path.parent)
c.run_id=r['run_id'];c.docs={d['url']:d for d in r['documents']};c.checks=r['checks']
c.proposals={p['id']:p for p in r['proposals'] if not p.get('discovery')}
accounts=json.loads(Path('radar2/accounts.json').read_text())
for d in r['documents']:
 if d.get('discovery'):extract_document(c,d,accounts,d.get('acquisition_method','public_search_then_public_link'))
output=c.save();output['reprocessed_from_current_acquisition']=True
if len(sys.argv)>2:output=reconcile(output,json.loads(Path(sys.argv[2]).read_text()))
path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
print(json.dumps({'documents':len(output['documents']),'observations':len(output['proposals']),'aliases':len(output.get('reconciliation',[]))}))
