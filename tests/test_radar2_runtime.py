import sys, unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError, HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from runtime import resolve_mode
from collector import Collector
from caption import interpret,dates
from datetime import date
import persist

class Runtime(unittest.TestCase):
 def test_three_slots_and_reject_unknown(self):
  self.assertEqual([resolve_mode('schedule',x) for x in ['27 8 * * *','27 16 * * *','27 23 * * *']],['full','incremental','incremental'])
  with self.assertRaises(ValueError):resolve_mode('schedule','bad')
 def test_publication_anchor_and_year_boundary(self):
  self.assertEqual(dates('mañana a las 20 hs',date(2026,11,6))[0][2],date(2026,11,7))
  self.assertEqual(dates('5/1',date(2026,12,28))[0][2],date(2027,1,5))
  self.assertEqual(dates('este viernes 21:30 hs',date(2026,10,28))[0][2],date(2026,10,30))
 def test_three_sessions_retained_and_not_approved(self):
  with tempfile.TemporaryDirectory() as t:
   c=Collector(t);d={'url':'https://www.instagram.com/p/Test/','source':'Instagram','fetched_at':'2026-11-07T00:00:00+00:00','published_at':'2026-09-10T12:00:00+00:00','text':'Teatro Escenario 40. Reunión de padres. sábado 19/09 a las 21 hs / domingo 20/09 a las 19 hs / viernes 25/09 a las 21:30 hs'}
   ps=interpret(c,d,[{'entity':'Escenario 40','identity':'catalog'}])
   self.assertEqual([p['date'] for p in ps],['2026-09-19','2026-09-20','2026-09-25'])
   self.assertTrue(all(not p['publication_approved'] for p in ps))
 def test_meta_failure_does_not_mutate_post_documents(self):
  from instagram_official_pilot import acquire
  from types import SimpleNamespace
  with patch.dict('os.environ',{'META_IG_USER_ID':'id','META_ACCESS_TOKEN':'fake','META_GRAPH_VERSION':'v27.0'}),patch('instagram_official_pilot.discover',return_value={'status':'OFFICIAL_API_ERROR','meta_error_code':190,'posts':[]}):
   c=SimpleNamespace(docs={},proposals={});r=acquire(c,set(),['one','two']);self.assertEqual(c.docs,{});self.assertEqual(r['queries_sent'],1)
 def test_neon_transient_retry_bounded_and_permissions_not_retried(self):
  with patch('persist.urlopen',side_effect=URLError('offline')) as call,patch('persist.time.sleep'):
   with self.assertRaises(URLError):persist.execute('postgres://x@y.neon.tech/db','SELECT 1')
   self.assertEqual(call.call_count,3)
  with patch('persist.urlopen',side_effect=HTTPError('https://y.neon.tech/sql',403,'denied',{},None)) as call:
   with self.assertRaises(HTTPError):persist.execute('postgres://x@y.neon.tech/db','SELECT 1')
   self.assertEqual(call.call_count,1)
if __name__=='__main__':unittest.main()
