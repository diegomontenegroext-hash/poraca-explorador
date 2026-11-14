import io, json, sys, unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'radar2'))
from fallback_guard import resolved_slot, check_slot, run_created_at, claim_metadata, verified_readback, operational_slot

ZONE=ZoneInfo('America/Argentina/Buenos_Aires')
def at(day,hour,minute=0):
    return datetime(2026,11,day,hour,minute,tzinfo=ZONE)
def trigger(day=14,label='05',mode='full'):
    return f'# Ordinary Radar launch\ntrigger_date=2026-11-{day:02}\ntrigger_slot={label}\ntrigger_mode={mode}\ntrigger_scope=chatgpt_primary\ncertification_batches=1\ncertification_modes={mode}\n'

class PrimaryAndBackup(unittest.TestCase):
    def test_primary_boundaries(self):
        for stamp in (at(14,5,12),at(14,5,45),at(14,6,57)):
            with self.subTest(stamp=stamp):
                got=resolved_slot('push',fallback_text=trigger(),now=stamp)
                self.assertEqual((got['slot'],got['origin'],got['mode']),('2026-11-14/05','chatgpt_primary','full'))
        for stamp in (at(14,5,11),at(14,6,58)):
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError,'WINDOW'):
                resolved_slot('push',fallback_text=trigger(),now=stamp)
    def test_incrementals_modes_and_dates(self):
        for label,hour in [('13',13),('21',20)]:
            got=resolved_slot('push',fallback_text=trigger(label=label,mode='incremental'),now=at(14,hour,45))
            self.assertEqual(got['slot'],'2026-11-14/'+label)
            self.assertEqual(got['mode'],'incremental')
        with self.assertRaisesRegex(ValueError,'MODE'):
            resolved_slot('push',fallback_text=trigger(label='13'),now=at(14,13,45))
    def test_primary_queued_worker_keeps_slot(self):
        got=resolved_slot('push',fallback_text=trigger(label='21',mode='incremental'),dispatched_at=at(14,20,45),now=at(15,0,40))
        self.assertEqual(got['slot'],'2026-11-14/21')
        self.assertEqual(got['dispatch_created_at'],at(14,20,45).isoformat())
    def test_stale_worker_rejected(self):
        with self.assertRaisesRegex(ValueError,'WINDOW'):
            resolved_slot('push',fallback_text=trigger(),dispatched_at=at(14,5,45),now=at(14,23,27))
    def test_strict_trigger_fields_and_duplicate_key(self):
        for raw in (trigger()+'extra=1\n',trigger()+'trigger_slot=13\n',trigger().replace('certification_batches=1','certification_batches=2')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                resolved_slot('push',fallback_text=raw,now=at(14,5,45))
    def test_unknown_and_manual_have_no_slot(self):
        self.assertIsNone(resolved_slot('workflow_dispatch',now=at(14,5,45)))
        self.assertIsNone(resolved_slot('push',fallback_text=trigger().replace('chatgpt_primary','unknown'),now=at(14,5,45)))
    def test_three_backup_crons_match_primary_nominals(self):
        for cron,label,hour in [('57 9 * * *','05',5),('57 17 * * *','13',13),('57 0 * * *','21',20)]:
            stamp=at(14,hour+1,57)
            got=resolved_slot('schedule',cron,now=stamp)
            self.assertEqual((got['slot'],got['origin'],got['nominal_at']),('2026-11-14/'+label,'github_backup',at(14,hour,27).isoformat()))
    def test_backup_cross_midnight_and_delayed_queue(self):
        got=resolved_slot('schedule','57 0 * * *',dispatched_at=at(15,1,0),now=at(15,6,0))
        self.assertEqual(got['slot'],'2026-11-14/21')
    def test_backup_rejects_ambiguous_older_dispatch(self):
        with self.assertRaisesRegex(ValueError,'TOO_OLD'):
            resolved_slot('schedule','57 9 * * *',now=at(14,13,0))
        with self.assertRaisesRegex(ValueError,'TOO_OLD'):
            resolved_slot('schedule','57 9 * * *',dispatched_at=at(14,7,0),now=at(15,0,0))
    def test_claim_states_never_retry(self):
        for status in ['running','ingested_pending_readback','failed','unverified_completed',None]:
            with self.subTest(status=status), patch('fallback_guard.execute',return_value={'rows':[{'run_id':'r','status':status}]}):
                self.assertEqual(check_slot('fake','2026-11-14/05')['action'],'BLOCK_UNRESOLVED')
    def test_completed_slot_skips_and_distinct_slot_runs(self):
        with patch('fallback_guard.execute',side_effect=[{'rows':[{'run_id':'r','status':'completed'}]},{'rows':[]}]) as execute:
            self.assertEqual(check_slot('fake','2026-11-14/05')['action'],'SKIP_COMPLETED')
            self.assertEqual(check_slot('fake','2026-11-14/13')['action'],'RUN')
            self.assertEqual(execute.call_args_list[-1].args[-1],['2026-11-14/13'])
            self.assertIn("neon_readback",execute.call_args_list[0].args[1])
    def test_dispatch_metadata_identity(self):
        env={'GITHUB_REPOSITORY':'diegomontenegroext-hash/poraca-explorador','GITHUB_RUN_ID':'123','GITHUB_TOKEN':'test-only','GITHUB_SHA':'abc','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1'}
        good={'id':123,'head_sha':'abc','event':'push','created_at':'2026-11-14T08:45:00Z'}
        with patch('fallback_guard.urlopen',return_value=io.BytesIO(json.dumps(good).encode())):
            self.assertEqual(run_created_at(env).astimezone(ZONE),at(14,5,45))
        for change in ({'head_sha':'different'},{'event':'schedule'},{'id':456}):
            with self.subTest(change=change), patch('fallback_guard.urlopen',return_value=io.BytesIO(json.dumps({**good,**change}).encode())), self.assertRaisesRegex(RuntimeError,'MISMATCH'):
                run_created_at(env)
        with self.assertRaisesRegex(RuntimeError,'RERUN'):
            run_created_at({**env,'GITHUB_RUN_ATTEMPT':'2'})
        with self.assertRaisesRegex(RuntimeError,'MISSING'):
            run_created_at({**env,'GITHUB_TOKEN':''})
    def test_future_dispatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'FUTURE'):
            resolved_slot('push',fallback_text=trigger(),dispatched_at=at(14,5,45),now=at(14,5,40))

    def test_claim_preserves_exact_origin_before_acquisition(self):
        resolved=resolved_slot('push',fallback_text=trigger(),now=at(14,5,45))
        env={'GITHUB_RUN_ID':'123','GITHUB_SHA':'abc','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1'}
        claim=claim_metadata(resolved,env)
        self.assertEqual((claim['status'],claim['recovery_slot'],claim['dispatch_kind'],claim['commit']),('running','2026-11-14/05','chatgpt_primary','abc'))
        self.assertEqual(claim['slot_nominal_at'],at(14,5,27).isoformat())
        with self.assertRaisesRegex(RuntimeError,'UNSCOPED'):
            claim_metadata(None,env)
    def test_readback_requires_ingested_and_exact_counts(self):
        write={'documents_written':'5','proposals_written':'7'}
        read={'status':'ingested_pending_readback','documents':'5','proposals':'7'}
        self.assertEqual(verified_readback(read,write),{'status':'completed','documents':'5','proposals':'7'})
        for bad in ({**read,'status':'completed'},{**read,'documents':'4'},{**read,'proposals':'6'}):
            with self.subTest(bad=bad), self.assertRaisesRegex(RuntimeError,'MISMATCH'):
                verified_readback(bad,write)

    def test_operational_worker_rejects_old_cron_and_unscoped_requests(self):
        with self.assertRaisesRegex(RuntimeError,'OBSOLETE'):
            operational_slot('schedule','27 8 * * *',now=at(14,5,45))
        for event,raw in [('workflow_dispatch',''),('push','trigger_scope=compound_acceptance'),('push','trigger_scope=unknown')]:
            with self.subTest(event=event,raw=raw), self.assertRaisesRegex(RuntimeError,'UNSCOPED'):
                operational_slot(event,fallback_text=raw,now=at(14,5,45))
        self.assertEqual(operational_slot('push',fallback_text=trigger(),now=at(14,5,45))['origin'],'chatgpt_primary')

if __name__=='__main__': unittest.main()
