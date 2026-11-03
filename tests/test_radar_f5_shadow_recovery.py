import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from radar_f5_shadow_recovery import assess,markdown,SCENES,STRONG,PARTIAL,NONE,SQL_FILE


def row(scene,*,before=3,alternatives=(),result=None):
    alts=[dict(root=host,sourceIds=host,precise=p,datedLeads=n,
               proof="https://"+host+"/evento") for host,p,n in alternatives]
    remaining_precise=sum(x["precise"] for x in alts)
    remaining_leads=sum(x["datedLeads"] for x in alts)
    result=result or (STRONG if before>0 and any(x["precise"]>0 for x in alts)
        else PARTIAL if remaining_leads else NONE)
    return dict(circuit=scene,removed_root="primary."+scene+".example",
        removed_precise=before,removed_leads=max(1,before),removed_proof="https://primary.example/a",
        remaining_domains=len(alts),
        remaining_precise_domains=sum(x["precise"]>0 for x in alts),
        remaining_precise_sessions=remaining_precise,
        remaining_dated_leads=remaining_leads,
        alternatives=alts,simulated_result=result,
        actual_outage_verified=False,same_event_recovered=False,
        editorial_approved=False,f5_certified=False)


class F5Tests(unittest.TestCase):
    def test_genuine_four_scenes_are_not_inflated_by_composite_circuit(self):
        x=[row("arte_y_cultura",alternatives=[("arts.example",1,1)]),
           row("musica",alternatives=[("tickets.example",0,5)]),
           row("teatro",alternatives=[("agenda.example",0,8)]),
           row("literatura",alternatives=[("libros.example",0,1)]),
           row("teatro_y_musica",alternatives=[("sala.example",9,12)])]
        s=assess(x)
        self.assertEqual(s["fourDistinctSceneTarget"],list(SCENES))
        self.assertEqual(s["fourSceneShadowStrong"],1)
        self.assertEqual(s["fourSceneShadowPartial"],3)
        self.assertTrue(s["compositeCircuitNotExtraIndependentScene"])
        self.assertEqual(s["gateStatus"],"NOT_CHECKED")
        self.assertFalse(s["actualFaultInjected"])
        self.assertFalse(s["publicationApproved"])
        self.assertIn("NOT_CHECKED",markdown(s))

    def test_four_strong_shadow_does_not_yet_mean_real_fallback(self):
        x=[row(scene,alternatives=[(scene+".original.example",2,3)]) for scene in SCENES]
        s=assess(x)
        self.assertEqual(s["fourSceneShadowStrong"],4)
        self.assertEqual(s["gateStatus"],"NOT_CHECKED")
        self.assertFalse(s["sameEventRecovered"])
        self.assertTrue(s["noSourceChanges"])

    def test_unproductive_backup_is_lead_only(self):
        a=assess([row("literatura",alternatives=[("libros.example",0,2)])])
        self.assertEqual(a["fourSceneShadowStrong"],0)
        self.assertEqual(a["fourSceneShadowPartial"],1)

    def test_same_root_cannot_disguise_second_source_id(self):
        q=row("teatro",alternatives=[("samehost.example",2,2),("samehost.example",3,3)])
        with self.assertRaisesRegex(ValueError,"SAME_HOST"):
            assess([q])
        q=row("teatro",alternatives=[("independent.example",2,2)])
        q["removed_root"]="independent.example"
        with self.assertRaisesRegex(ValueError,"SAME_HOST"):
            assess([q])

    def test_claimed_success_without_precise_survival_is_rejected(self):
        q=row("teatro",alternatives=[("index.example",0,12)],result=STRONG)
        with self.assertRaisesRegex(ValueError,"FALSE_GREEN"):
            assess([q])

    def test_source_status_change_or_approval_is_not_an_f5_shadow_receipt(self):
        for key in ("actual_outage_verified","same_event_recovered",
                    "editorial_approved","f5_certified"):
            q=row("arte_y_cultura",alternatives=[("alternative.example",2,2)])
            q[key]=True
            with self.assertRaisesRegex(ValueError,"CANNOT_PUBLISH"):
                assess([q])

    def test_missing_evidence_and_wrong_totals_are_rejected(self):
        q=row("teatro",alternatives=[("backup.example",2,2)])
        q["alternatives"][0]["proof"]="http://unsecured.example"
        with self.assertRaisesRegex(ValueError,"MISSING_ORIGINAL"):
            assess([q])
        q=row("teatro",alternatives=[("backup.example",2,2)])
        q["remaining_precise_sessions"]=12
        with self.assertRaisesRegex(ValueError,"WRONG_SESSION"):
            assess([q])

    def test_sql_uses_independent_domains_and_read_only_neon(self):
        import re
        src=SQL_FILE.read_text(encoding="utf-8")
        code="\n".join(line.split("--",1)[0] for line in src.splitlines())
        for operation in ("INSERT","UPDATE","DELETE","CREATE","DROP","GRANT",
                          "ALTER","TRUNCATE","CALL"):
            self.assertIsNone(re.search(r"\b"+operation+r"\b",code,re.I),operation)
        for needle in ("public.poraca_source_host_v1(s.url)",
                       "l.last_seen_at>=p.from_time",
                       "c.http_status BETWEEN 200 AND 299",
                       "public.poraca_first_party_event_detail_v1",
                       "l.event_date BETWEEN p.today AND p.today+45",
                       "s.enabled AND s.monitoring_mode='fetch'",
                       "WHERE position>1","false AS actual_outage_verified",
                       "false AS same_event_recovered","false AS f5_certified"):
            self.assertIn(needle,src)

if __name__=="__main__":
    unittest.main()
