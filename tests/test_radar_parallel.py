import importlib.util
import pathlib
import unittest
from unittest.mock import patch

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
        page2 = ('<a href="/agenda/recintos/categor%C3%ADa/abtipoplazabuenpiso/">Lugar</a>'
                 '<a href="/agenda/recintos/categoría/otro-lugar/">Otra categoría</a>')
        more = radar.discover_links(page2, radar.parse_html(page2),
                                    "https://laplatatango.com.ar/agenda/lista/")
        self.assertEqual(more, [])


    def test_full_breadth_and_embedded_instagram_permalinks(self):
        self.assertGreaterEqual(radar.MAX_SOURCES, 15)
        self.assertGreater(radar.MAX_DETAILS_FULL, radar.MAX_DETAILS_INCREMENTAL)
        base = "https://www.0221.com.ar/que-hago"
        article = "https://www.0221.com.ar/que-hago/teatro-platense-n123/"
        post = "https://www.instagram.com/p/DeHOPiJRwNi/"
        def mocked_fetch(url):
            if url == base:
                return 200, '<a href="/que-hago/teatro-platense-n123/">Teatro platense</a>', None
            if url == article:
                return 200, '<a href="' + post + '">Instagram original</a>', None
            if url == post:
                return 200, '<meta property="og:title" content="Una obra en La Plata">', None
            raise AssertionError("Unexpected URL " + url)
        with patch.object(radar, "fetch", side_effect=mocked_fetch):
            check, candidates = radar.scan_source(
                {"source_id": "src-0221", "url": base},
                max_details=radar.MAX_DETAILS_FULL)
        self.assertEqual(check["status"], "ok")
        self.assertIn(article, [c["original_url"] for c in candidates])
        self.assertIn(post, [c["original_url"] for c in candidates])
        self.assertTrue(all(c["evidence"]["announced_only"] for c in candidates))

    def test_percent_encode_non_ascii_source_links(self):
        url = radar.clean_link("/agenda/evento/música-y-teatro/", "https://laplatatango.com.ar/")
        self.assertEqual(url, "https://laplatatango.com.ar/agenda/evento/m%C3%BAsica-y-teatro/")

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

    def test_explicit_music_event_performers_passive_cultural_signals(self):
        raw = ('<script type="application/ld+json">'
            '{"@graph":[{"@type":"WebSite","name":"Sitio"},'
            '{"@type":"MusicEvent","name":"Festival en La Plata",'
            '"startDate":"2026-11-20T21:00:00-03:00",'
            '"location":{"@type":"Place","name":"Sala local"},'
            '"organizer":{"@type":"Organization","name":"Productora invitada"},'
            '"performer":[{"@type":"MusicGroup","name":"Banda visitante"},'
            '{"@type":"Person","name":"DJ local"},'
            '{"@type":"Person","name":"DJ local"}]}]}</script>')
        url="https://venue.example.org/evento/festival/"
        page=radar.parse_html(raw)
        event=radar.structured_event(page)
        self.assertEqual(event["performers"],["Banda visitante","DJ local"])
        item=radar.make_candidate(url,"source-cultural","Festival",page,200)
        self.assertEqual(item["event_date"],"2026-11-20")
        self.assertEqual(item["event_time"],"21:00")
        self.assertEqual(item["organizer"],"Productora invitada")
        self.assertEqual(item["venue"],"Sala local")
        signal=item["evidence"]["cultural_signals_v1"]
        self.assertEqual(signal["status"],"lead_unverified")
        self.assertEqual(signal["artists"],["Banda visitante","DJ local"])
        self.assertEqual(signal["organizers"],["Productora invitada"])
        self.assertEqual(signal["venues"],["Sala local"])

    def test_not_infer_artist_or_entities_from_title(self):
        html='<title>Artista visitante en La Plata</title>'
        candidate=radar.make_candidate("https://site.example.org/evento/artista/",
            "src", "Artista visitante", radar.parse_html(html),200)
        self.assertNotIn("cultural_signals_v1",candidate["evidence"])
        self.assertIsNone(candidate["organizer"])

    def test_event_performer_text_allowed_only_in_structured_role(self):
        html=('<script type="application/ld+json">'
            '{"@type":"Event","name":"Teatro y lectura",'
            '"startDate":"2026-11-07","performer":"Grupo Escénico",'
            '"location":"Espacio cultural","organizer":"Colectivo"}'
            '</script>')
        event=radar.structured_event(radar.parse_html(html))
        self.assertEqual(event["performers"],["Grupo Escénico"])
        self.assertEqual(event["venue"],"Espacio cultural")
        self.assertEqual(event["organizer"],"Colectivo")

    def test_unverified_when_only_index_link(self):
        row = radar.make_candidate("https://www.0221.com.ar/que-hago/un-show-n123/",
                                    "src-0221","Un show",None,None)
        self.assertIsNone(row["event_date"])
        self.assertEqual(row["evidence"]["detail_opened"],False)


if __name__ == "__main__":
    unittest.main()
