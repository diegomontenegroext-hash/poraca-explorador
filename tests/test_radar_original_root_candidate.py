import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_original_root_candidate import root_review_candidate


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
        x=root_review_candidate(self.src("first_party_organizer"),
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
        for role in ("original_cycle","first_party_organizer"):
            result=root_review_candidate(self.src(role),
                "https://cycle.example/",object(),200,mk)[0]
            self.assertIsNone(result["event_date"])
            self.assertFalse(result["evidence"]["auto_publish"])
    def test_07_origin_mismatch_not_a_new_proof(self):
        def wrong(url,source_id,label,page,status):
            a=mk(url,source_id,label,page,status)
            a["original_url"]="https://different.example/"
            return a
        self.assertEqual(root_review_candidate(self.src("original_ticketing"),
            "https://site.example/events",object(),200,wrong),[])

if __name__=="__main__": unittest.main()
