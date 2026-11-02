"""Pure contract tests for read-only executive report (no Neon or writes)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from radar_executive_gates import EXPECTED, report_for, markdown


def sample_rows():
    result = []
    for gate in EXPECTED:
        result.append({"gate":gate,"state":"PASS","evidence":{"runId":"sample-run"},
                       "acceptance":"Read-only fixture","next_action":"None"})
    return result


class ExecutiveGateTests(unittest.TestCase):
    def test_p0_fail_is_never_certified(self):
        rows=sample_rows()
        rows[5]["state"]="FAIL"
        output=report_for(rows)
        self.assertEqual(output["decision"],"NOT_END_TO_END_CERTIFIED")
        self.assertEqual(output["counts"]["FAIL"],1)
        self.assertFalse(output["autoPublished"])
        self.assertIn("CANONICAL_INTEGRITY",markdown(output))

    def test_missing_gate_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING_OR_DUPLICATED"):
            report_for(sample_rows()[:-1])

    def test_unexpected_state_is_rejected(self):
        rows=sample_rows();rows[0]["state"]="CERTIFIED"
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_STATE"):
            report_for(rows)

    def test_latest_full_run_separates_fetch_health_from_yield(self):
        # A healthy 62/62 fetch is not proof that all 32 index_only have events.
        root=Path(__file__).resolve().parents[1]
        sql=(root/"sql/20261101_executive_readiness_gates_READ_ONLY.sql").read_text()
        self.assertIn("last_full AS",sql)
        self.assertIn("full_checks AS",sql)
        self.assertIn("'SOURCE_FETCH_HEALTH'",sql)
        self.assertIn("AND x.full_other=0 THEN 'PASS'",sql)
        self.assertIn("'COVERAGE_BY_CIRCUIT'",sql)
        self.assertIn("http_status NOT BETWEEN 200 AND 299",sql)
        self.assertIn("'lastFullIndexOnly',x.full_index_only",sql)
        self.assertIn("'lastFullRunId',x.last_full_run_id",sql)
        self.assertIn("'baselineCanonicalIdsMissing',x.lost_count",sql)
        self.assertIn("'auditScope','CANONICAL_SURVIVAL_AND_CONTEXTUAL_RELATION_RECONCILIATION'",sql)
        self.assertIn("'legacyV1Decision',x.integrity->'decision'",sql)
        self.assertIn("(x.integrity->>'orphanAcceptedEventRelations')::int=0",sql)
        self.assertIn("(x.integrity->>'missingAcceptedRelationEventIds')::int=0",sql)
        self.assertIn("'acceptedEventRelationGuardEnabled'",sql)
        self.assertIn("tgname='poraca_accepted_event_relation_guard_v1'",sql)
        self.assertNotIn("jsonb_build_object('decision',x.integrity->'decision'",sql)
        self.assertIn("poraca_contextual_relation_evidence_attestation_v1()",sql)
        self.assertIn("contextMissingProvenance",sql)
        self.assertIn("acceptedMissingEventObjects",sql)
        self.assertIn("admission_proof AS (",sql)
        self.assertIn("circuit_checks AS (",sql)
        self.assertIn("'acceptedReceipts',x.integrity->'acceptedReceipts'",sql)
        self.assertIn("'confirmedFutureWithEvidence',x.confirmed_future_with_evidence",sql)
        self.assertIn("'cityActivityExhaustiveness','not_measured'",sql)
        self.assertIn("x.fetch_without_circuit=0 AND x.fetch_unchecked=0",sql)
        self.assertNotIn("(5,'EDITORIAL_ADMISSION',\n 'PARTIAL'",sql)
        self.assertNotIn("(9,'COVERAGE_BY_CIRCUIT',\n 'PARTIAL'",sql)
        # SQL never mutates Neon and cannot claim API/SSO access.
        self.assertNotIn("INSERT INTO ",sql)
        self.assertNotIn("UPDATE public.",sql)
        self.assertNotIn("DELETE FROM ",sql)

    def test_minimum_privilege_separates_live_scope_from_legacy_risk(self):
        sql=(Path(__file__).resolve().parents[1]/"sql/20261101_executive_readiness_gates_READ_ONLY.sql").read_text()
        self.assertIn("limited_scope_verified",sql)
        self.assertIn("'poraca_radar_limited_prod'",sql)
        self.assertIn("'limitedRoleGrantsSafe',x.limited_scope_verified",sql)
        self.assertIn("'legacyIngestNeonSuperuserMember',x.ingest_elevated",sql)
        self.assertIn("'legacyWriterNeonSuperuserMember',x.writer_elevated",sql)
        self.assertIn("WHEN NOT x.limited_scope_verified OR x.ingest_elevated OR x.writer_elevated",sql)
        # A limited active login cannot hide lingering legacy elevated users.
        self.assertIn("'residualLegacyPrivilegeRisk',(x.ingest_elevated OR x.writer_elevated)",sql)

    def test_stability_uses_actual_status_spelling(self):
        sql=(Path(__file__).resolve().parents[1]/"sql/20261101_executive_readiness_gates_READ_ONLY.sql").read_text()
        self.assertIn("->>'state'='correcto'",sql)
        self.assertNotIn("->>'state'='healthy'",sql)

    def test_no_pass_can_self_certify(self):
        self.assertEqual(report_for(sample_rows())["decision"],"NOT_END_TO_END_CERTIFIED")


if __name__=="__main__":
    unittest.main()
