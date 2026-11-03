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


HANDOFF=(ROOT/"sql/20261103_editorial_handoff_gap_READ_ONLY.sql").read_text()

class EditorialHandoffGapTests(unittest.TestCase):
    def test_gap_preview_cannot_write_or_publish(self):
        code="\n".join(line.split("--",1)[0] for line in HANDOFF.splitlines())
        for pattern in (r"\bINSERT\b",r"\bUPDATE\b",r"\bDELETE\b",
                        r"\bALTER\b",r"\bCREATE\b",r"\bDROP\b",
                        r"\bTRUNCATE\b",r"\bGRANT\b",r"\bCALL\b"):
            self.assertIsNone(re.search(pattern,code,re.I),pattern)
        self.assertIn("false AS authorized_to_write",HANDOFF)
        self.assertIn("false AS publication_approved",HANDOFF)

    def test_observation_gap_requires_exact_session_identity(self):
        for token in ("radar_definitivo.listing_occurrences",
                      "public.radar_v3_source_observations",
                      "public.radar_agenda_events",
                      "poraca_fact_key_v1",
                      "c.event_date", "c.event_time", "c.proof_url",
                      "same_original_rank=1",
                      "MISSING_EDITORIAL_OBSERVATION",
                      "proposed_observation_id"):
            self.assertIn(token,HANDOFF)
        self.assertIn("concat_ws('|'",HANDOFF)
        self.assertIn("PARTITION BY",HANDOFF)
        self.assertIn("left(md5(",HANDOFF)

    def test_holds_cannot_be_ignored_to_inflate_events(self):
        for token in ("DO_NOT_APPROVE","explicit_editorial_hold",
                      "HOLD_PRIOR_EDITORIAL_DECISION",
                      "NOOP_POSSIBLE_CANONICAL",
                      "HOLD_SCHEDULE_COLLISION",
                      "HOLD_ORIGINAL_DETAIL_REQUIRED",
                      "HOLD_VENUE_VARIANTS",
                      "HOLD_VENUE_IDENTITY",
                      "OBSERVATION_PRESENT_REVIEW_REQUIRED",
                      "poraca_first_party_event_detail_v1",
                      "America/Argentina/Buenos_Aires"):
            self.assertIn(token,HANDOFF)
        self.assertLess(HANDOFF.index("WHEN explicit_editorial_hold"),
                        HANDOFF.index("WHEN possible_canonical"))
        self.assertLess(HANDOFF.index("WHEN NOT exact_original_detail"),
                        HANDOFF.index("WHEN legacy_observation_count=0"))

    def test_ticketing_host_not_equivalent_to_any_venue(self):
        self.assertIn("c.source_role IN ('original_venue','original_venue_program'",HANDOFF)
        self.assertIn("v.entity_kind='venue'",HANDOFF)
        self.assertIn("v.editorial_state='approved_public'",HANDOFF)
        self.assertIn("v.merged_into_id IS NULL",HANDOFF)
        self.assertIn("possible_approved_venue_count<>1",HANDOFF)
        self.assertIn("instagram.com",HANDOFF)

if __name__=="__main__":
    unittest.main()
