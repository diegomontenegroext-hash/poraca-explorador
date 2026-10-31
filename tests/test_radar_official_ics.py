"""Regression: primary iCalendar schedule reaches staging, never public canon.

Run: python -m unittest discover -s tests -p 'test_radar_official_ics.py' -v
"""
import pathlib
import sys
import unittest
from unittest.mock import patch
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from radar_ical_agenda import FEED_URL, calendar_sessions
import radar_agenda_adapters as adapters
import radar_definitivo as radar
import radar_parallel as net

def item(uid, title, location, when, proof, extra=""):
    return (f"BEGIN:VEVENT\nUID:{uid}@festival.freezer.com.ar\n"
            f"SUMMARY:Freezer · {title}\n"
            f"LOCATION:{location}\n"
            f"{when}\nURL:{proof}\n{extra}END:VEVENT\n")

def feed(*items):
    return "BEGIN:VCALENDAR\nVERSION:2.0\n" + "".join(items) + "END:VCALENDAR"

DAY5 = "https://festival.freezer.com.ar/2026/programacion/#jueves-5"
DAY11 = "https://festival.freezer.com.ar/2026/programacion/#miercoles-11"

class OfficialICalendarTests(unittest.TestCase):
    def test_utc_conversion_and_two_distinct_events_same_day(self):
        raw=feed(
            item("id1","Inauguración de Exposiciones","Pasaje Dardo Rocha",
                 "DTSTART:20261105T200000Z",DAY5),
            item("id2","Brindis de Inauguración Freezer Festival 2026",
                 "Ciudad de gatos","DTSTART:20261105T233000Z",DAY5))
        rows=calendar_sessions(raw,FEED_URL)
        self.assertEqual(len(rows),2)
        self.assertEqual([(x[1],x[2]) for x in rows],
                         [(date(2026,11,5),"17:00"),(date(2026,11,5),"20:30")])
        self.assertEqual(rows[1][3],"Ciudad de gatos")
        self.assertEqual(rows[0][4],DAY5)

    def test_unknown_hour_is_not_midnight(self):
        raw=feed(item("id3","Pre-Inauguración CDA",
                      r"Centro de Arte\, 48 entre 6 y 7",
                      "DTSTART;VALUE=DATE:20261111",DAY11))
        rows=calendar_sessions(raw,FEED_URL)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1],date(2026,11,11))
        self.assertIsNone(rows[0][2])
        self.assertEqual(rows[0][3],"Centro de Arte, 48 entre 6 y 7")

    def test_folded_ical_lines_unfolded(self):
        raw=feed(item("id4","Brindis en Ciu\r\n dad de gatos",
                      "Ciudad de gatos","DTSTART:20261105T233000Z",DAY5))
        rows=calendar_sessions(raw,FEED_URL)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],"Freezer · Brindis en Ciudad de gatos")

    def test_dedupe_exact_event_only(self):
        one=item("id1","Inauguración de Exposiciones","Pasaje Dardo Rocha",
                 "DTSTART:20261105T200000Z",DAY5)
        self.assertEqual(len(calendar_sessions(feed(one,one),FEED_URL)),1)

    def test_bad_anchor_invalid_host_wrong_weekday_and_missing_room_fail_closed(self):
        good=item("id1","Inauguración","Pasaje Dardo Rocha",
                  "DTSTART:20261105T200000Z",DAY5)
        wrongday=item("id2","Inauguración","Pasaje Dardo Rocha",
                      "DTSTART:20261105T200000Z",DAY11)
        no_location=item("id3","Inauguración","",
                         "DTSTART:20261105T200000Z",DAY5)
        bad_uid=good.replace("id1@festival.freezer.com.ar","id1@other.org")
        self.assertEqual(len(calendar_sessions(feed(good,wrongday,no_location,bad_uid),FEED_URL)),1)
        self.assertEqual(calendar_sessions(feed(good),"https://other.org/schedule.ics"),[])
        self.assertEqual(calendar_sessions(feed(good).replace("END:VCALENDAR",""),FEED_URL),[])

    def test_existing_adapter_preserves_stage_only_and_proof(self):
        raw=feed(item("id1","Brindis de Inauguración","Ciudad de gatos",
                      "DTSTART:20261105T233000Z",DAY5),
                 item("id3","Pre-Inauguración CDA","Centro de Arte UNLP",
                      "DTSTART;VALUE=DATE:20261111",DAY11))
        with patch.object(adapters,"active_date",return_value=True):
            rows=adapters.extract_listings(raw,FEED_URL)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["event_time"],"20:30")
        self.assertIsNone(rows[1]["event_time"])
        self.assertEqual(rows[0]["proof_url"],DAY5)
        self.assertEqual(rows[0]["evidence_tier"],"primary_program_ics")
        self.assertEqual(rows[0]["method"],"official_ics_explicit_session")
        self.assertEqual(rows[0]["review_state"],"observed_unverified")
        self.assertEqual(adapters.extract_listings(raw,"https://evil.org/events"),[])

    def test_existing_radar_scan_processes_feed_without_other_requests(self):
        body=feed(item("id1","Brindis de Inauguración","Ciudad de gatos",
                       "DTSTART:20261105T233000Z",DAY5))
        class Budget:
            def request(self,url):
                self.requests.append(url)
                return 200,body,None
            def __init__(self):self.requests=[]
            def can_fetch(self,url):return False
        source=dict(source_id="rd-official-freezer-2026",url=FEED_URL,
                    source_role="original_festival_program",seed_urls=[])
        budget=Budget()
        with patch.object(adapters,"active_date",return_value=True):
            check,candidates=radar.scan_source(source,budget,"incremental")
        self.assertEqual(budget.requests,[FEED_URL])
        self.assertEqual(len(check["_listings"]),1)
        self.assertEqual(check["status"],"ok")
        self.assertEqual(candidates,[])

    def test_fetch_allows_pinned_calendar_but_not_other_non_html(self):
        body=feed(item("id1","Brindis de Inauguración","Ciudad de gatos",
                       "DTSTART:20261105T233000Z",DAY5)).encode("utf-8")
        class Fake:
            status=200
            headers={"Content-Type":"text/calendar; charset=utf-8"}
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return body[:n]
        def get(request,timeout):
            return Fake()
        with patch.object(net,"urlopen",side_effect=get):
            status,raw,error=net.fetch(FEED_URL)
            self.assertEqual((status,error),(200,None))
            self.assertTrue(raw.startswith("BEGIN:VCALENDAR"))
            status,raw,error=net.fetch("https://not-pinned.example/calendar.ics")
            self.assertEqual((status,raw,error),(200,None,"NON_HTML"))

if __name__=="__main__":
    unittest.main()
