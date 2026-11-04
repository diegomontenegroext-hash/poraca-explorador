import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from radar_parallel import parse_html,make_candidate

class LifecycleTests(unittest.TestCase):
    def candidate(self,event,http=200):
        page=parse_html('<script type="application/ld+json">'+json.dumps(event)+'</script>')
        return make_candidate('https://example.org/event/one','primary','',page,http)
    def test_explicit_cancel_is_a_signal_not_approval(self):
        c=self.candidate({'@type':'MusicEvent','name':'Concierto','startDate':'2026-11-10',
            'eventStatus':'https://schema.org/EventCancelled'})
        self.assertEqual(c['evidence']['lifecycle_v1']['status'],'cancelled')
        self.assertFalse(c['evidence']['lifecycle_v1']['approval'])
        self.assertIsNotNone(c['evidence']['originalOpenedAt'])
    def test_reschedule_preserves_previous_and_unknown_hour(self):
        c=self.candidate({'@type':'TheaterEvent','name':'Obra','startDate':'2026-11-12',
            'previousStartDate':'2026-11-10','eventStatus':'https://schema.org/EventRescheduled'})
        self.assertEqual(c['event_date'],'2026-11-12')
        self.assertIsNone(c['event_time'])
        self.assertEqual(c['evidence']['lifecycle_v1']['previousStart'],'2026-11-10')
    def test_missing_status_does_not_imply_scheduled(self):
        c=self.candidate({'@type':'Event','name':'Obra','startDate':'2026-11-12'})
        self.assertIsNone(c['evidence']['lifecycle_v1']['status'])
    def test_http_failure_never_has_fresh_original_timestamp(self):
        c=self.candidate({'@type':'Event','name':'Obra'},503)
        self.assertNotIn('originalOpenedAt',c['evidence'])

if __name__=='__main__': unittest.main()
