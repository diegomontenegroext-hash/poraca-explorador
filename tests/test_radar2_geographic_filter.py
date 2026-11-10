import sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector
from extract import extract_document

class OriginalLocationFilter(unittest.TestCase):
 def test_eventbrite_listing_mixed_caba_and_la_plata(self):
  listing='https://www.eventbrite.com.ar/b/argentina--la-plata/food-and-drink/wine/'
  def item(title,city,venue,day):
   return {'@type':'Event','name':title,'description':'Una cata de vinos',
           'startDate':day+'T20:00:00-03:00',
           'location':{'@type':'Place','name':venue,'address':{
             'addressLocality':city,'addressCountry':'AR'}},
           'url':listing}
  with tempfile.TemporaryDirectory() as folder:
   c=Collector(folder);d={'url':listing,'final_url':listing,'title':'Agenda de vino La Plata',
     'source':'Eventbrite','fetched_at':'2026-11-10T14:00:00+00:00',
     'text':'Eventos de vinos en La Plata y Buenos Aires: catas para todos',
     'sha256':'a'*64,'http_status':200}
   events=[item('Cata de vinos en Palermo','Palermo','Palermo Wine Club','2026-11-20'),
           item('Feria de vinos platenses','La Plata','Casa Vinoteca LP','2026-11-21')]
   with patch.object(c,'structured',return_value=events),patch.object(c,'tree',return_value=SimpleNamespace(walk=lambda:[])):
    result=extract_document(c,d,[], 'source_original')
   titles=[p['title'] for p in result if p.get('kind')=='event']
   self.assertEqual(titles,['Feria de vinos platenses'])
   self.assertEqual(next(p for p in result if p['title']==titles[0])['territory_resolution']['status'],'source_stated_local')
   self.assertEqual(len([x for x in c.checks if x['status']=='discarded_out_of_area_original_event']),1)
 def test_missing_locality_is_not_treated_as_definite_outside(self):
  listing='https://event.example/entry'
  with tempfile.TemporaryDirectory() as folder:
   c=Collector(folder);d={'url':listing,'final_url':listing,'title':'Agenda La Plata',
      'source':'Unknown','fetched_at':'2026-11-10T14:00:00+00:00',
      'text':'La Plata evento cultural','sha256':'b'*64,'http_status':200}
   e={'@type':'Event','name':'Festival de arte','startDate':'2026-11-22T19:00:00-03:00',
      'location':{'name':'Centro Cultural Sin Localidad'},'url':listing}
   with patch.object(c,'structured',return_value=[e]),patch.object(c,'tree',return_value=SimpleNamespace(walk=lambda:[])):
    result=extract_document(c,d,[], 'source_original')
   self.assertTrue(result)
   self.assertEqual(result[0]['territory_resolution']['status'],'pending')
if __name__=='__main__':unittest.main()
