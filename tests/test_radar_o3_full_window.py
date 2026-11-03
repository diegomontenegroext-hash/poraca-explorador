"""O3 seven FULL window: never infer PASS from GitHub, pre-cutover or partial."""
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_o3_full_window import assess,markdown,SQL_FILE,SCHEMA


def case(n,*,post=True,state="complete",failed=0,checks=3):
    strict=(state=="complete" and failed==0 and checks==3)
    return dict(run_id="full-%02d"%n,started_at="2026-11-04T08:00:00Z",
                status=state,is_post_cutover=post,sources_selected=3,
                persisted_checks=checks,sources_ok=3-failed,
                sources_index_only=0,failed_or_errored=failed,
                negative_checks=[dict(sourceId="failure")] if failed else [],
                health_schema="poraca-health-v2",
                o3_run_state="STRICT_COMPLETE" if strict else "PARTIAL_OR_UNCERTIFIED")


class WindowTests(unittest.TestCase):
    def test_past_runs_are_never_postcutover_evidence(self):
        z=assess([case(i,post=False) for i in range(7)])
        self.assertEqual(z["postCutoverFulls"],0)
        self.assertEqual(z["postCutoverStrictComplete"],0)
        self.assertEqual(z["decision"],"PENDING_POST_CUTOVER_FULL_RUNS")
        self.assertFalse(z["publicationApproved"])
        self.assertFalse(z["websiteSsoConfirmed"])

    def test_one_full_cannot_be_certification(self):
        z=assess([case(1)])
        self.assertEqual(z["postCutoverFulls"],1)
        self.assertEqual(z["decision"],"PENDING_POST_CUTOVER_FULL_RUNS")

    def test_six_of_seven_new_real_complete_runs_are_only_candidate(self):
        xs=[case(i) for i in range(6)]+[case(6,state="partial")]
        z=assess(xs)
        self.assertEqual(z["decision"],"CANDIDATE_6_OF_7_FOR_SEPARATE_E2E_CERTIFICATION")
        self.assertEqual(z["postCutoverStrictComplete"],6)
        self.assertFalse(z["publicationApproved"])
        self.assertIn("FULL",markdown(z))

    def test_declared_complete_with_failed_http_is_not_strict(self):
        xs=[case(i) for i in range(6)]+[case(6,failed=1)]
        z=assess(xs)
        self.assertEqual(z["postCutoverStrictComplete"],6)
        self.assertEqual(z["cases"][-1]["declared"],"complete")
        self.assertEqual(z["cases"][-1]["strict"],"PARTIAL_OR_UNCERTIFIED")
        z=assess([case(i,failed=1) for i in range(2)]+
                 [case(i) for i in range(2,7)])
        self.assertEqual(z["decision"],"POST_CUTOVER_7_FULLS_FAIL")

    def test_cannot_claim_strict_over_missing_check(self):
        bad=case(0,checks=2);bad["o3_run_state"]="STRICT_COMPLETE"
        with self.assertRaisesRegex(ValueError,"MISMATCH"):
            assess([bad])

    def test_reject_duplicate_run_or_unrecognized_state(self):
        with self.assertRaisesRegex(ValueError,"REPEATED"):
            assess([case(0),case(0)])
        a=case(1);a["status"]="approved"
        with self.assertRaisesRegex(ValueError,"UNEXPECTED"):
            assess([a])
        with self.assertRaisesRegex(ValueError,"INVALID"):
            assess([case(i) for i in range(8)])

    def test_sql_is_readonly_and_uses_persisted_checks(self):
        sql=SQL_FILE.read_text(encoding="utf-8")
        import re
        code="\n".join(line.split("--",1)[0] for line in sql.splitlines())
        for cmd in ("INSERT","UPDATE","DELETE","TRUNCATE","ALTER","CREATE","DROP","CALL","GRANT"):
            self.assertIsNone(re.search(r"\b"+cmd+r"\b",code,re.I),cmd)
        for token in ("radar_definitivo.runs","radar_definitivo.source_checks",
                      "r.mode='full'","LIMIT 7","2026-11-03 12:00:00-03",
                      "l.started_at>=b.lower_bound","c.http_status NOT BETWEEN 200 AND 299",
                      "l.status='complete'","STRICT_COMPLETE"):
            self.assertIn(token,sql)
        self.assertEqual(SCHEMA,"poraca-o3-seven-natural-full-postcutover-v1")


if __name__=="__main__":
    unittest.main()
