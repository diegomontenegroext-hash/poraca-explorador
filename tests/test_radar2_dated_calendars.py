import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector
from caption import interpret
from compound import classify,effective_version,VERSION

FIXTURE=Path(__file__).with_name('fixtures')/'radar2_dated_calendars_20261112.json'

class DatedCalendars(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.c=Collector(self.tmp.name)
  self.docs=json.loads(FIXTURE.read_text(encoding='utf-8'))
 def doc(self,handle):return dict(next(d for d in self.docs if d['profile_username']==handle))
 def test_cineclub_all_fourteen_sessions_bound_to_day(self):
  d=self.doc('proyeccionesterrestres')
  self.assertEqual(classify(d)['shape'],'weekly_dated_rows')
  ps=interpret(self.c,d,[])
  self.assertEqual(len(ps),14)
  self.assertEqual([(p['date'],p['time'],p['title']) for p in ps],[
   ('2026-11-09','19:00','Olivia'),('2026-11-09','21:30','La doncella'),
   ('2026-11-10','19:00','Olivia'),('2026-11-10','21:30','Last shift'),
   ('2026-11-11','19:00','Operación Travesti'),
   ('2026-11-12','19:00','Operación Travesti'),('2026-11-12','21:00','Hombre mirando al sudeste'),
   ('2026-11-13','19:00','Nuestra tierra'),('2026-11-13','21:30','María Antonieta'),('2026-11-13',None,'La doncella'),
   ('2026-11-14','20:00','Ciclo Plenilunio'),
   ('2026-11-15','17:00','Hombre mirando al sudeste'),('2026-11-15','19:00','La raíz del olivo'),('2026-11-15','21:00','Nuestra tierra')])
  self.assertTrue(all(p['venue']=='Cineclub Proyecciones Terrestres' and p['venue_entity_id']=='cineclub-proyecciones' for p in ps))
  self.assertTrue(all(p['publication_approved'] is False for p in ps))
  self.assertEqual(ps[9]['announced_time'],'00:00')
  self.assertIn('midnight_calendar_day_requires_review',ps[9]['ambiguities'])
  self.assertEqual(ps[10]['category'],'Música')
  self.assertEqual(effective_version(d,[]),VERSION)
  for p in ps:
   for span in p['evidence_spans'].values():
    if span:self.assertEqual(d['text'][span['start']:span['end']],span['quote'])
 def test_missing_publication_never_infers_from_fetch(self):
  d=self.doc('proyeccionesterrestres');d.pop('published_at')
  self.assertEqual(interpret(self.c,d,[]),[])
 def test_wrong_weekday_cannot_bleed_previous_day(self):
  d=self.doc('proyeccionesterrestres');d['text']=d['text'].replace('Viernes 13','Sábado 13')
  ps=interpret(self.c,d,[])
  self.assertFalse(any(p['date']=='2026-11-13' for p in ps))
  self.assertTrue(any(p['date']=='2026-11-14' and p['title']=='Ciclo Plenilunio' for p in ps))
 def test_monthly_calendar_uses_row_not_generic_title(self):
  d=self.doc('comunidadferroviaria')
  self.assertEqual(classify(d)['shape'],'monthly_dated_rows')
  ps=interpret(self.c,d,[])
  self.assertEqual([p['date'] for p in ps],['2026-11-01','2026-11-07','2026-11-13','2026-11-14','2026-11-20','2026-11-21','2026-11-22'])
  self.assertIn('Murgas al Galpón',ps[2]['title'])
  self.assertIn('Festival por la Soberania',ps[4]['title'])
  self.assertTrue(all('AGENDA DE NOVIEMBRE' not in p['title'] and p['publication_approved'] is False for p in ps))
 def test_unknown_owner_never_supplies_venue(self):
  d=self.doc('proyeccionesterrestres');d['profile_username']='unclassified_test'
  self.assertTrue(all(p['venue'] is None for p in interpret(self.c,d,[])))

if __name__=='__main__':unittest.main()
