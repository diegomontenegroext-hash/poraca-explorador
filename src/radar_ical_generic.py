"""General iCalendar discovery: only linked same-origin .ics/.ical feeds.

No URL synthesis, timezone guesses, RRULE expansion, editorial admission,
or source trust upgrades. Feeds of unknown origin remain unverified.
Festival-specific attested feed continues through its existing parser.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
import re

ART=ZoneInfo("America/Argentina/Buenos_Aires")
_CALENDAR_PATH=re.compile(r"\.(?:ics|ical)$",re.I)
_UNCONFIRMED=re.compile(
    r"^(?:direcci[oó]n por inbox|sede a confirmar|lugar a confirmar|por confirmar)$",re.I)


def is_calendar_url(url):
    try:
        p=urlsplit(url)
        return bool(p.scheme=="https" and p.hostname and
                    not p.username and not p.password and
                    p.port in (None,443) and not p.query and not p.fragment and
                    _CALENDAR_PATH.search(p.path))
    except ValueError:
        return False


def discover_calendar_links(root, anchors, limit=2):
    """Existing real HTML anchors, not guesses or external calendar providers."""
    origin=urlsplit(root)
    if origin.scheme!="https" or not origin.hostname:
        return []
    found=[]
    for href,label in anchors[:900]:
        if not isinstance(href,str) or not href.strip() or href.startswith("//"):
            continue
        target=urljoin(root,href.strip())
        if (is_calendar_url(target) and
            urlsplit(target).hostname==origin.hostname and
            target not in found):
            found.append(target)
        if len(found)>=max(0,min(int(limit),2)):
            break
    return [(url,"adaptive_calendar_feed") for url in found]


def _unescape(value):
    return re.sub(r"\\([nN,;\\])",
                  lambda m:"\n" if m.group(1).lower()=="n" else m.group(1),
                  value or "")


def _when(field):
    if field is None:
        return None
    name,value=field
    key=name.upper()
    try:
        if "VALUE=DATE" in key and re.fullmatch(r"20\d{6}",value):
            return date(int(value[:4]),int(value[4:6]),int(value[6:8])),None
        if re.fullmatch(r"20\d{6}T\d{6}Z",value):
            instant=datetime.strptime(value,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            local=instant.astimezone(ART)
            return local.date(),local.strftime("%H:%M")
        if "TZID=AMERICA/ARGENTINA/BUENOS_AIRES" in key and re.fullmatch(
                r"20\d{6}T\d{6}",value):
            local=datetime.strptime(value,"%Y%m%dT%H%M%S")
            return local.date(),local.strftime("%H:%M")
        if "TZID=" not in key and re.fullmatch(r"20\d{6}T\d{6}",value):
            # Floating clock has no authoritative timezone: preserve day only.
            return date(int(value[:4]),int(value[4:6]),int(value[6:8])),None
    except ValueError:
        return None
    return None


def _safe_event_proof(proof,calendar_url):
    if not proof:
        return calendar_url
    try:
        p=urlsplit(proof)
        calendar=urlsplit(calendar_url)
        if (p.scheme=="https" and p.hostname==calendar.hostname and
            p.username is None and p.password is None and
            p.port in (None,443)):
            return proof
    except ValueError:
        pass
    return calendar_url


def calendar_sessions(body,url):
    """Yield individual (title, day, clock, venue, proof) observations.

    An ICS schedule alone is *not* proof that its hostname is the event organizer.
    """
    if not is_calendar_url(url) or not isinstance(body,str) or len(body)>450_000:
        return []
    raw=body.strip()
    if not (raw.startswith("BEGIN:VCALENDAR") and raw.endswith("END:VCALENDAR")):
        return []
    rows=[]
    for line in raw.splitlines()[:16000]:
        if line.startswith((" ","\t")) and rows:
            rows[-1]+=line[1:]
        else:
            rows.append(line)
    out=[];seen=set();fields=None
    for line in rows:
        if line=="BEGIN:VEVENT":
            fields={}
            continue
        if line=="END:VEVENT":
            if fields:
                if fields.get("STATUS",("",""))[1].upper()!="CANCELLED" and "RRULE" not in fields:
                    uid=_unescape(fields.get("UID",("",""))[1]).strip()
                    title=_unescape(fields.get("SUMMARY",("",""))[1]).strip()
                    parsed=_when(fields.get("DTSTART"))
                    if uid and len(uid)<=300 and 4<=len(title)<=180 and parsed:
                        venue=_unescape(fields.get("LOCATION",("",""))[1]).strip()
                        if not venue or _UNCONFIRMED.fullmatch(venue):
                            venue=None
                        proof=fields.get("URL",("",""))[1].strip()
                        proof=_safe_event_proof(proof,url)
                        d,clock=parsed
                        key=(uid,title,d,clock,venue,proof)
                        if key not in seen:
                            out.append((title,d,clock,venue,proof))
                            seen.add(key)
                            if len(out)>=100:
                                break
            fields=None
            continue
        if fields is not None and ":" in line:
            name,value=line.split(":",1)
            key=name.split(";",1)[0].upper()
            if key in ("UID","SUMMARY","LOCATION","DTSTART","URL","STATUS","RRULE"):
                fields.setdefault(key,(name,value))
    return out
