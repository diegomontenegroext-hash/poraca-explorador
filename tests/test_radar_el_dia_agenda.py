"""Regression gates for editorial agenda -> staging, never automatic release."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from html import escape
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import radar_agenda_adapters as adapter
import radar_definitivo as radar
import radar_parallel as parallel

ROOT = "https://www.eldia.com/ttags/espectaculos"
PUBLISHED_URL = "https://www.eldia.com/espectaculos/agenda-espectaculos_1793338233"

def fixture(day=None):
    day = day or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    month = next(k for k, v in adapter.MONTHS.items() if v == day.month)
    title = "Hoy"
    p = [
        "<p>Publicidad</p>",
        "<p>Galeria Foto Música</p>",
        "<time>Viernes, %d de %s de %d a las 02:30</time>" % (day.day,month,day.year),
        "<article><p>Hoy</p><p>Música</p>",
        "<p>Fito Páez.- A las 21 en el Hipódromo de La Plata, 44 y 115. Presenta su gira.</p>",
        "<p>Festival con funciones.- A las 17 y 19 en La Alborada, 58 entre 10 y 11.</p>",
        "<p>Teatro</p><p>El principio de Arquímedes.- En Teatro Abierto, avenida 38. Horario no informado.</p>",
        "<p>Sin título ni horario de show.</p>",
        "<p>Mañana</p><p>Fiestas</p>",
        "<p>Halloween Party.- De 17.30 a 19.30 en Maybe Eventos, calle 67. Es un evento anunciado.</p>",
        "<p>Caravana CUGA.- Desde las 11 en Parque Alberti, 25 y 38.</p>",
        "<p>Domingo</p><p>Festival de Barrio.- A las 16 en el Playón de Estación Provincial, 17 y 71.</p>",
        "<p>Guía publicitaria</p><p>PUBLICIDAD</p></article>",
    ]
    return "".join(p)

class EditorialPressTests(unittest.TestCase):
    def test_parses_dates_clocks_and_venues_without_promotion(self):
        raw = fixture()
        rows = adapter.extract_listings(raw, PUBLISHED_URL)
        self.assertEqual(len(rows), 7, rows)
        f = next(x for x in rows if x["title"] == "Fito Páez")
        today = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
        self.assertEqual(f["event_date"], today.isoformat())
        self.assertEqual(f["event_time"], "21:00")
        self.assertIn("Hipódromo de La Plata", f["venue"])
        self.assertEqual(f["evidence_tier"], "secondary_press_agenda")
        self.assertEqual(f["review_state"], "observed_unverified")
        self.assertEqual(f["proof_url"], PUBLISHED_URL)
        self.assertEqual(sum(x["title"]=="Festival con funciones" for x in rows),2)
        self.assertIn("17:00", [x["event_time"] for x in rows])
        self.assertIn("19:00", [x["event_time"] for x in rows])
        no_clock = next(x for x in rows if x["title"]=="El principio de Arquímedes")
        self.assertIsNone(no_clock["event_time"])
        self.assertIn("Teatro Abierto", no_clock["venue"])
        party = next(x for x in rows if x["title"]=="Halloween Party")
        self.assertEqual(party["event_date"],(today+timedelta(days=1)).isoformat())
        self.assertEqual(party["event_time"],"17:30")
        self.assertEqual(next(x for x in rows if x["title"]=="Caravana CUGA")["venue"],
                         "Parque Alberti")
        sunday = next(x for x in rows if x["title"]=="Festival de Barrio")
        self.assertEqual(sunday["event_date"],
                         (today+timedelta(days=(6-today.weekday())%7)).isoformat())

    def test_no_inference_without_publication_time(self):
        self.assertEqual(adapter.extract_listings(
            "<p>Hoy</p><p>Concierto.- A las 21 en Teatro Metro.</p>",
            PUBLISHED_URL),[])

    def test_never_read_generic_tags_or_other_articles(self):
        for path in (ROOT, "https://www.eldia.com/la-plata/agenda-espectaculos_1793338233",
                     "https://agendalaplata.ar/?fecha=2026-10-30"):
            self.assertEqual(adapter.el_dia_editorial_agenda(fixture(),path),[])

    def test_disregard_stale_article_with_old_publication_date(self):
        self.assertEqual(adapter.el_dia_editorial_agenda(
            fixture(date(2022,10,30)),PUBLISHED_URL),[])

    def test_tag_page_prioritizes_only_real_recent_permalinks(self):
        now = datetime(2026,10,30,12,0,tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
        html = ('<a href="https://www.eldia.com/espectaculos/agenda-espectaculos_1792130350">vieja</a>'
                '<a href="/espectaculos/agenda-espectaculos_1793338233">hoy</a>'
                '<a href="https://www.eldia.com/espectaculos/agenda-espectaculos_1792734839">previa</a>'
                '<a href="/espectaculos/noticia-irrelevante_1793338233">no</a>'
                '<a href="https://example.net/espectaculos/agenda-espectaculos_1793338233">ajeno</a>')
        links=adapter.special_links(ROOT,parallel.parse_html(html),at=now)
        self.assertEqual([x[0] for x in links],[PUBLISHED_URL,
            "https://www.eldia.com/espectaculos/agenda-espectaculos_1792734839"])
        self.assertTrue(all("agenda semanal" in x[1] for x in links))

    def test_collector_reuses_budget_and_keeps_secondary_tier(self):
        html='<a href="%s">Agenda de hoy</a>'%PUBLISHED_URL
        class Budget:
            def __init__(self):
                self.pages={ROOT:(200,html,None),PUBLISHED_URL:(200,fixture(),None)}
                self.calls=[]
            def request(self,url):
                self.calls.append(url)
                return self.pages[url]
            def can_fetch(self,url):
                return url in self.pages
        src={"source_id":"rd-eldia","source_role":"local_press","url":ROOT,"seed_urls":[]}
        budget=Budget()
        with patch.object(adapter,"datetime") as mocked_datetime:
            # The discovery path's special_links uses module-level clock.
            mocked_datetime.now.return_value=datetime(2026,10,30,12,0,
                tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
            # The fixture is constructed for the actual local test date;
            # if the caller is not 30/10, this test exercises budget only.
            check,candidates=radar.scan_source(src,budget,"full")
        self.assertEqual(budget.calls[:2],[ROOT,PUBLISHED_URL])
        self.assertTrue(check["_listings"])
        self.assertTrue(all(x["review_state"]=="observed_unverified"
                            for x in check["_listings"]))
        self.assertTrue(all(x["proof_url"]==PUBLISHED_URL
                            for x in check["_listings"]))
        self.assertTrue(all(x["evidence_tier"]=="secondary_press_agenda"
                            for x in check["_listings"]))
        self.assertLessEqual(len(budget.calls),1+radar.MAX_DETAILS_FULL)

if __name__=="__main__":
    unittest.main()
