"""Offline guardrails for four-account Meta pilot; never contacts Instagram."""
import io
import json
import os
import sys
import unittest
from urllib.error import HTTPError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "radar2"))
from instagram_official_pilot import ACCOUNTS, acquire


class OfficialInstagramPilot(unittest.TestCase):
    def test_unconfigured_is_no_network_and_not_a_success(self):
        fake = SimpleNamespace(docs={}, proposals={})
        with patch.dict(os.environ, {}, clear=True), patch(
            "instagram_official_pilot.discover"
        ) as discover:
            outcome = acquire(fake, set())
        self.assertEqual(outcome["status"], "NOT_CONFIGURED")
        self.assertEqual(outcome["queries_sent"], 0)
        self.assertEqual(outcome["new_documents"], 0)
        self.assertEqual(len(outcome["accounts"]), 4)
        self.assertIn("teatroargentinopba", outcome["accounts"])
        discover.assert_not_called()

    def test_configured_limits_to_four_official_requests(self):
        fake = SimpleNamespace(docs={}, proposals={})
        creds = {"META_IG_USER_ID":"test_id", "META_ACCESS_TOKEN":"fake_token",
                 "META_GRAPH_VERSION":"vX"}
        with patch.dict(os.environ, creds, clear=True), patch(
            "instagram_official_pilot.discover",
            return_value={"status":"NO_MEDIA_RETURNED","posts":[]}
        ) as discover:
            outcome = acquire(fake, set())
        self.assertEqual(outcome["queries_sent"], 4)
        self.assertEqual(discover.call_count, 4)
        self.assertEqual([c.args[0] for c in discover.call_args_list], list(ACCOUNTS))
        self.assertEqual(outcome["new_documents"], 0)
        self.assertEqual(outcome["status"], "NO_NEW_POSTS_OR_UNAVAILABLE")

    def test_meta_http_error_records_only_safe_codes(self):
        from instagram import discover
        creds = {"META_IG_USER_ID":"test_id","META_ACCESS_TOKEN":"very_secret_token",
                 "META_GRAPH_VERSION":"v27.0"}
        body = b'{"error":{"type":"OAuthException","code":190,"error_subcode":463,"message":"sensitive"}}'
        err = HTTPError("https://graph.facebook.com/v27.0/test_id",400,"Bad Request",{},io.BytesIO(body))
        with patch.dict(os.environ,creds,clear=True),patch("instagram.urlopen",side_effect=err):
            result = discover("teatroargentinopba")
        self.assertEqual(result["http_status"],400)
        self.assertEqual(result["meta_error_code"],190)
        self.assertEqual(result["meta_error_subcode"],463)
        serialized = json.dumps(result)
        self.assertNotIn("very_secret_token",serialized)
        self.assertNotIn("sensitive",serialized)

    def test_expired_token_is_not_a_quiet_day(self):
        fake = SimpleNamespace(docs={}, proposals={})
        creds = {"META_IG_USER_ID":"test_id", "META_ACCESS_TOKEN":"expired",
                 "META_GRAPH_VERSION":"v27.0"}
        expired = {"status":"OFFICIAL_API_ERROR", "error_type":"HTTPError",
                   "http_status":401,"meta_error_code":190,"meta_error_subcode":463,
                   "posts":[]}
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",return_value=expired):
            outcome=acquire(fake,set())
        self.assertEqual(outcome["status"],"META_TOKEN_EXPIRED")
        self.assertEqual(outcome["queries_sent"],1)

    def test_extra_accounts_rotate_without_duplicate_controls(self):
        fake=SimpleNamespace(docs={},proposals={})
        creds={"META_IG_USER_ID":"test","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        candidates=["teatroargentinopba"]+["venue_"+str(i) for i in range(15)]
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",
            return_value={"status":"NO_MEDIA_RETURNED","posts":[]}) as discover:
            report=acquire(fake,set(),candidates)
        self.assertEqual(report["queries_sent"],14)
        self.assertEqual(len(report["rotating_accounts"]),10)
        self.assertEqual(len(set(report["accounts"])),14)
        self.assertEqual(discover.call_count,14)

    def test_rate_limit_stops_remaining_requests(self):
        fake=SimpleNamespace(docs={},proposals={})
        creds={"META_IG_USER_ID":"test","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        response={"status":"OFFICIAL_API_ERROR","meta_error_code":80002,"http_status":429,"posts":[]}
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",return_value=response) as discover:
            report=acquire(fake,set(),["venue_test"])
        self.assertEqual(report["status"],"META_RATE_LIMITED")
        self.assertEqual(report["queries_sent"],1)
        self.assertEqual(len(report["unattempted_accounts"]),4)
        discover.assert_called_once()

    def test_official_post_becomes_investigable_not_canonical(self):
        class FakeCollector:
            def __init__(self):
                self.docs = {}
                self.proposals = {}
            def add(self,d,title,**kwargs):
                self.proposals["test"]={"id":"test","title":title,"state":kwargs.get("state")}
                return "test"
        fake=FakeCollector()
        creds={"META_IG_USER_ID":"test_id","META_ACCESS_TOKEN":"fake_token",
               "META_GRAPH_VERSION":"vX"}
        fixture={"status":"MEDIA_RETURNED","posts":[{
            "permalink":"https://www.instagram.com/p/EXAMPLE123/",
            "caption":"Teatro y música en La Plata",
            "timestamp":"2026-11-05T12:00:00+0000"}]}
        with patch.dict(os.environ,creds,clear=True), patch(
             "instagram_official_pilot.discover",return_value=fixture):
            outcome=acquire(fake,set())
        self.assertEqual(outcome["new_documents"],1)
        self.assertEqual(outcome["new_cultural_candidates"],1)
        self.assertEqual(fake.proposals["test"]["state"],"investigable")
        self.assertEqual(fake.docs["https://www.instagram.com/p/EXAMPLE123/"]["acquisition_method"],"official_meta_api")


if __name__=="__main__":
    unittest.main()
