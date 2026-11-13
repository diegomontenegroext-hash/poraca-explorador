import sys, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'radar2'))
from fallback_guard import resolved_slot,check_slot

ART=ZoneInfo('America/Argentina/Buenos_Aires')
def at(day,hour,minute=0):
 return datetime.fromisoformat(day+'T'+f'{hour:02}:{minute:02}:00').replace(tzinfo=ART)
def text(day='2026-11-10',slot='05',mode='full'):
 return '\n'.join(['trigger_date='+day,'trigger_slot='+slot,'trigger_mode='+mode,'trigger_scope=watchdog_fallback','certification_batches=1','certification_modes='+mode])

class FallbackGuards(unittest.TestCase):
 def test_schedule_resolves_previous_local_day_when_delayed_past_midnight(self):
  self.assertEqual(resolved_slot('schedule','27 23 * * *',now=at('2026-11-11',1,42))['slot'],'2026-11-10/21')
 def test_schedule_full_same_day_and_late(self):
  self.assertEqual(resolved_slot('schedule','27 8 * * *',now=at('2026-11-10',16))['slot'],'2026-11-10/05')
 def test_fallback_full_at_eight(self):
  self.assertEqual(resolved_slot('push',fallback_text=text(),now=at('2026-11-10',8))['mode'],'full')
 def test_fallback_incremental_late(self):
  self.assertEqual(resolved_slot('push',fallback_text=text(slot='13',mode='incremental'),now=at('2026-11-10',16))['slot'],'2026-11-10/13')
 def test_fallback_rejects_too_early_or_stale(self):
  with self.assertRaisesRegex(ValueError,'WINDOW'):resolved_slot('push',fallback_text=text(),now=at('2026-11-10',5,45))
  with self.assertRaisesRegex(ValueError,'WINDOW'):resolved_slot('push',fallback_text=text(),now=at('2026-11-11',1))
 def test_watchdog_observes_operator_grace_and_expiry(self):
  for day,hour,minute in [('2026-11-10',6,11),('2026-11-10',23,27)]:
   with self.subTest(day=day,hour=hour,minute=minute):
    with self.assertRaisesRegex(ValueError,'WINDOW'):
     resolved_slot('push',fallback_text=text(),now=at(day,hour,minute))
  for hour,minute in [(6,12),(23,26)]:
   with self.subTest(hour=hour,minute=minute):
    self.assertEqual(resolved_slot('push',fallback_text=text(),now=at('2026-11-10',hour,minute))['slot'],'2026-11-10/05')
 def test_fallback_invalid_mode_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'MODE'):resolved_slot('push',fallback_text=text(slot='05',mode='incremental'),now=at('2026-11-10',8))
 def test_fallback_multi_batch_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'SINGLE_BATCH'):resolved_slot('push',fallback_text=text().replace('certification_batches=1','certification_batches=2'),now=at('2026-11-10',8))
 def test_old_pilot_does_not_claim_slot(self):
  self.assertIsNone(resolved_slot('push',fallback_text='trigger_scope=compound_acceptance',now=at('2026-11-10',8)))
 def test_slot_guard_missing_allows_and_completed_suppresses(self):
  with patch('fallback_guard.execute',return_value={'rows':[]}):
   self.assertEqual(check_slot('fake','2026-11-10/05')['action'],'RUN')
  with patch('fallback_guard.execute',return_value={'rows':[{'run_id':'radar2-ghpilot-1-attempt1','status':'completed'}]}):
   self.assertEqual(check_slot('fake','2026-11-10/05')['action'],'SKIP_COMPLETED')
 def test_slot_guard_failed_neon_attempt_blocks_automatic_retry(self):
  with patch('fallback_guard.execute',return_value={'rows':[{'run_id':'radar2-ghdaily-1-attempt1','status':'failed'}]}):
   self.assertEqual(check_slot('fake','2026-11-10/05')['action'],'BLOCK_UNRESOLVED')
if __name__=='__main__':unittest.main()
