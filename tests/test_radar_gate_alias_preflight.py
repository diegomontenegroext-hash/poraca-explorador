import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import radar_gate_alias_preflight as gate

class GateAliasTests(unittest.TestCase):
    def test_two_review_cases_are_already_in_public_observations(self):
        rows=[
            ("c-bol","REVIEW_ORIGINAL_BEFORE_ANY_INSERT","obs-bol",
             "SINDICATO ARGENTINO DE BOLEROS","2026-11-04","21:00",
             "https://casametro.com.ar/categoria-producto/casa-metro/",
             "https://casametro.com.ar/evento/nombre/"),
            ("c-gato","REVIEW_ORIGINAL_BEFORE_ANY_INSERT","obs-gato",
             "Música como en casa – Gato Luna","2026-12-05","21:00",
             "https://casametro.com.ar/categoria-producto/casa-metro/",
             "https://casametro.com.ar/evento/musica-como-en-casa-gato-luna/"),
            ("c-bol-2","HOLD_MULTIPLE_EVIDENCE_FOR_SAME_FUNCTION","obs-bol",
             "SINDICATO ARGENTINO DE BOLEROS","2026-11-04","21:00","index","original")
        ]
        r=gate.summarize(rows)
        self.assertEqual(r["matched_gate_rows"],3)
        self.assertEqual(r["distinct_public_observations"],2)
        self.assertEqual(r["review_original_already_present"],2)
        self.assertFalse(r["authorized_to_write"])
        self.assertEqual(r["by_gate"]["REVIEW_ORIGINAL_BEFORE_ANY_INSERT"],2)

    def test_sql_must_use_same_source_date_time_title_and_compatible_venue(self):
        s=gate.SQL
        self.assertTrue(s.lstrip().startswith("WITH candidates"))
        self.assertIn("c.mapped_public_source_id=e.origin_source_id",s)
        self.assertIn("c.observed_date=e.observed_date",s)
        self.assertIn("left(c.observed_time,5)=left(e.observed_time,5)",s)
        self.assertIn("c.title_key=e.title_key",s)
        self.assertIn("c.venue_key=e.venue_key",s)
        self.assertIn("m.existing_observation_count=0",s)
        self.assertNotRegex(s,r"(?i)\b(?:INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|CALL)\s+")
        self.assertEqual(gate.summarize([])["matched_gate_rows"],0)
