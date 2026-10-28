import importlib.util
import pathlib
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("explore", BASE / "src" / "explore.py")
explore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(explore)


class TestExplorador(unittest.TestCase):
    def test_fuentes(self):
        self.assertEqual(len(explore.SOURCES), 9)
        self.assertEqual(len({x["id"] for x in explore.SOURCES}), 9)
        self.assertTrue(all(x["url"].startswith("https://") for x in explore.SOURCES))
        self.assertEqual(sum(s["kind"] == "instagram" for s in explore.SOURCES), 3)

    def test_extraccion_sin_red(self):
        page = '<html><head><title>Agenda cultural</title></head><body>' \
               '<h1>Próximos conciertos</h1><a href="/evento/2026">Concierto</a>' \
               '<a href="/ayuda">Ayuda</a></body></html>'
        r = explore.extract(page, "https://ejemplo.org/")
        self.assertEqual(r["page_title"], "Agenda cultural")
        self.assertEqual(r["headings"], ["Próximos conciertos"])
        self.assertEqual(len(r["candidate_links_unverified"]), 1)
        self.assertEqual(
            r["candidate_links_unverified"][0]["url"],
            "https://ejemplo.org/evento/2026",
        )

    def test_etiqueta_pistas_y_no_eventos(self):
        self.assertEqual(explore.markdown_cell("cine | arte <h1>"), "cine / arte &lt;h1&gt;")


if __name__ == "__main__":
    unittest.main()
