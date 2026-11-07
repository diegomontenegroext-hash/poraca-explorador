import json,sys,tempfile,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector,Tree
from compound import interpret,classify,dates_for_heading,permanent_recommendations,effective_version,VERSION
from caption import interpret as caption
from capabilities import enrich_graph

class Compound(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.c=Collector(self.tmp.name)
 def doc(self,text):return {'url':'https://example.test/news','final_url':'https://example.test/news','source':'test','text':text,'published_at':'2026-11-06T04:11:00Z','fetched_at':'2026-11-07T01:00:00Z','sha256':'hash'}
 def test_unrelated_publishers_same_editorial_bullet_shape(self):
  d=self.doc('Por Redacción Hoy Música Grupo Uno.- A las 23.55 en La Casa, calle 1. Grupo Dos.- A las 21 en El Club, calle 2. Mañana Teatro Obra Sur.- A las 19.30 y 21.30 en Teatro Norte, calle 3.')
  ps=interpret(self.c,d,[]);self.assertEqual(len(ps),4)
  self.assertEqual([(p['date'],p['time']) for p in ps],[('2026-11-06','23:55'),('2026-11-06','21:00'),('2026-11-07','19:30'),('2026-11-07','21:30')]);self.assertEqual(ps[0]['venue'],'La Casa')
 def test_uppercase_headers_and_work_name_not_stripped(self):
  d=self.doc('Por Redacción HOY ÓPERA La flauta.- A las 17 en el Teatro Sur, calle 1. TEATRO Teatro Comunitario Barrial.- A las 21 en el Club, calle 2. LUNES MÚSICA Banda Azul.- A las 20 en Casa Azul, calle 3.')
  ps=interpret(self.c,d,[]);self.assertEqual(ps[0]['title'],'La flauta');self.assertEqual(ps[1]['title'],'Teatro Comunitario Barrial');self.assertEqual(ps[-1]['date'],'2026-11-09')
 def test_newspaper_rows_are_not_one_day_event(self):
  d=self.doc('Agenda cultural completa Viernes 6 20 - Banda Uno Club Sur 21 - Banda Dos Club Norte Sábado 7 18 - Obra Tres Club Sur Temas: noticias')
  ps=interpret(self.c,d,[],[{'venue':'Club Sur'},{'venue':'Club Norte'}]);self.assertEqual(len(ps),3);self.assertEqual([p['title'] for p in ps],['Banda Uno','Banda Dos','Obra Tres']);self.assertEqual(ps[-1]['date'],'2026-11-07')
 def test_curator_days_and_local_venues_never_global(self):
  d=self.doc('planes recomendados\n\nmiércoles:\n\nFiesta en lugar.uno\n\njueves:\n\nRecital en lugar.dos\n\nsábado y domingo:\n\nFestival del libro')
  d['profile_username']='curador_nuevo';ps=interpret(self.c,d,[])
  self.assertEqual(len(ps),4);self.assertEqual([p['date'] for p in ps],['2026-11-04','2026-11-05','2026-11-07','2026-11-08']);self.assertEqual([p['venue'] for p in ps],['lugar.uno','lugar.dos',None,None]);self.assertTrue(all(p['organizer'] is None for p in ps))
  graph=enrich_graph({'proposals':ps},[]);self.assertIn('recommended_by',[e['predicate'] for e in graph['relationships']]);self.assertNotIn('organized_by',[e['predicate'] for e in graph['relationships']])
 def test_relative_is_publication_not_acquisition_and_year(self):
  self.assertEqual(dates_for_heading('mañana',date(2026,12,31))[0],[date(2027,1,1)])
  self.assertEqual(dates_for_heading('Domingo 1',date(2026,10,30))[0],[date(2026,11,1)])
 def test_shared_month_two_sessions_and_interval_not_daily_expansion(self):
  self.assertEqual(len(dates_for_heading('16 y 17 de octubre',date(2026,10,11))[0]),2)
  ds,end,_=dates_for_heading('del 23 de octubre al 1 de noviembre',date(2026,10,11));self.assertEqual(ds,[date(2026,10,23)]);self.assertEqual(end,'2026-11-01')
 def test_curator_offer_deadline_is_not_start(self):
  from compound import timing
  self.assertEqual(timing('Entradas gratuitas hasta las 23hs'),(None,None))
 def test_place_recommendation_has_no_event_date(self):
  d=self.doc('Un lugar para cenar\n\nrestaurante.sur\n📍1 y 2');d['profile_username']='curador'
  ps=permanent_recommendations(self.c,d,[{'username':'curador','circuit':'curaduría'}]);self.assertEqual(ps[0]['kind'],'place_recommendation');self.assertIsNone(ps[0]['date']);self.assertEqual(effective_version(d,[{'username':'curador','circuit':'curaduría'}]),VERSION)
 def test_single_specialized_caption_not_routed_to_generic(self):
  d=self.doc('Obra Lazos en Sala Sur. 7/11 a las 21hs');self.assertFalse(classify(d)['compound']);self.assertEqual(len(caption(self.c,d,[])),1)
 def test_exact_original_block_spans_and_stable_ids(self):
  d=self.doc('Agenda cultural Viernes 6 20 - Banda Club Sur 21 - Otro Club Sur Sábado 7 18 - Obra Club Sur Temas: noticias')
  ps=interpret(self.c,d,[],[{'venue':'Club Sur'}]);ids=[p['id'] for p in ps]
  self.assertEqual(ids,[p['id'] for p in interpret(self.c,d,[],[{'venue':'Club Sur'}])])
  for p in ps:
   for span in p['evidence_spans'].values():
    if span:self.assertEqual(d['text'][span['start']:span['end']],span['quote'])
 def test_missing_publication_anchor_never_uses_fetch_date(self):
  d=self.doc('Agenda cultural Viernes 6 20 - Banda Club Sur 21 - Otro Club Sur Sábado 7 18 - Obra Club Sur');d.pop('published_at');self.assertEqual(interpret(self.c,d,[]),[])

if __name__=='__main__':unittest.main()

class CompoundBoundaries(unittest.TestCase):
 def test_curated_newlines_and_clock_belong_to_separate_activity(self):
  with tempfile.TemporaryDirectory() as t:
   c=Collector(t);d={'url':'https://example.test/post','source':'test','text':'planes recomendados\n\nmiércoles: Cafe abierto\n\njueves menú en bar.uno y a las 16hs charla abierta\n\nviernes:\n\ntoca A en sala.dos\ny fiesta B en sala.tres','published_at':'2026-11-04T15:00:00Z','fetched_at':'2026-11-05T00:00:00Z','sha256':'hash'}
   ps=interpret(c,d,[]);self.assertEqual(len(ps),5);self.assertIsNone(ps[1]['time']);self.assertEqual(ps[2]['time'],'16:00');self.assertEqual(ps[-1]['venue'],'sala.tres')
 def test_unchanged_compound_does_not_reinterpret(self):
  from extract import extract_document
  with tempfile.TemporaryDirectory() as t:
   c=Collector(t);d={'url':'https://example.test/news','source':'test','text':'Agenda cultural Viernes 6 20 - Banda Club Sur 21 - Otro Club Sur Sábado 7 18 - Obra Club Sur','published_at':'2026-11-06T15:00:00Z','fetched_at':'2026-11-07T00:00:00Z','sha256':'hash'}
   ps=interpret(c,d,[],[{'venue':'Club Sur'}]);c.baseline=[{'document_url':d['url'],'evidence':p} for p in ps];c.proposals={}
   self.assertEqual(extract_document(c,d,[],'test'),[]);self.assertEqual(c.proposals,{})

class MixedEvidenceRegression(unittest.TestCase):
 def test_place_lexicon_accepts_ledger_json_and_incoming_text(self):
  from compound import known_places
  self.assertIn('Sala Sur',known_places([],[{'venue':'Sala Sur','evidence':'Source text that is not JSON'}]))
 def test_multi_band_bill_uses_existing_caption_program_interpreter(self):
  d={'text':'AGENDA SEMANAL\n\n🗓️ VIERNES 6 DE NOVIEMBRE 21HS\n\n• Banda Uno\n• Banda Dos\n\n🗓️ SÁBADO 7 DE NOVIEMBRE 21HS\n\n• Banda Tres\n\n🗓️ DOMINGO 8 DE NOVIEMBRE 21HS\n\n• Banda Cuatro'}
  self.assertFalse(classify(d)['compound']);self.assertEqual(classify(d)['shape'],'specialized_caption_program')
 def test_recommended_addresses_are_not_numeric_date_headers(self):
  d={'profile_username':'curador','text':'Lugares para cenar\n\nbar.uno\n📍17 y 63\n\nbar.dos\n📍13 y 34\n\nbar.tres\n📍5 y 54'}
  self.assertFalse(classify(d,[{'username':'curador','circuit':'curaduría'}])['compound'])

class AcquisitionBudgetRegression(unittest.TestCase):
 def test_incremental_day_does_not_refetch_seven_days(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   c=Collector(t)
   with patch.object(c,'fetch',return_value=None) as fetch:c.genda(date(2026,11,7),days=1);self.assertEqual(fetch.call_count,1)
   with patch.object(c,'fetch',return_value=None) as fetch:c.genda(date(2026,11,7));self.assertEqual(fetch.call_count,7)
 def test_empty_result_document_can_be_cached_without_fake_proposal(self):
  from compound import requires_interpretation,effective_version
  d={'url':'https://example.test/a','text':'Un comunicado sin fecha','published_at':'2026-11-06T10:00:00Z','sha256':'a'};previous=dict(d,interpretation_version=effective_version(d,[]))
  self.assertFalse(requires_interpretation(d,[],previous,[]))
  self.assertTrue(requires_interpretation(dict(d,sha256='b'),[],previous,[]))
  self.assertTrue(requires_interpretation(dict(d,published_at='2026-11-07T10:00:00Z'),[],previous,[]))
  self.assertTrue(requires_interpretation(d,[],dict(previous,interpretation_version='old'),[]))

class NarrativePrograms(unittest.TestCase):
 setUp=Compound.setUp
 doc=Compound.doc
 def program(self,description):
  return self.doc('Hoy Música Encuentro.- De 15.30 a 18 en el Museo Sur, calle 1. '+description+' Otro.- A las 21 en Sala Norte, calle 2. Tercero.- A las 22 en Sala Este, calle 3.')
 def test_explicit_clock_and_sequential_book_have_parent_evidence(self):
  d=self.program('A las 17.45 habrá un cierre coral en las escalinatas del museo, que interpretará canciones. Luego se presentará el libro “Versos del sur”, de Ana Pérez.')
  ps=interpret(self.c,d,[]);children=[p for p in ps if p.get('parent_program_id')]
  self.assertEqual(len(children),2);self.assertEqual([(p['title'],p['time']) for p in children],[('un cierre coral','17:45'),('Versos del sur',None)])
  self.assertTrue(all(p['venue']=='Museo Sur' and p['date']=='2026-11-06' for p in children))
  self.assertEqual(children[0]['sublocation'],'las escalinatas del museo')
  self.assertIn('time',children[1]['missing_fields'])
  for p in children:
   span=p['evidence_spans']['subactivity'];self.assertEqual(d['text'][span['start']:span['end']],span['quote'])
   self.assertIn(p['parent_program_id'][9:],[q['id'] for q in ps])
  self.assertEqual([p['id'] for p in ps],[p['id'] for p in interpret(self.c,d,[])])
 def test_artist_lists_past_story_and_show_description_not_events(self):
  ps=interpret(self.c,self.program('Participarán Banda Uno y Banda Dos. A las 17.45 hubo un cierre coral. Luego se presentó un libro. La obra cuenta que luego se presentaba un héroe.'),[])
  self.assertEqual(len(ps),3)
 def test_relocation_does_not_inherit_parent_venue_or_time(self):
  ps=interpret(self.c,self.program('Luego se presentará el libro “Azul” online. A las 19 habrá una charla en Sala Nueva.'),[])
  children=[p for p in ps if p.get('parent_program_id')]
  self.assertIsNone(children[0]['venue']);self.assertIsNone(children[0]['time']);self.assertEqual(children[1]['venue'],'Sala Nueva')
 def test_real_saved_sunday_two_narrative_omissions(self):
  path=Path(__file__).resolve().parents[1]/'radar2/evidence/compound-reserved-20261107.json'
  case=next(x for x in json.loads(path.read_text())['cases'] if 'agenda-septimo-dia_1793514734' in x['document']['url'])
  ps=interpret(self.c,case['document'],[]);self.assertEqual(len(ps),23)
  children=[p for p in ps if p.get('parent_program_id')];self.assertEqual(len(children),2)
  self.assertEqual({(p['title'],p['date'],p['time'],p['venue']) for p in children},{('un cierre con una masa coral de 300 integrantes','2026-11-01','17:45','Museo de Ciencias Naturales'),('Versos de mi pago','2026-11-01',None,'Centro de Jubilados Telefónicos')})


class ScheduleCategoryRegression(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.c=Collector(self.tmp.name)
 def doc(self,text):
  return {'url':'https://example.test/agenda','source':'El Día','text':text,
          'published_at':'2026-11-06T04:11:00Z','fetched_at':'2026-11-07T01:00:00Z','sha256':'category-v12'}
 def test_venue_teatro_bar_is_not_theatre_category(self):
  d=self.doc('Por Redacción Hoy Música Solo Cerati.- A las 21 en El Teatro Bar, 1. '
    'Diego Frenkel.- A las 20 en Desafinados Club, 2. '
    '14º Encuentro Coral.- A las 19 en Escuela Secundaria, 3. '
    'Eventos Feria del Playón.- Desde las 14 en el Playón, 4. '
    'Teatro Obra Sur.- A las 21 en Sala Norte, 5. '
    'Mañana Música Los Totora.- A las 20 en Club Azul, 6.')
  ps=interpret(self.c,d,[])
  by_title={p['title']:p for p in ps}
  self.assertEqual(len(ps),6)
  for title in ('Solo Cerati','Diego Frenkel','14º Encuentro Coral'):
   self.assertEqual(by_title[title]['category'],'Música',title)
  self.assertEqual(by_title['Feria del Playón']['category'],'Cultura')
  self.assertEqual(by_title['Obra Sur']['category'],'Teatro')
  self.assertEqual(by_title['Los Totora']['category'],'Música')
  self.assertEqual(by_title['Los Totora']['date'],'2026-11-07')
 def test_theatre_name_is_not_heading(self):
  d=self.doc('Hoy Música Banda Uno.- A las 20 en Sala Azul, calle 1. '
   'Teatro Comunitario Sin Telón.- A las 19 en La Caterva, calle 2. '
   'Eventos Feria de Arte.- A las 15 en Plaza Mayor, calle 3.')
  ps=interpret(self.c,d,[])
  self.assertEqual([p['title'] for p in ps],
    ['Banda Uno','Teatro Comunitario Sin Telón','Feria de Arte'])
  self.assertEqual([p['category'] for p in ps],['Música','Música','Cultura'])
 def test_genda_category_badges_have_clean_genres(self):
  from collector import genda_category
  cases={
    'Gratis Feria En 10 h 41 min':'Feria',
    'Música En vivo En 19 h 41 min':'Música',
    'Cine Infantil En 16 h 11 min':'Cine',
    'Gratis Muestra - Expo':'Arte',
    'Teatro Stand Up En 19 h 41 min':'Teatro',
    'Literatura Muestra - Expo':'Literatura',
    'Infantil Actividad Danza Baile Gastronomía Juegos':'Danza'
  }
  for raw,expected in cases.items():
   with self.subTest(raw=raw):self.assertEqual(genda_category(raw),expected)
  self.assertIsNone(genda_category(None))
