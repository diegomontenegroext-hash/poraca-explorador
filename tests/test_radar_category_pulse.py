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

    def test_runtime_queries_are_select_only(self):
        self.assertTrue(pulse.CANONICAL_SQL.lstrip().startswith("SELECT "))
        self.assertTrue(pulse.OBS_SQL.lstrip().startswith("SELECT "))
        self.assertIn("matched_event_key IS NULL",pulse.OBS_SQL)
        self.assertIn("verification='confirmed'",pulse.CANONICAL_SQL)
        self.assertIn("first_seen_at",pulse.CANONICAL_SQL)

if __name__=="__main__":
    unittest.main()
