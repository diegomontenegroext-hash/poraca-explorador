"""Behavioral guards for acquisition boundaries, staged graph and rotation."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from capabilities import parse_profile,enrich_graph,PublicAccess
from rotation import initial,select
from reconcile import reconcile
from datetime import datetime,timezone

class Capabilities(unittest.TestCase):
 def test_profile_requires_explicit_identity_and_caption(self):
  node={'shortcode':'TEST','edge_media_to_caption':{'edges':[{'node':{'text':'Una exposición'}}]}}
  def raw(name):return '<script type="application/json">'+json.dumps({'username':name,'edge_owner_to_timeline_media':{'edges':[{'node':node}]}})+'</script>'
  self.assertEqual(parse_profile(raw('other'),'expected'),[])
  self.assertEqual(parse_profile(raw('expected'),'expected')[0]['caption'],'Una exposición')
 def test_blocked_attempts_advance_fair_rotation(self):
  state=initial(json.loads((Path(__file__).resolve().parents[1]/'radar2/instagram_roster.json').read_text()));at=datetime.now(timezone.utc)
  first=select(state,at)
  for a in first:a['attempt_count']=1
  self.assertFalse({a['username'] for a in first}&{a['username'] for a in select(state,at)})
  self.assertTrue(all(a['review_count']==0 for a in first))
 def test_graph_roles_require_evidence_and_never_approve(self):
  p={'id':'abc','title':'Concierto','document_url':'https://example.org/show','date':'2026-11-08','time':None,'state':'observado_agenda','entities':[{'name':'Sala A','role':'venue','evidence':'En Sala A'},{'name':'Inventado','role':'organizer','evidence':'No acredita organizador'}]}
  r={'proposals':[p]};g=enrich_graph(r,[])
  self.assertEqual(len(g['nodes']),1);self.assertEqual(len(g['relationships']),1)
  self.assertEqual(p['entities'][0]['event_relationship']['predicate'],'takes_place_at');self.assertFalse(p['publication_approved'])
 def test_reconciliation_never_uses_an_alias_as_representative(self):
  old=[{'proposal_id':'old','title':'Concierto','event_date':'2026-11-08','event_time':'20:00','venue':'Sala A','evidence':{'duplicate_of':'new'}}]
  p={'id':'new','title':'Concierto','date':'2026-11-08','time':'20:00','venue':'Sala A','kind':'event'}
  reconcile({'proposals':[p]},old);self.assertNotIn('duplicate_of',p)
 def test_labeled_program_uses_live_year_and_paragraph_credits(self):
  import tempfile
  from collector import Collector,Tree
  from extract import extract_document
  raw='<title>Film – Teatro de Cámara de City Bell | Asociación Lumen Artis</title><h1>Príncipe Achmed</h1><p>Videodromo presenta una película de 1926 en City Bell.</p><p>Musicalizan: Nacho Stoppani, Sebastián Piatti y Lucas Muñoz.</p><h2>FECHA Y HORA</h2><p>sábado 7 de noviembre, 20:00</p>'
  with tempfile.TemporaryDirectory() as out:
   c=Collector(out);Path(out,'page.html').write_text(raw)
   d={'url':'https://example.org/film','final_url':'https://example.org/film','source':'Example','title':'Film – Teatro de Cámara de City Bell | Asociación Lumen Artis','text':Tree(raw).root.text(),'fetched_at':'2026-11-05T22:00:00+00:00','html_file':'page.html'}
   extract_document(c,d,[],'test');p=next(iter(c.proposals.values()))
   self.assertEqual(p['date'],'2026-11-07');self.assertEqual(p['time'],'20:00');self.assertEqual(p['organizer'],'Videodromo')
   self.assertEqual([e['name'] for e in p['entities'] if e['role']=='performer'],['Nacho Stoppani','Sebastián Piatti','Lucas Muñoz'])
 def test_instagram_explicit_permission_notice_blocks_even_allow_path(self):
  from urllib.robotparser import RobotFileParser
  p=PublicAccess();rp=RobotFileParser();rp.parse(['User-agent: *','Allow: /'])
  p.cache['https://www.instagram.com']=(rp,{'permission_notice':'Requires express written permission'})
  self.assertFalse(p.policy('https://www.instagram.com/example/')['allowed'])

if __name__=='__main__':unittest.main()
