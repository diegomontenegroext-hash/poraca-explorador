import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import radar_definitivo as rd

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
        self.assertGreaterEqual(rd.MAX_SOURCES,30)
        self.assertLessEqual(rd.MAX_SOURCES,50)
        self.assertGreater(rd.MAX_DETAILS_FULL,rd.MAX_DETAILS_INCREMENTAL)
        self.assertLessEqual(rd.MAX_REQUESTS,250)
        self.assertEqual(rd.SCHEMA,"radar_definitivo")
        self.assertEqual(rd.DB_NAME,"poraca_explorador")
        self.assertEqual(rd.DB_ROLE,"poraca_explorador_writer")

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

    def test_budget_stops_excess_and_rate_limited_domain(self):
        budget=rd.Budget(seconds=10)
        url="https://www.instagram.com/p/DeHOPiJRwNi/"
        with patch.object(rd,"fetch",return_value=(429,None,"RATE_LIMIT")):
            response=budget.request(url)
        self.assertEqual(response[0],429)
        self.assertFalse(budget.can_fetch(url))

if __name__=="__main__":
    unittest.main()
