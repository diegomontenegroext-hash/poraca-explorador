"""Slot-scoped guard for ChatGPT watchdog fallback and delayed GitHub schedule.

Never counts a fallback as a natural schedule. Serial workflow concurrency ensures
slot check + insert in the worker do not race with the same workflow's jobs.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from persist import execute

ZONE = ZoneInfo('America/Argentina/Buenos_Aires')
CRONS = {
    '27 8 * * *': ('05', 'full', 5),
    '27 16 * * *': ('13', 'incremental', 13),
    '27 23 * * *': ('21', 'incremental', 20),
}
SLOTS = {entry[0]: (entry[1], entry[2]) for entry in CRONS.values()}


def parse_file(content):
    return dict(line.split('=', 1) for line in content.splitlines()
                if '=' in line and not line.lstrip().startswith('#'))


def resolved_slot(event, schedule='', fallback_text='', now=None):
    """Return slot/mode or None; invalid watchdog requests fail closed."""
    at = (now or datetime.now(ZONE)).astimezone(ZONE)
    if event == 'schedule':
        if schedule not in CRONS:
            raise ValueError('UNKNOWN_RADAR_SCHEDULE')
        label, mode, hour = CRONS[schedule]
        scheduled = at.replace(hour=hour, minute=27, second=0, microsecond=0)
        if scheduled > at:
            scheduled -= timedelta(days=1)
        if at - scheduled > timedelta(hours=23):
            raise ValueError('SCHEDULE_SLOT_TOO_OLD')
        return dict(slot=f'{scheduled.date().isoformat()}/{label}', mode=mode,
                    origin='schedule')
    if event != 'push':
        return None
    trigger = parse_file(fallback_text)
    if trigger.get('trigger_scope') != 'watchdog_fallback':
        return None
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
    scheduled = datetime(day.year, day.month, day.day, SLOTS[label][1], 27,
                         tzinfo=ZONE)
    lag = at - scheduled
    if lag < timedelta(minutes=45) or lag >= timedelta(hours=18):
        raise ValueError('WATCHDOG_OUTSIDE_RECOVERY_WINDOW')
    return dict(slot=f'{day.date().isoformat()}/{label}', mode=mode,
                origin='watchdog_fallback')


def check_slot(conn, slot):
    """No re-acquisition for a completed or unresolved run of this slot.

    A failed post-Neon attempt requires diagnosis, never blind repetition.
    Earlier failures before Neon do not create a receipt and can be recovered.
    Recovery grace is 45 minutes; the target start is within 60 minutes.
    """
    rows = execute(conn, """
    SELECT run_id, summary->>'status' AS status
    FROM radar2.runs
    WHERE summary->>'recovery_slot'=$1
    ORDER BY finished_at DESC LIMIT 1
    """, [slot])['rows']
    if not rows:
        return dict(action='RUN', slot=slot)
    last = rows[0]
    return dict(action='SKIP_COMPLETED' if last['status']=='completed'
                else 'BLOCK_UNRESOLVED', slot=slot,
                existing_run_id=last['run_id'], existing_status=last['status'])
