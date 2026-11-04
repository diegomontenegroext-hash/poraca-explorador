import sys
import unittest
import copy
import pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_o3_historical_backtest import assess,PATH
import json

class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(PATH.read_text(encoding="utf-8"))
    def test_exact_seven_fulls_and_honest_metric(self):
        r=assess(self.data)
        self.assertEqual(r["persistedComplete"],1)
        self.assertEqual(r["counterfactualHttpCleanUnderV2"],5)
        self.assertEqual(r["sourceChecksPersisted"],437)
        self.assertEqual(r["sourceIndexOnly"],227)
        self.assertEqual(r["httpFailedChecks"],2)
        self.assertFalse(r["o3Certified"])
        self.assertFalse(r["postCutoverCertifiable"])
        self.assertFalse(r["historicalStatusChanged"])
        self.assertEqual(r["historicalHealthSchemas"],{"poraca-health-v1":4,"poraca-health-v2":3})
        self.assertEqual(r["fragileWithoutDatedExtraction"],{"yoga":2,"talleres":3})
    def test_counterfactual_never_rewrites_run_status(self):
        data=copy.deepcopy(self.data)
        data["runs"][3]["persistedStatus"]="partial"
        self.assertEqual(assess(data)["persistedComplete"],1)
        data["publishedStatusImmutable"]=False
        with self.assertRaisesRegex(ValueError,"STATE_MUTATION"):
            assess(data)
    def test_missing_duplicate_bad_values_do_not_pass(self):
        data=copy.deepcopy(self.data)
        data["runs"][2]["id"]=data["runs"][1]["id"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            assess(data)
        data=copy.deepcopy(self.data)
        data["runs"][2]["checked"]=80
        with self.assertRaisesRegex(ValueError,"BAD_COUNTERS"):
            assess(data)
        data=copy.deepcopy(self.data)
        data["runs"][0]["indexOnly"]=32
        with self.assertRaisesRegex(ValueError,"INCONSISTENT"):
            assess(data)

if __name__=="__main__":
    unittest.main()
