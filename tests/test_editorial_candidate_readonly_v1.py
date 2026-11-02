"""Editorial candidate diagnostic is SELECT-only and fail-closed.

CI validates the *SQL contract*, never pretends it ran a signed editorial
decision. Live Neon readback is documented separately.
"""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PROBE=(ROOT/"sql/20261102_editorial_candidate_chain_READ_ONLY.sql").read_text()
NEG=(ROOT/"sql/20261102_editorial_candidate_negative_gates_READ_ONLY.sql").read_text()

class EditorialCandidateSafetyTests(unittest.TestCase):
    def test_read_only_never_approves(self):
        for sql in (PROBE,NEG):
            # Ignore comments and reject DML or DDL statements as actual SQL.
            code="\n".join(line.split("--",1)[0] for line in sql.splitlines())
            for pattern in (r"\bINSERT\b",r"\bUPDATE\b",r"\bDELETE\b",
                            r"\bTRUNCATE\b",r"\bALTER\b",r"\bCREATE\b",
                            r"\bDROP\b",r"\bGRANT\b",r"\bCALL\b"):
                self.assertIsNone(re.search(pattern,code,re.I))
            self.assertIn("false AS publication_approved",sql)
        self.assertIn("READY_FOR_INDEPENDENT_EDITORIAL_DECISION_NOT_RELEASED",PROBE)
        self.assertIn("HOLD_ALREADY_CANONICAL_OR_IDENTITY_COLLISION",PROBE)
        self.assertIn("HOLD_NO_EXACT_ORIGINAL_SESSION",PROBE)

    def test_full_identity_criteria_and_host_evidence(self):
        for field in ("title","event_day","event_time","venue","original_url"):
            self.assertIn(field,PROBE)
            self.assertIn(field,NEG)
        self.assertIn("editorial_state='approved_public'",PROBE)
        self.assertIn("review_state='observed_unverified'",PROBE)
        self.assertIn("accepted_event_receipts",PROBE)
        self.assertIn("canon_collision",NEG)

    def test_negative_fixtures(self):
        for name in ("original_exact","clock_mismatch","venue_mismatch",
                     "source_mismatch","not_approved_host"):
            self.assertIn(name,NEG)
        self.assertIn("expected=actual AS pass",NEG)

if __name__=="__main__":
    unittest.main()
