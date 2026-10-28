import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import radar_definitivo as rd
import radar_parallel as rp

class FakeBudget:
    def __init__(self, pages):
        self.pages=pages
    def can_fetch(self,url):
        return url in self.pages
    def request(self,url):
        return self.pages[url]
    def remaining(self):
        return 999

class RadarDefinitivoTests(unittest.TestCase):
    def test_bounds_and_isolation(self):
        self.assertGreaterEqual(rd.MAX_SOURCES_FULL,60)
        self.assertLessEqual(rd.MAX_SOURCES_FULL,100)
        self.assertLessEqual(rd.MAX_SOURCES_INCREMENTAL,50)
        self.assertGreater(rd.MAX_DETAILS_FULL,rd.MAX_DETAILS_INCREMENTAL)
        self.assertLessEqual(rd.MAX_REQUESTS,400)
        self.assertEqual(rd.SCHEMA,"radar_definitivo")
        self.assertEqual(rd.EXPECTED_LAB_DB,"poraca_explorador")
        self.assertEqual(rd.EXPECTED_OPERATIVE_DB,"neondb")
        self.assertEqual(rd.EXPECTED_OPERATIVE_SCOPE,"poraca_definitivo_scope")

    def test_instagram_profiles_are_not_fetched_as_posts(self):
        b=rd.Budget(seconds=100)
        self.assertTrue(b.can_fetch("https://www.instagram.com/malisialibros/p/DeHOPiJRwNi/"))
        self.assertTrue(b.can_fetch("https://www.instagram.com/malisialibros/"))
        # Selection SQL, not the HTTP budget, is what excludes monitored profiles.
        class Cursor:
            def __init__(self): self.query=""
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,params):self.query=sql
            def fetchall(self):return []
        cur=Cursor()
        class Conn:
            def cursor(self):return cur
        rd.choose_sources(Conn(),"full")
        self.assertIn("monitoring_mode='fetch'",cur.query)
        self.assertNotIn("discover_only",cur.query)

    def test_incremental_due_filter_and_full_prioritize_never_checked(self):
        class Cursor:
            def __init__(self):self.queries=[]
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,params):self.queries.append(sql)
            def fetchall(self):return []
        cursor=Cursor()
        class Conn:
            def cursor(self):return cursor
        rd.choose_sources(Conn(),"incremental")
        rd.choose_sources(Conn(),"full")
        self.assertIn("next_due_at<=now()",cursor.queries[0])
        self.assertNotIn("next_due_at<=now()",cursor.queries[1])
        self.assertIn("NULLS FIRST",cursor.queries[1])

    def test_discovers_instagram_permalink_from_article_second_level(self):
        source=dict(source_id="s1",url="https://www.0221.com.ar/que-hago",source_role="local_press")
        article="https://www.0221.com.ar/que-hago/teatro-platense-n123/"
        post="https://www.instagram.com/p/DeHOPiJRwNi/"
        pages={
            source["url"]:(200,'<a href="/que-hago/teatro-platense-n123/">Teatro platense</a>',None),
            article:(200,'<a href="'+post+'">Flyer de la organizacion</a>',None),
            post:(200,'<meta property="og:title" content="Teatro en La Plata">',None)
        }
        check,candidates=rd.scan_source(source,FakeBudget(pages),"full")
        self.assertEqual(check["status"],"ok")
        self.assertIn(article,[c["original_url"] for c in candidates])
        self.assertIn(post,[c["original_url"] for c in candidates])
        self.assertTrue(all(c["evidence"]["announced_only"] for c in candidates))

    def test_entity_proposal_is_not_canonical(self):
        entity=rd.entity_for("s1","Museo Azzarini","venue",
                             "https://example.org/evento/","event_jsonld_original")
        self.assertEqual(entity["entity_type"],"venue")
        self.assertTrue(entity["evidence"]["not_verified"])
        self.assertIsNone(rd.entity_for("s1","","venue","https://x.org/","test"))

    def test_full_urls_preserve_agenda_dates(self):
        p=rd.parse_html('<a href="/evento/milonga/?fecha=2026-11-01">Milonga</a>')
        got=rd.links_from_page('<a href="/evento/milonga/?fecha=2026-11-01">Milonga</a>',p,
                "https://agenda.example.org/")
        self.assertTrue(any("fecha=2026-11-01" in url for url,_ in got))
        self.assertIsNone(rd.safe_public_link("http://127.0.0.1/admin","https://agenda.example.org/"))

    def test_recency_requires_jsonld_original_event_and_valid_year(self):
        today=rd.datetime.now(rd.timezone.utc).date()
        a=dict(kind="event_detail",title="Festival cultural en La Plata",
               event_date=str(today+rd.timedelta(days=12)),
               event_time="20:00",evidence={"structured_event_found":True,"detail_opened":True})
        self.assertEqual(rd.credible_occurrence(a),today+rd.timedelta(days=12))
        b=dict(a,event_date="2025-01-01")
        self.assertIsNone(rd.credible_occurrence(b))
        c=dict(a,evidence={"structured_event_found":False,"detail_opened":True})
        self.assertIsNone(rd.credible_occurrence(c))

    def test_ig_ogimage_is_reference_only(self):
        body='<meta property="og:image" content="https://example.org/poster.jpg?foo=bar">'
        self.assertEqual(rd.extract_og_image(body,"https://example.org/evento/"),
                         "https://example.org/poster.jpg?foo=bar")

    def test_budget_stops_excess_and_rate_limited_domain(self):
        budget=rd.Budget(seconds=10)
        url="https://www.instagram.com/p/DeHOPiJRwNi/"
        with patch.object(rd,"fetch",return_value=(429,None,"RATE_LIMIT")):
            response=budget.request(url)
        self.assertEqual(response[0],429)
        self.assertFalse(budget.can_fetch(url))

if __name__=="__main__":
    unittest.main()


class CulturalIsoTimeTests(unittest.TestCase):
    def test_utc_jsonld_is_local_argentina_time(self):
        self.assertEqual(rp.iso_event_fields("2026-11-09T23:30:00Z"),
                         ("2026-11-09","20:30"))
        self.assertEqual(rp.iso_event_fields("2026-11-14T19:30:00+00:00"),
                         ("2026-11-14","16:30"))
        self.assertEqual(rp.iso_event_fields("2026-11-09T01:30:00Z"),
                         ("2026-11-08","22:30"))

    def test_explicit_local_offset_and_naive_stay_local(self):
        self.assertEqual(rp.iso_event_fields("2026-11-09T20:30:00-03:00"),
                         ("2026-11-09","20:30"))
        self.assertEqual(rp.iso_event_fields("2026-11-09T20:30"),
                         ("2026-11-09","20:30"))
        self.assertEqual(rp.iso_event_fields("2026-11-09"),("2026-11-09",None))

    def test_invalid_dates_and_timezones_rejected(self):
        for text in ("2026-02-30","2026-11-09T25:30:00Z",
                     "2026-11-09T20:30Zgarbage","2026-11-09T20:30:00+29:00",
                     "2026-11-09T20:30 UTC",""):
            with self.subTest(text=text):
                self.assertEqual(rp.iso_event_fields(text),(None,None))

