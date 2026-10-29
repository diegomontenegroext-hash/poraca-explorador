import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import radar_function_gate_review as gate

class FunctionGateReviewTests(unittest.TestCase):
    def test_preflight_sql_is_select_only_and_room_safe(self):
        sql=gate.query()
        up=sql.upper()
        self.assertIn("OTHER_HOSTS_SAME_ORIGINAL",up)
        self.assertIn("SPECIFIC_ROOMS>1",up)
        self.assertIn("SOURCE_URL=ANY(G.DETAIL_URLS)",up)
        self.assertIn("OBSERVATION_BY_ORIGINAL",up)
        self.assertIn("CANONICAL_BY_ORIGINAL",up)
        self.assertIn("LEFT(P.EVENT_TIME,5)=LEFT(G.OBSERVED_TIME,5)",up)
        self.assertIn("AUTHORIZED_TO_WRITE",up)
        self.assertIn("FALSE AS AUTHORIZED_TO_WRITE",up)
        self.assertIn("HOLD_CONFLICTING_ROOMS",up)
        self.assertIn("HOLD_PUBLIC_OBSERVATION_ALREADY_EXISTS",up)
        self.assertNotIn("CREATE OR REPLACE VIEW",up)
        self.assertNotIn("INSERT INTO",up)
        self.assertNotIn("UPDATE PUBLIC.",up)
        self.assertNotIn("DELETE FROM",up)
    def test_xeito_one_candidate_play_six_distinct_sessions(self):
        def row(name,date,hour,host,status,details=1,rooms=1):
            data=[name,date,hour,"src-casa-metro-official",host,2,1,details,rooms,
                  ["sala-c"],["https://example.org/event"],["HOLD_MULTIPLE_EVIDENCE"],
                  0,0,0,0,0,0,status,False]
            return tuple(data)
        rows=[
          row("Xeito Novo","2026-12-12","21:00","casa-metro",
             "REVIEW_ONE_FUNCTION_PENDING_GATE_AUTHORIZATION"),
          row("Las del Lirio","2026-11-07","21:00","en-eso-estamos",
             "HOLD_CONFLICTING_HOST_FOR_ORIGINAL"),
          *[row("Play","2026-10-30",time,"teatro-argentino",
             "HOLD_CANONICAL_ALREADY_EXISTS") for time in ("19:30","20:30")]
        ]
        x=gate.summarize(rows)
        self.assertEqual(x["function_groups"],4)
        self.assertEqual(x["review_candidates"],1)
        self.assertEqual(x["by_decision"]["HOLD_CANONICAL_ALREADY_EXISTS"],2)
        self.assertEqual(x["by_decision"]["HOLD_CONFLICTING_HOST_FOR_ORIGINAL"],1)
        self.assertFalse(x["authorized_to_write"])
        self.assertEqual(gate.summarize([])["review_candidates"],0)
