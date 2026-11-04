"""Cultural losses reproduced from actual page structures; bounded review only."""
import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from radar_agenda_adapters import extract_listings, MONTHS
from radar_definitivo import scan_source, curator_multi_plan_preview
from radar_cultural_evidence import press_evidence
from radar_parallel import parse_html

class Budget:
    def __init__(self, pages): self.pages=pages; self.visited=[]
    def can_fetch(self,url): return url in self.pages
    def request(self,url): self.visited.append(url); return self.pages[url]

class CulturalRecoveryTests(unittest.TestCase):
    def test_separate_headings_keep_undated_curatorial_context(self):
        caption='miércoles:\nabre el patio de @cervezabarfuss\njueves:\nfábrica abierta @vermu_interferencia @residenciacorazon\nsábado:\naniversario @bocanada.bar'
        got=curator_multi_plan_preview(caption)
        self.assertEqual(got['plan_lead_count'],3)
        self.assertEqual(got['leads'][1]['literal_context'],'jueves:')
        self.assertEqual(got['event_count'],0)
        self.assertFalse(got['date_or_venue_inferred'])

    def test_dated_caption_keeps_plan_without_an_account(self):
        caption='🗓️ 7 de noviembre\n@laplata.muerde\n📍Hipódromo\n🗓️ 12 de noviembre\n@vermu_interferencia\n🗓️19 de noviembre\nPatio gastronómico en Premio Dardo Rocha\n🗓️ 23 de noviembre\n@migamerienda'
        got=curator_multi_plan_preview(caption)
        self.assertEqual(len(got['literal_sections']),4)
        self.assertIn('Patio gastronómico',got['literal_sections'][2]['fragments'][0])

    def test_http200_instagram_shell_is_unreadable_not_coverage(self):
        url='https://www.instagram.com/reel/DfVEIVTSTGu/'
        source=dict(source_id='rd-ig-lutitravelguide',account='lutitravelguide',source_role='curadora',url='https://www.instagram.com/lutitravelguide/',seed_only=True,seed_urls=[url])
        check,leads=scan_source(source,Budget({url:(200,'<title>Instagram</title><meta name="description" content="Log in to Instagram">',None)}),'incremental')
        self.assertEqual(check['status'],'failed')
        self.assertEqual(leads[0]['original_url'],url)
        self.assertFalse(leads[0]['evidence']['caption_readable'])
        self.assertEqual(check['_cultural_yield']['captions_read'],0)

    def test_0221_exact_list_cards_do_not_use_news_date_as_event_day(self):
        now=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
        month=next(k for k,v in MONTHS.items() if v==now.month)
        raw='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','datePublished':now.isoformat()+'T09:00:00-03:00'})+'</script>'
        raw+=f'<article class="article-body"><h3>Miércoles {now.day} de {month}</h3><ul><li><strong>18.30 - Muestra colectiva</strong><br>Sala del barrio</li></ul><li>21 - Texto sin sede</li></article>'
        rows=extract_listings(raw,'https://www.0221.com.ar/que-hago/agenda-cultural-n123456')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['event_time'],'18:30')
        self.assertEqual(rows[0]['evidence_tier'],'secondary_press_agenda')
        self.assertEqual(rows[0]['review_state'],'observed_unverified')
        self.assertEqual(extract_listings(raw.replace('datePublished','dateModified'),'https://www.0221.com.ar/que-hago/agenda-cultural-n123456'),[])

    def test_other_shortcode_is_not_a_successful_exact_reel_read(self):
        url='https://www.instagram.com/reel/DfVEIVTSTGu/'
        source=dict(source_id='rd-ig-lutitravelguide',account='lutitravelguide',source_role='curadora',url='https://www.instagram.com/lutitravelguide/',seed_only=True,seed_urls=[url])
        markup='<meta name="description" content="Una publicación cultural extensa de @un_espacio que corresponde a otro reel"><meta property="og:url" content="https://www.instagram.com/lutitravelguide/reel/OTHER123/">'
        check,leads=scan_source(source,Budget({url:(200,markup,None)}),'incremental')
        self.assertEqual(check['status'],'failed')
        self.assertIn('IDENTITY_MISMATCH',check['error_type'])
        self.assertFalse(leads[0]['evidence']['caption_readable'])

    def test_wevix_explicit_noon_and_venue_no_jsonld_required(self):
        now=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
        month=next(k for k,v in MONTHS.items() if v==now.month)
        raw=f'<div class="wp-detail-hero__body"><h1>Festival gastronómico</h1><p>sábado, {now.day} de {month} de {now.year}, 12:00 p. m. hs</p><p>Hipódromo de La Plata · La Plata</p></div>'
        rows=extract_listings(raw,'https://wevix.com.ar/events/festival')
        self.assertEqual(rows[0]['event_time'],'12:00')
        self.assertEqual(rows[0]['venue'],'Hipódromo de La Plata')
        self.assertEqual(extract_listings(raw.replace(str(now.year),'sin año'),'https://wevix.com.ar/events/festival'),[])

    def test_press_preserves_original_reference_without_approving(self):
        raw='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'Una fiesta singular','datePublished':'2026-11-04'})+'</script><article class="article-body"><p>La fiesta tiene música y un juego cultural.</p><p><a href="https://alltickets.com.ar/evento/latrifulca">Entradas</a></p></article><footer><a href="https://unrelated.example/">Publicidad</a></footer>'
        evidence=press_evidence(raw,'https://www.0221.com.ar/la-plata/fiesta-n123',parse_html(raw))
        self.assertEqual(len(evidence['original_references']),1)
        self.assertFalse(evidence['auto_accept'])

if __name__=='__main__': unittest.main()
