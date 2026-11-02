import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from radar_circuit_recovery import reconstruct,inspect_packs

PACK=json.loads((ROOT/"data/circuit-recovery/vinos-20261102.json").read_text(encoding="utf-8"))

class HistoricalNetworkTests(unittest.TestCase):
    def test_dionisio_archive_generates_candidates_not_replacements(self):
        x=reconstruct(PACK,"2026-11-02")
        self.assertEqual(x["historicRecordsExamined"],7)
        self.assertEqual(x["historicalActorCandidates"],10)
        self.assertEqual(x["futureOriginalsFound"],1)
        self.assertEqual(x["verifiedReplacementSources"],0)
        self.assertEqual(x["sourceWrites"],0)
        self.assertEqual(x["eventWrites"],0)
        self.assertFalse(x["publicationApproved"])
        gold=next(a for a in x["actorCandidates"] if a["id"]=="golden-wine")
        self.assertEqual(gold["historicalEvidence"][0]["relation"],"coorganizer")
        self.assertIsNone(gold["sourceUrl"])
        self.assertFalse(gold["sourceRegistered"])
        self.assertEqual(x["currentIndependentLeads"][0]["relationToSeed"],
                         "SAME_CIRCUIT_NOT_ESTABLISHED_ORGANIZER_RELATION")

    def test_future_must_be_real_dated_post_not_recurring_assumption(self):
        for key,value in (("date","2026-10-27"),("time",""),("venue",None),
                          ("evidenceUrl","http://example.com/"),("organizerId","invisible")):
            pack=json.loads(json.dumps(PACK))
            pack["future"][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                reconstruct(pack,"2026-11-02")
        with self.assertRaises(ValueError):
            reconstruct(PACK,"2026-12-01")

    def test_old_events_never_become_new_events(self):
        pack=json.loads(json.dumps(PACK))
        pack["historical"][0]["date"]="2026-11-15"
        with self.assertRaises(ValueError):
            reconstruct(pack,"2026-11-02")
        self.assertTrue(all(a["historicalDate"]<"2026-11-02"
            for c in reconstruct(PACK,"2026-11-02")["actorCandidates"]
            for a in c["historicalEvidence"]))

    def test_missing_or_untrusted_url_does_not_make_a_fake_source(self):
        pack=json.loads(json.dumps(PACK))
        pack["actors"][1]["sourceUrl"]="https://127.0.0.1/private"
        with self.assertRaises(ValueError):
            reconstruct(pack,"2026-11-02")
        self.assertEqual(PACK["actors"][1]["sourceUrl"],None)

    def test_integrates_only_for_unproductive_same_circuit(self):
        seed={"sourceId":"rd-web-56c74fce","circuit":"vinos",
              "diagnosis":"REPEATED_INDEX_ONLY"}
        directory=ROOT/"data/circuit-recovery"
        found=inspect_packs([seed],"2026-11-02",directory)
        self.assertEqual(found["coveredSeeds"],1)
        self.assertEqual(found["autoRegistered"],0)
        self.assertEqual(found["autoPublished"],0)
        for diagnosis in ("DATED_SESSIONS_OBSERVED","INSUFFICIENT_SIGNAL"):
            self.assertEqual(inspect_packs([{**seed,"diagnosis":diagnosis}],
                "2026-11-02",directory)["coveredSeeds"],0)
        self.assertEqual(inspect_packs([{**seed,"circuit":"teatro"}],
            "2026-11-02",directory)["coveredSeeds"],0)

if __name__=="__main__":
    unittest.main()
