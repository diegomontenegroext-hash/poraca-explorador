"""Generic ICS without URL heuristics, fabricated recurrences or approvals."""
import pathlib
import sys
import unittest
from datetime import date,timedelta

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from radar_ical_generic import (
    calendar_sessions,discover_calendar_links,is_calendar_url)
from radar_agenda_adapters import extract_listings
import radar_definitivo as radar


def feed(*items):
    return "BEGIN:VCALENDAR\nVERSION:2.0\n"+"".join(items)+"END:VCALENDAR"


def event(uid,day,when="21:00",title="Encuentro en club",extra="",
          venue="Club local",proof=None):
    start=("DTSTART;VALUE=DATE:"+day.replace("-","") if when is None else
           "DTSTART;TZID=America/Argentina/Buenos_Aires:"+
           day.replace("-","")+"T"+when.replace(":","")+"00")
    origin=("URL:"+proof+"\n") if proof else ""
    return ("BEGIN:VEVENT\nUID:"+uid+"\nSUMMARY:"+title+"\n"+
            start+"\nLOCATION:"+venue+"\n"+origin+extra+"END:VEVENT\n")


class GenericIcalTests(unittest.TestCase):
    def setUp(self):
        self.today=(date.today()+timedelta(days=8)).isoformat()
        self.origin="https://club-de-barrio.example/"
        self.ics=self.origin+"agenda.ics"

    def test_01_unknown_calendar_is_explicitly_unverified(self):
        raw=feed(event("id-1",self.today))
        sessions=extract_listings(raw,self.ics)
        self.assertEqual(len(sessions),1)
        self.assertEqual(sessions[0]["event_time"],"21:00")
        self.assertEqual(sessions[0]["venue"],"Club local")
        self.assertEqual(sessions[0]["evidence_tier"],"structured_origin_unverified")
        self.assertEqual(sessions[0]["review_state"],"observed_unverified")
        self.assertEqual(sessions[0]["proof_url"],self.ics)

    def test_02_two_times_are_distinct_and_replay_idempotent(self):
        raw=feed(event("id1",self.today,"18:00"),
                 event("id2",self.today,"21:00"))
        a=extract_listings(raw,self.ics)
        b=extract_listings(raw,self.ics)
        self.assertEqual(len(a),2)
        self.assertEqual(a,b)
        self.assertEqual({r["event_time"] for r in a},{"18:00","21:00"})

    def test_03_cancelled_and_recurring_entries_not_invented(self):
        raw=feed(event("cancel",self.today,extra="STATUS:CANCELLED\n"),
                 event("recur",self.today,extra="RRULE:FREQ=WEEKLY;COUNT=8\n"))
        self.assertEqual(extract_listings(raw,self.ics),[])

    def test_04_no_timezone_means_no_guessed_clock(self):
        raw=feed("BEGIN:VEVENT\nUID:tz-free\nSUMMARY:Taller cultural\n"
                 "DTSTART:"+self.today.replace("-","")+"T190000\nEND:VEVENT\n")
        got=extract_listings(raw,self.ics)
        self.assertEqual(len(got),1)
        self.assertIsNone(got[0]["event_time"])

    def test_05_no_venue_does_not_fabricate_location(self):
        raw=feed(event("unknown-venue",self.today,venue="Dirección por inbox"))
        got=extract_listings(raw,self.ics)
        self.assertEqual(len(got),1)
        self.assertIsNone(got[0]["venue"])

    def test_06_external_proof_must_not_claim_to_be_original(self):
        raw=feed(event("external",self.today,proof="https://third-party.example/event/2"))
        got=extract_listings(raw,self.ics)
        self.assertEqual(got[0]["proof_url"],self.ics)

    def test_06b_malformed_event_url_does_not_crash_the_source(self):
        raw=feed(event("invalid",self.today,proof="https://host.example:bad/venue"))
        got=extract_listings(raw,self.ics)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["proof_url"],self.ics)

    def test_07_ics_must_be_real_same_host_html_link(self):
        html=radar.parse_html(
            '<a href="/agenda.ics">Calendario</a>'
            '<a href="https://outside.example/agenda.ics">Externo</a>'
            '<a href="/otro.ical">Otras sesiones</a>'
            '<a href="/agenda.ics">repetido</a>'
            '<a href="/informe.pdf">informe</a>')
        self.assertEqual(discover_calendar_links(self.origin,html.links),[
            (self.ics,"adaptive_calendar_feed"),
            (self.origin+"otro.ical","adaptive_calendar_feed")])

    def test_08_url_validation_blocks_query_and_insecure(self):
        for link in ("http://site.example/a.ics",
                     "https://site.example/a.ics?auth=secret",
                     "https://site.example/a.ics#fragment",
                     "https://site.example:8080/a.ics",
                     "https://user@site.example/a.ics"):
            self.assertFalse(is_calendar_url(link))
        self.assertTrue(is_calendar_url(self.ics))

    def test_09_broken_ics_never_becomes_event(self):
        bad="BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Sin fecha\nEND:VEVENT\n"
        self.assertEqual(calendar_sessions(bad,self.ics),[])
        self.assertEqual(calendar_sessions(bad+"END:VCALENDAR",self.ics),[])

    def test_10_existing_homepage_can_recover_calendar_with_one_detail(self):
        raw=feed(event("test",self.today))
        pages={self.origin:(200,'<a href="/agenda.ics">Calendario</a>',None),
               self.ics:(200,raw,None)}
        class Budget:
            def __init__(self):self.requested=[]
            def request(self,url):
                self.requested.append(url)
                return pages[url]
            def can_fetch(self,url):return url in pages
            def remaining(self):return 100
        budget=Budget()
        check,candidates=radar.scan_source(
            {"source_id":"new-club","url":self.origin},budget,"full")
        self.assertEqual(budget.requested,[self.origin,self.ics])
        self.assertEqual(len(check["_listings"]),1)
        self.assertEqual(check["details_opened"],1)
        self.assertEqual(candidates,[])
        self.assertEqual(check["status"],"ok")

    def test_11_unproductive_calendar_is_index_only(self):
        pages={self.origin:(200,'<a href="/agenda.ics">Agenda</a>',None),
               self.ics:(200,feed(),None)}
        class Budget:
            def request(self,url):return pages[url]
            def can_fetch(self,url):return url in pages
            def remaining(self):return 100
        check,candidates=radar.scan_source(
            {"source_id":"new","url":self.origin},Budget(),"full")
        self.assertEqual(check["status"],"index_only")
        self.assertEqual(check["_listings"],[])
        self.assertEqual(candidates,[])


if __name__=="__main__":
    unittest.main()
