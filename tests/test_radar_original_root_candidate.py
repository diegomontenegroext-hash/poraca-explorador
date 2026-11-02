import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_original_root_candidate import root_review_candidate, suppress_unverified_cycle_root_sessions


def mk(url,source_id,label,page,http):
    return {"candidate_key":"key-"+source_id,
            "original_url":url,"kind":"event_detail",
            "title":"Org Event","summary":"source metadata",
            "event_date":"2026-11-27","event_time":"19:00",
            "venue":"Paseo Mitre","organizer":"Organizador",
            "evidence":{"structured_event_found":True,
                        "cultural_signals_v1":{"organizers":["Organizador"]}}}

class GenericOriginalIntakeTests(unittest.TestCase):
    def src(self, role):
        return {"source_id":"rd-web-test","source_role":role}
    def test_01_first_party_ticket_returns_single_unverified_existing_candidate(self):
        x=root_review_candidate(self.src("first_party_ticketing"),
          "https://ticket.example/eventos/feria",object(),200,mk)
        self.assertEqual(len(x),1)
        c=x[0]
        self.assertEqual(c["kind"],"event_detail")
        self.assertEqual(c["event_date"],"2026-11-27")
        self.assertEqual(c["event_time"],"19:00")
        self.assertFalse(c["evidence"]["auto_publish"])
        self.assertFalse(c["evidence"]["auto_accept"])
        self.assertEqual(c["evidence"]["admission"],
                         "UNVERIFIED_ORIGINAL_NEEDS_EDITORIAL_REVIEW")
    def test_02_cycle_is_not_an_individual_event_nor_unverified_venue(self):
        x=root_review_candidate(self.src("original_cycle"),
          "https://libros.example/",object(),200,mk)[0]
        self.assertEqual(x["kind"],"cultural_cycle_index")
        for k in ("event_date","event_time","venue","organizer"):
            self.assertIsNone(x[k])
        self.assertFalse(x["evidence"]["structured_event_found"])
        self.assertTrue(x["evidence"]["not_an_atomic_event"])
        self.assertNotIn("cultural_signals_v1",x["evidence"])
    def test_03_legacy_and_secondary_sources_are_unchanged(self):
        for role in ("secondary_agenda","institutional_program",
                     "ticketing_blocked","organizador",None):
            with self.subTest(role=role):
                self.assertEqual(root_review_candidate(self.src(role),
                  "https://site.example/a",object(),200,mk),[])
    def test_04_http_failure_is_never_materialized(self):
        for status in (None,204,301,403,429,500,503):
            self.assertEqual(root_review_candidate(self.src("original_ticketing"),
                "https://site.example/events",object(),status,mk),[])
        self.assertEqual(root_review_candidate(self.src("original_ticketing"),
            "https://site.example/events",None,200,mk),[])
    def test_05_reject_non_https_credentials_and_iparser(self):
        for url in ("http://site.example/a","https://bob:secret@site.example/a",
                    "https://","file:///etc/passwd",":oops"):
            self.assertEqual(root_review_candidate(self.src("original_ticketing"),
                url,object(),200,mk),[])
        self.assertEqual(root_review_candidate({"source_id":"",
                  "source_role":"first_party_ticketing"},
                  "https://site.example/a",object(),200,mk),[])
    def test_06_no_automatic_date_when_cycle_is_multi_venue(self):
        # Only an explicitly multi-venue cycle is a non-atomic root.
        # An organizer's own detail may be a genuine dated event (test_12).
        result=root_review_candidate(self.src("original_cycle"),
            "https://cycle.example/",object(),200,mk)[0]
        self.assertIsNone(result["event_date"])
        self.assertIsNone(result["event_time"])
        self.assertIsNone(result["venue"])
        self.assertTrue(result["evidence"]["not_an_atomic_event"])
        self.assertFalse(result["evidence"]["auto_publish"])
    def test_07_origin_mismatch_not_a_new_proof(self):
        def wrong(url,source_id,label,page,status):
            a=mk(url,source_id,label,page,status)
            a["original_url"]="https://different.example/"
            return a
        self.assertEqual(root_review_candidate(self.src("original_ticketing"),
            "https://site.example/events",object(),200,wrong),[])

    def test_08_multivenue_jsonld_root_not_staged_as_single_session(self):
        root="https://libros.example/"
        cycle=root_review_candidate(self.src("original_cycle"),root,object(),200,mk)
        listing={"title":"Noche de librerías","event_date":"2026-11-06",
                 "event_time":"18:00","venue":"Librerías Independientes",
                 "proof_url":root}
        self.assertEqual(suppress_unverified_cycle_root_sessions([listing],root,cycle),[])
        self.assertEqual(len(cycle),1)
        self.assertIsNone(cycle[0]["event_date"])

    def test_09_individual_detail_with_distinct_original_url_survives(self):
        root="https://bookfestival.example/"
        cycle=root_review_candidate(self.src("original_cycle"),root,object(),200,mk)
        child={"title":"Presentación de un libro","event_date":"2026-11-06",
               "event_time":"19:00","venue":"Librería propia",
               "proof_url":"https://bookfestival.example/programacion/taller-1"}
        self.assertEqual(suppress_unverified_cycle_root_sessions([child],root,cycle),[child])

    def test_10_non_cycle_never_suppresses_dated_original(self):
        root="https://tickets.example/events/feria"
        ticket=root_review_candidate(self.src("first_party_ticketing"),root,object(),200,mk)
        real={"title":"Feria Catar V","event_date":"2026-11-27",
              "event_time":"19:00","venue":"Paseo Mitre","proof_url":root}
        self.assertEqual(suppress_unverified_cycle_root_sessions([real],root,ticket),[real])
        self.assertEqual(suppress_unverified_cycle_root_sessions([real],root,[]),[real])

    def test_11_filter_is_pure_and_does_not_mutate_input(self):
        root="https://literature.example/"
        cycle=root_review_candidate(self.src("original_cycle"),root,object(),200,mk)
        records=[{"proof_url":root,"title":"cycle","event_date":"2026-11-06"},
                 {"proof_url":root+"/session","title":"individual","event_date":"2026-11-06"}]
        out=suppress_unverified_cycle_root_sessions(records,root,cycle)
        self.assertEqual(len(records),2)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["title"],"individual")

    def test_12_first_party_organizer_with_atomic_event_remains_dated(self):
        # An organizer can genuinely advertise one dated function on its root.
        # Only an explicit original_cycle role should drop root JSON-LD Event.
        root="https://organizer.example/"
        item=root_review_candidate(self.src("first_party_organizer"),root,object(),200,mk)
        self.assertEqual(item[0]["kind"],"event_detail")
        self.assertEqual(item[0]["event_date"],"2026-11-27")
        listed={"proof_url":root,"title":"Función puntual","event_date":"2026-11-27"}
        self.assertEqual(suppress_unverified_cycle_root_sessions([listed],root,item),[listed])

if __name__=="__main__": unittest.main()
