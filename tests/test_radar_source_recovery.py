import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_source_recovery import plan


def src(id,name,circuit="teatro",mode="fetch",diagnosis="DATED_SESSIONS_OBSERVED",
        observed=3,checks=3):
    return {"sourceId":id,"sourceName":name,"circuit":circuit,
            "monitoringMode":mode,"diagnosis":diagnosis,
            "checks7d":checks,"observedSessions7d":observed}

class SourceRecoveryTests(unittest.TestCase):
    def test_01_source_with_lost_yield_gets_alternative_coverage_not_identity(self):
        data=[src("a","Agenda cayó",diagnosis="RECENT_YIELD_DROP",observed=0),
              src("b","Otra cartelera",observed=5),
              src("c","Taller de cerámica",circuit="ceramica",observed=9)]
        got=plan(data)
        self.assertEqual(got["sourcesNeedingRecovery"],1)
        action=got["actions"][0]
        self.assertEqual(action["alternativeCoverageSources"][0]["sourceId"],"b")
        self.assertEqual(action["alternativeCoverageSources"][0]["reason"],
                         "ALTERNATE_COVERAGE_IN_SAME_CIRCUIT_NOT_SAME_ORGANIZER")
        self.assertFalse(action["selfHealConfirmed"])
        self.assertFalse(action["sourceDisabled"])
        self.assertEqual(got["confirmedReplacements"],0)

    def test_02_missing_alternative_is_explicit_uncovered(self):
        got=plan([src("a","Agenda cayó","deportes",
                      diagnosis="REPEATED_INDEX_ONLY",observed=0)])
        self.assertEqual(got["uncoveredCases"],1)
        self.assertEqual(got["actions"][0]["recommendation"],
                         "DISCOVER_NEW_VERIFIABLE_CHANNEL")

    def test_03_discover_only_is_not_fake_alternative(self):
        got=plan([src("a","A",diagnosis="SUCCESSFUL_FETCH_ZERO_DATED_SESSIONS",observed=0),
                  src("b","Instagram",mode="discover_only",observed=10)])
        self.assertEqual(got["uncoveredCases"],1)

    def test_04_productive_sources_are_not_demoted(self):
        got=plan([src("a","Productivo"),src("b","Productivo2")])
        self.assertEqual(got["sourcesNeedingRecovery"],0)

    def test_05_does_not_confuse_recent_success_with_proven_original(self):
        got=plan([src("a","A",diagnosis="RECENT_YIELD_DROP",observed=0),
                  src("b","B",observed=5)])
        self.assertEqual(got["strategy"],"SHADOW_RECOMMENDATIONS_ONLY")
        self.assertTrue(all(not item["selfHealConfirmed"] for item in got["actions"]))

    def test_06_limit_does_not_trigger_another_run(self):
        data=[src(str(i),str(i),diagnosis="REPEATED_INDEX_ONLY",observed=0)
              for i in range(20)]
        got=plan(data,limit=5)
        self.assertEqual(got["sourcesNeedingRecovery"],20)
        self.assertEqual(got["shown"],5)

if __name__=="__main__":unittest.main()
