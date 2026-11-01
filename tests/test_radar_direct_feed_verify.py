import pathlib
import sys
import unittest
from datetime import date, datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from radar_direct_feed_verify import (
    assess, collect_pages, safe_https, FEED_SQL, IDENTITY_SQL, OVERLAP_SQL, LAST_RUN_SQL
)


def fixture(*, category="artes", name="Feria de Fotografía",
            day="2026-11-02", url="https://programa.example/evento/123",
            rid="radar-"+"a"*32, time="19:30"):
    return (rid, name, day, time, "Pasaje Dardo Rocha", category,
            url, url, datetime(2026, 11, 1, 1, 1, tzinfo=timezone.utc),
            "Programa oficial")


RUN = ("definitivo-id", "full", "partial",
       datetime(2026, 10, 31, 23, 0, tzinfo=timezone.utc),
       datetime(2026, 10, 31, 23, 6, tzinfo=timezone.utc), 62, 29)


class DirectRadarReadContractTests(unittest.TestCase):
    def test_good_direct_read_stays_separate_from_http_and_approval(self):
        report = assess([fixture()], date(2026, 10, 31), 0, RUN)
        self.assertEqual(report["status"],
                         "DIRECT_RADAR_NEON_READ_PASS_API_HTTP_SEPARATE")
        self.assertEqual(report["visibleUnverified"], 1)
        self.assertFalse(report["autoPublished"])
        self.assertEqual(report["apiHttp"], "NOT_CHECKED")
        self.assertEqual(report["directResultsTouchedSinceLastRun"], 1)

    def test_original_https_required(self):
        self.assertFalse(safe_https("http://example.org"))
        self.assertFalse(safe_https("https://user:secret@example.org/event"))
        self.assertFalse(safe_https("https://example.org/space here"))
        self.assertTrue(safe_https("https://example.org/event?x=1"))

    def test_duplicate_fails_not_hidden_in_aggregation(self):
        report = assess([fixture(), fixture()], "2026-10-31", 0, RUN)
        self.assertIn("duplicate_identity", report["problems"])
        self.assertEqual(report["status"], "DIRECT_RADAR_NEON_READ_FAIL")

    def test_false_promotion_conflict_fails(self):
        report = assess([fixture()], "2026-10-31", 1, RUN)
        self.assertIn("already_in_canonical", report["problems"])

    def test_stale_or_invalid_time_fails(self):
        report = assess([fixture(day="2026-10-29", time="24:00")],
                        "2026-10-31", 0, RUN)
        self.assertIn("expired_or_bad_date", report["problems"])
        self.assertIn("bad_time", report["problems"])

    def test_zero_results_explicitly_blocks_certification(self):
        report = assess([], "2026-10-31", 0, RUN)
        self.assertEqual(report["status"], "DIRECT_RADAR_NEON_READ_FAIL")
        self.assertIn("no_radar_discoveries", report["problems"])

    def test_fully_traverses_60_100_200_without_truncation(self):
        for total in (60, 100, 200):
            records = [fixture(rid="radar-"+format(i, "032x"),
                               url=f"https://original.example/{i}",
                               name=f"Original {i}", day="2026-11-02") for i in range(total)]
            keys = [r[0] for r in records]
            def fetch(day, after_date, after_time, after_id):
                start = keys.index(after_id)+1 if after_id else 0
                return records[start:start+49]
            collected, pages = collect_pages(fetch, date(2026, 10, 31))
            self.assertEqual(len(collected), total)
            self.assertEqual(len(set(x[0] for x in collected)), total)
            self.assertGreaterEqual(pages, 2)
            self.assertEqual(assess(collected,"2026-10-31",0,RUN)["status"],
                             "DIRECT_RADAR_NEON_READ_PASS_API_HTTP_SEPARATE")

    def test_cursor_loop_refused(self):
        rows = [fixture(rid="radar-"+format(i, "032x"), name=f"Evento {i}")
                for i in range(49)]
        with self.assertRaisesRegex(ValueError, "RADAR_PAGE_CURSOR_LOOP"):
            collect_pages(lambda *_: rows, date(2026,10,31))

    def test_non_new_report_is_still_valid(self):
        old = list(fixture())
        old[8] = datetime(2026, 10, 30, tzinfo=timezone.utc)
        report = assess([tuple(old)], "2026-10-31", 0, RUN)
        self.assertEqual(report["directResultsTouchedSinceLastRun"], 0)
        self.assertEqual(report["status"],
                         "DIRECT_RADAR_NEON_READ_PASS_API_HTTP_SEPARATE")

    def test_readonly_sql_and_scoped_identity(self):
        self.assertIn("poraca_radar_direct_discoveries_v2", FEED_SQL)
        self.assertIn("SET LOCAL ROLE poraca_definitivo_scope",
                      pathlib.Path(__file__).parents[1].joinpath(
                          "src/radar_direct_feed_verify.py").read_text())
        for s in (FEED_SQL, OVERLAP_SQL, LAST_RUN_SQL, IDENTITY_SQL):
            for bad in ("INSERT INTO ", "DELETE FROM ", "TRUNCATE ", "DROP TABLE "):
                self.assertNotIn(bad, s.upper())


if __name__ == "__main__":
    unittest.main()
