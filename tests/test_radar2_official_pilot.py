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
        self.assertEqual(outcome["status"], "QUERIED_NO_NEW")

    def test_no_due_accounts_is_not_reported_as_no_news(self):
        fake=SimpleNamespace(docs={},proposals={})
        creds={"META_IG_USER_ID":"test","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover") as discover:
            report=acquire(fake,set(),include_controls=False)
        self.assertEqual(report["status"],"NOT_DUE")
        self.assertEqual(report["accounts_eligible"],0)
        self.assertEqual(report["queries_sent"],0)
        discover.assert_not_called()

    def test_mixed_api_failure_does_not_look_like_no_news(self):
        fake=SimpleNamespace(docs={},proposals={})
        creds={"META_IG_USER_ID":"test","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        responses=iter([
            {"status":"NO_MEDIA_RETURNED","posts":[],"checked_at":"2026-11-08T14:00:00Z"},
            {"status":"OFFICIAL_API_ERROR","http_status":403,"meta_error_code":10,"posts":[]},
            {"status":"NO_MEDIA_RETURNED","posts":[]},
            {"status":"NO_MEDIA_RETURNED","posts":[]}
        ])
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",side_effect=lambda _:next(responses)):
            report=acquire(fake,set())
        self.assertEqual(report["status"],"PARTIAL_OFFICIAL_API_ERRORS")
        self.assertEqual(report["accounts_successful"],3)
        self.assertEqual(report["accounts_failed"],1)
        self.assertEqual([r["operational_status"] for r in report["results"]],
                         ["QUERIED_NO_NEW","QUERY_FAILED","QUERIED_NO_NEW","QUERIED_NO_NEW"])
        self.assertEqual(report["queries_sent"],4)
        self.assertEqual(report["last_successful_query_at"],"2026-11-08T14:00:00Z")

    def test_http_receipt_distinguishes_empty_media_from_missing_media(self):
        from instagram import discover
        creds = {"META_IG_USER_ID":"id","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        for body, status in [({"business_discovery":{"media":{"data":[]}}}, "NO_MEDIA_RETURNED"),
                             ({}, "OFFICIAL_API_ERROR"), ({"business_discovery":{"media":{"data":[None]}}}, "OFFICIAL_API_ERROR")]:
            with self.subTest(body=body):
                response = io.BytesIO(json.dumps(body).encode())
                response.status = 200
                with patch.dict(os.environ,creds), patch("instagram.urlopen",return_value=response):
                    result = discover("example")
                self.assertEqual((result["http_status"],result["status"]), (200,status))

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
        self.assertEqual(report["queries_sent"],19)
        self.assertEqual(len(report["rotating_accounts"]),15)
        self.assertEqual(len(set(report["accounts"])),19)
        self.assertEqual(discover.call_count,19)

    def test_rotating_accounts_never_exceed_twenty(self):
        fake=SimpleNamespace(docs={},proposals={})
        creds={"META_IG_USER_ID":"test","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        candidates=["venue_"+str(i) for i in range(30)]
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",
            return_value={"status":"NO_MEDIA_RETURNED","posts":[]}) as discover:
            report=acquire(fake,set(),candidates,include_controls=False)
        self.assertEqual(report["queries_sent"],20)
        self.assertEqual(len(report["rotating_accounts"]),20)
        self.assertEqual(len(report["unattempted_accounts"]),0)
        self.assertEqual(discover.call_count,20)

    def test_controls_share_absolute_twenty_request_budget(self):
        fake=SimpleNamespace(docs={},proposals={})
        creds={"META_IG_USER_ID":"test","META_ACCESS_TOKEN":"dummy","META_GRAPH_VERSION":"v27.0"}
        candidates=["venue_"+str(i) for i in range(30)]
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",
            return_value={"status":"NO_MEDIA_RETURNED","posts":[]}) as discover:
            report=acquire(fake,set(),candidates,include_controls=True,
                           extra_curators=["extra_curator"])
        self.assertEqual(report["queries_sent"],20)
        self.assertEqual(len(report["controls"]),4)
        self.assertEqual(len(report["rotating_accounts"]),16)
        self.assertEqual(report["extra_curators"],[])
        self.assertEqual(discover.call_count,20)

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

    def test_new_documents_are_split_by_publication_age_not_ingest_time(self):
        class FakeCollector:
            def __init__(self):
                self.docs={}
                self.proposals={}
            def add(self,d,title,**kwargs):
                self.proposals[d["url"]]={"title":title,**kwargs}
                return d["url"]
        fake=FakeCollector()
        creds={"META_IG_USER_ID":"id", "META_ACCESS_TOKEN":"mock", "META_GRAPH_VERSION":"v27.0"}
        posts=[
            {"permalink":"https://www.instagram.com/p/RECENT1/",
             "caption":"Teatro del viernes", "timestamp":"2026-11-07T19:00:00+0000"},
            {"permalink":"https://www.instagram.com/p/OLD2019/",
             "caption":"Concierto del año anterior", "timestamp":"2019-11-07T19:00:00+0000"},
            {"permalink":"https://www.instagram.com/p/NODATE1/",
             "caption":"Música sin sello temporal"},
            {"permalink":"https://www.instagram.com/p/KNOWN001/",
             "caption":"Festival viejo", "timestamp":"2018-11-07T19:00:00+0000"}
        ]
        with patch.dict(os.environ,creds,clear=True),patch(
            "instagram_official_pilot.discover",return_value={
                "status":"MEDIA_RETURNED","checked_at":"2026-11-08T20:39:37Z","posts":posts
            }):
            report=acquire(fake,{"https://www.instagram.com/p/KNOWN001/"},
                           rotating_accounts=["venue_test"],include_controls=False)
        self.assertEqual(report["status"],"POSTS_ACQUIRED")
        self.assertEqual(report["new_documents"],3)
        self.assertEqual(report["new_recent_documents_7d"],1)
        self.assertEqual(report["new_backfill_documents_older_7d"],1)
        self.assertEqual(report["new_documents_date_unknown"],1)
        self.assertEqual(sum(report[k] for k in (
            "new_recent_documents_7d","new_backfill_documents_older_7d",
            "new_documents_date_unknown")),report["new_documents"])
        self.assertEqual(report["results"][0]["known_documents"],1)
        self.assertEqual(len(fake.docs),4)
        self.assertTrue(all(not p.get("publication_approved",False) for p in fake.proposals.values()))

    def test_age_bucket_is_fail_closed_for_invalid_and_future_dates(self):
        from instagram_official_pilot import publication_age_bucket
        at="2026-11-08T20:39:37Z"
        self.assertEqual(publication_age_bucket("2026-11-08T19:00:00+0000",at),"recent_7d")
        self.assertEqual(publication_age_bucket("2026-10-01T19:00:00+0000",at),"backfill_older_7d")
        self.assertEqual(publication_age_bucket("2026-11-14T19:00:00+0000",at),"unknown")
        self.assertEqual(publication_age_bucket(None,at),"unknown")
        self.assertEqual(publication_age_bucket("not a timestamp",at),"unknown")

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
