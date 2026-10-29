import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import instagram_seed_inbox as inbox
import radar_definitivo as radar


class DummyBudget:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []
    def can_fetch(self, url):
        return url in self.pages
    def request(self, url):
        self.requested.append(url)
        return self.pages[url]


class DummyConn:
    def __init__(self, recent=()):
        self.recent = recent
        self.executed = []
        self.query = ""
    def cursor(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def execute(self, sql, params):
        self.executed.append((sql, params))
        self.query = sql
    def fetchall(self):
        if "FROM radar_definitivo.sources" in self.query:
            return [("rd-ig-lutitravelguide", "Luti", "https://www.instagram.com/lutitravelguide/",
                     "curadora", 50, 72, 0)]
        return [(url,) for url in self.recent]


class InstagramSeedTests(unittest.TestCase):
    URL = "https://www.instagram.com/reel/DfDGyw_SkDA/"

    def inbox(self, items):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        path = Path(self.tempdir.name) / "inbox.json"
        path.write_text(json.dumps(items), encoding="utf-8")
        return path

    def seed(self, **extras):
        return dict(source_id="rd-ig-lutitravelguide", account="lutitravelguide",
                    url=self.URL, expires_on="2026-11-04", **extras)

    def test_input_is_strict_and_short_lived(self):
        self.assertEqual(inbox.normalized_post(self.URL + "?vrfl=abc"), None)
        self.assertEqual(inbox.normalized_post("http://instagram.com/reel/DfDGyw_SkDA/"), None)
        self.assertEqual(inbox.normalized_post("https://www.instagram.com/lutitravelguide/"), None)
        self.assertEqual(inbox.normalized_post(self.URL), self.URL)
        path = self.inbox([self.seed(), self.seed()])
        self.assertEqual(len(inbox.read_inbox(path, today=radar.date(2026, 10, 28))), 1)
        self.assertEqual(inbox.read_inbox(path, today=radar.date(2026, 11, 5)), [])

    def test_uses_catalogued_discover_only_account_without_fetching_profile(self):
        path = self.inbox([self.seed()])
        conn = DummyConn()
        sources = inbox.choose_seed_sources(conn, path=path, today=radar.date(2026, 10, 28))
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["seed_urls"], [self.URL])
        self.assertTrue(sources[0]["seed_only"])
        self.assertIn("monitoring_mode='discover_only'", conn.executed[0][0])
        self.assertEqual(inbox.choose_seed_sources(DummyConn(recent=(self.URL,)),
                         path=path, today=radar.date(2026, 10, 28)), [])

    def test_reads_only_exact_reel_and_retains_available_caption(self):
        source = dict(source_id="rd-ig-lutitravelguide", url="https://www.instagram.com/lutitravelguide/",
                      source_role="curadora", account="lutitravelguide", seed_only=True,
                      seed_urls=[self.URL])
        caption = "miércoles de Piano Bar en Casa Tomada\\n" + ("más planes culturales\\n" * 40)
        html = ('<meta property="og:title" content="Luti planes La Plata">'
                '<meta name="description" content="' + caption + '">'
                '<meta property="og:url" content="https://www.instagram.com/lutitravelguide/reel/DfDGyw_SkDA/">'
                '<meta property="og:image" content="https://example.org/flyer.jpg">')
        budget = DummyBudget({self.URL: (200, html, None)})
        check, candidates = radar.scan_source(source, budget, "incremental")
        self.assertEqual(budget.requested, [self.URL])
        self.assertEqual(check["status"], "ok")
        self.assertTrue(check["_seed_only"])
        self.assertEqual(check["details_opened"], 1)
        self.assertEqual(check["links_found"], 0)
        self.assertEqual(len(candidates), 1)
        evidence = candidates[0]["evidence"]
        self.assertTrue(evidence["profile_not_scanned"])
        self.assertTrue(evidence["seeded_permalink"])
        self.assertIn("Piano Bar", evidence["public_caption_text"])
        self.assertGreater(len(evidence["public_caption_text"]), 500)
        self.assertEqual(evidence["public_caption_extraction"], "html_meta_full_v2")
        self.assertEqual(evidence["attribution_status"], "public_url_account_matched")
        self.assertEqual(evidence["og_image_url"], "https://example.org/flyer.jpg")
        self.assertIsNone(candidates[0]["event_date"])

    def test_multiplan_curator_caption_preserves_twelve_distinct_review_leads(self):
        caption = """planes recomendados en La Plata
miércoles de Perritos calientes en @veredita.bar
miércoles de chori en @mirafloreslp
miércoles de Piano Bar en @casatomadawinehouse
jueves todo el día menú en @radici.lp con @alcachofasplatenses
jueves en la fábrica de @vermu_interferencia con @oldiesbutgoldies.lp y @mirafloreslp
y si querés 29 con ñoquis en @cretino8y61
viernes cumple del Diego en @mirafloreslp
y abre @destileriamoreira con @desobediente.sr
sábado aniversario de @aurelius.yes
y a la noche fiesta Gateo en @ciudaddegatos con @zoemeier__
domingo presentación Charly absoluto en @veredita.bar con @repmiguel
y antidomingo de DJs y VJs de @radiociudad933
"""
        got=radar.curator_multi_plan_preview(caption)
        self.assertEqual(got["classification"],"curatorial_multiplan_caption")
        self.assertEqual(got["state"],"review_only")
        self.assertEqual(got["plan_lead_count"],12)
        self.assertEqual(got["event_count"],0)
        self.assertTrue(got["original_confirmation_required"])
        self.assertFalse(got["date_or_venue_inferred"])
        self.assertEqual(got["leads"][0]["mentioned_accounts"],["veredita.bar"])
        self.assertEqual(got["leads"][3]["mentioned_accounts"],
                         ["radici.lp","alcachofasplatenses"])
        self.assertIsNone(got["leads"][-1]["literal_weekday"])
        self.assertFalse(any("event_date" in lead or "venue_id" in lead or
                         "organized_by" in lead for lead in got["leads"]))
        source=dict(source_id="rd-ig-lutitravelguide",
                    url="https://www.instagram.com/lutitravelguide/",
                    source_role="curadora",account="lutitravelguide",
                    seed_only=True,seed_urls=[self.URL])
        import html as stdhtml
        markup=('<meta name="description" content="'+
                stdhtml.escape(caption,quote=True)+'">'+
                '<meta property="og:url" content="'+
                'https://www.instagram.com/lutitravelguide/reel/DfDGyw_SkDA/">')
        check,candidates=radar.scan_source(
            source,DummyBudget({self.URL:(200,markup,None)}),"incremental")
        self.assertEqual(check["status"],"ok")
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]["evidence"]["multi_plan_review"]["plan_lead_count"],12)
        self.assertIsNone(candidates[0]["event_date"])
        self.assertIsNone(candidates[0]["venue"])

    def test_multiplan_does_not_invent_events_from_single_promotional_post(self):
        self.assertIsNone(radar.curator_multi_plan_preview(
            "sábado gran show en @ciudaddegatos con @dj.ana @dj.mario"))
        self.assertIsNone(radar.curator_multi_plan_preview(
            "martes @lugar1\\nmartes @lugar2\\nmartes @lugar3"))
        self.assertIsNone(radar.curator_multi_plan_preview(None))

    def test_does_not_fetch_profile_when_reel_blocked(self):
        source = dict(source_id="rd-ig-lutitravelguide", url="https://www.instagram.com/lutitravelguide/",
                      source_role="curadora", account="lutitravelguide", seed_only=True,
                      seed_urls=[self.URL])
        budget = DummyBudget({self.URL: (429, None, "RATE_LIMIT")})
        check, candidates = radar.scan_source(source, budget, "full")
        self.assertEqual(budget.requested, [self.URL])
        self.assertEqual(check["status"], "failed")
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
