import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from primary_followups import (ticket_detail,secondary_detail,dates_in,classify_ticket,
                               follow_secondary,CANDIDATES_SQL,FOLLOWUP_STAGE_SQL)

class PrimarySourceFollowupTests(unittest.TestCase):
 def test_exact_specific_ticket_url_only(self):
  self.assertTrue(ticket_detail('https://www.casualpass.net/e/ligadeimprovisadores'))
  self.assertTrue(ticket_detail('https://centralticket.net/event/lololaplata'))
  self.assertTrue(ticket_detail('https://catpass.net/eventos/los-espiritus-en-la-plata-07-11-2026-mG2'))
  for url in ('http://www.casualpass.net/e/show','https://www.plateanet.com/teatro/13?teatro=COLISEO-PODESTA',
              'https://instagram.com/ciudaddegatos','https://localhost/e/ligadeimprovisadores',
              'https://www.casualpass.net/','https://www.casualpass.net/e/id?token=secret'):
   self.assertFalse(ticket_detail(url),url)
 def test_secondary_detail_allowlist(self):
  self.assertTrue(secondary_detail('https://elevenflow.app/events/joystick-presenta-diarios-de-humo-en-la-plata-junto-a-ktacumbas-y-cikes-20261121-hsmp'))
  self.assertTrue(secondary_detail('https://agendalaplata.ar/evento/liga-de-improvisadores-espacio-sudaka-20261104185007'))
  self.assertFalse(secondary_detail('https://elevenflow.app/latest'))
  self.assertFalse(secondary_detail('https://instagram.com/mujercebra'))
 def test_future_passline_exact_three_fields(self):
  row={'event_day':'2026-11-21','title':'Joystick presenta Diarios de Humo en La Plata (Junto a Ktacumbas y Cikes)','venue':'Guajira'}
  url='https://www.passline.com/eventos/joystick-presenta-diarios-de-humo-en-la-plata-junto-a-ktacumbas-y-cikes'
  doc={'url':url,'final_url':url,'http_status':200,'text':'Joystick presenta Diarios de Humo en La Plata (Junto a Ktacumbas y Cikes) Sábado 21 de Noviembre 2026 - 20:00 hrs. Guajira 49 n 484 Buenos Aires, LA PLATA'}
  self.assertEqual(classify_ticket(row,doc),('PRIMARY_RECEIPT_REVIEW_REQUIRED',['date','title','venue']))
 def test_future_centralticket_exact_proof(self):
  row={'event_day':'2026-11-15','title':'LOLO MORALES','venue':'GUAJIRA'}
  url='https://centralticket.net/event/lololaplata'
  doc={'url':url,'final_url':url,'http_status':200,
   'text':'LOLO MORALES en LA PLATA (15/11) Domingo 15 de noviembre 20:00 GUAJIRA 15 de nov de 2026'}
  self.assertEqual(classify_ticket(row,doc),('PRIMARY_RECEIPT_REVIEW_REQUIRED',['date','title','venue']))
 def test_dates_explicit_year(self):
  self.assertIn('2026-10-23',dates_in('viernes, 23 de octubre de 2026, 20:30'))
  self.assertIn('2026-11-13',dates_in('13/11/2026'))
  self.assertIn('2026-11-21',dates_in('Sábado 21 de Noviembre 2026 - 20:00 hrs.'))
  self.assertIn('2026-11-15',dates_in('15 de nov de 2026'))
  self.assertEqual(dates_in('viernes 13 de noviembre'),[])
 def test_contradictory_ticket_not_admissible(self):
  row={'event_day':'2026-11-13','title':'Liga de improvisadores','venue':'Espacio Sudaka'}
  doc={'url':'https://www.casualpass.net/e/ligadeimprovisadores',
       'final_url':'https://www.casualpass.net/e/ligadeimprovisadores',
       'http_status':200,'text':'LigadeImprovisadores CUÁNDO viernes, 23 de octubre de 2026, 20:30 DÓNDE Espacio Sudaka'}
  self.assertEqual(classify_ticket(row,doc),('ORIGINAL_DATE_CONFLICT',[]))
  doc['text']='LigadeImprovisadores CUÁNDO viernes, 13 de noviembre de 2026, 20:30 DÓNDE Espacio Sudaka'
  self.assertEqual(classify_ticket(row,doc),('PRIMARY_RECEIPT_REVIEW_REQUIRED',['date','title','venue']))
  doc['text']='viernes, 13 de noviembre de 2026, 20:30 DÓNDE Espacio Sudaka'
  self.assertEqual(classify_ticket(row,doc),('ORIGINAL_IDENTITY_INCOMPLETE',['date','venue']))
  doc['final_url']='https://redirect.invalid'
  self.assertEqual(classify_ticket(row,doc),('ORIGINAL_FETCH_NOT_VERIFIED',[]))
 def test_query_has_bounded_identity_and_freshness(self):
  for term in ('LIMIT 18','event_date BETWEEN','duplicate_of','primary_source_followup','24 hours',
               'agendalaplata','ORDER BY'):
   self.assertIn(term,CANDIDATES_SQL)
  for term in ("UPDATE radar2.proposals","source_followup","d.last_run_id=$2","src.last_run_id=$2",
               "p.proposal_id=x.receipt->>'proposalId'"):
   self.assertIn(term,FOLLOWUP_STAGE_SQL)
  self.assertNotIn('public.radar_agenda_events',FOLLOWUP_STAGE_SQL)
  self.assertIn('DISTINCT ON (p.event_date',CANDIDATES_SQL)
  self.assertIn('p.event_time IS NULL',CANDIDATES_SQL)
  self.assertIn("p.event_time>to_char",CANDIDATES_SQL)
  self.assertIn("x.receipt->>'secondarySha256' IS NULL",FOLLOWUP_STAGE_SQL)
 def test_detail_without_primary_is_held(self):
  row={'proposal_id':'x','event_day':'2026-11-13','title':'Mujer Cebra','venue':'Ciudad de Gatos',
       'detail_url':'https://agendalaplata.ar/evento/mujer-cebra-ciudad-de-gatos-20261023172701'}
  detail={'url':row['detail_url'],'final_url':row['detail_url'],
          'http_status':200,'sha256':'a'*64,'fetched_at':'2026-11-07T22:00:00+00:00'}
  class Fake:
   run_id='test-run'
   source_followups=[]
   def fetch(self,u,s,origin=None):return detail
   def links(self,d):return ['https://instagram.com/ciudaddegatos',
                             'https://www.plateanet.com/teatro/13?teatro=COLISEO-PODESTA']
  with patch('primary_followups.execute',return_value={'rows':[row]}),\
       patch('primary_followups.safe_url',return_value=True):
   obj=Fake();obj.source_followups=[]
   status=follow_secondary(None,obj,limit=3)
  self.assertEqual(status['selected'],1)
  self.assertEqual(obj.source_followups[0]['status'],'NO_EXPLICIT_PRIMARY_EVENT_LINK')
  self.assertFalse(obj.source_followups[0]['publicationApproved'])

if __name__=='__main__':unittest.main()
