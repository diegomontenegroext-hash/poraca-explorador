import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from rotation import initial,select
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
 def test_index_excerpt_never_fetches_or_asserts_date(self):
  with tempfile.TemporaryDirectory() as out:
   c=Collector(out)
   c.fetch=lambda *a,**kw: self.fail('Instagram HTTP was attempted')
   c.discovery({'documents':[{'url':'https://www.instagram.com/p/SYNTHETIC/','title':'Synthetic local art announcement','excerpt':'Test excerpt, not a real event.', 'searches':[{'query_id':'ig-public-index-demo','query':'synthetic','searched_at':self.at.isoformat(),'accounts':['demo']}]}]})
   p=next(iter(c.proposals.values()));self.assertEqual(p['state'],'investigable');self.assertIsNone(p['date']);self.assertFalse(p['direct_profile_read'])
   self.assertFalse(c.allowed('https://www.instagram.com/demo/'))
   self.assertFalse(c.allowed('https://m.instagram.com/demo/'))
if __name__=='__main__':unittest.main()
