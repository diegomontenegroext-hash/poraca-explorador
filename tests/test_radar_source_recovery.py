import pathlib,sys,unittest,json
from datetime import date
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_source_recovery import plan,reconstruct_historical_network,discover_directory_review_leads,is_local_future_original


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
        # The standard bounded report must show the actual past co-organizers,
        # not only arbitrary alphabetically earlier wine shops.
        top=reconstruct_historical_network(data["evidence"],"vinos",date(2026,11,2))
        self.assertEqual(top[0]["targetId"],"acsba")
        self.assertTrue({"camara-platense-vinotecas","golden-wine-lp",
                         "villa-wine-lp","terruno-vinoteca-lp"}.issubset(
                            {item["targetId"] for item in top}))
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


    def test_circuit_yield_resilience_has_zero_for_unproductive_wine(self):
        data=[
            src("wine-home","Dionisio","vinos",diagnosis="REPEATED_INDEX_ONLY",observed=0),
            src("yoga-one","Yoga directo","yoga",observed=3),
            src("ig-wine","IG sin extracción","vinos",mode="discover_only",observed=80)
        ]
        out=plan(data)
        by_circuit={r["circuit"]:r for r in out["circuitResilience"]}
        self.assertEqual(by_circuit["vinos"]["fetchSources"],1)
        self.assertEqual(by_circuit["vinos"]["reportedDatedYieldSources7d"],0)
        self.assertEqual(by_circuit["vinos"]["sourceResilienceGate"],
                         "NO_REPORTED_DATED_YIELD")
        self.assertEqual(by_circuit["yoga"]["sourceResilienceGate"],
                         "SINGLE_REPORTED_YIELD_CHANNEL")
        self.assertEqual(out["circuitsWithoutReportedDatedYield"],1)
        self.assertEqual(out["circuitsWithOneReportedYieldChannel"],1)
        self.assertFalse(by_circuit["vinos"]["resilienceCertified"])

    def test_multiple_source_yields_never_certify_independent_organizers(self):
        out=plan([src("a","Agenda 1","musica",observed=7),
                  src("b","Agenda 2","musica",observed=15)])
        metric=out["circuitResilience"][0]
        self.assertEqual(metric["reportedDatedYieldSources7d"],2)
        self.assertEqual(metric["sourceResilienceGate"],
                         "MULTIPLE_REPORTED_YIELD_CHANNELS_NOT_CERTIFIED")
        self.assertFalse(metric["independentOrganizerVerified"])
        self.assertFalse(metric["resilienceCertified"])
        self.assertEqual(out["confirmedReplacements"],0)
        self.assertEqual(out["resilienceCertification"],
                         "NOT_CERTIFIED_REQUIRES_INDEPENDENT_ORIGINALS")

    def test_reporting_deduplicates_source_ids_not_runs(self):
        out=plan([src("same","Repeated","talleres",observed=3),
                  src("same","Repeated","talleres",observed=6),
                  src("empty","Institution","talleres",
                      diagnosis="REPEATED_INDEX_ONLY",observed=0)])
        metric=out["circuitResilience"][0]
        self.assertEqual(metric["fetchSources"],2)
        self.assertEqual(metric["reportedDatedYieldSources7d"],1)
        self.assertEqual(metric["fetchSourcesWithoutReportedDatedYield7d"],1)
        self.assertEqual(out["circuitsWithOneReportedYieldChannel"],1)

    def test_no_fetch_sources_do_not_create_false_coverage(self):
        out=plan([src("seed","Direct permalink","vinos",
                      mode="discover_only",observed=10),
                  src("review","Secondary","vinos",mode="review",observed=20)])
        self.assertEqual(out["circuitResilience"],[])
        self.assertEqual(out["circuitsWithoutReportedDatedYield"],0)


    def test_future_original_marks_circuit_with_no_fetch_source(self):
        evidence=json.loads((pathlib.Path(__file__).resolve().parents[1]/
             "data/historical-circuit-network-v1.json").read_text())["evidence"]
        out=plan([],today=date(2026,11,2),historical_evidence=evidence)
        wine={x["circuit"]:x for x in out["circuitResilience"]}["vinos"]
        self.assertEqual(wine["fetchSources"],0)
        self.assertEqual(wine["reportedDatedYieldSources7d"],0)
        self.assertTrue(wine["futureOriginalResearchHint"])
        self.assertFalse(wine["resilienceCertified"])
        self.assertEqual(out["confirmedReplacements"],0)

    def test_incomplete_future_research_hint_does_not_create_circuit(self):
        bad=[{"circuit":"vinos","kind":"upcoming_original",
              "date":"2026-11-27","url":"https://example.org/event",
              "event":{"date":"2026-11-27","time":"19:00"},
              "targets":[{"id":"organizer","name":"Org","locality":"La Plata"}]}]
        out=plan([],today=date(2026,11,2),historical_evidence=bad)
        self.assertEqual(out["circuitResilience"],[])

    def test_national_directory_never_counts_as_local_future_event(self):
        raw=json.loads((pathlib.Path(__file__).resolve().parents[1]/
                       "data/historical-circuit-network-v1.json").read_text())
        data=raw["evidence"]
        directories=discover_directory_review_leads(data,"vinos",date(2026,11,2))
        self.assertEqual(len(directories),1)
        self.assertEqual(directories[0]["date"],"2026-11-13")
        self.assertEqual(directories[0]["directoryScope"],"AR_nationwide")
        self.assertFalse(directories[0]["localParticipantVerified"])
        self.assertFalse(directories[0]["localEventDetected"])
        self.assertFalse(directories[0]["publicationApproved"])
        out=plan([src("dionisio","Dionisio","vinos",
                      diagnosis="REPEATED_INDEX_ONLY",observed=0)],
                 historical_evidence=data,today=date(2026,11,2))
        self.assertEqual(len(out["actions"][0]["directoryReviewCandidates"]),1)
        self.assertEqual(out["actions"][0]["historicalNetworkCandidates"][0]["targetId"],"acsba")
        self.assertEqual(out["confirmedReplacements"],0)
        self.assertEqual(out["circuitResilience"][0]["reportedDatedYieldSources7d"],0)

    def test_directory_expires_and_never_registers_source(self):
        data=[{"kind":"upcoming_directory","circuit":"vinos","date":"2026-11-13",
               "url":"https://example.org/map","dateEvidenceUrl":"https://example.org/date",
               "directoryScope":"AR_nationwide","localParticipantVerified":False}]
        self.assertEqual(discover_directory_review_leads(data,"vinos",date(2026,11,14)),[])
        self.assertEqual(discover_directory_review_leads(data,"yoga",date(2026,11,2)),[])
        self.assertEqual(plan([],historical_evidence=data,today=date(2026,11,2))["circuitResilience"],[])
        self.assertEqual(plan([],historical_evidence=data,today=date(2026,11,2))["confirmedReplacements"],0)

    def test_directory_rejects_unverified_urls_and_no_date_evidence(self):
        bad=[{"kind":"upcoming_directory","circuit":"vinos","date":"2026-11-13",
              "url":"https://unsafe.example@evil.invalid/","directoryScope":"AR_nationwide",
              "localParticipantVerified":False}]
        self.assertEqual(discover_directory_review_leads(bad,"vinos",date(2026,11,2)),[])
        bad[0]["url"]="http://bad.invalid"
        bad[0]["dateEvidenceUrl"]="https://example.org/d"
        self.assertEqual(discover_directory_review_leads(bad,"vinos",date(2026,11,2)),[])

    def test_local_organizer_does_not_localize_out_of_area_event(self):
        remote={"kind":"upcoming_original","circuit":"vinos","date":"2026-11-27",
                "url":"https://example.org/event","title":"Cata en Córdoba",
                "event":{"date":"2026-11-27","time":"19:00",
                         "venue":"Local de Córdoba","locality":"Cordoba"},
                "targets":[{"id":"local","name":"Organizador LP",
                            "locality":"La Plata"}]}
        self.assertFalse(is_local_future_original(remote,date(2026,11,2)))
        remote_leads=reconstruct_historical_network([remote],"vinos",date(2026,11,2))
        self.assertFalse(remote_leads[0]["upcomingOriginals"])
        self.assertFalse(remote_leads[0]["historicalProofUrls"])
        result=plan([],historical_evidence=[remote],today=date(2026,11,2))
        self.assertEqual(result["circuitResilience"],[])
        self.assertEqual(result["confirmedReplacements"],0)

    def test_official_gorina_original_verified_and_eligible_as_research_hint(self):
        records=json.loads((pathlib.Path(__file__).resolve().parents[1]/
                           "data/historical-circuit-network-v1.json").read_text())["evidence"]
        original=next(x for x in records if x.get("kind")=="upcoming_original"
                      and x.get("date")=="2026-11-27")
        self.assertEqual(original["event"]["locality"],"Gorina")
        self.assertTrue(is_local_future_original(original,date(2026,11,2)))
        self.assertFalse(is_local_future_original(original,date(2026,12,1)))
        missing_locality=json.loads(json.dumps(original))
        del missing_locality["event"]["locality"]
        self.assertFalse(is_local_future_original(missing_locality,date(2026,11,2)))

if __name__=="__main__":unittest.main()
