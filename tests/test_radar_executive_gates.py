"""Pure contract tests for read-only executive report (no Neon or writes)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from radar_executive_gates import EXPECTED, report_for, markdown


def sample_rows():
    result = []
    for gate in EXPECTED:
        result.append({"gate":gate,"state":"PASS","evidence":{"runId":"sample-run"},
                       "acceptance":"Read-only fixture","next_action":"None"})
    return result


class ExecutiveGateTests(unittest.TestCase):
    def test_p0_fail_is_never_certified(self):
        rows=sample_rows()
        rows[5]["state"]="FAIL"
        output=report_for(rows)
        self.assertEqual(output["decision"],"NOT_END_TO_END_CERTIFIED")
        self.assertEqual(output["counts"]["FAIL"],1)
        self.assertFalse(output["autoPublished"])
        self.assertIn("CANONICAL_INTEGRITY",markdown(output))

    def test_missing_gate_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OR_DUPLICATED"):
            report_for(sample_rows()[:-1])

    def test_unexpected_state_is_rejected(self):
        rows=sample_rows();rows[0]["state"]="CERTIFIED"
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_STATE"):
            report_for(rows)

    def test_latest_full_run_determines_source_yield(self):
        # A 10/10 incremental must not hide 33 index_only in a 62-source FULL.
        root=Path(__file__).resolve().parents[1]
        sql=(root/"sql/20261101_executive_readiness_gates_READ_ONLY.sql").read_text()
        self.assertIn("last_full AS",sql)
        self.assertIn("full_checks AS",sql)
        self.assertIn("x.full_index_only>0 THEN 'PARTIAL'",sql)
        self.assertIn("'lastFullIndexOnly',x.full_index_only",sql)
        self.assertIn("'lastFullRunId',x.last_full_run_id",sql)
        self.assertIn("'baselineCanonicalIdsMissing',x.lost_count",sql)
        # SQL never mutates Neon and cannot claim API/SSO access.
        self.assertNotIn("INSERT INTO ",sql)
        self.assertNotIn("UPDATE public.",sql)
        self.assertNotIn("DELETE FROM ",sql)

    def test_no_pass_can_self_certify(self):
        self.assertEqual(report_for(sample_rows())["decision"],"NOT_END_TO_END_CERTIFIED")


if __name__=="__main__":
    unittest.main()
