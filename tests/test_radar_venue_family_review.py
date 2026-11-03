"""Safety and scope contract for the venue-family read-only review."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
SQL=(ROOT / "sql/20261103_venue_family_review_READ_ONLY.sql").read_text(encoding="utf-8")
class VenueFamilyReviewTests(unittest.TestCase):
    def test_no_writes_or_privilege_changes(self):
        # Reject executable mutations (the query is a single WITH... SELECT).
        statement=SQL.split("WITH editorial_queue AS (",1)[1]
        for keyword in ("INSERT INTO", "UPDATE public.", "DELETE FROM", "TRUNCATE ", "GRANT ", "ALTER ROLE"):
            self.assertNotIn(keyword,statement.upper())
        self.assertIn("SELECT * FROM assessed",statement)
        self.assertIn("false AS publication_approved",SQL)
        self.assertIn("false AS editorial_observation_authorized",SQL)
        self.assertIn("false AS subspace_approved",SQL)
    def test_generalized_review_instead_of_auto_aliases(self):
        self.assertIn("HOLD_APPROVED_VENUE_MAPPING",SQL)
        self.assertIn("HOLD_VENUE_VARIANTS",SQL)
        self.assertIn("HOLD_AMBIGUOUS_PARENT",SQL)
        self.assertIn("HOLD_PARENT_INTERNAL",SQL)
        self.assertIn("REVIEW_PARENT_AND_SUBSPACE",SQL)
        self.assertIn("e.editorial_state IN ('approved_public','verified_internal')",SQL)
        self.assertIn("e.merged_into_id IS NULL",SQL)
        self.assertIn("candidate_count>1",SQL)
    def test_preserve_original_subspace_and_source(self):
        self.assertIn("s.venue AS original_venue_with_room",SQL)
        self.assertIn("s.proof_url",SQL)
        self.assertIn("s.editorial_source_id",SQL)
        self.assertIn("s.source_circuit",SQL)
        self.assertIn("split_part(q.venue,',',1)",SQL)
        self.assertIn("EXACT_HEAD",SQL)
        self.assertIn("SHORTENED_NAME_REQUIRES_REVIEW",SQL)
    def test_different_stages_of_approval_remain_distinct(self):
        self.assertLess(SQL.index("WHEN hits.candidate_count>1"),SQL.index("WHEN hits.approved_count=1"))
        self.assertLess(SQL.index("WHEN hits.approved_count=0"),SQL.index("WHEN hits.approved_count=1"))
        self.assertIn("false AS venue_identity_approved",SQL)
        self.assertIn("false AS publication_approved",SQL)
if __name__ == "__main__":
    unittest.main()
