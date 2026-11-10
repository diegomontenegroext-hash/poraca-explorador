import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector,Tree,sha
from media_source_leads import leads, safe_image_url


class MediaSourceLeads(unittest.TestCase):
 def test_selects_real_image_above_logo_and_deduplicates_without_fetch(self):
  html='''<html><head><meta property="og:image" content="/img/logo.png">
  <meta property="og:image:secure_url" content="https://cdn.example.net/sala-foto.webp">
  <meta name="twitter:image" content="https://cdn.example.net/sala-foto.webp">
  <meta property="og:image" content="http://bad.example/p.png"></head></html>'''
  d={'url':'https://sala.example.org/cartelera','final_url':'https://sala.example.org/cartelera',
     'sha256':'a'*64,'fetched_at':'2026-11-10T16:00:00Z'}
  a=leads(Tree(html).root,d)
  self.assertEqual(len(a),2)
  self.assertEqual(a[0]['imageUrl'],'https://cdn.example.net/sala-foto.webp')
  self.assertEqual(a[1]['roleHint'],'brand_graphic_candidate')
  self.assertTrue(all(not x['subjectVerified'] and not x['cardSafe'] and not x['publicReleaseEligible'] and not x['assetFetched'] for x in a))
  self.assertTrue(all(x['entityId'] is None for x in a))

 def test_untrusted_urls_rejected(self):
  page='https://source.example.org/event'
  for val in ['data:image/png,aaa','javascript:alert(1)','http://bad.test/x.png',
              'https://localhost/img.png','https://192.168.1.1/x.png',
              'https://user:password@cdn.example.org/x.png','/path<bad>.png']:
   self.assertIsNone(safe_image_url(val,page),val)
  self.assertEqual(safe_image_url('//cdn.example.org/photo.jpg',page),'https://cdn.example.org/photo.jpg')

 def test_collector_persists_lead_as_evidence_not_as_published_photo(self):
  html=b'<html><head><title>Casa cultural La Plata</title><meta property="og:image" content="https://cdn.example.org/casa-cultural.jpg"></head><body><h1>Casa cultural</h1></body></html>'
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):return False
   def read(self,n):return html
   @property
   def url(self):return 'https://source.example.org/original'
   @property
   def status(self):return 200
  with tempfile.TemporaryDirectory() as tmp:
   c=Collector(tmp)
   with patch.object(c,'allowed',return_value=True),patch('collector.public_open',return_value=Response()),patch('collector.time.sleep',return_value=None):
    d=c.fetch('https://source.example.org/original','Original cultural')
   self.assertEqual(d['media_leads_v1'][0]['documentSha256'],sha(html.decode()))
   self.assertEqual(d['media_leads_v1'][0]['reviewState'],'candidate_only')
   result=c.save()
   self.assertEqual(len(result['documents'][0]['media_leads_v1']),1)
   self.assertEqual(result['documents'][0]['media_leads_v1'][0]['imageUrl'],'https://cdn.example.org/casa-cultural.jpg')

if __name__=='__main__': unittest.main()
