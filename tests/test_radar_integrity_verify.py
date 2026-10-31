"""Regression: on-demand E2E MUST not need Radar to run and must fail closed."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from radar_integrity_verify import certify
from radar_end_to_end import assess


class IndependentE2ECertificationTests(unittest.TestCase):
    def sample(self, orphaned=0, canonical=0, editorial=7):
        return assess(("definitivo-current", "partial", 62, 62,
                       315, 77, editorial, canonical, canonical, canonical,
                       0, orphaned))

    def test_real_defect_fails_due_to_missing_canons_not_unchanged_acquisition(self):
        report = self.sample(orphaned=27)
        decision, code = certify(report)
        self.assertEqual((decision, code), ("P0_BROKEN_CANONICAL_REFERENCES", 2))
        self.assertEqual(report["nextBlockingGate"], "canonical_integrity")

    def test_no_canonical_future_is_still_not_success(self):
        decision, code = certify(self.sample(orphaned=0, canonical=0))
        self.assertEqual((decision, code), ("BLOCKED_EDITORIAL_ADMISSION", 2))

    def test_healthy_sql_is_only_ready_for_http_not_full_certified(self):
        decision, code = certify(self.sample(orphaned=0, canonical=9))
        self.assertEqual((decision, code),
                         ("DATA_CHAIN_READY_HTTP_AND_SSO_NOT_VERIFIED", 0))

    def test_no_query_or_missing_values_never_pass(self):
        self.assertEqual(certify({}),
                         ("NOT_CERTIFIED_MISSING_INTEGRITY_READBACK", 2))

    def test_workflow_has_no_ingestion_in_verification_mode(self):
        yml = (ROOT / ".github/workflows/radar-definitivo.yml").read_text()
        self.assertIn("python3 src/radar_integrity_verify.py", yml)
        self.assertIn("if: steps.alcance.outputs.mode != 'verify_only'", yml)
        self.assertIn("if: success() && steps.alcance.outputs.mode == 'verify_only'", yml)
        self.assertIn("fetch-depth: 2", yml)

    def test_verification_has_read_only_transaction_and_explicit_scope(self):
        text = (ROOT / "src/radar_integrity_verify.py").read_text()
        self.assertIn('SET TRANSACTION READ ONLY', text)
        self.assertIn('SET LOCAL ROLE poraca_definitivo_scope', text)
        self.assertIn('E2E_READONLY_PRIVILEGES_NOT_ENFORCED', text)
        self.assertIn('current_setting(\'neon.branch_id\',true)', text)
        self.assertNotIn('persist_run_funnel', text)
        self.assertNotIn('radar_definitivo.py --mode', text)


if __name__ == "__main__":
    unittest.main()
