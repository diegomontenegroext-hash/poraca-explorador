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

    def test_04_two_time_slots_are_one_program_day_for_review_only(self):
        # The SQL groups one title/day and reports multiple source clocks;
        # it never creates two canonical sessions nor loses the original.
        out=summarize([item(clock="19:30",gate="REVIEW_MULTIPLE_SLOTS_SAME_DAY")+
                       (False,False,False,2)])
        self.assertEqual(out["reviewGroups"],1)
        self.assertEqual(out["sample"][0]["timeVariants"],2)
        self.assertIsNone(out["sample"][0]["time"])
        self.assertFalse(out["sample"][0]["publicationApproved"])
        self.assertEqual(out["gates"]["REVIEW_MULTIPLE_SLOTS_SAME_DAY"],1)

    def test_04b_null_time_eligible_without_invented_hour(self):
        out=summarize([item(clock=None)])
        self.assertEqual(out["sample"][0]["timeMeaning"],"NO_CLOCK_REQUIRED_FOR_DISCOVERY")
        self.assertIsNone(out["sample"][0]["time"])
        self.assertFalse(out["canonWriteApproved"])

    def test_05_preview_reads_live_staging_not_old_public_observations(self):
        self.assertIn("radar_definitivo.listing_occurrences",SQL)
        self.assertIn("radar_archive_20261031.bootstrap_crosslink_listings",SQL)
        self.assertIn("source_id",SQL)
        self.assertIn("event_time",SQL)
        self.assertIn("venue_variants>1",SQL)
        self.assertIn("GROUP BY title_key,event_date",SQL)
        self.assertNotIn("GROUP BY title_key,event_date,event_time",SQL)
        self.assertNotIn("AND l.event_time ~",SQL)
        self.assertIn("AND l.proof_url ~ '^https://'",SQL)
        self.assertIn("time_variants>1",SQL)
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

    def test_10_time_is_nonblocking_but_real_holds_remain(self):
        self.assertNotIn("HOLD_EXISTING_OBSERVATION_OTHER_TIME", SQL)
        self.assertIn("HOLD_ACCESSORY_TICKET_NOT_SEPARATE_EVENT", SQL)
        self.assertIn("o.source_event_url=ranked.proof_url", SQL)
        self.assertNotIn("left(coalesce(o.observed_time,''),5)<>ranked.event_time", SQL)
        self.assertIn("meet[[:space:]]*(&|and|y)[[:space:]]*greet", SQL)
        self.assertIn("o.reconciliation_state IN ('rejected','conflict','disputed')",SQL)
        out=summarize([
            item(gate="REVIEW_MULTIPLE_SLOTS_SAME_DAY")+(False,False,False,2),
            item(gate="HOLD_ACCESSORY_TICKET_NOT_SEPARATE_EVENT")+(False,False,False,1),
            item(gate="HOLD_VENUE_IDENTITY_VARIANTS")+(False,True,False,1),
            item(gate="REVIEW_ORIGINAL_EVENT")+(False,False,True,1),
        ])
        self.assertEqual(out["reviewGroups"],4)
        self.assertEqual(out["gates"]["REVIEW_MULTIPLE_SLOTS_SAME_DAY"],1)
        self.assertEqual(out["gates"]["HOLD_VENUE_IDENTITY_VARIANTS"],1)
        self.assertTrue(out["sample"][2]["priorEditorialHold"])
        self.assertEqual(out["editorialObservationsWritten"],0)
        self.assertFalse(out["canonWriteApproved"])
        self.assertFalse(out["publicationApproved"])

    def test_07_unfamiliar_status_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize([item(gate="APPROVED")])

if __name__=="__main__":
    unittest.main()
