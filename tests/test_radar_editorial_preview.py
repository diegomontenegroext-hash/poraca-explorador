"""Contrato de preadmisión: leer, agrupar y retener dudas."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_editorial_preview import SQL,summarize


def item(day="2026-11-05",clock="20:00",title="Función de prueba",venue="Sala",
         proof="https://example.org/agenda",gate="REVIEW_ORIGINAL_EVENT",
         monitors=1,observations=1,proofs=1,variants=1):
    return (day,clock,title,venue,proof,"ticket_original",
            "primary_venue","Sala",monitors,observations,proofs,variants,gate)


class EditorialPreviewTests(unittest.TestCase):
    def test_01_review_group_never_approves(self):
        output=summarize([item()])
        self.assertEqual(output["reviewGroups"],1)
        self.assertEqual(output["gates"]["REVIEW_ORIGINAL_EVENT"],1)
        self.assertFalse(output["canonWriteApproved"])
        self.assertFalse(output["publicationApproved"])
        self.assertEqual(output["state"],"READ_ONLY_QUEUE_NOT_EDITORIAL_HANDOFF")
        self.assertEqual(output["editorialObservationsWritten"],0)

    def test_02_venue_conflict_requires_individual_review(self):
        output=summarize([item(gate="HOLD_VENUE_IDENTITY_VARIANTS",variants=2,observations=3)])
        self.assertEqual(output["gates"]["HOLD_VENUE_IDENTITY_VARIANTS"],1)
        self.assertEqual(output["sample"][0]["venueVariants"],2)
        self.assertFalse(output["sample"][0]["canonWriteApproved"])

    def test_03_multiple_monitors_same_proof_are_not_independent(self):
        output=summarize([item(monitors=3,observations=3,proofs=1)])
        self.assertEqual(output["sample"][0]["monitors"],3)
        self.assertEqual(output["sample"][0]["differentProofUrls"],1)
        self.assertEqual(output["independentCorroborationsVerified"],0)

    def test_04_two_time_slots_remain_separate(self):
        output=summarize([item(clock="19:30"),item(clock="20:30")])
        self.assertEqual(output["reviewGroups"],2)
        self.assertEqual([x["time"] for x in output["sample"]],["19:30","20:30"])

    def test_05_preview_reads_live_staging_not_old_public_observations(self):
        self.assertIn("radar_definitivo.listing_occurrences",SQL)
        self.assertIn("radar_archive_20261031.bootstrap_crosslink_listings",SQL)
        self.assertIn("source_id",SQL)
        self.assertIn("event_time",SQL)
        self.assertIn("venue_variants>1",SQL)
        self.assertIn("public.radar_v3_source_observations",SQL)
        self.assertIn("public.radar_agenda_events",SQL)
        self.assertIn("DO_NOT_APPROVE",SQL)
        self.assertIn("prior_editorial_hold",SQL)
        self.assertIn("has_editorial_observation",SQL)
        self.assertIn("likely_canonical",SQL)

    def test_06_only_select_not_canonical_write(self):
        self.assertTrue(SQL.strip().upper().startswith("WITH ELIGIBLE"))
        self.assertIn("NOT EXISTS",SQL)
        self.assertIn("choice=1",SQL)
        self.assertIn("America/Argentina/Buenos_Aires",SQL)
        self.assertNotIn("INSERT INTO",SQL.upper())
        self.assertNotIn("UPDATE ",SQL.upper())
        self.assertNotIn("DELETE FROM",SQL.upper())

    def test_07_cross_stage_probe_counts_are_not_publication(self):
        # Live query adds three booleans to the old 13-column contract.
        a=item(clock="21:00")+(False,False,False)
        b=item(clock="22:00")+(True,True,False)
        c=item(clock="23:00")+(False,False,True)
        result=summarize([a,b,c])
        d=result["handoffDiagnostic"]
        self.assertEqual(d["groupsWithProbe"],3)
        self.assertEqual(d["missingEditorialObservation"],2)
        self.assertEqual(d["withEditorialObservation"],1)
        self.assertEqual(d["priorEditorialHolds"],1)
        self.assertEqual(d["possiblyCanonical"],1)
        self.assertEqual(result["handoffDiagnosticState"],"READ_ONLY_NOT_AUTHORIZATION")
        self.assertFalse(result["canonWriteApproved"])
        self.assertFalse(result["publicationApproved"])

    def test_08_old_fixture_contract_is_backward_compatible(self):
        d=summarize([item()])["handoffDiagnostic"]
        self.assertEqual(d["groupsWithProbe"],0)
        self.assertEqual(d["missingEditorialObservation"],0)

    def test_09_any_writer_blocked_handoff_is_prior_hold(self):
        # The canonical writer treats ANY conflict != 'false' as blocking;
        # QA staging uses a textual sentinel, not the boolean string 'true'.
        self.assertIn("coalesce(o.original_evidence->>'conflict','false')<>'false'",SQL)
        self.assertIn("'DO_NOT_APPROVE','DO_NOT_AUTO_APPROVE'",SQL)
        self.assertIn("o.reconciliation_state IN ('rejected','conflict','disputed')",SQL)
        self.assertNotIn("o.original_evidence->>'conflict'='true'",SQL)
        # Staging can be present while explicitly held. Neither is approval.
        out=summarize([item()+(True,True,False)])
        self.assertEqual(out["handoffDiagnostic"]["withEditorialObservation"],1)
        self.assertEqual(out["handoffDiagnostic"]["priorEditorialHolds"],1)
        self.assertTrue(out["sample"][0]["priorEditorialHold"])
        self.assertFalse(out["sample"][0]["canonWriteApproved"])
        self.assertFalse(out["sample"][0]["publicationApproved"])

    def test_07_unfamiliar_status_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize([item(gate="APPROVED")])

if __name__=="__main__":
    unittest.main()
