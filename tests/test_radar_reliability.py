import json
import pathlib
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
from radar_parallel import iso_event_fields
from radar_agenda_adapters import structured_sessions
from radar_agenda_adapters import make_record
from radar_health import assess, stability
from radar_url_clock_review import summarize
from radar_gate_alias_preflight import summarize as aliases


@patch('radar_agenda_adapters.active_date', return_value=True)
class TemporalRegression(unittest.TestCase):
    def test_single_contract_both_extractors(self, _active):
        # Doble-T historical clock regressions, rollover, offsets, unknown hour.
        cases = [
            ('2026-11-09T23:30:00Z', ('2026-11-09', '20:30')),
            ('2026-11-14T19:30:00+00:00', ('2026-11-14', '16:30')),
            ('2026-11-09T20:30:00-03:00', ('2026-11-09', '20:30')),
            ('2026-11-09T20:30:00', ('2026-11-09', '20:30')),
            ('2026-11-10T01:15:00Z', ('2026-11-09', '22:15')),
            ('2026-11-10T03:00:00Z', ('2026-11-10', '00:00')),
            ('2026-11-10', ('2026-11-10', None)),
            ('2026-11-10T20:30:00z', ('2026-11-10', '17:30')),
            ('2026-11-10T24:00:00', (None, None)),
            ('2026-11-32T19:00', (None, None)),
            ('2026-11-10T20', (None, None)),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(iso_event_fields(raw), expected)
                node = {'@type':'Event','name':'Prueba temporal','startDate':raw,
                        'location':{'name':'Doble-T'}}
                page = '<script type="application/ld+json">'+json.dumps(node)+'</script>'
                rows = structured_sessions(page, 'https://teatrodoblet.com.ar/event/test/')
                self.assertEqual([(r['event_date'],r['event_time']) for r in rows],
                                 [] if expected[0] is None else [expected])

    def test_multiple_sessions_remain_separate(self, _active):
        node={'@type':'Event','name':'Play','startDate':[
            '2026-11-01T19:30:00-03:00','2026-11-01T20:30:00-03:00'],
            'location':{'name':'TACEC — Teatro Argentino'}}
        rows=structured_sessions('<script type="application/ld+json">'+json.dumps(node)+'</script>',
                                 'https://www.alternativateatral.com/obra103606-play')
        self.assertEqual([r['event_time'] for r in rows],['19:30','20:30'])

    def test_markup_without_angle_brackets_cannot_become_venue(self, _active):
        from datetime import date
        for bad in ['div class="venue"', 'javascript:document.location', 'document.querySelector']:
            with self.subTest(venue=bad):
                row=make_record('Actividad',date(2026,11,1),'21:00',bad,
                                'https://example.org/event/','fixture','secondary_agenda')
                self.assertIsNone(row['venue'])


class OperationalHealth(unittest.TestCase):
    def good(self):
        return dict(selected=4,checked=4,success=4,index_only=0,evidence_quality={
            k:{'status':'read_only'} for k in
            ('public_observation_aliases','function_gate_v2','url_clock_aliases')})

    def test_http_success_does_not_hide_missing_controls(self):
        stats=self.good()
        stats['evidence_quality']['function_gate_v2']={'status':'unavailable','reason':'InsufficientPrivilege'}
        result=assess(stats)
        self.assertEqual(result['acquisition'],'correcto')
        self.assertEqual(result['overall'],'bloqueado')
        self.assertEqual(result['api'],'not_checked')
        self.assertEqual(result['admission'],'not_performed')

    def test_partial_and_empty_run_do_not_claim_success(self):
        stats=self.good();stats.update(selected=6,checked=5,success=3,index_only=1)
        result=assess(stats)
        self.assertEqual(result['overall'],'parcial')
        self.assertEqual(result['sources']['failed'],1)
        self.assertEqual(result['sources']['unvisited'],1)
        stats.update(selected=0,checked=0,success=0,index_only=0)
        self.assertEqual(assess(stats)['overall'],'sin_evidencia_suficiente')

    def test_stability_requires_observed_days_and_healthy_history(self):
        now=datetime(2026,11,10,tzinfo=timezone.utc)
        def run(hours,health='correcto'):
            return dict(started_at=now-timedelta(hours=hours),finished_at=now-timedelta(hours=hours-1),
                        status='complete',summary={'health':{'schema':'poraca-health-v1','overall':health}})
        self.assertEqual(stability([run(1)],now)['3d']['state'],'sin_evidencia_suficiente')
        rows=[run(h) for h in range(1,194,8)]
        self.assertEqual(stability(rows,now)['7d']['state'],'correcto')
        rows[0]=run(1,'bloqueado')
        self.assertEqual(stability(rows,now)['3d']['state'],'degradado')
        self.assertEqual(stability([run(190),run(1)],now)['7d']['state'],'degradado')

    def test_url_conflicts_are_review_only(self):
        result=summarize([('https://teatrodoblet.com.ar/event/167089','2026-11-09',2,
                           ['20:30','23:30'],['url','url/'])])
        self.assertEqual(result['samples'][0]['decision'],'HOLD_URL_CLOCK_CONFLICT')
        self.assertFalse(result['authorized_to_write'])

    def test_editorial_hold_survives_alias_summary(self):
        rows=[('candidate','REVIEW_ORIGINAL_BEFORE_ANY_INSERT','obs-sab',
               'Sindicato Argentino de Boleros','2026-11-04','21:00','index','original',
               'Casa Metro','HOLD_EDITORIAL_DO_NOT_APPROVE')]
        result=aliases(rows)
        self.assertEqual(result['editorial_holds'],1)
        self.assertEqual(result['samples'][0]['safe_next_step'],'HOLD_EDITORIAL_DO_NOT_APPROVE')
        self.assertFalse(result['authorized_to_write'])
