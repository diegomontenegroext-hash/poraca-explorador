"""Static contract regression for Neon proof roles, no Neon writes."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MIGRATION=(ROOT/"sql/20261102_generic_field_provenance_v2.sql").read_text(encoding="utf8")
READBACK=(ROOT/"sql/20261102_event_provenance_readback_READ_ONLY.sql").read_text(encoding="utf8")

class ProvenanceContractTests(unittest.TestCase):
    def test_not_domain_specific_and_exact_fields(self):
        self.assertIn("CREATE OR REPLACE VIEW public.poraca_event_field_evidence_quality_v1",MIGRATION)
        self.assertEqual(MIGRATION.count("'first_party_ticketing'::text"),4)
        self.assertEqual(MIGRATION.count("'official_institution'::text"),4)
        self.assertEqual(MIGRATION.count("'first_party'::text"),4)
        for field in ("title","date","time","venue"):
            self.assertEqual(MIGRATION.count("'fieldEvidence'::text ->> '"+field+"'::text"),4)
        self.assertEqual(MIGRATION.count('["title","date","time","venue"]'),4)
        for domain in ("livepass.com","alternativateatral.com","teatroargentino.gba.gob.ar"):
            self.assertNotIn(domain,MIGRATION.lower())

    def test_no_row_mutation_or_auto_publication(self):
        for dml in ("INSERT INTO","DELETE FROM","TRUNCATE TABLE","UPDATE public.", "ALTER ROLE"):
            self.assertNotIn(dml,MIGRATION)
        self.assertNotIn("UPDATE public.",READBACK)
        self.assertIn("poraca_event_release_readiness_v2",READBACK)
        self.assertIn("structurally_reviewed_needs_independent_publication_gate",MIGRATION)
        self.assertIn("hold_event_confirmation",MIGRATION)

    def test_real_original_and_civil_day_required(self):
        self.assertEqual(MIGRATION.count("(x.value ->> 'url'::text) = e.source_url"),4)
        for text in ("= e.title","= e.event_date::text","= e.event_time","= e.venue"):
            self.assertEqual(MIGRATION.count(text),4)
        self.assertIn("jsonb_typeof(x.value -> 'supports'::text)='array'::text",MIGRATION)

if __name__=="__main__":
    unittest.main()
