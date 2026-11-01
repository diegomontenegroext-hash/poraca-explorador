"""QA: source-owned Centro de Arte UNLP sections -> individual dated posts.

This is ONE Radar source and its existing 6-detail FULL budget, not a
new source or a recursive crawler. Every lead is explicitly observed_unverified.
"""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import radar_agenda_adapters as adapter
import radar_definitivo as radar

ROOT="https://www.centrodearte.unlp.edu.ar/"
MUSIC=ROOT+"musica/"
STAGE=ROOT+"artes-escenicas/"
VISUAL=ROOT+"artes-visuales/"
CONCERT=ROOT+"concierto-proximo-con-horario/"
THEATRE=ROOT+"teatro-sin-horario-de-funcion/"
SHOW=ROOT+"exposicion-bienal-del-14-al-28-de-noviembre/"

def original(title,fields):
    return ('<html><main><h1>'+title+'</h1><div class="entry-content">'
            +fields+'</div></main></html>')

class CentroArteUNLPTests(unittest.TestCase):
    def test_one_explicit_original_date_time_and_room(self):
        html=original("Concierto. Nueva programación oficial",
          "<p>Música</p><p>Sábado 07.11.26</p><p>20:00h</p>"
          "<p>Auditorio</p><p>Entrada gratuita.</p>")
        with patch.object(adapter,"active_date",return_value=True):
            out=adapter.extract_listings(html,CONCERT)
        self.assertEqual(len(out),1,out)
        x=out[0]
        self.assertEqual(x["event_date"],"2026-11-07")
        self.assertEqual(x["event_time"],"20:00")
        self.assertEqual(x["venue"],"Centro de Arte UNLP · Auditorio")
        self.assertEqual(x["proof_url"],CONCERT)
        self.assertEqual(x["evidence_tier"],"primary_venue")
        self.assertEqual(x["review_state"],"observed_unverified")

    def test_rejects_wrong_weekday_undated_exhibition_and_no_showtime(self):
        samples=[
          original("Concierto inventado", "<p>Viernes 07.11.26</p><p>20:00h Auditorio</p>"),
          original("Exposición 8º Bienal", "<p>Del 14 al 28 de noviembre de 2026</p>"
                   "<p>Auditorio abierto de 15:00 a 20:00h.</p>"),
          original("Concierto sin hora", "<p>Sábado 07.11.26</p><p>Auditorio</p>"),
          original("Concierto con 24h", "<p>Sábado 07.11.26</p><p>24:00h Auditorio</p>"),
          original("Concierto con fecha inválida", "<p>Sábado 39.11.26</p><p>20:00h Auditorio</p>")
        ]
        for raw in samples:
            with patch.object(adapter,"active_date",return_value=True):
                self.assertEqual(adapter.extract_listings(raw,CONCERT),[],raw)

    def test_rejects_categories_off_host_embedded_credentials_and_query(self):
        html=original("Concierto. Prueba","<p>Sábado 07.11.26</p><p>20:00h Auditorio</p>")
        sites=[
          ROOT,MUSIC,STAGE,VISUAL,
          "https://www.centrodearte.unlp.edu.ar/informacion-util/",
          "https://centrodearte.unlp.edu.ar.attacker.example/concierto-test/",
          "https://bad@centrodearte.unlp.edu.ar/concierto-test/",
          "https://www.centrodearte.unlp.edu.ar/concierto-test/?date=2026-11-07"
        ]
        for url in sites:
            with patch.object(adapter,"active_date",return_value=True):
                self.assertEqual(adapter.extract_listings(html,url),[],url)

    def test_one_bounded_category_hop_consumes_same_full_detail_budget(self):
        home=('<a href="/calendario-2/">Calendario</a>'
              '<a href="/artes-visuales/">Artes visuales</a>'
              '<a href="/musica/">Música</a>'
              '<a href="/artes-escenicas/">Artes escénicas</a>')
        pages={
          ROOT:home,
          MUSIC:'<a href="/concierto-proximo-con-horario/">Concierto próximo</a>',
          STAGE:'<a href="/teatro-sin-horario-de-funcion/">Obra teatral</a>',
          VISUAL:'<a href="/exposicion-bienal-del-14-al-28-de-noviembre/">Bienal</a>',
          CONCERT:original("Concierto. Nueva programación oficial",
               "<p>Sábado 07.11.26</p><p>20:00h</p><p>Auditorio</p>"),
          THEATRE:original("Teatro sin función fechada",
               "<p>Obra durante noviembre de 2026. Actividad en desarrollo.</p>"),
          SHOW:original("Exposición 8º Bienal","<p>Del 14 al 28 de noviembre de 2026</p>")
        }
        class Budget:
            def __init__(self):self.calls=[]
            def request(self,url):
                self.calls.append(url)
                return (200,pages[url],None)
            def can_fetch(self,url):return url in pages
        budget=Budget()
        src={"source_id":"rd-web-6d71ee20","source_role":"institutional_program",
             "url":ROOT,"seed_urls":[]}
        with patch.object(adapter,"active_date",return_value=True):
            check,candidates=radar.scan_source(src,budget,"full")
        self.assertEqual(budget.calls[:4],[ROOT,MUSIC,STAGE,VISUAL])
        self.assertIn(CONCERT,budget.calls)
        self.assertIn(THEATRE,budget.calls)
        self.assertIn(SHOW,budget.calls)
        self.assertLessEqual(len(budget.calls),1+radar.MAX_DETAILS_FULL)
        self.assertEqual(len(check["_listings"]),1,check["_listings"])
        self.assertEqual(check["details_opened"],6)
        self.assertEqual(check["status"],"ok")
        self.assertEqual(check["_listings"][0]["review_state"],"observed_unverified")
        self.assertEqual(check["_listings"][0]["method"],
          "centro_arte_unlp_official_original_explicit_session")

if __name__=="__main__":
    unittest.main()
