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

class OriginalWatchTests(unittest.TestCase):
    def test_removed_index_link_is_reopened_within_detail_budget(self):
        from radar_definitivo import scan_source,MAX_DETAILS_INCREMENTAL
        original='https://example.org/event/known'
        class Budget:
            def __init__(self): self.urls=[]
            def request(self,url):
                self.urls.append(url)
                if url==original:
                    return 200,'<script type="application/ld+json">'+json.dumps({'@type':'Event','name':'Obra conocida','startDate':'2026-11-10','eventStatus':'https://schema.org/EventCancelled'})+'</script>',None
                return 200,'<html><title>Cartelera</title></html>',None
            def can_fetch(self,url): return True
            def remaining(self): return 600
        budget=Budget()
        check,candidates=scan_source({'source_id':'test','url':'https://example.org/',
            'source_role':'original_venue','lifecycle_watch_url':original},budget,'incremental')
        self.assertIn(original,budget.urls)
        self.assertLessEqual(len(budget.urls),MAX_DETAILS_INCREMENTAL+1)
        found=next(c for c in candidates if c['original_url']==original)
        self.assertEqual(found['evidence']['lifecycle_v1']['status'],'cancelled')
        self.assertRegex(found['evidence']['originalBodySha256'],r'^[a-f0-9]{64}$')

if __name__=='__main__': unittest.main()
