import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_source_learning import SQL,classify,summarize


def sample(name="Fuente",mode="fetch",checks=0,empty=0,idx=0,
           sessions=0,latest=0,prev=0,latest_n=0,prev_n=0):
    return ("id",name,"institutional_program","artes",mode,
            checks,empty,idx,sessions,sessions,latest,prev,latest_n,prev_n)


class YieldLearningTests(unittest.TestCase):
    def test_ok_without_events_is_not_productive(self):
        r=classify(sample("Diario",checks=5,empty=5,latest_n=3))
        self.assertEqual(r["diagnosis"],"SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS")
        self.assertFalse(r["autoPriorityChanged"])

    def test_drop_after_previous_production(self):
        r=classify(sample(checks=8,empty=3,sessions=12,
                          latest=0,prev=12,latest_n=3,prev_n=5))
        self.assertEqual(r["diagnosis"],"RECENT_YIELD_DROP")

    def test_institutional_index_not_removed(self):
        r=classify(sample(checks=6,idx=6,latest_n=3))
        self.assertEqual(r["diagnosis"],"REPEATED_INDEX_ONLY")
        self.assertFalse(r["autoEntityRemoved"])

    def test_existing_and_new_sources(self):
        self.assertEqual(classify(sample())["diagnosis"],"NOT_RECENTLY_OBSERVED")
        self.assertEqual(classify(sample(mode="discover_only"))["diagnosis"],
                         "PRESERVE_DISCOVERY_OR_REVIEW_ROLE")

    def test_productive_is_still_unapproved(self):
        r=classify(sample(checks=3,sessions=18,latest=18,latest_n=3))
        self.assertEqual(r["diagnosis"],"DATED_SESSIONS_OBSERVED")
        self.assertEqual(r["evidenceClass"],"per_run_reported_sessions_unapproved")

    def test_readonly_uses_historical_run_outcomes(self):
        self.assertIn("source_outcomes",SQL)
        self.assertIn("30 days",SQL)
        self.assertNotIn("last_run_id",SQL)

    def test_summary_sorts_diagnostic_anomalies(self):
        r=summarize([sample("Fuente A",checks=5,empty=5),
                     sample("Fuente B",mode="discover_only")])
        self.assertEqual(r["sourceCount"],2)
        self.assertEqual(r["priorityReview"][0]["sourceName"],"Fuente A")
        self.assertEqual(r["learningState"],"DIAGNOSTIC_ONLY")


if __name__=="__main__":
    unittest.main()
