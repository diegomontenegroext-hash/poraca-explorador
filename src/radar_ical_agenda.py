"""One pinned, first-party iCalendar feed -> dated sessions for review only.

No HTTP, database, editorial admission, or generic third-party ICS crawling.
This avoids parsing the same festival's promotional HTML as 24 vague links.
"""
from __future__ import annotations

from datetime import datetime, date, timezone
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

FEED_URL = "https://festival.freezer.com.ar/2026/programacion.ics"
PROGRAM_URL = "https://festival.freezer.com.ar/2026/programacion/"
ART = ZoneInfo("America/Argentina/Buenos_Aires")
_DAY_NAMES = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
_EVENT_ANCHOR = re.compile(
    r"^https://festival[.]freezer[.]com[.]ar/2026/programacion/#"
    r"(lunes|martes|miercoles|jueves|viernes|sabado|domingo)-(\d{1,2})$",
    re.I,
)


def _unescape(value):
    return re.sub(r"\\([nN,;\\])",
                  lambda match: "\n" if match.group(1).lower() == "n" else match.group(1),
                  value or "")


def _start_time(fields):
    item = fields.get("DTSTART")
    if not item:
        return None
    name, value = item
    try:
        if "VALUE=DATE" in name.upper() and re.fullmatch(r"20\d{6}", value):
            return date.fromisoformat(value[0:4] + "-" + value[4:6] + "-" + value[6:8]), None
        if re.fullmatch(r"20\d{6}T\d{6}Z", value):
            instant = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            local = instant.astimezone(ART)
            return local.date(), local.strftime("%H:%M")
        if ("TZID=AMERICA/ARGENTINA/BUENOS_AIRES" in name.upper() or
            "TZID=AMERICA/ARGENTINA/BUENOS\\_AIRES" in name.upper()):
            if re.fullmatch(r"20\d{6}T\d{6}", value):
                local = datetime.strptime(value, "%Y%m%dT%H%M%S")
                return local.date(), local.strftime("%H:%M")
    except ValueError:
        return None
    return None


def _event(fields):
    uid = _unescape(fields.get("UID", ("", ""))[1])
    summary = _unescape(fields.get("SUMMARY", ("", ""))[1]).strip()
    location = _unescape(fields.get("LOCATION", ("", ""))[1]).strip()
    proof = fields.get("URL", ("", ""))[1].strip()
    parsed = _start_time(fields)
    if (not uid.endswith("@festival.freezer.com.ar") or
        not summary.startswith("Freezer · ") or not parsed or not location):
        return None
    day, clock = parsed
    anchor = _EVENT_ANCHOR.fullmatch(proof)
    if not anchor or int(anchor.group(2)) != day.day or anchor.group(1).lower() != _DAY_NAMES[day.weekday()]:
        return None
    p = urlsplit(proof)
    if p.username or p.password or p.port not in (None, 443) or p.query:
        return None
    return summary, day, clock, location, proof


def calendar_sessions(body, url):
    """Unique, date-specific original sessions; all-day means UNKNOWN time.

    Reject unknown sources, malformed/incomplete VCALENDAR, and missing UID,
    location or exact organizer day anchor. Do not infer weekday or repeat.
    """
    if url != FEED_URL or not isinstance(body, str) or len(body) > 450_000:
        return []
    raw = body.strip()
    if not raw.startswith("BEGIN:VCALENDAR") or not raw.endswith("END:VCALENDAR"):
        return []
    unfolded = []
    for line in raw.splitlines():
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    events = []
    fields = None
    seen = set()
    for line in unfolded[:15_000]:
        if line == "BEGIN:VEVENT":
            fields = {}
        elif line == "END:VEVENT":
            if fields is not None:
                entry = _event(fields)
                if entry and entry not in seen:
                    seen.add(entry)
                    events.append(entry)
            fields = None
            if len(events) >= 100:
                break
        elif fields is not None and ":" in line:
            name, value = line.split(":", 1)
            key = name.split(";", 1)[0].upper()
            if key in {"UID", "SUMMARY", "LOCATION", "DTSTART", "URL"} and key not in fields:
                fields[key] = (name, value)
    return events
