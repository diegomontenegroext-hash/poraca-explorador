"""Slot-scoped guard for ordinary ChatGPT launch and GitHub backup.

One workflow serializes acquisition; a slot remains claimed until verified readback.
"""
import json
import os
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from persist import execute

ZONE = ZoneInfo('America/Argentina/Buenos_Aires')
# Old cron expressions are retained for historical attribution/tests, not configured.
CRONS = {
    '27 8 * * *': ('05', 'full', 5),
    '27 16 * * *': ('13', 'incremental', 13),
    '27 23 * * *': ('21', 'incremental', 20),
}
BACKUP_CRONS = {
    '57 9 * * *': ('05', 'full', 5),
    '57 17 * * *': ('13', 'incremental', 13),
    '57 0 * * *': ('21', 'incremental', 20),
}
SLOTS = {entry[0]: (entry[1], entry[2]) for entry in CRONS.values()}
SCOPED_PUSHES = {'watchdog_fallback', 'chatgpt_primary'}


def parse_file(content):
    result = {}
    for line in content.splitlines():
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        key, value = line.split('=', 1)
        if key in result:
            raise ValueError('DUPLICATE_TRIGGER_KEY')
        result[key] = value
    return result


def run_created_at(env=None):
    """Use immutable run dispatch time, not a delayed worker's wall clock."""
    env = os.environ if env is None else env
    repo = env.get('GITHUB_REPOSITORY', '')
    run_id = env.get('GITHUB_RUN_ID', '')
    token = env.get('GITHUB_TOKEN', '')
    if repo != 'diegomontenegroext-hash/poraca-explorador' or not run_id.isdigit() or not token:
        raise RuntimeError('MISSING_RADAR_DISPATCH_METADATA')
    if env.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise RuntimeError('RADAR_RERUN_REQUIRES_REVIEW')
    url = 'https://api.github.com/repos/' + repo + '/actions/runs/' + run_id
    request = Request(url, headers={'Authorization': 'Bearer ' + token,
                                    'Accept': 'application/vnd.github+json'})
    with urlopen(request, timeout=20) as response:
        run = json.load(response)
    if (str(run.get('id')) != run_id or run.get('head_sha') != env.get('GITHUB_SHA')
            or run.get('event') != env.get('GITHUB_EVENT_NAME')):
        raise RuntimeError('RADAR_DISPATCH_IDENTITY_MISMATCH')
    stamp = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('RADAR_DISPATCH_TIME_UNZONED')
    return stamp


