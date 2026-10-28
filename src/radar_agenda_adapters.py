#!/usr/bin/env python3
"""Extract individual event sessions from known agenda layouts, no publication.

A listing is *evidence to review*, not an accepted event. No web requests here.
URLs are always real source/document URLs; no manufactured post anchors.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
import html
import re
from urllib.parse import urlsplit, parse_qs

MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
        "noviembre":11,"diciembre":12}
CLOCK=re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")
DMY=re.compile(r"\b([0-3]?\d)/([01]?\d)/(20\d{2})\b")
SCOPED_HOSTS={"agendalaplata.ar","www.agendalaplata.ar",
              "www.alternativateatral.com","alternativateatral.com",
              "casametro.com.ar","www.casametro.com.ar",
              "operalp.com.ar","www.operalp.com.ar"}
def tidy(s):
    return re.sub(r"\s+"," ",html.unescape(s or "")).strip()

class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.chunks=[]
        self.text=[]
        self.headings=[]
        self._ignore=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg"):
            self._ignore+=1
        if tag in ("p","li","h1","h2","h3","br","section","div"):
            self.text.append("\n")
        if tag in ("p","h1","h2","h3"):
            self.stack.append((tag,len(self.text)))
    def handle_data(self,data):
        if not self._ignore:
            self.text.append(data)
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg"):
            self._ignore=max(0,self._ignore-1)
        if tag in ("p","h1","h2","h3"):
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==tag:
                    a=self.stack.pop(i)[1]
                    val=tidy(" ".join(self.text[a:]))
                    if val:
                        self.chunks.append((tag,val))
                        if tag.startswith("h"):
                            self.headings.append((tag,val))
                    break
        if tag in ("p","li","h1","h2","h3","section","div","br"):
            self.text.append("\n")

def parse_dmy(s):
    m=DMY.search(s or "")
    if not m:
        return None
    try:
        return date(int(m[3]),int(m[2]),int(m[1]))
    except ValueError:
        return None

def active_date(d,at=None):
    at=at or datetime.now().date()
    return bool(d and at-timedelta(days=14)<=d<=at+timedelta(days=365))

def make_record(title,when,time,venue,url,method,tier):
    title=tidy(title)[:180]
    venue=tidy(venue)[:180]
    if len(title)<4 or not active_date(when):
        return None
    if time is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",time):
        return None
    return dict(title=title,event_date=when.isoformat(),event_time=time,
                venue=venue or None,proof_url=url,method=method,
                evidence_tier=tier,review_state="observed_unverified")

def visible_blocks(raw):
    blocks=Blocks()
    blocks.feed(raw[:600_000])
    return blocks

def scope(url):
    p=urlsplit(url)
    return (p.hostname or "").lower(), p.path.lower()

def extract_listings(raw,url):
    """Returns individual session observations; never returns verified status."""
    host,path=scope(url)
    if host not in SCOPED_HOSTS:
        return []
    blocks=visible_blocks(raw)
    out=[]
    if "alternativateatral.com" in host and re.match(r"/obra\d+",path):
        title=next((t for tag,t in blocks.headings if tag=="h1"),None)
        if title:
            # Several clock times may appear before ONE printed performance date.
            text=tidy(" ".join(blocks.text))
            for m in re.finditer(r"Entrada:\s*.{0,220}?\b([0-3]?\d/[01]?\d/20\d{2})",text,re.I):
                d=parse_dmy(m.group(1))
                times=list(dict.fromkeys(CLOCK.findall(m.group(0))))
                for tm in times[:6]:
                    r=make_record(title,d,tm,"Teatro Argentino" if "av. 51 entre 9 y 10" in text.lower()
                                  else None,url,"alternativa_obra_funcion_text","primary_ticket_listing")
                    if r: out.append(r)
    elif "casametro.com.ar" in host and "/evento/" in path:
        title=next((t for tag,t in blocks.headings if tag=="h1"),None)
        plain=tidy(" ".join(blocks.text))
        when=re.search(r"\bFecha:\s*([a-záéíóúñ]+)\s+([0-3]?\d),?\s+(20\d{2})",plain,re.I)
        tm=re.search(r"\bHora de inicio:\s*((?:[01]?\d|2[0-3]):[0-5]\d)",plain,re.I)
        venue=re.search(r"\bLugar:\s*(.{3,100}?)(?=\s+Coordenadas:|\s+Eventos relacionados|$)",plain,re.I)
        if when and tm and title:
            month=MONTHS.get(when.group(1).casefold())
            try: d=date(int(when.group(3)),month,int(when.group(2))) if month else None
            except ValueError: d=None
            time=tm.group(1).zfill(5)
            r=make_record(title,d,time,venue.group(1) if venue else "Casa Metro",
                          url,"casa_metro_detalle_fecha_hora","primary_venue")
            if r: out.append(r)
    elif host.endswith("operalp.com.ar") and path.rstrip("/")=="/agenda":
        # Official listing gives dates, but not always a time. Keep it unverified.
        raw_text=re.sub(r"<[^>]+>","\n",raw)
        raw_text=html.unescape(raw_text)
        for m in re.finditer(r"<h2\b[^>]*>(.*?)</h2>(.{0,700}?)(?=<h2\b|</section|$)",raw,re.I|re.S):
            title=tidy(re.sub(r"<[^>]+>"," ",m.group(1)))
            d=parse_dmy(tidy(re.sub(r"<[^>]+>"," ",m.group(2))))
            r=make_record(title,d,None,"Teatro Ópera La Plata",url,
                          "opera_official_program_date_only","primary_program")
            if r: out.append(r)
    elif "agendalaplata.ar" in host:
        params=parse_qs(urlsplit(url).query)
        param=(params.get("fecha") or [None])[0]
        try: day=date.fromisoformat(param) if param else None
        except ValueError: day=None
        if day and active_date(day):
            ps=[t for tag,t in blocks.chunks if tag=="p"]
            # Agenda Genda renders category, event name, and clock|venue in consecutive p tags.
            for i in range(len(ps)-2):
                cat,title,when=ps[i:i+3]
                if not re.search(r"\b(?:Cine|Teatro|Música|Muestra|Expo|Taller|Ciencia|Danza|Literatura|Actividad|Fiesta)\b",cat,re.I):
                    continue
                if len(title)<4 or len(title)>180 or "¿Con quién" in title:
                    continue
                m=re.search(r"\b((?:[01]?\d|2[0-3]):[0-5]\d)\s*hs?\s*\|\s*(.{3,180})",when,re.I)
                if not m: continue
                r=make_record(title,day,m.group(1).zfill(5),m.group(2),url,
                              "genda_dated_listing","secondary_agenda")
                if r:out.append(r)
    seen=set()
    unique=[]
    for r in out:
        key=(r["title"].casefold(),r["event_date"],r["event_time"],(r["venue"] or "").casefold())
        if key not in seen:
            seen.add(key);unique.append(r)
    return unique[:100]

def special_links(url,page):
    """Verified family navigation: dates for Genda; tickets for Ópera."""
    host,path=scope(url)
    if host.endswith("agendalaplata.ar") and path=="/":
        links=[]
        now=datetime.now().date()
        for raw,label in page.links:
            if not raw.startswith("https://") and not raw.startswith("/?") and not raw.startswith("?"):
                continue
            absolute=raw if raw.startswith("https://") else "https://agendalaplata.ar"+(raw if raw.startswith("/") else "/"+raw)
            h,p=scope(absolute)
            if h not in ("agendalaplata.ar","www.agendalaplata.ar") or p!="/":
                continue
            d=(parse_qs(urlsplit(absolute).query).get("fecha") or [None])[0]
            try:day=date.fromisoformat(d) if d else None
            except ValueError:day=None
            if day and now <= day <= now+timedelta(days=4):
                links.append((absolute,"agenda por fecha"))
        return links[:5]
    if host.endswith("operalp.com.ar") and path.rstrip("/")=="/agenda":
        return [(href,"ticketera oficial enlazada")
                for href,label in page.links
                if re.match(r"^https://livepass\.com\.ar/events/[a-z0-9-]+/?(?:\?.*)?$",href,re.I)][:15]
    return []
