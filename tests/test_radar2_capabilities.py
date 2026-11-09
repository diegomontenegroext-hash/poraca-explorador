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
 def test_next_agenda_read_preserves_original_credit_evidence(self):
  from capabilities import carry_forward
  old=[{'proposal_id':'agenda','evidence':{'entities':[{'name':'Artista Prueba','role':'performer','evidence':'Musicaliza Artista Prueba','evidence_url':'https://original.example/show'}],'organizer':'Colectivo Prueba','supporting_evidence':[{'proposal_id':'alias','url':'https://original.example/show'}]}}]
  p={'id':'agenda','title':'Film','document_url':'https://agenda.example/show','date':'2026-11-07','state':'observado_agenda','entities':[]}
  result=carry_forward({'proposals':[p]},old);enrich_graph(result,old)
  self.assertEqual(p['entities'][0]['evidence_url'],'https://original.example/show')
  self.assertEqual(p['entities'][0]['event_relationship']['evidence_url'],'https://original.example/show')
  self.assertEqual(len(p['supporting_evidence']),1)
  self.assertEqual(p['organizer'],'Colectivo Prueba')
 def test_original_film_and_agenda_are_one_performance(self):
  old=[{'proposal_id':'agenda','title':'Las aventuras del príncipe Achmed, de Lotte Reiniger','event_date':'2026-11-07','event_time':'20:00','venue':'Teatro de Cámara City Bell','evidence':{}}]
  p={'id':'original','title':'Las mil y una noches: Las aventuras del príncipe Achmed','date':'2026-11-07','time':'20:00','venue':'Teatro de Cámara de City Bell','kind':'event'}
  reconcile({'proposals':[p]},old);self.assertEqual(p.get('duplicate_of'),'agenda')
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

 def test_frontier_nullable_image_alt_does_not_break_discovery(self):
  import tempfile
  from collector import Collector
  from capabilities import discover_links
  with tempfile.TemporaryDirectory() as folder:
   c=Collector(folder);c.run_id='qa-null-image-alt'
   raw='<a href="https://new.example/proximos-eventos/"><img alt><img alt="Programación cultural"></a>'
   Path(folder,'original.html').write_text(raw)
   c.docs['https://venue.example/']={
     'url':'https://venue.example/','final_url':'https://venue.example/',
     'source':'Institution','title':'Agenda','text':'Cultura de La Plata',
     'html_file':'original.html'}
   state={'sources':{}}
   with patch('capabilities.load_state',return_value=state),patch('capabilities.save_state'):
    result=discover_links(c,None,set(),limit=0)
   self.assertEqual(result['candidates_discovered'],1)
   self.assertIn('https://new.example/proximos-eventos/',state['sources'])
   self.assertIn('Programación',state['sources']['https://new.example/proximos-eventos/']['link_label'])

 def test_finished_previous_edition_cannot_reappear_as_today(self):
  import tempfile
  from collector import Collector,Tree
  from extract import extract_document
  with tempfile.TemporaryDirectory() as folder:
   c=Collector(folder)
   old={'@type':'Event','name':'TOLOSA CORRE 2025 EDICION XV',
     'startDate':'2026-11-09T19:00:39.510Z',
     'location':{'@type':'Place','name':'Tolosa, La Plata'}}
   d={'url':'https://tickets.example/event/2025',
      'final_url':'https://tickets.example/event/2025',
      'source':'Sincronía Deportiva original',
      'title':'TOLOSA CORRE 2025 EDICION XV',
      'text':'Event finished TOLOSA CORRE 2025 EDICION XV. Domingo 21 de Diciembre de 2025 en Tolosa, La Plata.',
      'fetched_at':'2026-11-09T19:00:40+00:00',
      'structured_items':[old]}
   extract_document(c,d,[],'institutional_sports_original_v1')
   self.assertEqual(len(c.proposals),0,'Do not resurrect a historic race')
   self.assertTrue(any(x.get('status')=='discarded_stale_structured_date' for x in c.checks))
   actual={**old,'name':'TOLOSA CORRE 2026 EDICION XVI',
     'startDate':'2026-12-20T11:00:00Z'}
   d['structured_items']=[actual]
   d['text']='TOLOSA CORRE 2026 EDICION XVI. Domingo 20 de Diciembre de 2026 en Tolosa, La Plata.'
   d['title']='TOLOSA CORRE 2026 EDICION XVI'
   extract_document(c,d,[],'institutional_sports_original_v1')
   self.assertEqual(len(c.proposals),1,'Real 2026 edition remains eligible')
   self.assertEqual(next(iter(c.proposals.values()))['date'],'2026-12-20')

 def test_finished_event_same_year_is_never_resurrected(self):
  import tempfile
  from collector import Collector
  from extract import extract_document
  with tempfile.TemporaryDirectory() as folder:
   c=Collector(folder)
   event={'@type':'Event','name':'SEGUI CORRIENDO 2026',
      'startDate':'2026-11-09T19:00:39.510Z',
      'location':{'@type':'Place','name':'Calle 416 & Calle 147, Arturo Seguí, La Plata'}}
   d={'url':'https://tickets.sincroniadeportiva.com.ar/event/seguicorriendo2026',
      'final_url':'https://tickets.sincroniadeportiva.com.ar/event/seguicorriendo2026',
      'source':'Sincronía Deportiva original',
      'title':'SEGUI CORRIENDO 2026',
      'text':'SEGUI CORRIENDO 2026 | Sincronía Deportiva Event finished SEGUI CORRIENDO 2026. Domingo 24 de Mayo de 2026 en Arturo Seguí, La Plata.',
      'fetched_at':'2026-11-09T19:00:40+00:00','structured_items':[event]}
   extract_document(c,d,[],'institutional_sports_original_detail_v1')
   self.assertFalse(c.proposals,'Historic event within the SAME year is not today')
   self.assertTrue(any(x.get('evidence')=='official_detail_explicit_finished' for x in c.checks))
   future={**event,'name':'TOLOSA CORRE 2026 EDICION XVI','startDate':'2026-12-20T11:00:00Z'}
   d.update(url='https://tickets.sincroniadeportiva.com.ar/event/tolosacorre2026',
     final_url='https://tickets.sincroniadeportiva.com.ar/event/tolosacorre2026',
     title='TOLOSA CORRE 2026 EDICION XVI',structured_items=[future],
     text='TOLOSA CORRE 2026. Domingo 20 de Diciembre de 2026, Tolosa, La Plata.\n'+
       'Más información: otro evento Event finished del año pasado.')
   extract_document(c,d,[],'institutional_sports_original_detail_v1')
   self.assertEqual(len(c.proposals),1,'Footer mention of a finished OTHER event is not a veto')
   self.assertEqual(next(iter(c.proposals.values()))['date'],'2026-12-20')

 def test_blocked_bing_is_not_invoked_by_scheduled_full(self):
  from urllib.robotparser import RobotFileParser
  rp=RobotFileParser();rp.parse(['User-agent: *','Disallow: /search'])
  self.assertFalse(rp.can_fetch('Radar2','https://www.bing.com/search?q=yoga&format=rss'))
  source=Path(__file__).resolve().parents[1].joinpath('radar2/actions_pilot.py').read_text()
  self.assertNotIn("public_search(c,access",source)
  self.assertIn("'queries':0",source)
  self.assertIn("'original_sources':origin_receipts",source)

 def test_frontier_rejects_utility_links_in_existing_and_new_sources(self):
  from capabilities import cultural_link
  for url,label in [('https://wa.me/123','Reservas'),('https://t.me/share/url?url=cultura','Compartir'),('https://automattic.com/cookies/','Cookie Policy'),('https://funebres.eldia.com/','Fúnebres'),('https://sponsor.example/',''),('https://www.dbyz.com.ar/','Design')]:
   self.assertFalse(cultural_link(url,label),(url,label))
  for url,label in [('https://new.example/?post_type=funcion&p=2','Entradas'),('https://new.example/proximos-eventos/','Programación'),('https://publico.alternativateatral.com/entradas123','Ir a comprar entradas')]:
   self.assertTrue(cultural_link(url,label),(url,label))
 def test_original_organizer_reaches_representative_without_resolving_conflicts(self):
  from capabilities import supplement_representatives
  for names in (['Colectivo Sur'],['Colectivo Sur','Colectivo Norte']):
   result={'proposals':[{'id':'alias','duplicate_of':'agenda','document_url':'https://original.example/show','entities':[{'name':n,'role':'organizer'} for n in names]}]}
   with patch('capabilities.execute',side_effect=[{'rows':[{'evidence':{}}]},{'rows':[]}]) as sql:
    supplement_representatives('limited',result)
    saved=json.loads(sql.call_args_list[1].args[2][1])
    if len(names)==1:self.assertEqual(saved['organizer'],'Colectivo Sur')
    else:self.assertNotIn('organizer',saved)

if __name__=='__main__':unittest.main()
