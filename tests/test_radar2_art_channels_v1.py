"""Existing FULL acquires multiple official arts originals without inventing daily sessions."""
import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector

ART={
 'MACLA original exhibitions':'https://maclamuseo.com.ar/',
 'Pettoruti original exhibitions':'https://www.gba.gob.ar/museo_pettoruti/muestras',
 'Islas Malvinas institutional':'https://institutocultural.gba.gob.ar/taxonomy/term/1746',
 'ExpoArte Casa Dionisio':'https://www.casadionisio.com.ar/expoarte'
}
class ArtSources(unittest.TestCase):
 def test_art_originals_in_existing_full_no_auto_admission(self):
  with tempfile.TemporaryDirectory() as t:
   collector=Collector(t)
   received=[]
   def fetch(url,source,*rest):
    if source not in ART:return None
    self.assertEqual(url,ART[source])
    return {'url':url,'final_url':url,'source':source,
      'title':'Official exhibition program','text':'Art exhibition page',
      'fetched_at':'2026-11-09T16:00:00Z','sha256':'source'}
   with patch.object(collector,'fetch',side_effect=fetch),patch.object(collector,'reuse',return_value=False),patch('extract.extract_document',side_effect=lambda c,d,accounts,method:received.append((d['source'],method))):
    collector.cultural_channels()
   self.assertEqual(set(x[0] for x in received),set(ART))
   self.assertTrue(all(x[1]=='institutional_art_original_v1' for x in received))
   self.assertFalse(collector.proposals,'No invented dated events before extraction and editorial admission')

 def test_official_organizer_sources_only_no_fabricated_dates(self):
  with tempfile.TemporaryDirectory() as tmp:
   collector=Collector(tmp);seen=[]
   def mocked(url,source,*args):
    if source not in ('Laura Gan institucional','Sincronía Eventbrite organizador'):return None
    seen.append(source)
    return {'url':url,'final_url':url,'source':source,'title':'Institución',
            'text':'Objetos cerámicos y eventos sin fecha','fetched_at':'2026-11-09T16:00:00Z','sha256':'abc'}
   with patch.object(collector,'fetch',side_effect=mocked),patch.object(collector,'reuse',return_value=False),patch.object(collector,'links',return_value=[]):
    collector.cultural_channels()
   self.assertEqual(set(seen),{'Laura Gan institucional','Sincronía Eventbrite organizador'})
   self.assertEqual(len(collector.proposals),2)
   self.assertTrue(all(p['date'] is None for p in collector.proposals.values()))
 def test_organizer_link_scope_and_original_before_proposal(self):
  with tempfile.TemporaryDirectory() as tmp:
   collector=Collector(tmp);parsed=[]
   good='https://www.eventbrite.com.ar/e/cruz-roja-corre-2026-tickets-1999488336439'
   wrong='https://www.eventbrite.com.ar/e/otro-tickets-1888888888888'
   outside='https://example.com/e/cruz-roja-corre-tickets-1999488336439'
   def fetched(url,source,*args):
    if source!='Sincronía Eventbrite organizador':return None
    return {'url':url,'final_url':url,'source':source,'title':'Eventos',
     'text':'Sincronía Deportiva Eventos' if url!=wrong else 'Otro productor',
     'fetched_at':'2026-11-09T16:00:00Z','sha256':url}
   with patch.object(collector,'fetch',side_effect=fetched),patch.object(collector,'reuse',return_value=False),patch.object(collector,'links',return_value=[good,wrong,outside]),patch('extract.extract_document',side_effect=lambda c,d,a,m:parsed.append((d['url'],m))):
    collector.cultural_channels(only=['Sincronía Eventbrite organizador'])
   self.assertEqual(parsed,[(good,'original_eventbrite_organizer_v1')])
   self.assertTrue(any(x.get('status')=='organizer_not_proven' for x in collector.checks))

if __name__=='__main__':unittest.main()
