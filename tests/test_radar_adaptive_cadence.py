import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from radar_adaptive_cadence import cadence_hours

class AdaptiveCadenceTests(unittest.TestCase):
    def test_one_empty_index_retries_quickly(self):
        self.assertEqual(cadence_hours(48,["index_only"],"index_only"),12)
    def test_two_empty_indexes_spread_incremental(self):
        self.assertEqual(cadence_hours(7,["index_only","index_only"],"index_only"),24)
    def test_four_empty_indexes_avoid_rechecking_every_incremental(self):
        self.assertEqual(cadence_hours(7,["index_only"]*4,"index_only"),72)
        self.assertEqual(cadence_hours(96,["index_only"]*4,"index_only"),96)
    def test_new_success_resets_streak(self):
        self.assertEqual(cadence_hours(7,["index_only","ok","index_only"],"index_only"),7)
        self.assertEqual(cadence_hours(7,["ok","index_only","index_only"],"ok"),7)
    def test_failure_backoff_is_preserved(self):
        self.assertEqual(cadence_hours(72,["failed"],"failed",1),2)
        self.assertEqual(cadence_hours(72,["failed"],"failed",7),32)
    def test_unvisited_source_defaults_to_existing_cadence(self):
        self.assertEqual(cadence_hours(24,[],"ok"),24)
    def test_pure_function_never_modifies_source(self):
        states=["index_only"]*5
        outcome=cadence_hours(7,states,"index_only")
        self.assertEqual(states,["index_only"]*5)
        self.assertEqual(outcome,72)

if __name__=="__main__":unittest.main()
