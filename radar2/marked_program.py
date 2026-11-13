"""Explicit calendar headings and check-mark activities; no cross-section clocks."""
import re
import unicodedata
from datetime import timedelta

VERSION = 'marked-program-v1.0'
DAYS = ('lunes','martes','miercoles','jueves','viernes','sabado','domingo')
HEAD = re.compile(r'^\s*📆\s*(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+([0-3]?\d)\s*$', re.I | re.M)
ITEM = re.compile(r'^\s*✅\s*([^\n]+)', re.M)
CLOCK = re.compile(r'(?<![\d.])(?:desde\s+las\s+|a\s+las\s+)?([01]?\d|2[0-3])(?:[.:]([0-5]\d))?\s*hs?\b', re.I)
PLACE = re.compile(r'^\s*📍\s*([^\n]+)', re.M)
SECTOR = re.compile(r'^(?:planta (?:alta|baja)|play[oó]n|patio|sala(?:\s+[\w-]+)?)$', re.I)

def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.lower()) if not unicodedata.combining(c))

def shape(text):
    return len(re.findall(r'^\s*📆',text,re.M)) >= 2 and len(list(ITEM.finditer(text))) >= 2

def parse(text, base):
    """Return scoped literal claims. Ambiguous dates never fall back to global dates."""
    if not base or not shape(text):
        return []
    headings = list(HEAD.finditer(text))
    if len(headings)!=len(re.findall(r'^\s*📆',text,re.M)) or len(headings)<2 or ITEM.search(text[:headings[0].start()]):
        return []
    result = []
    previous = None
    for i, heading in enumerate(headings):
        weekday, number = DAYS.index(fold(heading[1])), int(heading[2])
        candidates = [base+timedelta(days=n) for n in range(-14,15)]
        candidates = [day for day in candidates if day.day==number and day.weekday()==weekday]
        if len(candidates)!=1 or previous is not None and candidates[0]<=previous:
            return []
        day=candidates[0]; previous=day
        section=text[heading.end():headings[i+1].start() if i+1<len(headings) else len(text)]
        items=list(ITEM.finditer(section))
        if not items:return []
        for j,item in enumerate(items):
            block=section[item.start():items[j+1].start() if j+1<len(items) else len(section)].strip()
            label=item[1].strip()
            if fold(label) in ('inauguracion','presentacion','actividad'):
                tail=block.splitlines()[1:]
                label=next((line.strip() for line in tail if line.strip() and not line.strip().startswith(('📍','🕐','✅','📆'))),label)
            if not label or fold(label) in ('inauguracion','presentacion','actividad'):
                return []
            clocks=list(CLOCK.finditer(block)); places=list(PLACE.finditer(block))
            clock=clocks[0] if len(clocks)==1 else None
            time=f'{int(clock[1]):02}:{clock[2] or "00"}' if clock else None
            place=places[0][1].strip() if len(places)==1 else None
            result.append(dict(title=label[:160],date=day,heading=heading[0].strip(),heading_start=heading.start(),block_start=heading.end()+item.start(),block=block,time=None if time=='00:00' else time,announced_time=time,clock=clock[0] if clock else None,place=place,place_quote=places[0][0].strip() if place else None,sector=place if place and SECTOR.fullmatch(place) else None))
    return result
