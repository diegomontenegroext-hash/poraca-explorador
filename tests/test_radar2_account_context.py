"""Account-first Instagram contract. No network, Meta secrets or Neon mutations."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from collector import Collector
from caption import interpret,VERSION
from account_context import profile_for,preflight,location_for,read_profiles
from instagram_official_pilot import acquire

class ProfilePreflight(unittest.TestCase):
 def test_profile_roles_and_verified_source(self):
  self.assertGreaterEqual(len(read_profiles()),40)
  a=preflight('teatrounlp')
  self.assertEqual((a['role'],a['venue_entity_id']),('venue','teatro-unlp'))
  self.assertTrue(a['account_verified'])
  self.assertTrue(a['evidence_url'].startswith('https://'))
  self.assertEqual(preflight('lutitravelguide')['role'],'curator')
  for account in ('tribusocialclub','la_plata_pedalea','cicloturismolaplata','los_para_lelos','exp.kayak'):
   profile=preflight(account)
   self.assertEqual(profile['role'],'organizer')
   self.assertFalse(profile['account_verified'],'Documented group must not become approved venue')
   self.assertIsNone(profile.get('venue_entity_id'))
  rc=preflight('residenciacorazon')
  self.assertEqual((rc['role'],rc['venue_entity_id']),('venue','residencia-corazon'))
  self.assertTrue(rc['account_verified'])
  self.assertIn('RC_PDF.pdf',rc['evidence_url'])
  self.assertEqual(preflight('sindicatoargentinodeboleros')['role'],'itinerant_artist')
  self.assertFalse(preflight('teatroespacio44')['account_verified'])
  self.assertEqual(preflight('completamente_desconocida')['role'],'unclassified')
 def test_preflight_comes_before_meta_requests_even_without_token(self):
  with tempfile.TemporaryDirectory() as t:
   c=Collector(t)
   with patch.dict(os.environ,{},clear=True):
    a=acquire(c,set(),rotating_accounts=['teatrounlp','sindicatoargentinodeboleros'],include_controls=False)
   self.assertEqual(a['status'],'NOT_CONFIGURED')
   self.assertEqual([x['role'] for x in a['account_preflight']],['venue','itinerant_artist'])
   self.assertFalse(a['enabled'])
 def test_real_roles_protect_against_unqualified_inheritance(self):
  d={'profile_username':'sindicatoargentinodeboleros'}
  self.assertIsNone(location_for(d,'Sábado en el Camping Municipal')['venue'])
  d={'profile_username':'lutitravelguide'}
  self.assertIsNone(location_for(d,'Sábado en varias salas')['venue'])
  d={'profile_username':'teatroespacio44'}
  x=location_for(d,'Yuna soy yo, #espacio44')
  self.assertIsNone(x['venue'])
  self.assertEqual(x['basis'],'venue_identity_not_publicly_approved')
 def test_only_literal_venue_is_confirmed(self):
  d={'profile_username':'teatrounlp'}
  a=location_for(d,'Sábado 7/11 a las 21hs 📌 Teatro UNLP (10 e/ 54 y 55)')
  self.assertEqual(a['venue'],'Teatro UNLP')
  self.assertEqual(a['basis'],'explicit_name_in_owned_caption')
  b=location_for(d,'Sábado 7/11 21hs La Nona #teatrounlp')
  self.assertIsNone(b['venue'])
  self.assertEqual(b['candidate'],'Teatro UNLP')
  c=location_for(d,'Sábado en CABA, Teatro UNLP presenta una actividad de gira')
  self.assertIsNone(c['venue'])
  self.assertEqual(c['basis'],'offsite_or_remote_requires_review')

class CaptionVenueResolution(unittest.TestCase):
 def doc(self,handle,text,stamp='2026-11-05T13:00:00+00:00'):
  return {'url':'https://www.instagram.com/p/TEST_'+handle.replace('.','')+'/',
          'final_url':'https://www.instagram.com/p/TEST_'+handle.replace('.','')+'/',
          'source':'Instagram','text':text,'profile_username':handle,
          'published_at':stamp,'fetched_at':'2026-11-06T00:00:00Z','sha256':'original-preserved'}
 def parse(self,d,accounts=None):
  with tempfile.TemporaryDirectory() as root:
   c=Collector(root)
   observed = datetime.fromisoformat(d["fetched_at"].replace("Z", "+00:00"))
   with patch("caption.datetime", wraps=datetime) as clock:
    clock.now.side_effect = observed.astimezone
    return interpret(c,d,accounts or [])
 def test_explicit_theatre_with_city_address(self):
  p=self.parse(self.doc('teatrounlp','ÚLTIMA FUNCIÓN DE LA NONA 🎭\nSábado 7/11 21hs\n📌 Teatro UNLP (10 e/ 54 y 55)'))[0]
  self.assertEqual((p['venue'],p['venue_entity_id']),('Teatro UNLP','teatro-unlp'))
  self.assertEqual(p['field_evidence']['venue'],'Teatro UNLP')
  self.assertEqual(p['venue_basis'],'explicit_name_in_owned_caption')
  self.assertFalse(p['publication_approved'])
 def test_institutional_handle_inside_caption(self):
  p=self.parse(self.doc('centrodearteunlp','El sábado 7.11.26 a las 20:00h concierto de Josefina Ignisci en el auditorio del centrodearteunlp'))[0]
  self.assertEqual(p['venue'],'Centro de Arte UNLP')
  self.assertEqual(p['venue_entity_id'],'centro-arte')
 def test_named_workshop_followed_by_street(self):
  p=self.parse(self.doc('lauraganceramica','¡Taller de fotocerámica!\nDomingo 8 de noviembre 13 a 17hs\nTaller Laura Gan Av. 13 num 343 entre 38 y 39, La Plata'))[0]
  self.assertEqual(p['venue'],'Taller Laura Gan')
 def test_cinema_with_address_and_own_room(self):
  p=self.parse(self.doc('proyeccionesterrestres','Sábado 7 de Noviembre\n🎬 Cine nacional\n19:30 hs - Nuestra Tierra\n📍 Calle 3 e/ 66 y 67 n°1663, timbre 3\nNos vemos en la sala 🙂'))[0]
  self.assertEqual(p['venue'],'Cineclub Proyecciones Terrestres')
  self.assertEqual(p['venue_basis'],'owned_venue_with_explicit_address')
 def test_home_venue_only_is_candidate_not_fact(self):
  p=self.parse(self.doc('puravidalaplata2008','AGENDA SEMANAL\nSábado 7 de noviembre 21hs • Banda A • Banda B'))[0]
  self.assertIsNone(p['venue'])
  self.assertEqual(p['venue_candidate'],'Pura Vida')
  self.assertEqual(p['state'],'incompleto')
  self.assertNotIn('venue', [e['role'] for e in p['entities']])
 def test_verified_residencia_announces_open_house_address_before_date(self):
  source=('Cumple 20 Universal & Diagonal!\n'
    'Celebramos 20 años con exposiciones, proyecciones y músicos. '
    'Abrimos nuestra casa y salimos a la calle con amigos.\n'
    '📍 Calle 2 entre 46 y 47, La Plata\n'
    '🗓 Domingo 22 de noviembre · desde las 18 hs\n'
    'Todxs invitadxs. residenciacorazon')
  p=self.parse(self.doc('residenciacorazon',source))[0]
  self.assertEqual(p['date'],'2026-11-22')
  self.assertEqual(p['time'],'18:00')
  self.assertEqual(p['venue'],'Residencia Corazón')
  self.assertEqual(p['venue_entity_id'],'residencia-corazon')
  self.assertEqual(p['venue_basis'],'owned_venue_with_explicit_address')
  self.assertEqual(p['state'],'observado_agenda')
  self.assertFalse(p['publication_approved'])
 def test_other_account_cannot_inherit_residencia_open_house(self):
  caption=('Aniversario de un lugar amigo. Muestra de arte en La Plata. Abrimos nuestra casa. '
   '📍 Calle 2 entre 46 y 47, La Plata\nDomingo 22 de noviembre a las 18 hs')
  for handle in ('tribusocialclub','teatroespacio44','sindicatoargentinodeboleros'):
   d=self.doc(handle,caption)
   d['published_at']='2026-11-08T13:00:00+00:00'
   proposals=self.parse(d)
   self.assertTrue(proposals,'With an explicit date and real publication timestamp, preserve the event for review')
   for p in proposals:
    self.assertIsNone(p['venue'],'A non-owning account cannot inherit another venue')
    self.assertEqual(p['state'],'incompleto')
 def test_multi_stop_program_never_inherits_owned_house(self):
  caption=('Programa cultural y exposición. Abrimos nuestra casa. '
   '📍 Calle 2 entre 46 y 47, La Plata\n'
   'Domingo 22 de noviembre a las 18 hs música\n'
   'Lunes 23 de noviembre a las 19 hs proyección en otra sala')
  ps=self.parse(self.doc('residenciacorazon',caption))
  self.assertGreaterEqual(len(ps),2)
  self.assertTrue(all(x.get('venue_basis')!='owned_venue_with_explicit_address' for x in ps))
 def test_internal_venue_profile_is_not_autoapproved(self):
  p=self.parse(self.doc('teatroespacio44','Yuna soy yo\nSábado 7 de noviembre, 18:00hs\nEntradas en Alternativa Teatral'))[0]
  self.assertIsNone(p['venue'])
  self.assertEqual(p['venue_candidate'],'Teatro Espacio 44')
  self.assertFalse(p['account_context']['account_verified'])
 def test_itinerant_artist_never_inherits_sala(self):
  ps=self.parse(self.doc('sindicatoargentinodeboleros',
   'Agenda de Boleros - recitales y música\nSábado 7/11 22hs en Camping Municipal\nDomingo 8/11 por Canal 7 23:30hs\nMiércoles 11/11 por YouTube 20hs'))
  self.assertGreaterEqual(len(ps),1)
  self.assertTrue(all(p['venue'] is None for p in ps))
  self.assertTrue(all(p.get('venue_candidate') is None for p in ps))
 def test_unverified_interview_teaser_is_not_a_venue_fact(self):
  caption=('Siguiendo con los residentes INTRA, hoy hablamos con marquez.x__ sobre que siente acerca de INTRA y la musica electrónica.\n\n'
   'Este SÁBADO 14.11 cerramos el año con él y el resto de residentes en nuestro amado bosque 🌳 TICKETS DISPONIBLES EN BIO\n\n'
   '#INTRA: Arcano Vivo ⚛️ Capítulo Final de la narrativa 2026 “ARCANO VIVO”')
  d=self.doc('intra.prod',caption,stamp='2026-11-08T00:05:22+00:00')
  d['fetched_at']='2026-11-08T20:39:35Z'
  p=self.parse(d,[{'identity':'confirmed','entity':'INTRA'}])[0]
  self.assertEqual(p['title'],'INTRA: Arcano Vivo')
  self.assertEqual(p['date'],'2026-11-14')
  self.assertIsNone(p['venue'])
  self.assertEqual(p['venue_candidate'],'INTRA')
  self.assertEqual(p['venue_candidate_basis'],'unverified_text_mention')
  self.assertEqual(p['state'],'incompleto')
  self.assertFalse(p['publication_approved'])
 def test_explicit_unapproved_profile_venue_is_not_canonical(self):
  caption=('🎭 ¡Vuelve ROJA!\nDespués de una gran recepción, la última función del año.\n'
   '📅 Sábado 14 de noviembre\n🕘 21 hs\n📍 Espacio 44, La Plata\n🎟️ Entradas: Alternativateatral')
  d=self.doc('teatroespacio44',caption,stamp='2026-11-08T00:05:22+00:00')
  d['fetched_at']='2026-11-08T20:39:35Z'
  p=self.parse(d,[{'identity':'confirmed','entity':'Espacio'}])[0]
  self.assertEqual(p['date'],'2026-11-14')
  self.assertEqual(p['time'],'21:00')
  self.assertIsNone(p['venue'])
  self.assertEqual(p['venue_candidate'],'Espacio 44')
  self.assertEqual(p['venue_candidate_basis'],'explicit_literal_venue_pending_profile_identity')
  self.assertEqual(p['state'],'incompleto')
  self.assertFalse(p['publication_approved'])
 def test_marker_list_heading_is_not_a_place(self):
  # Reproduces the municipal calendar's "Librerías participantes:" false venue.
  caption=('Noviembre se vive en La Plata. Teatro, música y libros.\n'
   'Domingo 8 de noviembre, distintas actividades culturales.\n'
   '📍 Librerías participantes:\n'
   'La Colmena: 56 entre 21 y 22.\n'
   'Rayuela Libros: Plaza Italia, La Plata.')
  d=self.doc('unknown_agenda',caption,stamp='2026-11-05T13:00:00+00:00')
  d['fetched_at']='2026-11-07T15:00:00Z'
  results=self.parse(d)
  self.assertGreaterEqual(len(results),1)
  self.assertTrue(all(p['venue'] is None for p in results))
  self.assertTrue(all(p['state']=='incompleto' for p in results))
  self.assertTrue(all(not p['publication_approved'] for p in results))
 def test_multiple_pinned_list_headings_remain_unlocated(self):
  for label in ('Bibliotecas participantes:', 'Espacios adheridos:', 'Lugares asociados:'):
   with self.subTest(label=label):
    caption='Encuentro cultural y libros\nSábado 14 de noviembre\n📍 '+label+'\nConsultar programación'
    d=self.doc('unknown_agenda',caption,stamp='2026-11-05T13:00:00+00:00')
    d['fetched_at']='2026-11-07T15:00:00Z'
    proposals=self.parse(d)
    self.assertGreaterEqual(len(proposals),1)
    self.assertTrue(all(p['venue'] is None for p in proposals))
    self.assertTrue(all(not p['publication_approved'] for p in proposals))
 def test_marker_venue_literal_still_works(self):
  caption=('Teatro independiente, función el 14 de noviembre a las 21 hs\n'
   '📍 Sala Ginastera, La Plata\nReservas disponibles')
  d=self.doc('unknown_agenda',caption,stamp='2026-11-05T13:00:00+00:00')
  d['fetched_at']='2026-11-07T15:00:00Z'
  results=self.parse(d)
  self.assertGreaterEqual(len(results),1)
  self.assertEqual(results[0]['venue'],'Sala Ginastera')
  self.assertFalse(results[0]['publication_approved'])
 def test_identical_id_before_and_after_add_venue(self):
  d=self.doc('teatrounlp','La Nona sábado 7/11 21hs 📌 Teatro UNLP')
  from collector import sha,norm
  p=self.parse(d)[0]
  expected=sha('|'.join([d['url'],norm(p['title']),p['date'] or '',p['time'] or '']))
  self.assertEqual(p['id'],expected)

if __name__=='__main__':unittest.main()
