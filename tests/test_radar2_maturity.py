import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector
from caption import interpret
from checkpoint import Journal
from runtime import inspect_token
from capabilities import enrich_graph

class Maturity(unittest.TestCase):
 def parse(self,text):
  with tempfile.TemporaryDirectory() as t:
   c=Collector(t);d={'url':'https://www.instagram.com/p/real-test-fixture/','source':'Instagram','fetched_at':'2026-11-07T01:00:00+00:00','published_at':'2026-11-02T12:00:00+00:00','text':text}
   interpret(c,d,[{'entity':'Sala Sur','identity':'catalog'}]);return list(c.proposals.values())
 def test_distinct_same_day_and_midnight_unknown(self):
  ps=self.parse('Festival en Sala Sur\nViernes 6/11\n20 hs | Banda A\n22 hs | Banda B\n00 hs | Ciclo Fuego')
  self.assertEqual([(p['title'],p['time']) for p in ps],[('Banda A','20:00'),('Banda B','22:00'),('Ciclo Fuego',None)])
  self.assertEqual(ps[-1]['announced_time'],'00:00');self.assertIn('midnight_calendar_day_requires_review',ps[-1]['ambiguities'])
  self.assertEqual(len({p['id'] for p in ps}),3)
 def test_multiple_functions_same_work_and_replay_stable(self):
  text='La obra “Lazos” en Sala Sur\nFunciones: 6/11 20 hs / 7/11 21 hs'
  a=self.parse(text);b=self.parse(text)
  self.assertEqual(len(a),2);self.assertEqual([p['id'] for p in a],[p['id'] for p in b]);self.assertEqual(a[0]['work_identity_key'],a[1]['work_identity_key'])
 def test_range_is_not_two_sessions_and_discount_is_not_start(self):
  ps=self.parse('Taller en Sala Sur. 14/11 de 16.30 a 20.30hs\nEntradas gratis hasta las 23 hs')
  self.assertEqual(len(ps),1);self.assertEqual(ps[0]['time'],'16:30')
 def test_two_sessions_same_work_same_day(self):
  ps=self.parse('Obra Lazos en Sala Sur. 14/11 funciones a las 18 hs y 21 hs')
  self.assertEqual([p['time'] for p in ps],['18:00','21:00']);self.assertEqual(len({p['event_identity_key'] for p in ps}),1)
 def test_styled_unicode_proof_points_to_original(self):
  text='Cine en Sala Sur. 7/11\n𝟭𝟵:𝟯𝟬 𝗵𝘀 - Tierra\n𝟮𝟮 𝗵𝘀 - Noche'
  ps=self.parse(text);self.assertEqual(len(ps),2)
  for p in ps:
   for key,e in p['evidence_spans'].items():
    if e:self.assertEqual(text[e['start']:e['end']],e['quote'])
 def test_cancelled_not_approved_and_regular_not_expanded(self):
  ps=self.parse('FECHA SUSPENDIDA. Obra Lazos en Sala Sur. 7/11 21hs')
  self.assertEqual(ps[0]['event_status'],'cancelled');self.assertFalse(ps[0]['publication_approved'])
  ps=self.parse('Clases regulares en Sala Sur todos los lunes 20 hs')
  self.assertIsNone(ps[0]['date']);self.assertIsNotNone(ps[0]['recurrence_rule'])
 def test_synopsis_past_does_not_hide_program(self):
  ps=self.parse('7 de noviembre\nCine 19 hs - Tierra\nEl pasado lo acecha.\n22 hs - Mar')
  self.assertEqual(len(ps),2)
 def test_onsale_and_retro_do_not_become_future_events(self):
  for text in ['El 7/11 se habilitará la venta de entradas para la obra','Postales de lo que vivimos el 7/11 en el festival']:
   ps=self.parse(text);self.assertTrue(all(p.get('kind')!='event' for p in ps))
 def test_journal_survives_neon_failure_before_return(self):
  with tempfile.TemporaryDirectory() as t:
   journal=Journal(t,'postgres://x@y.neon.tech/db','run');d={'url':'https://source.test/show','sha256':'abc','source':'source','fetched_at':'2026-11-07T00:00:00Z','text':'original'}
   with patch('checkpoint.execute',side_effect=URLError('offline')):
    with self.assertRaises(URLError):journal.save(d)
   self.assertEqual(json.loads(next(Path(t).glob('*.json')).read_text()),d)
 def test_journal_recover_missing_and_do_not_overwrite_newer(self):
  with tempfile.TemporaryDirectory() as t:
   j=Journal(t,'conn','run');d={'url':'https://source.test/a','sha256':'abc','source':'s','fetched_at':'2026-11-07T00:00:00Z','text':'original'}
   with patch('checkpoint.execute',return_value={'rows':[]}):j.save(d)
   c=Collector(Path(t)/'out')
   with patch('checkpoint.execute',return_value={'rows':[]}):self.assertEqual(j.recover(c),1)
   with patch('checkpoint.execute',return_value={'rows':[{'sha256':'new','fetched_at':'2026-11-08T00:00:00Z'}]}):self.assertEqual(j.recover(c),0)
 def test_token_diagnostics_redacted_and_expiry_alert(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return json.dumps({'data':{'is_valid':True,'type':'USER','expires_at':1,'data_access_expires_at':2}}).encode()
  with patch('runtime.urlopen',return_value=Response()):r=inspect_token('TOPSECRET','v27.0')
  self.assertFalse(r['credential_usable']);self.assertTrue(r['expiry_introspected']);self.assertNotIn('TOPSECRET',json.dumps(r))
  with patch('runtime.urlopen',side_effect=URLError('url has TOPSECRET')):r=inspect_token('TOPSECRET','v27.0')
  self.assertNotIn('TOPSECRET',json.dumps(r));self.assertFalse(r['expiry_introspected'])
 def test_explicit_cycle_relationship_not_cooccurrence_circuit(self):
  ps=self.parse('Festival en Sala Sur. Viernes 6/11\n21 hs | Ciclo Fuego')
  # Explicit cycle on a lone clock is a heading after a separator.
  graph=enrich_graph({'proposals':ps},[])
  self.assertIn('part_of_cycle',[e['predicate'] for e in graph['relationships']])


class SourceDiscovery(unittest.TestCase):
 def test_structured_local_organizer_link_and_nonlocal_rejection(self):
  from rotation import source_hints
  event={'organizer':{'name':'Sala Sur','url':'https://www.instagram.com/salasur/'},'location':{'address':{'addressLocality':'La Plata'}}}
  p={'event_date':'2026-11-07','venue':'Sala Sur','document_url':'https://source.test/obra','evidence':{'entities':[{'name':'Sala Sur','role':'organizer','evidence':json.dumps(event)}]}}
  self.assertEqual(list(source_hints([p])),['salasur'])
  event['location']['address']['addressLocality']='Otra Ciudad';p['evidence']['entities'][0]['evidence']=json.dumps(event)
  self.assertEqual(source_hints([p]),{})

class FinalSemanticGuards(unittest.TestCase):
 parse=Maturity.parse
 def test_relative_retail_publication_is_not_a_cultural_event(self):
  ps=self.parse('Cerámica: mañana los subo a la tienda. Vení al taller a ver esmaltes')
  self.assertTrue(all(p.get('kind')!='event' for p in ps))
 def test_narrative_children_do_not_inherit_parent_start_time(self):
  ps=self.parse('Festival en Sala Sur. 7/11 a las 17 hs\nUn rato más tarde llega Ana a conversar sobre sus libros.\nPara terminar la noche viene Pedro con su música.')
  children=[p for p in ps if p.get('kind')=='program_component']
  self.assertEqual(len(children),2);self.assertTrue(all(p['date'] is None and p['time'] is None for p in children));self.assertTrue(all(p['parent_announced_date']=='2026-11-07' for p in children))
 def test_structured_work_url_groups_functions(self):
  ps=[{'id':str(i),'title':'Lazos','document_url':'https://teatro.test/obra/lazos','date':'2026-11-0'+str(i),'state':'observado_agenda','kind':'event','venue':'Sala Sur','entities':[]} for i in (7,8)]
  enrich_graph({'proposals':ps},[])
  self.assertEqual(ps[0]['work_identity_key'],ps[1]['work_identity_key'])

if __name__=='__main__':unittest.main()
