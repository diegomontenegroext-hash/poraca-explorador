"""Pure and negative tests for controlled automatic publication. No Neon writes."""
import copy
from datetime import datetime,date,timezone
import unittest
from src.radar_controlled_publication_shadow import evaluate,POLICY

NOW=datetime(2026,11,3,20,0,tzinfo=timezone.utc)
TODAY=date(2026,11,3)

def sample():
    return {
      "event":{"program":"Noche de bandas — Pura Vida","program_day":"2026-11-07",
               "venue":"Pura Vida","location_in_scope":True,"status":"scheduled",
               "lineup":["Banda A","Banda B","Banda C","Banda D"],"time":None},
      "original":{"url":"https://example.org/programacion/noche-de-bandas-07",
                  "exact_announcement":True,"primary_source":True,
                  "supports":["title","date","venue"],"day_matches":True,
                  "program_matches":True,"venue_matches":True,
                  "checked_at":"2026-11-03T19:00:00+00:00"},
      "source":{"enabled":True,"registered":True,"role":"original_venue"},
      "identity":{"approved_venue_matches":1,"approved_venue_id":"pura-vida"},
      "integrity":{"canonical_same_event_count":0,"collision_check_complete":True,
                   "different_event_same_url_day":False,"multiple_distinct_sessions":False}
    }
def outcome(obj):return evaluate(obj,today=TODAY,now=NOW)

class GateTests(unittest.TestCase):
    def test_happy_without_time_and_four_bands_as_one_program(self):
        r=outcome(sample())
        self.assertEqual(r["decision"],"AUTO_ELIGIBLE_SHADOW")
        self.assertFalse(r["writeAuthorized"])
        self.assertFalse(r["publicationApproved"])
        self.assertIsNone(r["suggestedTime"])
    def test_original_hour_not_required_or_invented(self):
        v=sample();v["event"]["time"]="20:00"
        self.assertIsNone(outcome(v)["suggestedTime"])
        v["event"]["time_kind"]="original_verified"
        self.assertEqual(outcome(v)["suggestedTime"],"20:00")
    def test_dedup_existing_same_event_does_not_create(self):
        v=sample();v["integrity"]["canonical_same_event_count"]=1
        v["integrity"]["same_identity_original_confirmed"]=True
        self.assertEqual(outcome(v)["decision"],"LINK_EXISTING_SHADOW")
    def test_existing_conflicts_are_not_rewritten(self):
        v=sample();v["integrity"]["canonical_same_event_count"]=1
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_two_real_sessions_need_review(self):
        v=sample();v["integrity"]["multiple_distinct_sessions"]=True
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_same_url_other_event_protects_lineup(self):
        v=sample();v["integrity"]["different_event_same_url_day"]=True
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_prior_hold_conflict_never_lifts(self):
        v=sample();v["integrity"]["prior_hold"]=True
        self.assertEqual(outcome(v)["decision"],"REVIEW")
        v=sample();v["integrity"]["source_date_conflict"]=True
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_cancelled_and_accessory_are_discarded(self):
        v=sample();v["event"]["status"]="cancelled"
        self.assertEqual(outcome(v)["decision"],"DISCARD")
        v=sample();v["original"]["accessory_ticket"]=True
        self.assertEqual(outcome(v)["decision"],"DISCARD")
    def test_missing_individual_source_and_host_only_skipped(self):
        v=sample();v["original"]["url"]="https://example.org/"
        self.assertEqual(outcome(v)["decision"],"SKIP")
        v=sample();v["original"]["exact_announcement"]=False
        self.assertEqual(outcome(v)["decision"],"SKIP")
    def test_secondary_source_and_disabled_source_skips_not_queue(self):
        v=sample();v["source"]["role"]="secondary_agenda"
        self.assertEqual(outcome(v)["decision"],"SKIP")
        v=sample();v["source"]["enabled"]=False
        self.assertEqual(outcome(v)["decision"],"SKIP")
    def test_venue_identity_missing_skips_while_ambiguous_reviews(self):
        v=sample();v["identity"]["approved_venue_matches"]=0
        self.assertEqual(outcome(v)["decision"],"SKIP")
        v=sample();v["identity"]["approved_venue_matches"]=2
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_missing_original_supported_day_never_autopublishes(self):
        v=sample();v["original"]["supports"]=["title","venue"]
        self.assertEqual(outcome(v)["decision"],"SKIP")
        v=sample();v["original"]["day_matches"]=False
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_date_ambiguous_or_out_of_scope(self):
        v=sample();v["event"]["program_day"]="2026-11-20";v["integrity"]["source_date_conflict"]=True
        self.assertEqual(outcome(v)["decision"],"REVIEW")
        v=sample();v["event"]["location_in_scope"]=False
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_stale_evidence_skips_this_pass(self):
        v=sample();v["original"]["checked_at"]="2026-10-01T09:00:00Z"
        self.assertEqual(outcome(v)["decision"],"SKIP")
    def test_no_collision_check_no_autopublication(self):
        v=sample();v["integrity"]["collision_check_complete"]=False
        self.assertEqual(outcome(v)["decision"],"REVIEW")
    def test_one_uncertain_item_cannot_block_other_clear_events(self):
        safe=sample();uncertain=sample()
        uncertain["original"]["exact_announcement"]=False
        outcomes=[outcome(c) for c in [uncertain,safe]]
        self.assertEqual([o["decision"] for o in outcomes],
                         ["SKIP","AUTO_ELIGIBLE_SHADOW"])
        self.assertTrue(all(o["written"]==False for o in outcomes) if all("written" in o for o in outcomes) else
                        all(o["writeAuthorized"] is False for o in outcomes))
    def test_fail_closed_even_if_config_toggled(self):
        p=copy.deepcopy(POLICY);p["productionEnabled"]=True
        with self.assertRaises(ValueError):
            evaluate(sample(),today=TODAY,now=NOW,policy=p)
    def test_instagram_account_is_not_specific_event(self):
        v=sample();v["original"]["url"]="https://www.instagram.com/puravidalaplata2008/"
        self.assertEqual(outcome(v)["decision"],"REVIEW")
        v["original"]["url"]="https://www.instagram.com/p/ABC12345/"
        self.assertEqual(outcome(v)["decision"],"AUTO_ELIGIBLE_SHADOW")

if __name__=="__main__":unittest.main()
