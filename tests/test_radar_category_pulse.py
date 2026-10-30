"""Regression for the read-only category pulse. No Neon secret or network needed."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import radar_category_pulse as pulse


class PulseCategoryTest(unittest.TestCase):
    def test_normalization_does_not_guess_from_title(self):
        self.assertEqual(pulse.category_of("Música"),"musica")
        self.assertEqual(pulse.category_of("music"),"musica")
        self.assertEqual(pulse.category_of("Cerámica"),"ceramica")
        self.assertEqual(pulse.category_of("milonga"),"danza")
        self.assertEqual(pulse.category_of("clase_tango"),"danza")
        self.assertEqual(pulse.category_of("fiesta"),"fiestas")
        self.assertEqual(pulse.category_of(None),"otras")
        self.assertEqual(pulse.category_of("ritual ceramica en la plaza"),"otras")

    def test_summarize_counts_are_not_promotions(self):
        canon=[("teatro",10,3,5,2,1),("Música",20,2,8,0,0),
               ("musica",1,1,1,1,1),("other unrecognized",4,0,0,0,0)]
        pending=[("teatro",7,4),("Música",11,5),("music",2,1),
                 ("clase_tango",3,0),("misterio",1,1)]
        out=pulse.summarize(canon,pending,"2026-10-30")
        self.assertEqual(out["totalCanonical"],35)
        self.assertEqual(out["totalConfirmedNext15"],6)
        self.assertEqual(out["totalPendingObservations46"],24)
        self.assertFalse(out["publicationApproved"])
        groups={g["rubro"]:g for g in out["categories"]}
        self.assertEqual(groups["musica"]["pendingObservations46"],13)
        self.assertEqual(groups["danza"]["pendingObservations46"],3)
        self.assertEqual(groups["otras"]["historical"],4)
        self.assertEqual(groups["yoga"]["confirmedNext15"],0)
        self.assertEqual(groups["ceramica"]["confirmedNext15"],0)

    def test_complete_taxonomy_no_duplicates(self):
        result=pulse.summarize([],[],"2026-10-30")
        self.assertEqual(len(result["categories"]),14)
        self.assertEqual(len({x["rubro"] for x in result["categories"]}),14)
        self.assertTrue(all(x["confirmedNext15"]==0 for x in result["categories"]))

    def test_original_review_queue_never_approves_and_deduplicates(self):
        from datetime import date
        sample=("Música","Fito Páez",date(2026,10,31),"21:00",
                "Hipódromo de La Plata","https://www.fitopaezoficial.com/event/la-plata/",
                "src-original-fito")
        rows=[
            sample,
            ("musica",)+sample[1:],
            ("Danza","Muestra M.G.",date(2026,11,9),"20:30",
             "Doble-T","https://teatrodoblet.com.ar/event/167089-muestra-de-taller-de-montaje-mg",
             "src-original-doblet"),
            ("Danza","Fake page",date(2026,11,10),"20:30",
             "Doble-T","http://example.com/unsafe","fake"),
            ("musica","Bad URL",date(2026,11,9),"20:30",
             "Hipódromo","https://username:password@example.org/event","bad"),
            ("musica","Unsafe text",date(2026,11,10),"21:00",
             "Venue","https://example.org/e?<script>","bad")]
        out=pulse.review_queue(rows)
        self.assertEqual(len(out),2)
        self.assertEqual(set(x["category"] for x in out),{"musica","danza"})
        self.assertTrue(all(x["publicationApproved"] is False for x in out))
        self.assertTrue(all(x["reviewState"]=="UNAPPROVED_ORIGINAL_DETAIL_REVIEW"
                            for x in out))
        self.assertEqual(out[0]["date"],"2026-10-31")
        self.assertEqual(out[0]["time"],"21:00")

    def test_source_modes_are_last_check_only(self):
        rows=[("fetch",65,7,9),("discover_only",123,0,0),("review",39,0,0)]
        counts=pulse.source_mode_counts(rows)
        self.assertEqual(sum(x["enabled"] for x in counts.values()),227)
        self.assertEqual(counts["fetch"]["lastIndexOnly"],7)
        self.assertEqual(counts["fetch"]["lastFailed"],9)

    def test_markdown_safety(self):
        self.assertNotIn("|",pulse.safe_cell("abc|def"))
        self.assertNotIn(chr(10),pulse.safe_cell("line"+chr(10)+"second"))
        self.assertEqual(pulse.review_queue([(
             "Música","No year","yesterday","20:00","venue",
             "https://example.org/event","s")]),[])

    def test_runtime_queries_are_select_only(self):
        self.assertTrue(pulse.CANONICAL_SQL.lstrip().startswith("SELECT "))
        self.assertTrue(pulse.OBS_SQL.lstrip().startswith("SELECT "))
        self.assertIn("matched_event_key IS NULL",pulse.OBS_SQL)
        self.assertIn("verification='confirmed'",pulse.CANONICAL_SQL)
        self.assertIn("first_seen_at",pulse.CANONICAL_SQL)
        self.assertIn("matched_event_key IS NULL",pulse.REVIEW_QUEUE_SQL)
        self.assertIn("enabled=true",pulse.SOURCE_MODES_SQL)

if __name__=="__main__":
    unittest.main()
