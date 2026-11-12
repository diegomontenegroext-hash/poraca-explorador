"""Live identity refresh, no network or operational ingestion."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from account_context import configure_live_profiles,reset_live_profiles,preflight,location_for,profile_fingerprint,identity_changed
from compound import requires_interpretation,effective_version

def venue(handle,entity,name):
 return {'handle':handle,'entity_id':entity,'name':name,'venue_name':name,'role':'venue',
         'identity_state':'approved_public','location_scope':'La Plata',
         'account_evidence_url':'https://example.org/official','account_evidence_basis':'accepted_exact_id_crosswalk'}

def receipt(entries,branch='br-mute-recipe-b4odj2bl'):
 return {'rows':[{'role':'poraca_radar_limited_prod','project':'frosty-union-52906378','branch':branch,
   'profiles':json.dumps({'schema':'radar2-live-account-profiles-v1','entries':entries})}]}

class LiveProfiles(unittest.TestCase):
 def setUp(self):
  reset_live_profiles();self.addCleanup(reset_live_profiles)
  self.metro=venue('casametrolp','casa-metro','Casa Metro')
  self.estacion=venue('estacionprovincial','estacion-provincial','Centro Cultural Estación Provincial · Meridiano V')
  self.doc={'url':'https://www.instagram.com/p/TEST/','profile_username':'casametrolp',
   'text':'Música en Casa Metro\nSábado 21 de noviembre 22 hs','published_at':'2026-11-10T15:00:00Z','sha256':'same-original'}
 def load(self,entries,branch='br-mute-recipe-b4odj2bl'):
  return configure_live_profiles('test-only',lambda c,q:receipt(entries,branch))
 def test_current_crosswalk_resolves_new_accounts_but_not_profile_alone(self):
  self.assertEqual(preflight('casametrolp')['role'],'unclassified')
  result=self.load([self.metro,self.estacion])
  self.assertEqual(result['status'],'live_accepted_crosswalk')
  self.assertEqual(result['approved_venues'],2)
  self.assertTrue(preflight('casametrolp')['account_verified'])
  self.assertEqual(location_for(self.doc,self.doc['text'])['venue'],'Casa Metro')
  self.assertIsNone(location_for(self.doc,'Sábado 21 de noviembre a las 22 hs')['venue'])
  self.assertIsNone(location_for(self.doc,'En CABA, Casa Metro presenta música')['venue'])
  self.assertEqual(location_for({'profile_username':'estacionprovincial'},'📍 Estación Provincial | 17 y 71')['venue'],self.estacion['venue_name'])
  self.assertFalse(preflight('lutitravelguide')['account_verified'])
  self.assertEqual(preflight('lutitravelguide')['role'],'curator')
 def test_identity_change_reopens_unchanged_archive_once(self):
  previous=dict(self.doc,interpretation_version=effective_version(self.doc,[]))
  old=[{'parser_version':previous['interpretation_version'],'source_document_sha256':'same-original',
        'account_context':{'role':'unclassified','venue_entity_id':None,'account_verified':False}}]
  self.load([self.metro])
  self.assertTrue(identity_changed(self.doc,previous,old))
  self.assertTrue(requires_interpretation(self.doc,[],previous,old))
  previous['account_identity_fingerprint']=profile_fingerprint('casametrolp')
  self.assertFalse(requires_interpretation(self.doc,[],previous,old))
  self.load([])
  self.assertTrue(identity_changed(self.doc,previous,old))
  self.assertFalse(preflight('casametrolp')['account_verified'])
 def test_wrong_branch_or_malformed_response_never_inherits_stale_approval(self):
  for entries,branch in (([self.metro],'wrong'),([self.metro,self.metro],'br-mute-recipe-b4odj2bl')):
   result=self.load(entries,branch)
   self.assertEqual(result['status'],'live_unavailable_discovery_only')
   self.assertFalse(preflight('casametrolp')['account_verified'])
   self.assertFalse(preflight('teatrounlp')['account_verified'])
   self.assertIsNone(profile_fingerprint('casametrolp'))
   self.assertFalse(identity_changed(self.doc,{},[]))
 def test_nonvenue_conflict_never_becomes_host(self):
  self.load([venue('lutitravelguide','fake','Fake Place')])
  self.assertEqual(preflight('lutitravelguide')['role'],'curator')
  self.assertIsNone(location_for({'profile_username':'lutitravelguide'},'Fake Place')['venue'])

if __name__=='__main__':unittest.main()
