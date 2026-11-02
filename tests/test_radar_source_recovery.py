import pathlib,sys,unittest,json
from datetime import date
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_source_recovery import plan,reconstruct_historical_network


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


    def test_07_actual_network_recovers_future_organizer_without_publishing(self):
        path=pathlib.Path(__file__).resolve().parents[1]/"data/historical-circuit-network-v1.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"],"poraca-historical-circuit-network-v1")
        result=plan([src("rd-web-56c74fce","Casa Dionisio","vinos",
                         diagnosis="REPEATED_INDEX_ONLY",observed=0)],
                    historical_evidence=data["evidence"],today=date(2026,11,2))
        action=result["actions"][0]
        leads=action["historicalNetworkCandidates"]
        self.assertEqual(leads[0]["targetId"],"acsba")
        self.assertEqual(leads[0]["reviewPriority"],"VERIFY_UPCOMING_ORIGINAL")
        self.assertEqual(leads[0]["upcomingOriginals"][0]["date"],"2026-11-27")
        self.assertEqual(leads[0]["upcomingOriginals"][0]["status"],"UNVERIFIED_FOR_PORACA")
        self.assertTrue(all(not x["publicationApproved"] and not x["autoRegistered"]
                            for x in leads))
        self.assertEqual(result["confirmedReplacements"],0)
        self.assertFalse(action["sourceDisabled"])
        self.assertGreaterEqual(len(leads),6)

    def test_11_archival_network_expansion_is_source_discovery_not_registration(self):
        data=json.loads((pathlib.Path(__file__).resolve().parents[1]/
                        "data/historical-circuit-network-v1.json").read_text())
        items=reconstruct_historical_network(data["evidence"],"vinos",date(2026,11,2),limit=30)
        by_id={x["targetId"]:x for x in items}
        self.assertIn("camara-platense-vinotecas",by_id)
        self.assertEqual(by_id["camara-platense-vinotecas"]["reviewPriority"],
                         "FIND_CURRENT_LOCAL_PROGRAM")
        self.assertEqual(by_id["camara-platense-vinotecas"]["accountHint"],
                         "@camaraplatensedevinotecas")
        self.assertEqual(by_id["terruno-vinoteca-lp"]["reviewPriority"],
                         "FIND_CURRENT_LOCAL_PROGRAM")
        self.assertEqual(by_id["villa-wine-lp"]["reviewPriority"],
                         "FIND_CURRENT_LOCAL_PROGRAM")
        self.assertEqual(by_id["acsba"]["reviewPriority"],
                         "VERIFY_UPCOMING_ORIGINAL")
        self.assertNotIn("casa-dionisio",by_id)
        self.assertNotIn("golden-wine",by_id)
        self.assertNotIn("villa-wine",by_id)
        self.assertNotIn("terruno-vinoteca",by_id)
        self.assertIn("golden-wine-lp",by_id)
        self.assertEqual(len(by_id),17)
        self.assertTrue(all(not x["autoRegistered"] and not x["publicationApproved"]
                            for x in items))

    def test_08_no_prediction_after_event_expiration(self):
        data=json.loads((pathlib.Path(__file__).resolve().parents[1]/
                        "data/historical-circuit-network-v1.json").read_text())
        leads=reconstruct_historical_network(data["evidence"],"vinos",date(2026,12,1))
        self.assertFalse(any(x["upcomingOriginals"] for x in leads))
        self.assertEqual(leads[0]["reviewPriority"],"FIND_CURRENT_LOCAL_PROGRAM")

    def test_09_past_mentions_do_not_make_future_events(self):
        records=[{"circuit":"vinos","date":"2026-07-01","kind":"historical",
                  "url":"https://organizer.example/2026-july","title":"Feria",
                  "targets":[{"id":"org","name":"Organizador",
                              "locality":"La Plata"}]},
                 {"circuit":"ciencia","date":"2026-11-27","kind":"upcoming_original",
                  "url":"https://organizer.example/tickets","title":"Otro circuito",
                  "targets":[{"id":"other","name":"Otro","locality":"La Plata"}]}]
        leads=reconstruct_historical_network(records,"vinos",date(2026,11,2))
        self.assertEqual(len(leads),1)
        self.assertEqual(leads[0]["historicalProofUrls"],["https://organizer.example/2026-july"])
        self.assertEqual(leads[0]["upcomingOriginals"],[])

    def test_10_rejects_unverifiable_and_non_https_originals(self):
        sample=[{"circuit":"vinos","date":"2026-11-27","kind":"upcoming_original",
                 "url":"http://not-secure.example/event","targets":[
                     {"id":"candidate","name":"Fake","locality":"La Plata"}]}]
        self.assertEqual(reconstruct_historical_network(sample,"vinos",date(2026,11,2)),[])



    def test_future_original_bubbles_uncovered_circuit_into_top_n(self):
        rows=[src(str(i),"Index source","artes",diagnosis="REPEATED_INDEX_ONLY",
                  observed=0,checks=8) for i in range(20)]
        rows.append(src("wine","Source without events","vinos",
                        diagnosis="REPEATED_INDEX_ONLY",observed=0))
        data=json.loads((pathlib.Path(__file__).resolve().parents[1]/
                         "data/historical-circuit-network-v1.json").read_text())
        out=plan(rows,limit=12,historical_evidence=data["evidence"],
                 today=date(2026,11,2))
        self.assertEqual(out["actions"][0]["sourceId"],"wine")
        self.assertEqual(out["sourcesNeedingRecovery"],21)
        self.assertFalse(out["actions"][0]["selfHealConfirmed"])

if __name__=="__main__":unittest.main()
