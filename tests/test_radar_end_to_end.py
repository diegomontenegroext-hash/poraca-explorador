import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_end_to_end import SQL, assess


class RadarEndToEndReadinessTests(unittest.TestCase):
    def test_real_bootstrap_break_is_reconciliation_not_web_success(self):
        r=assess(("definitivo-bootstrap","partial",63,63,315,83,0,0,0,0,15))
        self.assertEqual(r["nextBlockingGate"],"radar_to_editorial_reconciliation")
        self.assertEqual(r["status"],"DATA_CHAIN_BLOCKED")
        self.assertEqual(r["radarFutureObservations"],315)
        self.assertEqual(r["futurePrimaryWithTimeVenue"],83)
        self.assertEqual(r["suspectTicketCrosslinks"],15)
        self.assertFalse(r["publicationApprovedByRadar"])
        self.assertEqual(r["webSso"],"NOT_CHECKED")

    def test_no_future_sources_blocks_discovery(self):
        r=assess(("run","complete",62,62,0,0,0,0,0,0,0))
        self.assertEqual(r["nextBlockingGate"],"discover_future_sessions")

    def test_partial_selected_vs_checked_never_reports_chain_ready(self):
        r=assess(("run","partial",62,48,20,12,5,3,3,3,0))
        self.assertEqual(r["nextBlockingGate"],"radar_acquisition")

    def test_editorial_gate_distinct_from_unverified_public_observation(self):
        r=assess(("run","complete",62,62,20,8,10,0,0,0,0))
        self.assertEqual(r["nextBlockingGate"],"editorial_admission")

    def test_existing_canonical_is_not_proof_of_live_api_or_ssosuccess(self):
        r=assess(("run","complete",62,62,20,8,10,5,4,1,0))
        self.assertEqual(r["status"],"HTTP_NOT_VERIFIED")
        self.assertEqual(r["nextBlockingGate"],"authenticated_api_and_web_check")
        self.assertEqual(r["apiHttp"],"NOT_CHECKED")
        self.assertEqual(r["webSso"],"NOT_CHECKED")

    def test_no_radar_history_is_explicit(self):
        r=assess(None)
        self.assertEqual(r["status"],"NO_COMPLETED_RUN")
        self.assertEqual(r["nextBlockingGate"],"radar")

    def test_sql_read_only_and_no_surprise_publication(self):
        self.assertTrue(SQL.lstrip().upper().startswith("WITH LAST_RUN"))
        self.assertIn("radar_definitivo.listing_occurrences",SQL)
        self.assertIn("public.radar_v3_source_observations",SQL)
        self.assertIn("public.radar_agenda_events",SQL)
        for statement in ("INSERT ","DELETE ","UPDATE ","TRUNCATE ","ALTER ","DROP "):
            self.assertNotIn(statement,SQL.upper())
        self.assertIn("America/Argentina/Buenos_Aires",SQL)


if __name__=="__main__":
    unittest.main()
