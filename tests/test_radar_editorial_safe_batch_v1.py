"""Regression contract for editor-owned staging-to-observation handoff."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SQL=(ROOT/"sql"/"20261103_editorial_observation_safe_batch_v1.sql").read_text(encoding="utf-8")
class SafeBatchTests(unittest.TestCase):
    def test_explicit_two_ids_and_determinism(self):
        selected=SQL.split("WITH requested(observation_id) AS (VALUES",1)[1].split("), bridge AS (",1)[0]
        self.assertEqual(selected.count("'obs-stage-"), 2)
        self.assertIn("obs-stage-f416b398b13ad999fc693019", SQL)
        self.assertIn("obs-stage-780e4b6e4e4c424c457034f7", SQL)
        self.assertIn("ON CONFLICT(observation_id) DO NOTHING",SQL)
        self.assertIn("row_number() OVER(PARTITION BY x.proposed_observation_id",SQL)
    def test_source_authority_and_venue_approval(self):
        self.assertIn("editorial_bridge_state='MANUAL_REVIEW_FOR_OBSERVATION_ONLY'",SQL)
        self.assertIn("x.editorial_source_count=1",SQL)
        self.assertIn("x.editorial_source_id IS NOT NULL",SQL)
        self.assertIn("v.editorial_state='approved_public'",SQL)
        self.assertIn("source_circuit='teatro'",SQL)
        self.assertIn("source_role='theatre_ticketing'",SQL)
    def test_safeguards_no_canonical_publication(self):
        self.assertIn("INSERT INTO public.radar_v3_source_observations",SQL)
        self.assertNotIn("INSERT INTO public.radar_agenda_events",SQL)
        self.assertNotIn("UPDATE public.radar_agenda_events",SQL)
        self.assertNotIn("DELETE FROM",SQL.upper())
        self.assertIn("'publication','DO_NOT_APPROVE'",SQL)
        self.assertIn("'conflict','pending_editorial_handoff_review'",SQL)
        self.assertIn("'canonicalCreationApproved',false",SQL)
        self.assertIn("'observed_unverified',NULL",SQL)
        self.assertIn("NOT EXISTS(SELECT 1 FROM public.radar_agenda_events",SQL)
        self.assertIn("NOT EXISTS(SELECT 1 FROM public.radar_v3_source_observations",SQL)
    def test_preserve_provenance_and_staleness(self):
        self.assertIn("'stagingSourceId',source_id",SQL)
        self.assertIn("'stagingListingKey',listing_key",SQL)
        self.assertIn("l.last_seen_at>=now()-interval '7 days'",SQL)
        self.assertIn("last_run_id",SQL)
        self.assertIn("editorial_source_url",SQL)
if __name__=="__main__":
    unittest.main()
