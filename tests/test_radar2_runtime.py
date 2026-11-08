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
 def test_numbered_venue_and_mixed_itinerary(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=Collector(tmp)
   d={'url':'https://www.instagram.com/p/fixture/','source':'Instagram','fetched_at':'2026-11-08T20:00:00Z','published_at':'2026-11-01T16:00:00Z','text':'Teatro de sombras\n14/11 a las 21 hs\n📍 Galpón 12, La Plata'}
   self.assertEqual(interpret(c,d,[])[0]['venue'],'Galpón 12')
   d=dict(d,url='https://www.instagram.com/p/tour/',text='Conciertos de noviembre\n14/11 | BSAS\nMarea Roja en concierto\n27/11 | Trío en el Coliseo')
   stops=interpret(c,d,[])
   self.assertEqual([p['title'] for p in stops],['Marea Roja en concierto','Trío en el Coliseo'])
   self.assertIn('nonlocal_or_digital_program_section',stops[0]['ambiguities'])
 def test_shared_month_and_explicit_week_stay_anchored(self):
  self.assertEqual([x[2].day for x in dates('viernes 28, sábado 29 y domingo 30 de abril',date(2023,4,26))],[28,29,30])
  self.assertEqual([x[2].isoformat() for x in dates('Esta semana en la sala\nViernes Concierto\nSábado Teatro',date(2026,11,2))],['2026-11-06','2026-11-07'])
 def test_date_change_is_retained_for_review(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=Collector(tmp);d={'url':'https://www.instagram.com/p/change/','source':'Instagram','fetched_at':'2026-11-08T20:00:00Z','published_at':'2026-11-07T12:00:00Z','text':'Cambio de fecha del concierto del 14/11 al 21/11'}
   self.assertEqual(interpret(c,d,[]),[])
   self.assertEqual(next(iter(c.proposals.values()))['event_status'],'rescheduled_pending_review')
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
