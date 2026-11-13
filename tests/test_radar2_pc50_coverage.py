"""Coverage routing only: no external HTTP, admission or invented sessions."""
import pathlib,sys,tempfile,unittest
from datetime import date
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector,Tree

class CoverageRoutes(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.c=Collector(self.tmp.name)
 def doc(self,url,source,html=''):
  return {'url':url,'final_url':url,'source':source,'title':source,'text':Tree(html).root.text(),
          'fetched_at':'2026-11-12T20:00:00Z','sha256':'fixture'}
 def test_link_scope_budget_and_receipt(self):
  root=self.doc('https://fesaalp.com/','FESAALP')
  html='<a href="/peliculas/a/">A</a><a href="/peliculas/a/?tracking=1">A</a><a href="https://evil.example/peliculas/x/">X</a><a href="http://fesaalp.com/peliculas/y/">Y</a><a href="/peliculas/b/">B</a><a href="/peliculas/c/">C</a>'
  fetched=[]
  def fetch(url,source,origin):
   fetched.append(url);return self.doc(url,source)
  with patch.object(self.c,'tree',return_value=Tree(html).root),patch.object(self.c,'fetch',side_effect=fetch),patch.object(self.c,'reuse',return_value=False),patch('extract.extract_document') as parse:
   self.c.follow_cultural_details(root,r'/peliculas/[a-z0-9-]+/?',2,[],today=date(2026,11,12))
  self.assertEqual(fetched,['https://fesaalp.com/peliculas/a/','https://fesaalp.com/peliculas/b/'])
  self.assertEqual(parse.call_count,2);self.assertEqual(self.c.checks[-1]['deferred'],1)
  self.assertEqual(self.c.checks[-1]['eligible_links'],3)
 def test_future_sessions_prioritized_no_reservation_url(self):
  root=self.doc('https://teatroargentino.gba.gob.ar/','Teatro Argentino')
  html='<a href="/meet/1">01/11/2026 19:00</a><a href="/meet/102">26/11/2026 20:00</a><a href="/meet/100">22/11/2026 18:00</a><a href="/meet/101">25/11/2026 20:00</a><a href="/login">Adquirir entradas</a>'
  with patch.object(self.c,'tree',return_value=Tree(html).root),patch.object(self.c,'fetch',side_effect=lambda u,s,*a:self.doc(u,s)) as fetch,patch.object(self.c,'reuse',return_value=False),patch('extract.extract_document'):
   self.c.follow_cultural_details(root,r'/meet/\d+/?',3,[],today=date(2026,11,12))
  self.assertEqual([x.args[0] for x in fetch.call_args_list],['https://teatroargentino.gba.gob.ar/meet/100','https://teatroargentino.gba.gob.ar/meet/101','https://teatroargentino.gba.gob.ar/meet/102'])
 def test_dynamo_link_even_if_listing_lacks_date_and_failed_fetch(self):
  root=self.doc('https://www.dynamoteatro.com/','Dynamo Teatro')
  html='<a href="https://dynamoteatro.com/event/170750-agridulce-expres">From {date} Agridulce Expres</a><a href="/event/170751-otra">Otra</a>'
  with patch.object(self.c,'tree',return_value=Tree(html).root),patch.object(self.c,'fetch',side_effect=[None,self.doc('https://www.dynamoteatro.com/event/170751-otra','Dynamo Teatro')]) as fetch,patch.object(self.c,'reuse',return_value=False),patch('extract.extract_document') as parse:
   self.c.follow_cultural_details(root,r'/event/\d+-[a-z0-9-]+/?',8,[],today=date(2026,11,12))
  self.assertEqual(fetch.call_count,2);self.assertEqual(parse.call_count,1);self.assertFalse(self.c.proposals)
 def test_root_and_cross_origin_redirect_not_interpreted(self):
  root=self.doc('https://fesaalp.com/','FESAALP')
  html='<a href="/peliculas/a/">A</a>'
  child=self.doc('https://fesaalp.com/peliculas/a/','FESAALP');child['final_url']='https://elsewhere.example/a'
  with patch.object(self.c,'tree',return_value=Tree(html).root),patch.object(self.c,'fetch',return_value=child),patch('extract.extract_document') as parse:
   self.c.follow_cultural_details(root,r'/peliculas/[a-z0-9-]+/?',2,[])
  parse.assert_not_called();self.assertEqual(self.c.checks[-1]['status'],'coverage_detail_redirect_outside_publisher')
 def test_permanent_roots_in_full(self):
  expected={'FESAALP','Teatro Argentino oficial','Teatro Argentino calendario','Casa Metro original','Biblioteca Pública UNLP','UNLP Arte','Colegio Nacional UNLP','CENEXA','MoVeTe ferias','Dynamo Teatro'}
  got=[]
  def fetch(url,source,*a):
   got.append(source);return self.doc(url,source)
  with patch.object(self.c,'fetch',side_effect=fetch),patch.object(self.c,'reuse',return_value=False),patch.object(self.c,'follow_cultural_details') as follow,patch('extract.extract_document'):
   self.c.cultural_channels(only=expected)
  self.assertEqual(set(got),expected);self.assertEqual(follow.call_count,10)
  self.assertFalse(self.c.proposals)

if __name__=='__main__':unittest.main()
