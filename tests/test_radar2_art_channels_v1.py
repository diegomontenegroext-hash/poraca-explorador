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

if __name__=='__main__':unittest.main()
