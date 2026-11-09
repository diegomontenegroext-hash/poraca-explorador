import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from rotation import initial,select,claim,complete,adaptive_query_budget
from unittest.mock import patch
from collector import Collector
class Rotation(unittest.TestCase):
 def setUp(self):
  self.state=initial(json.loads((Path(__file__).resolve().parents[1]/'radar2/instagram_roster.json').read_text()))
  self.at=datetime.now(timezone.utc)
 def test_roster_and_fairness(self):
  first=select(self.state,self.at);self.assertEqual(len(first),10)
  for a in first:a.update(review_count=1,next_review_at=(self.at-timedelta(seconds=1)).isoformat())
  second=select(self.state,self.at);self.assertFalse({a['username'] for a in first}&{a['username'] for a in second})
 def test_leases_and_cooldown(self):
  first=select(self.state,self.at)
  for a in first:a['lease_until']=(self.at+timedelta(hours=2)).isoformat()
  self.assertFalse({a['username'] for a in first}&{a['username'] for a in select(self.state,self.at)})
  for a in self.state['accounts'].values():a['next_review_at']=(self.at+timedelta(days=1)).isoformat()
  self.assertEqual(select(self.state,self.at),[])
 def test_due_count_and_unattempted_after_partial_batch(self):
  with patch('rotation.read',return_value=self.state), patch('rotation.cas',return_value=True), patch('rotation.execute',return_value={'rows':[{}]}):
   batch=claim(None,'run',2)
   self.assertEqual(batch['batch']['eligible_at_claim'],123)
   first,second=batch['accounts']
   receipt={'username':first['username'],'checked_at':self.at.isoformat(),'status':'NO_MEDIA_RETURNED','http_status':200}
   complete(None,'run',{'official_results':[receipt]})
   self.assertEqual(first['result'],'official_queried_no_new')
   self.assertEqual(first['official_success_count'],1)
   self.assertEqual(first['official_last_result']['checked_at'],receipt['checked_at'])
   self.assertIsNone(second['next_review_at'])
   self.assertIsNone(second['lease_until'])
   self.assertNotIn('official_attempt_count',second)
   self.assertIn(second,select(self.state,self.at))
   complete(None,'run',{'official_results':[receipt]})
   self.assertEqual(first['official_success_count'],1)
 def test_adaptive_capacity_is_capped_and_only_due_accounts_count(self):
  self.assertEqual([adaptive_query_budget(n) for n in (0,10,20,21,33,40,41,125)],
                   [10,10,10,15,15,15,20,20])
  self.assertEqual(len(select(self.state,self.at,20)),20)
  for i,a in enumerate(self.state['accounts'].values()):
   if i>=33:a['next_review_at']=(self.at+timedelta(days=1)).isoformat()
  self.assertEqual(len(select(self.state,self.at,20)),15)
  with patch('rotation.read',return_value=self.state), patch('rotation.cas',return_value=True):
   batch=claim(None,'adaptive',20)
  self.assertEqual(batch['batch']['eligible_at_claim'],33)
  self.assertEqual(batch['batch']['budget'],15)
  self.assertEqual(batch['batch']['due_remaining_at_claim'],18)
  self.assertEqual(len(batch['accounts']),15)
  self.assertEqual(len({a['username'] for a in batch['accounts']}),15)
 def test_index_excerpt_never_fetches_or_asserts_date(self):
  with tempfile.TemporaryDirectory() as out:
   c=Collector(out)
   c.fetch=lambda *a,**kw: self.fail('Instagram HTTP was attempted')
   c.discovery({'documents':[{'url':'https://www.instagram.com/p/SYNTHETIC/','title':'Synthetic local art announcement','excerpt':'Test excerpt, not a real event.', 'searches':[{'query_id':'ig-public-index-demo','query':'synthetic','searched_at':self.at.isoformat(),'accounts':['demo']}]}]})
   p=next(iter(c.proposals.values()));self.assertEqual(p['state'],'investigable');self.assertIsNone(p['date']);self.assertFalse(p['direct_profile_read'])
   self.assertFalse(c.allowed('https://www.instagram.com/demo/'))
   self.assertFalse(c.allowed('https://m.instagram.com/demo/'))
if __name__=='__main__':unittest.main()
