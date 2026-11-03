"""Guard the read-only handoff contract: no phantom observations or add-on events."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "sql" / "20261103_editorial_handoff_gap_READ_ONLY.sql").read_text(encoding="utf-8")


class EditorialHandoffSqlTests(unittest.TestCase):
    def test_read_only_and_no_writer_claim(self):
        executable = re.sub(r"(?m)^\\s*--.*$", "", SQL).strip().upper()
        self.assertTrue(executable.startswith("WITH SCOPE AS"))
        for mutation in ("INSERT INTO", "UPDATE ", "DELETE FROM", "TRUNCATE "):
            self.assertNotIn(mutation, executable)
        self.assertIn("false AS authorized_to_write", SQL)
        self.assertIn("false AS publication_approved", SQL)

    def test_identical_source_original_other_clock_is_hold(self):
        self.assertIn("o.source_event_url=c.proof_url", SQL)
        self.assertIn("o.observed_date=c.event_date", SQL)
        self.assertIn("left(coalesce(o.observed_time,''),5)<>c.event_time", SQL)
        self.assertIn("AS alternate_time_observation", SQL)
        self.assertIn("WHEN alternate_time_observation THEN 'HOLD_EXISTING_OBSERVATION_OTHER_TIME'", SQL)
        self.assertLess(SQL.index("WHEN alternate_time_observation THEN"), SQL.index("WHEN legacy_observation_count=0 THEN"))

    def test_ancillary_ticket_must_not_become_separate_event(self):
        self.assertIn("AS possible_accessory_ticket", SQL)
        self.assertIn("meet[[:space:]]*(&|and|y)[[:space:]]*greet", SQL)
        self.assertIn("HOLD_ACCESSORY_TICKET_NOT_SEPARATE_EVENT", SQL)
        self.assertLess(SQL.index("WHEN possible_accessory_ticket THEN"), SQL.index("WHEN legacy_observation_count=0 THEN"))

    def test_writer_holds_are_all_blocking(self):
        self.assertIn("'DO_NOT_APPROVE','DO_NOT_AUTO_APPROVE'", SQL)
        self.assertIn("coalesce(o.original_evidence->>'conflict','false')<>'false'", SQL)
        self.assertIn("HOLD_PRIOR_EDITORIAL_DECISION", SQL)
        self.assertIn("HOLD_SCHEDULE_COLLISION", SQL)
        self.assertIn("HOLD_VENUE_IDENTITY", SQL)


if __name__ == "__main__":
    unittest.main()
