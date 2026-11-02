"""L4 regression: independent data-integrity verification is strict and read-only."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from radar_integrity_verify import certify, load_canonical_survival_ledger, assess_canonical_survival
from radar_end_to_end import assess

PROJECT = "frosty-union-52906378"
BRANCH = "br-mute-recipe-b4odj2bl"


class IndependentE2ECertificationTests(unittest.TestCase):
    def sample(self, orphaned=0, canonical=4, editorial=7,
               missing_receipts=0, missing_approved=0, dangling_relations=0, guards=2,
               survival=True, canary=1):
        report = assess(("definitivo-current", "complete", 62, 62,
                         315, 77, editorial, canonical, canonical,
                         canonical, 0, orphaned))
        report["attestation"] = {
            "schema": "poraca-e2e-integrity-attestation-v1",
            "projectId": PROJECT, "branchId": BRANCH,
            "acceptedReceipts": 22,
            "missingAcceptedReceipts": missing_receipts,
            "orphanedObservationLinks": orphaned,
            "orphanAcceptedEventRelations": dangling_relations,
            "missingAcceptedRelationEventIds": dangling_relations,
            "missingCanonicalIdentities": orphaned,
            "approvedEventIds": 1,
            "missingApprovedEventIds": missing_approved,
            "canonicalTotal": 140,
            "canonicalFuture": canonical,
            "confirmedScheduledFuture": canonical,
            "canaryElAnimo": canary,
            "protectionTriggers": guards,
            "checkpointSurvivalGuard": survival,
            "decision": ("P0_CANONICAL_HISTORY_BROKEN"
                         if orphaned or missing_receipts or missing_approved or dangling_relations
                         else "DATA_INTEGRITY_PASS_HTTP_SSO_SEPARATE"),
        }
        report["contextAudit"] = {
            "schema": "poraca-context-relations-v1",
            "scope": "documented_context_not_publication",
            "database": "neondb", "branchId": BRANCH,
            "contextOnlyAccepted": dangling_relations,
            "contextOnlyEventKeys": dangling_relations,
            "contextMissingProvenance": 0,
            "contextUnsupportedPredicate": 0,
            "acceptedMissingEventObjects": 0,
            "writesPerformed": False,
        }
        report["canonicalSurvivalLedger"] = {
            "baselineRequired": 133, "baselinePresent": 133,
            "baselineMissing": 0, "newIdsSinceBaseline": 7,
            "baselineDigest": "5f651497da4b186acc9f24dc80922d89",
            "writesPerformed": False,
        }
        report["historicalCanaries"] = {
            "elAnimo": 1, "freezer": 1, "immutableGuard": 1, "relationGuard": 1,
        }
        return report

    def test_migration_guard_is_non_destructive_and_canonical_anchored(self):
        sql=(ROOT / "sql/20261101_accepted_event_relation_guard_v1_REQUIRES_APPROVAL.sql").read_text()
        self.assertIn("BEFORE INSERT OR UPDATE OF review_state, subject_kind, subject_id, object_kind, object_id", sql)
        self.assertIn("NEW.review_state='accepted'",sql)
        self.assertIn("NEW.subject_kind='event'",sql)
        self.assertIn("c.event_key=NEW.subject_id",sql)
        self.assertIn("NEW.object_kind='event'",sql)
        self.assertIn("c.event_key=NEW.object_id",sql)
        self.assertIn("RAISE EXCEPTION 'PORACA_ACCEPTED_EVENT_RELATION_MISSING_CANONICAL'",sql)
        self.assertIn("CREATE OR REPLACE FUNCTION",sql)
        self.assertIn("REQUIRES",str(ROOT / "sql/20261101_accepted_event_relation_guard_v1_REQUIRES_APPROVAL.sql"))
        self.assertNotIn("DELETE FROM ",sql)
        self.assertNotIn("TRUNCATE TABLE ",sql)
        self.assertNotIn("UPDATE public.poraca_knowledge_relations SET",sql)
        self.assertNotIn("INSERT INTO public.radar_agenda_events",sql)

    def test_unpublished_link_reconciliation_requires_evidence(self):
        sql=(ROOT / "sql/20261101_reconcile_unpublished_observation_links_REQUIRES_APPROVAL.sql").read_text()
        self.assertIn("n_before NOT IN (0,5)",sql)
        self.assertIn("reconciliation_state='reconciled_linked'",sql)
        self.assertIn("original_evidence#>>'{reconciliation_v1,publication_approved}'='false'",sql)
        self.assertIn("original_evidence#>>'{reconciliation_v1,canonical_target}'=o.matched_event_key",sql)
        self.assertIn("matched_event_key=NULL",sql)
        self.assertIn("'previous_event_key',o.matched_event_key",sql)
        self.assertIn("reconciliation_state='observed_unverified'",sql)
        self.assertIn("n_updated<>n_before",sql)
        self.assertNotIn("DELETE FROM ",sql)
        self.assertNotIn("TRUNCATE TABLE ",sql)
        self.assertNotIn("UPDATE public.radar_agenda_events",sql)
        self.assertNotIn("UPDATE public.poraca_knowledge_relations",sql)

    def test_observation_link_guard_preserves_independent_relations(self):
        sql=(ROOT / "sql/20261102_observation_canonical_link_guard_and_relation_policy.sql").read_text()
        self.assertIn("NEW.matched_event_key IS NOT NULL",sql)
        self.assertIn("c.event_key=NEW.matched_event_key",sql)
        self.assertIn("BEFORE INSERT OR UPDATE OF matched_event_key,reconciliation_state",sql)
        self.assertIn("DISABLE TRIGGER poraca_accepted_event_relation_guard_v1",sql)
        self.assertNotIn("UPDATE public.radar_v3_source_observations SET",sql)
        self.assertNotIn("DELETE FROM public.",sql)
        self.assertNotIn("TRUNCATE TABLE ",sql)

    def test_real_defect_fails_due_to_missing_canons(self):
        report = self.sample(orphaned=26, missing_receipts=13)
        self.assertEqual(certify(report), ("P0_CANONICAL_HISTORY_BROKEN", 2))
        self.assertEqual(report["nextBlockingGate"], "canonical_integrity")

    def test_receipt_loss_never_hidden_by_zero_orphans(self):
        self.assertEqual(certify(self.sample(missing_receipts=1)),
                         ("P0_CANONICAL_HISTORY_BROKEN", 2))

    def test_approved_review_loss_never_hidden_by_zero_orphans(self):
        self.assertEqual(certify(self.sample(missing_approved=1)),
                         ("P0_CANONICAL_HISTORY_BROKEN", 2))

    def test_documented_context_is_never_an_accepted_orphan(self):
        report = self.sample(dangling_relations=17)
        report["attestation"]["missingAcceptedRelationEventIds"] = 15
        report["contextAudit"]["contextOnlyEventKeys"] = 15
        self.assertEqual(certify(report),
                         ("P0_ACCEPTED_RELATION_WITHOUT_CANONICAL", 2))

    def test_unreviewed_context_remains_real_failure(self):
        report = self.sample()
        report["contextAudit"]["contextMissingProvenance"] = 1
        self.assertEqual(certify(report), ("P0_CANONICAL_HISTORY_BROKEN", 2))

    def test_unknown_context_predicate_fails(self):
        report = self.sample()
        report["contextAudit"]["contextUnsupportedPredicate"] = 1
        self.assertEqual(certify(report), ("P0_CANONICAL_HISTORY_BROKEN", 2))

    def test_context_missing_fails_closed(self):
        report = self.sample(dangling_relations=17)
        report.pop("contextAudit")
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_MISSING_CONTEXT_PROVENANCE_AUDIT", 2))

    def test_context_count_conflict_fails_closed(self):
        report = self.sample(dangling_relations=17)
        report["contextAudit"]["contextOnlyAccepted"] = 16
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_CONTEXT_RELATION_COUNT_CONFLICT", 2))

    def test_missing_accepted_event_object_fails(self):
        report = self.sample()
        report["contextAudit"]["acceptedMissingEventObjects"] = 1
        self.assertEqual(certify(report), ("P0_CANONICAL_HISTORY_BROKEN", 2))

    def test_missing_triggers_fail_even_when_data_appears_healthy(self):
        self.assertEqual(certify(self.sample(guards=1)),
                         ("P0_CANONICAL_PROTECTION_MISSING", 2))

    def test_disabled_relation_guard_fails_even_with_healthy_data(self):
        report = self.sample()
        report["historicalCanaries"]["relationGuard"] = 0
        self.assertEqual(certify(report),
                         ("P0_ACCEPTED_EVENT_RELATION_GUARD_DISABLED", 2))

    def test_one_accepted_orphan_event_cannot_pass_context_attestation(self):
        report = self.sample(dangling_relations=1)
        self.assertEqual(certify(report),
                         ("P0_ACCEPTED_RELATION_WITHOUT_CANONICAL", 2))

    def test_missing_checkpoint_survival_guard_fails(self):
        self.assertEqual(certify(self.sample(survival=False)),
                         ("P0_CANONICAL_PROTECTION_MISSING", 2))

    def test_missing_canary_fails(self):
        self.assertEqual(certify(self.sample(canary=0)),
                         ("P0_CANARY_NOT_PRESENT", 2))

    def test_independent_approval_canary_missing_even_with_no_orphans(self):
        report = self.sample()
        report["historicalCanaries"]["freezer"] = 0
        self.assertEqual(certify(report),
                         ("P0_INDEPENDENT_ACCEPTANCE_CANARY_MISSING", 2))

    def test_immutable_event_key_guard_must_exist(self):
        report = self.sample()
        report["historicalCanaries"]["immutableGuard"] = 0
        self.assertEqual(certify(report),
                         ("P0_CANONICAL_IMMUTABILITY_MISSING", 2))

    def test_missing_independent_canary_readback_fails_closed(self):
        report = self.sample()
        report.pop("historicalCanaries")
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_MISSING_INDEPENDENT_CANARIES", 2))

    def test_git_baseline_ledger_is_valid_and_contains_133_id_hashes(self):
        ledger=load_canonical_survival_ledger()
        self.assertEqual(len(ledger["idsMd5"]),133)
        self.assertEqual(ledger["expectedAtLeast"],133)
        self.assertEqual(ledger["baselineSortedHashesMd5"],
                         "5f651497da4b186acc9f24dc80922d89")

    def test_ledger_detects_silent_canonical_deletion_without_receipt(self):
        ledger=load_canonical_survival_ledger()
        full=assess_canonical_survival(ledger,ledger["idsMd5"]+["0"*32])
        self.assertEqual(full["baselineMissing"],0)
        self.assertEqual(full["newIdsSinceBaseline"],1)
        removed=assess_canonical_survival(ledger,ledger["idsMd5"][1:])
        self.assertEqual(removed["baselineMissing"],1)
        report=self.sample()
        report["canonicalSurvivalLedger"]=removed
        self.assertEqual(certify(report),
                         ("P0_CANONICAL_SURVIVAL_LEDGER_MISSING_IDS",2))

    def test_ledger_missing_technical_readback_never_certifies(self):
        report=self.sample()
        report.pop("canonicalSurvivalLedger")
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_MISSING_CANONICAL_SURVIVAL_LEDGER",2))

    def test_ledger_contradictory_total_never_certifies(self):
        report=self.sample()
        report["canonicalSurvivalLedger"]["baselinePresent"]=132
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_CONTRADICTORY_CANONICAL_SURVIVAL",2))

    def test_zero_future_events_is_not_success(self):
        self.assertEqual(certify(self.sample(canonical=0)),
                         ("P0_NO_CONFIRMED_FUTURE_EVENTS", 2))

    def test_missing_receipt_audit_fails_closed(self):
        report = self.sample()
        del report["attestation"]
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_MISSING_RECEIPT_ATTESTATION", 2))

    def test_no_query_never_passes(self):
        self.assertEqual(certify({}),
                         ("NOT_CERTIFIED_MISSING_INTEGRITY_READBACK", 2))

    def test_wrong_branch_fails(self):
        report = self.sample()
        report["attestation"]["branchId"] = "br-wrong"
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_WRONG_DATABASE_SCOPE", 2))

    def test_missing_numeric_field_fails(self):
        report = self.sample()
        del report["attestation"]["missingAcceptedReceipts"]
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_MALFORMED_RECEIPT_COUNTS", 2))

    def test_contradictory_readbacks_fail(self):
        report = self.sample()
        report["attestation"]["orphanedObservationLinks"] = 3
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_CONTRADICTORY_READBACK", 2))

    def test_attestation_false_green_decision_conflict(self):
        report = self.sample()
        report["attestation"]["decision"] = "P0_CANONICAL_HISTORY_BROKEN"
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_ATTESTATION_DECISION_CONFLICT", 2))

    def test_healthy_sql_only_ready_for_http_not_full_certification(self):
        self.assertEqual(certify(self.sample()),
                         ("DATA_INTEGRITY_PASS_HTTP_AND_SSO_NOT_VERIFIED", 0))

    def test_reconciliation_gate_remains_explicit_and_distinct_from_integrity(self):
        report = self.sample(editorial=0)
        self.assertEqual(report["nextBlockingGate"], "radar_to_editorial_reconciliation")
        self.assertEqual(report["editorialObservationsTouchedSinceRadarRun"], 0)
        self.assertEqual(certify(report),
                         ("DATA_INTEGRITY_PASS_EDITORIAL_CONTINUITY_PENDING_HTTP_SSO_NOT_VERIFIED", 0))
        self.assertEqual(report["nextBlockingGate"], "radar_to_editorial_reconciliation")

    def test_missing_all_accepted_receipts_never_passes(self):
        report = self.sample(editorial=0)
        report["attestation"]["acceptedReceipts"] = 0
        self.assertEqual(certify(report), ("NOT_CERTIFIED_NO_ACCEPTED_RECEIPTS", 2))

    def test_editorial_gate_conflict_fails_closed(self):
        report = self.sample(editorial=0)
        report["editorialObservationsTouchedSinceRadarRun"] = 4
        self.assertEqual(certify(report),
                         ("NOT_CERTIFIED_CONTRADICTORY_EDITORIAL_GATE", 2))

    def test_workflow_keeps_ingestion_separate(self):
        yml = (ROOT / ".github/workflows/radar-definitivo.yml").read_text()
        self.assertIn("python3 src/radar_integrity_verify.py", yml)
        self.assertIn("if: steps.alcance.outputs.mode != 'verify_only'", yml)
        self.assertIn("if: success() && steps.alcance.outputs.mode == 'verify_only'", yml)
        self.assertIn("fetch-depth: 2", yml)

    def test_verifier_has_read_only_transaction_and_explicit_scope(self):
        text = (ROOT / "src/radar_integrity_verify.py").read_text()
        self.assertIn("SET TRANSACTION READ ONLY", text)
        self.assertIn("SET LOCAL ROLE poraca_definitivo_scope", text)
        self.assertIn("E2E_READONLY_PRIVILEGES_NOT_ENFORCED", text)
        self.assertIn("current_setting('neon.branch_id',true)", text)
        self.assertIn("poraca_e2e_integrity_attestation_v1()", text)
        self.assertIn("poraca_contextual_relation_evidence_attestation_v1()", text)
        self.assertNotIn("persist_run_funnel", text)
        self.assertNotIn("radar_definitivo.py --mode", text)


if __name__ == "__main__":
    unittest.main()