def resolved_slot(event, schedule='', fallback_text='', now=None, dispatched_at=None):
    """Resolve from the explicit request or dispatch time; reject stale/invalid claims."""
    at = (now or datetime.now(ZONE)).astimezone(ZONE)
    dispatch = (dispatched_at or at).astimezone(ZONE)
    if dispatch > at + timedelta(minutes=2):
        raise ValueError('RADAR_DISPATCH_TIME_IN_FUTURE')
    if event == 'schedule':
        if schedule not in CRONS and schedule not in BACKUP_CRONS:
            raise ValueError('UNKNOWN_RADAR_SCHEDULE')
        backup = schedule in BACKUP_CRONS
        label, mode, hour = (BACKUP_CRONS if backup else CRONS)[schedule]
        scheduled = dispatch.replace(hour=hour, minute=27, second=0, microsecond=0)
        offset = timedelta(minutes=90 if backup else 0)
        if scheduled + offset > dispatch:
            scheduled -= timedelta(days=1)
        if dispatch - (scheduled + offset) > timedelta(hours=6 if backup else 23):
            raise ValueError('SCHEDULE_SLOT_TOO_OLD')
        if backup and at - scheduled >= timedelta(hours=18):
            raise ValueError('BACKUP_SLOT_TOO_OLD')
        return dict(slot=f'{scheduled.date().isoformat()}/{label}', mode=mode,
                    origin='github_backup' if backup else 'schedule',
                    nominal_at=scheduled.isoformat(), dispatch_created_at=dispatch.isoformat())
    if event != 'push':
        return None
    trigger = parse_file(fallback_text)
    scope = trigger.get('trigger_scope')
    if scope not in SCOPED_PUSHES:
        return None  # Historical unscoped pilots are denied by the operational worker.
    if set(trigger) != {'trigger_date', 'trigger_slot', 'trigger_mode', 'trigger_scope',
                        'certification_batches', 'certification_modes'}:
        raise ValueError('INVALID_SCOPED_TRIGGER_FIELDS')
    date = trigger.get('trigger_date', '')
    label = trigger.get('trigger_slot', '')
    mode = trigger.get('trigger_mode')
    if label not in SLOTS or SLOTS[label][0] != mode:
        raise ValueError('INVALID_WATCHDOG_MODE_OR_SLOT')
    if trigger.get('certification_batches') != '1' or trigger.get('certification_modes') != mode:
        raise ValueError('INVALID_WATCHDOG_SINGLE_BATCH')
    try:
        day = datetime.strptime(date, '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError('INVALID_WATCHDOG_DATE') from exc
    if day.date().isoformat() != date:
        raise ValueError('INVALID_WATCHDOG_DATE')
    scheduled = datetime(day.year, day.month, day.day, SLOTS[label][1], 27, tzinfo=ZONE)
    lag = dispatch - scheduled
    if scope == 'watchdog_fallback':
        valid = timedelta(minutes=45) <= lag < timedelta(hours=18)
    else:
        valid = -timedelta(minutes=15) <= lag <= timedelta(minutes=90)
    if not valid or at - scheduled >= timedelta(hours=18):
        raise ValueError('RADAR_OUTSIDE_RECOVERY_WINDOW')
    return dict(slot=f'{day.date().isoformat()}/{label}', mode=mode, origin=scope,
                nominal_at=scheduled.isoformat(), dispatch_created_at=dispatch.isoformat())


def check_slot(conn, slot):
    """A completed slot wins; any incomplete claim blocks blind re-acquisition."""
    rows = execute(conn, """
    SELECT run_id, CASE
      WHEN summary->>'dispatch_kind' IN ('chatgpt_primary','github_backup')
        AND summary->>'status'='completed'
        AND coalesce(summary->'neon_readback'->>'status','')<>'completed'
      THEN 'unverified_completed' ELSE summary->>'status' END AS status
    FROM radar2.runs
    WHERE summary->>'recovery_slot'=$1
    ORDER BY (summary->>'status'='completed') DESC NULLS LAST, finished_at DESC LIMIT 1
    """, [slot])['rows']
    if not rows:
        return dict(action='RUN', slot=slot)
    last = rows[0]
    return dict(action='SKIP_COMPLETED' if last['status']=='completed'
                else 'BLOCK_UNRESOLVED', slot=slot,
                existing_run_id=last['run_id'], existing_status=last['status'])


def claim_metadata(resolved, env=None):
    """Persist identity before any acquisition; never substitute a worker's current slot."""
    if not resolved:
        raise RuntimeError('UNSCOPED_RADAR_ACQUISITION_REQUIRES_REVIEW')
    env = os.environ if env is None else env
    return dict(status='running', mode=resolved['mode'], recovery_slot=resolved['slot'],
                dispatch_kind=resolved['origin'], slot_nominal_at=resolved['nominal_at'],
                dispatch_created_at=resolved['dispatch_created_at'],
                github_event=env.get('GITHUB_EVENT_NAME'), github_schedule=env.get('RADAR2_SCHEDULE'),
                github_run_id=env['GITHUB_RUN_ID'], github_run_attempt=env.get('GITHUB_RUN_ATTEMPT','1'),
                commit=env['GITHUB_SHA'])


def verified_readback(read, write):
    """Only the final receipt may transition from ingested to completed."""
    if (read['status'] != 'ingested_pending_readback'
            or int(read['proposals']) != int(write['proposals_written'])
            or int(read['documents']) != int(write['documents_written'])):
        raise RuntimeError('SAME_RUN_READBACK_MISMATCH')
    return dict(read, status='completed')


def operational_slot(event, schedule='', fallback_text='', now=None, dispatched_at=None):
    """The new regime never runs an unscoped manual or historical pilot."""
    if event == 'schedule' and schedule not in BACKUP_CRONS:
        raise RuntimeError('OBSOLETE_OR_UNKNOWN_RADAR_SCHEDULE')
    resolved = resolved_slot(event, schedule, fallback_text, now, dispatched_at)
    if not resolved:
        raise RuntimeError('UNSCOPED_RADAR_ACQUISITION_REQUIRES_REVIEW')
    return resolved
