import pathlib
import sys
import unittest
from datetime import date,datetime,timezone
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import radar_funnel_metrics as m

class RunFunnelTests(unittest.TestCase):
    def run_record(self):
        now=datetime(2026,10,31,3,20,tzinfo=timezone.utc)
        return ("run-A","incremental","complete",now,now,2,2,4,2,3,5)

    def row(self,key,clock,first="run-A",rubro="teatro_y_musica",
            url=None,pub=None,primary=True,venue="Teatro Metro"):
        return (key,"source-1","Las Hijas",date(2026,11,8),clock,
                venue,url or "https://teatrometrolp.com.ar/entrada/"+key,
                first,rubro,"lashijas","teatrometro" if venue else None,
                primary,pub)

    def test_separate_showtimes_are_not_duplicates(self):
        rows=[self.row("show-a","19:30"),self.row("show-b","21:30")]
        d=m.calculate(self.run_record(),rows,{"ok":1},(161,161,627,517))
        c=d["counts"]
        self.assertEqual(c["distinctDetected"],2)
        self.assertEqual(c["new"],2)
        self.assertEqual(c["seenAgain"],0)
        self.assertEqual(c["possibleDuplicates"],0)
        self.assertEqual(c["pendingEditorial"],2)
        self.assertEqual(c["completePrimaryEvidence"],2)
        self.assertEqual(c["matchedPublished"],0)
        self.assertEqual(c["venueNamesMentioned"],1)
        self.assertEqual(c["parsedListingReads"],4)
        self.assertIsNone(c["publishedNewThisRun"])
        self.assertIsNone(c["newPlacesApprovedThisRun"])
        self.assertFalse(d["autoPublished"])
        self.assertEqual(d["byRubro"][0]["label"],"Teatro y música (mixto)")

    def test_repeat_not_duplicate_and_published_requires_catalogue_link(self):
        rows=[self.row("old","19:30",first="earlier",pub="event-public"),
              self.row("new","21:30",primary=False)]
        d=m.calculate(self.run_record(),rows,{"ok":1},(160,161,627,517))
        self.assertEqual(d["counts"]["seenAgain"],1)
        self.assertEqual(d["counts"]["possibleDuplicates"],0)
        self.assertEqual(d["counts"]["matchedPublished"],1)
        self.assertEqual(d["counts"]["pendingEditorial"],1)
        self.assertEqual(d["counts"]["completePrimaryEvidence"],1)

    def test_exact_same_show_different_sources_is_only_suspected(self):
        rows=[self.row("one","19:30",rubro="teatro"),
              self.row("two","19:30",first="old",rubro="teatro_y_musica")]
        d=m.calculate(self.run_record(),rows,{"ok":2},(160,161,627,517))
        self.assertEqual(d["counts"]["possibleDuplicates"],1)
        self.assertEqual(d["counts"]["new"],1)
        self.assertEqual(d["counts"]["seenAgain"],1)
        self.assertEqual(d["counts"]["pendingEditorial"],2)
        self.assertEqual(len(d["byRubro"]),2)

    def test_no_data_is_zero_not_made_up(self):
        d=m.calculate(self.run_record(),[],{},(160,161,625,517))
        self.assertEqual(d["counts"]["distinctDetected"],0)
        self.assertEqual(d["counts"]["new"],0)
        self.assertEqual(d["counts"]["matchedPublished"],0)
        self.assertIsNone(d["counts"]["publishedNewThisRun"])

    def test_source_circuit_is_not_inferred_as_event_genre(self):
        self.assertEqual(m.category(""),"unclassified")
        self.assertEqual(m.category(None),"unclassified")
        self.assertEqual(m.category("teatro_y_musica"),"teatro_y_musica")
        self.assertEqual(m.category("unfamiliar_new_label"),"unclassified")

    def test_source_yield_distinguishes_http_success_from_editorial_yield(self):
        source_rows=[
            ("genda","Agenda La Plata","https://agendalaplata.ar/",
             "general","secondary_agenda",95,"ok",200,7,42,None,105,40),
            ("arte","Centro de Arte UNLP","https://www.centrodearte.unlp.edu.ar/",
             "arte_y_cultura","primary_source",88,"index_only",200,0,0,None,0,0),
            ("dionisio","Casa Dionisio","https://www.casadionisio.com.ar/",
             "vinos","primary_source",75,"index_only",200,0,0,None,0,0),
            ("unknown","Sede sin circuito","https://example.org/",
             None,"institutional",60,"index_only",200,0,0,None,0,0),
        ]
        result=m.source_yield(source_rows)
        self.assertEqual(result["selectedChecks"],4)
        self.assertEqual(result["indexOnlyCount"],3)
        self.assertEqual(result["productiveSources"],1)
        self.assertEqual(result["detected"],105)
        self.assertEqual(result["new"],40)
        self.assertEqual(result["topContributors"][0]["sourceId"],"genda")
        self.assertEqual(result["priorityReview"][0]["sourceId"],"arte")
        self.assertEqual(result["priorityReview"][2]["sourceCircuit"],"unclassified")
        self.assertEqual(result["priorityReview"][0]["observation"],
                         "http_ok_no_dated_sessions_extracted")
        self.assertNotIn("approved",repr(result).lower())

    def test_source_yield_keeps_distinct_showtimes_without_automatic_changes(self):
        source_rows=[("a","Source A","https://example.org/a",
                      "teatro","primary",75,"ok",200,1,2,None,2,1)]
        rows=[self.row("one","19:30"),self.row("two","21:30")]
        r=m.calculate(self.run_record(),rows,{"ok":1},(160,161,627,517),source_rows)
        self.assertEqual(r["counts"]["possibleDuplicates"],0)
        self.assertEqual(r["sourceYieldV1"]["detected"],2)
        self.assertEqual(r["sourceYieldV1"]["new"],1)
        self.assertFalse(r["autoPublished"])

    def test_source_yield_is_read_only_and_run_scoped(self):
        query=m.SOURCE_YIELD_SQL.lower()
        self.assertIn("c.run_id=%s",query)
        self.assertIn("l.last_run_id=c.run_id",query)
        self.assertNotIn("update ",query)
        self.assertNotIn("insert ",query)
        self.assertEqual(m.source_yield([])["selectedChecks"],0)

    def test_persistence_is_one_scoped_run_summary_only(self):
        sql=m.PERSIST_SQL.lower()
        self.assertIn("update radar_definitivo.runs",sql)
        self.assertIn("editorial_funnel_v1",sql)
        self.assertIn("not (summary ? 'editorial_funnel_v1')",sql)
        self.assertIn("where run_id=%s",sql)
        self.assertNotIn("update public.",sql)
        self.assertNotIn("insert into public.",sql)
        self.assertIn("l.last_run_id=%s",m.FACTS_SQL.lower())
        self.assertIn("e.status='scheduled'",m.FACTS_SQL.lower())
        self.assertIn("e.verification='confirmed'",m.FACTS_SQL.lower())
        self.assertIn("e.published_at is not null",m.FACTS_SQL.lower())

if __name__=="__main__":
    unittest.main()
