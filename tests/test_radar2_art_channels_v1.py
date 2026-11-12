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
   self.assertTrue(all(p['state']=='actor' for p in collector.proposals.values()))
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

class CurrentProgramExtraction(unittest.TestCase):
 def parse(self,html,method,source='Institution'):
  from collector import Tree,sha
  from extract import extract_document
  with tempfile.TemporaryDirectory() as tmp:
   c=Collector(tmp);path=pathlib.Path(tmp)/'original.html';path.write_text(html)
   d={'url':'https://example.org/programa','final_url':'https://example.org/programa','source':source,'title':'Programa de noviembre · La Plata','text':Tree(html).root.text(),'html_file':path.name,'fetched_at':'2026-11-12T18:00:00Z','sha256':sha(html),'http_status':200}
   return extract_document(c,d,[],method)
 def test_labeled_institutional_program_not_three_fake_sessions(self):
  html='<article><h1>Noche de Museos a la luz de la luna</h1><p>“Hecho en Argentina. Ciencia nacional”. Noche de ciencias, soberanía y memoria 📆 14 de noviembre 🕐 19 a 24 hs 📍Museo de física – 49 y 115</p><p>🏛️ En la Sala del Museo: experiencias. 🎭 En el Anfiteatro: Resonancias. Universidad Nacional de La Plata.</p></article>'
  p=self.parse(html,'institutional_program_original_v1')
  self.assertEqual(len(p),1);self.assertEqual((p[0]['date'],p[0]['time'],p[0]['venue']),('2026-11-14','19:00','Museo de física'))
  self.assertEqual(p[0]['source_role'],'first_party');self.assertFalse(p[0]['publication_approved'])
 def test_named_museum_program_with_access_window_and_coral(self):
  html='<article><h1>El Beato Angélico se suma a Museos a la Luz de la Luna</h1><p>El Museo de Arte Contemporáneo Beato Angélico de la Universidad Católica de La Plata abrirá sus puertas.</p><p>La cita será el próximo sábado 14 de noviembre, entre las 19 y las 23 horas, con entrada libre y gratuita en la sede del Museo (diagonal 73, 16 y 47 N° 2137).</p><h4>Encuentro de coros desde las 21</h4><p>A partir de las 21 horas, se desarrollará un Encuentro de Coros.</p></article>'
  p=self.parse(html,'institutional_program_original_v1')
  self.assertEqual(len(p),1);self.assertEqual((p[0]['date'],p[0]['time'],p[0]['venue']),('2026-11-14','19:00','Museo de Arte Contemporáneo Beato Angélico'))
  self.assertIn('Encuentro de Coros',p[0]['program_receipt']['details'])
 def test_schedule_keeps_distinct_venue_not_inheriting_first_hall(self):
  html='<article><h1>Encuentro de acordeonistas del Río de la Plata 2026</h1><p>CRONOGRAMA COMPLETO</p><p>Sábado 14 de Noviembre</p><p>11hs – Taller Dimotteando.</p><p>21hs – Show Musical: Natalio Sturla &amp; Isabelle Bazin. Invitada: Noelia Sinkunas. Club Unión y Perseverancia (13 y 153, Berisso). Actividad arancelada.</p><p>Domingo 15 de Noviembre</p><p>Concierto para el humedal</p></article>'
  p=self.parse(html,'dated_local_program_secondary_v1')
  self.assertEqual(len(p),1);self.assertEqual((p[0]['title'],p[0]['date'],p[0]['time'],p[0]['venue']),('Natalio Sturla & Isabelle Bazin','2026-11-14','21:00','Club Unión y Perseverancia'))
  self.assertEqual(p[0]['source_role'],'secondary_publisher');self.assertFalse(p[0]['publication_approved'])

if __name__=='__main__':unittest.main()
