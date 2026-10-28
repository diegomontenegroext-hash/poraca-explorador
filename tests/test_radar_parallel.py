import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "src" / "radar_parallel.py"
spec = importlib.util.spec_from_file_location("radar_parallel", path)
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)


class RadarParallelTests(unittest.TestCase):
    def test_isolated_database_name(self):
        self.assertEqual(radar.DB_NAME, "poraca_explorador")
        self.assertEqual(radar.DB_ROLE, "poraca_explorador_writer")

    def test_permalink_requires_exact_public_post(self):
        self.assertTrue(radar.exact_instagram("https://www.instagram.com/p/DeHOPiJRwNi/"))
        self.assertTrue(radar.exact_instagram("https://www.instagram.com/alguien/reel/DeIP5x6RTRH/"))
        self.assertFalse(radar.exact_instagram("https://www.instagram.com/cineselect/"))
        self.assertFalse(radar.exact_instagram("http://www.instagram.com/p/DeHOPiJRwNi/"))

    def test_links_from_public_agenda(self):
        text = ('<a href="/que-hago/banda-platense-n200">Show de una banda</a>'
                '<a href="https://www.instagram.com/p/DeHOPiJRwNi/">Anuncio</a>'
                '<a href="/contacto">Contacto</a>')
        parsed = radar.parse_html(text)
        got = radar.discover_links(text, parsed, "https://www.0221.com.ar/que-hago")
        found = [url for url, _ in got]
        self.assertIn("https://www.instagram.com/p/DeHOPiJRwNi/", found)
        self.assertIn("https://www.0221.com.ar/que-hago/banda-platense-n200/", found)
        self.assertTrue(all("/contacto" not in url for url in found))

    def test_categories_are_not_events(self):
        page = ('<a href="/agenda/categoria/clases/">Clases</a>'
                '<a href="/agenda/categoria/clases/avanzados/">Nivel Avanzados</a>'
                '<a href="/agenda/evento/milonga-cultural/">Milonga cultural</a>')
        urls = [u for u, _ in radar.discover_links(page, radar.parse_html(page),
                    "https://laplatatango.com.ar/agenda/lista/")]
        self.assertFalse(any("/categoria/" in u for u in urls))
        self.assertIn("https://laplatatango.com.ar/agenda/evento/milonga-cultural/", urls)

    def test_schema_event_date_from_jsonld(self):
        raw = ('<script type="application/ld+json">'
               '{"@type":"Event","name":"Feria cultural","startDate":"2026-11-01T18:30:00-03:00",'
               '"location":{"name":"Centro Cultural"},"organizer":{"name":"Grupo"}'
               "}</script>")
        p = radar.parse_html(raw)
        event = radar.structured_event(p)
        self.assertEqual(event["name"], "Feria cultural")
        self.assertEqual(radar.iso_event_fields(event["date"]), ("2026-11-01","18:30"))
        self.assertEqual(event["venue"], "Centro Cultural")

    def test_unverified_when_only_index_link(self):
        row = radar.make_candidate("https://www.0221.com.ar/que-hago/un-show-n123/",
                                    "src-0221","Un show",None,None)
        self.assertIsNone(row["event_date"])
        self.assertEqual(row["evidence"]["detail_opened"],False)


if __name__ == "__main__":
    unittest.main()
