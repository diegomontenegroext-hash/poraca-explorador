"""Pruebas reproducibles de certificación: simulaciones sin red ni Neon."""
import pathlib
import sys
import unittest
from datetime import date,timedelta

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"src"))
import radar_definitivo as rd
from radar_agenda_adapters import extract_listings
from radar_adaptive_discovery import discover_sections
from radar_adaptive_cadence import cadence_hours
from radar_ical_agenda import calendar_sessions,FEED_URL
from radar_end_to_end import assess as assess_e2e
from radar_certification_matrix import CASES,CRITICAL,classify


class CertificationMatrixTests(unittest.TestCase):
    def facts(self,**extra):
        d=dict(run_finished=True,selected_sources=63,checked_sources=63,
               future_staging=315,future_primary_complete=83,
               editorial_touched_since_run=0,future_canonical=0,
               suspect_crosslinks=15,active_sports_sources=0)
        d.update(extra)
        return d

    def test_01_matrix_has_broad_unique_cases(self):
        self.assertGreaterEqual(len(CASES),45)
        self.assertEqual(len(set(x[0] for x in CASES)),len(CASES))
        self.assertTrue(all(len(row)==4 for row in CASES))

    def test_02_real_break_cannot_certify(self):
        result=classify(self.facts())
        self.assertEqual(result["state"],"NOT_CERTIFIED")
        states={x["gate"]:x["state"] for x in result["gates"]}
        self.assertEqual(states["acquisition"],"PASS")
        self.assertEqual(states["staging"],"PASS")
        self.assertEqual(states["editorial_handoff"],"FAIL")
        self.assertEqual(states["future_canonicals"],"FAIL")
        self.assertEqual(states["crosslink_quality"],"FAIL")
        self.assertEqual(states["source_recovery"],"NOT_TESTED")
        self.assertEqual(states["sports_discovery"],"FAIL")

    def test_03_cannot_certify_even_with_future_events_without_sso(self):
        data=self.facts(editorial_touched_since_run=8,
                        future_canonical=5,suspect_crosslinks=0,
                        active_sports_sources=1)
        states={x["gate"]:x["state"] for x in classify(data)["gates"]}
        self.assertEqual(states["future_canonicals"],"PASS")
        self.assertEqual(states["api_http"],"NOT_TESTED")
        self.assertEqual(classify(data)["state"],"NOT_CERTIFIED")

    def test_04_missing_sources_is_not_complete(self):
        self.assertEqual(classify(self.facts(checked_sources=27))
                         ["gates"][0]["state"],"FAIL")

    def test_05_new_source_event_is_never_autoapproved(self):
        day=(date.today()+timedelta(days=5)).isoformat()
        html=('<script type="application/ld+json">'
              '{"@type":"Event","name":"Encuentro deportivo barrial",'
              '"startDate":"'+day+'T18:30:00-03:00",'
              '"location":{"name":"Polideportivo de barrio"}}'
              '</script>')
        event=extract_listings(html,"https://organizador-nuevo.example/agenda/")
        self.assertEqual(len(event),1)
        self.assertEqual(event[0]["review_state"],"observed_unverified")
        self.assertEqual(event[0]["evidence_tier"],"structured_origin_unverified")

    def test_06_recurring_sport_is_not_invented_as_dated_event(self):
        html="<h1>Grupo de kayak polo</h1><p>Entrenamos cada lunes a las 18</p>"
        self.assertEqual(extract_listings(html,"https://grupo-nuevo.example/"),[])

    def test_07_change_of_menu_requires_no_host_specific_code(self):
        root="https://nuevo-centro.example/"
        for route in ("/agenda/","/programacion/","/cartelera/"):
            page=rd.parse_html('<a href="'+route+'">Agenda cultural</a>')
            self.assertTrue(any(u==root+route
                                for u,_ in discover_sections(root,page.links)))

    def test_08_unknown_host_does_not_follow_external_reference(self):
        root="https://nuevo-centro.example/"
        page=rd.parse_html('<a href="https://tercero.example/agenda/">Agenda</a>')
        self.assertEqual(discover_sections(root,page.links),[])

    def test_09_throttle_and_retry_are_separate_from_source_value(self):
        self.assertEqual(cadence_hours(7,["index_only"]*4,"index_only"),72)
        self.assertEqual(cadence_hours(7,["ok"],"ok"),7)
        self.assertEqual(cadence_hours(7,["failed"],"failed",2),4)

    def test_10_single_ticket_cannot_rediscover_third_party_tickets(self):
        root="https://plataforma.example/eventos/original"
        self.assertTrue(rd.is_single_event_source(root))
        class Stub:
            def __init__(self):self.calls=[]
            def request(self,url):
                self.calls.append(url)
                return (200,('<h1>Ticket</h1>'
                        '<a href="/eventos/otra-provincia">Recomendado</a>'),None)
            def can_fetch(self,url):return True
            def remaining(self):return 300
        stub=Stub()
        check,candidates=rd.scan_source({"source_id":"single","url":root},stub,"full")
        self.assertEqual(stub.calls,[root])
        self.assertEqual(candidates,[])
        self.assertEqual(check["_listings"],[])

    def test_11_ics_from_unrecognized_source_does_not_forge_original(self):
        body="BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:Actividades\nEND:VEVENT\nEND:VCALENDAR"
        self.assertEqual(calendar_sessions(body,"https://nuevo-club.example/agenda.ics"),[])

    def test_12_time_and_venue_unknown_remain_unconfirmed(self):
        day=(date.today()+timedelta(days=7)).isoformat()
        raw=('<script type="application/ld+json">'
             '{"@type":"Event","name":"Encuentro sin sede",'
             '"startDate":"'+day+'"}'
             '</script>')
        events=extract_listings(raw,"https://nuevo-espacio.example/")
        self.assertTrue(all(x["review_state"]=="observed_unverified" for x in events))

    def test_13_status_not_tested_remains_explicit(self):
        gates={x["gate"]:x["state"] for x in classify(self.facts())["gates"]}
        for gate in ("source_recovery","source_drift","multimodal_social","api_http","web_ssos"):
            self.assertEqual(gates[gate],"NOT_TESTED")

    def test_14_readiness_contract_remains_blocked(self):
        result=assess_e2e(("radar-1","partial",63,63,315,83,0,0,0,0,15))
        self.assertEqual(result["nextBlockingGate"],"radar_to_editorial_reconciliation")
        self.assertFalse(result["publicationApprovedByRadar"])

    def test_15_critical_gate_labels_cannot_be_missing(self):
        g={x["gate"] for x in classify(self.facts())["gates"]}
        self.assertTrue(set(CRITICAL).issubset(g))

if __name__=="__main__":
    unittest.main()
