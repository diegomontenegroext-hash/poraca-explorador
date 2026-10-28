#!/usr/bin/env python3
"""Extract individual event sessions from known agenda layouts, no publication.

A listing is *evidence to review*, not an accepted event. No web requests here.
URLs are always real source/document URLs; no manufactured post anchors.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
import json
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
              "operalp.com.ar","www.operalp.com.ar",
              "teatrometrolp.com.ar","www.teatrometrolp.com.ar",
              "teatroargentino.gba.gob.ar","lumenartis.org","www.lumenartis.org",
              "agendadecine.com","www.agendadecine.com",
              "feriaedita.com.ar","www.feriaedita.com.ar",
              "gritos.planetario.unlp.edu.ar",
              "www.fcnym.unlp.edu.ar",
              "alpedo.ar","www.alpedo.ar"}
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
    at=at or datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
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

def structured_sessions(raw,url):
    """All schema.org Events, not only the first one in a JSON-LD graph."""
    # The SAME structured Event may be mirrored by a secondary agenda.
    # A schema.org label never upgrades its source into the organizer.
    host=scope(url)[0]
    tier=("secondary_agenda" if host in (
          "agendalaplata.ar","www.agendalaplata.ar",
          "alpedo.ar","www.alpedo.ar") else "primary_structured_page")
    out=[]
    scripts=re.findall(r"<script\b(?=[^>]*\btype\s*=\s*['\"]application/ld\+json['\"])[^>]*>(.*?)</script\s*>",
                       raw[:700_000],re.I|re.S)
    for script in scripts[:25]:
        try: root=json.loads(html.unescape(script).strip())
        except (ValueError,TypeError): continue
        nodes=[root]
        attempts=0
        while nodes and attempts<250:
            attempts+=1
            item=nodes.pop(0)
            if isinstance(item,list):
                nodes.extend(item[:120]);continue
            if not isinstance(item,dict):
                continue
            for key in ("@graph","itemListElement","mainEntity","hasPart","events"):
                if isinstance(item.get(key),(dict,list)):
                    nodes.append(item[key])
            typ=item.get("@type",[])
            types=typ if isinstance(typ,list) else [typ]
            if not any(isinstance(t,str) and t.lower().split("/")[-1] in
                       ("event","musicevent","theaterevent","danceevent","visualartsevent",
                        "educationevent","festival","screeningevent")
                       for t in types):
                continue
            title=item.get("name")
            if not isinstance(title,str):continue
            starts=item.get("startDate")
            starts=starts if isinstance(starts,list) else [starts]
            loc=item.get("location")
            if isinstance(loc,list):loc=next((v for v in loc if isinstance(v,(dict,str))),None)
            venue=loc.get("name") if isinstance(loc,dict) else loc if isinstance(loc,str) else None
            for value in starts[:20]:
                if not isinstance(value,str):continue
                try:
                    if len(value)==10:
                        d=date.fromisoformat(value)
                        clock=None
                    else:
                        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
                        if dt.tzinfo:dt=dt.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
                        d=dt.date()
                        clock=dt.strftime("%H:%M")
                except ValueError:continue
                r=make_record(title,d,clock,venue,url,
                              "schema_org_event_sessions",tier)
                if r:out.append(r)
    return out

def spanish_day_month_year(value):
    """Requires an explicit YEAR for ticket listings."""
    m=re.search(r"\b([0-3]?\d)\s+de\s+([a-záéíóúñ]+)\s+de\s+(20\d{2})\b",value,re.I)
    if not m: return None
    month=MONTHS.get(m.group(2).casefold())
    if not month: return None
    try:return date(int(m.group(3)),month,int(m.group(1)))
    except ValueError:return None

def lumen_unyearred_date(value,now=None):
    """Lumen sometimes writes only 'domingo 1 de noviembre'; constrain to near-term."""
    now=now or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    m=re.search(r"\b([0-3]?\d)\s+de\s+([a-záéíóúñ]+)\b",value,re.I)
    if not m:return None
    month=MONTHS.get(m.group(2).casefold())
    if not month:return None
    possibilities=[]
    for year in (now.year,now.year+1):
        try:day=date(year,month,int(m.group(1)))
        except ValueError:continue
        if now-timedelta(days=14)<=day<=now+timedelta(days=90):
            possibilities.append(day)
    return min(possibilities) if len(possibilities)==1 else None

def alpedo_dated_sessions(raw,url):
    """Read date-scoped Alpedó cards only; all evidence stays SECONDARY.

    Alpedó's initial HTTP shell can contain no cards. The bounded browser
    fallback supplies rendered HTML for exactly the visited date URL.
    A card is an h6 TITLE followed by one clock and one explicit venue
    before the NEXT h6; generic museum opening-hour ranges are excluded.
    """
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname not in ("alpedo.ar","www.alpedo.ar")
        or p.path!="/" or p.port is not None or p.fragment):
        return []
    query=parse_qs(p.query)
    if set(query)!={"fecha"} or len(query["fecha"])!=1:
        return []
    try:day=date.fromisoformat(query["fecha"][0])
    except (TypeError,ValueError):return []
    if not active_date(day):
        return []
    # Require the rendered month's label to corroborate the URL date.
    # A stale SPA showing yesterday's page must not pollute tomorrow.
    plain=tidy(re.sub(r"<[^>]+>"," ",raw[:250_000]))
    header=re.search(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|"
        r"agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+"
        r"(20\d{2})\b",plain,re.I)
    if not header or MONTHS.get(header.group(1).casefold())!=day.month or int(header.group(2))!=day.year:
        return []
    cards=list(re.finditer(r"<h6\b[^>]*>(.*?)</h6\s*>",raw[:450_000],re.I|re.S))
    # "Finalizadas" begins an archive of earlier activities. It marks
    # upcoming sections by position, rather than invalidating the last
    # legitimate future card immediately before that heading.
    archive=re.search(r"<[^>]+>\s*Finalizadas\s*</[^>]+>",raw[:450_000],re.I)
    out=[]
    for i,m in enumerate(cards[:100]):
        if archive and m.start()>archive.start():
            continue
        title=tidy(re.sub(r"<[^>]+>"," ",m.group(1)))
        if not 5<=len(title)<=180:
            continue
        end=cards[i+1].start() if i+1<len(cards) else min(m.end()+1600,len(raw))
        # The archive header can sit immediately after the LAST current
        # card. Trim it instead of throwing away that real performance;
        # otherwise "Finalizadas" supplies unrelated clocks/venues.
        if archive and m.end()<=archive.start()<end:
            end=archive.start()
        tail=raw[m.end():min(end,m.end()+1800)]
        # HTML may end MID-TAG at this bounded slice (image gallery
        # markup is long). Regex removing only COMPLETE tags leaks
        # literal '<div class="img...' into the venue. The existing
        # HTMLParser ignores incomplete tags, scripts and styling.
        card_text=tidy(" ".join(visible_blocks(tail).text))
        clocks=CLOCK.findall(card_text)
        # "07:00 a 19:00" is museum opening hours, not a dated show.
        if len(clocks)!=1:
            continue
        match=CLOCK.search(card_text)
        if not match:
            continue
        venue=card_text[match.end():].strip(" |·–—:-")
        venue=re.split(r"\b(?:Más información|Detalles|Inscribite|Compartir)\b",
                       venue,maxsplit=1,flags=re.I)[0].strip()
        # Defensive boundary: a venue must be human-visible text, not
        # a partial tag, JS initializer or residual browser widget.
        if (not 4<=len(venue)<=130 or "<" in venue or ">" in venue
            or re.search(r"\\b(?:class=|document\\.|var tooltipTriggerList)\\b",venue,re.I)):
            continue
        rec=make_record(title,day,clocks[0].zfill(5),venue,url,
                        "alpedo_dated_card_rendered","secondary_agenda")
        if rec:out.append(rec)
    # Duplicate mobile markup must not multiply observations.
    return list({(x["title"],x["event_date"],x["event_time"],x["venue"]):x
                for x in out}.values())

def source_specific_sessions(raw,url,blocks):
    """Four known official layouts; no extrapolation of recurrences."""
    host,path=scope(url)
    visible=tidy(" ".join(blocks.text))
    records=[]
    if host in ("alpedo.ar","www.alpedo.ar"):
        return alpedo_dated_sessions(raw,url)
    if host.endswith("teatrometrolp.com.ar"):
        venue="Teatro Metro"
        if re.fullmatch(r"/entrada/[^/]+/?",path):
            title=next((t for tname,t in blocks.headings if tname in ("h1","h2")),None)
            # Only the actual 'Día/s y horario/s' ticket field, not opening hours
            # of the theatre or presale windows.
            m=re.search(r"Día/s\s+y\s+horario/s\s*:\s*(.{0,650})",visible,re.I)
            if title and m:
                for found in re.finditer(
                    r"([0-3]?\d\s+de\s+[a-záéíóúñ]+\s+de\s+20\d{2})"
                    r"\s*[.,-]?\s*((?:[01]?\d|2[0-3]):[0-5]\d)\s*hs",m.group(1),re.I):
                    d=spanish_day_month_year(found.group(1))
                    tm=found.group(2).zfill(5)
                    rec=make_record(title,d,tm,venue,url,"metro_official_ticket_date","primary_venue")
                    if rec:records.append(rec)
        elif re.fullmatch(r"/entradas/cartelera(?:/[1-3])?/?",path):
            # Index is organization-owned; individual ticket pages have
            # higher evidentiary value and arrive via watchlist or anchor.
            titles=list(re.finditer(r"<h3\b[^>]*>(.*?)</h3\s*>",raw,re.I|re.S))
            for i,m in enumerate(titles[:80]):
                end=titles[i+1].start() if i+1<len(titles) else len(raw)
                segment=raw[m.end():min(end,m.end()+2500)]
                title=tidy(re.sub(r"<[^>]+>"," ",m.group(1)))
                dated=re.search(r"([0-3]?\d/[01]?\d/20\d{2})\s*-\s*"
                    r"((?:[01]?\d|2[0-3]):[0-5]\d)\s*hs",tidy(re.sub(r"<[^>]+>"," ",segment)),re.I)
                if dated:
                    rec=make_record(title,parse_dmy(dated.group(1)),dated.group(2).zfill(5),venue,url,
                        "metro_official_cartelera","primary_program")
                    if rec:records.append(rec)
    elif host=="teatroargentino.gba.gob.ar" and re.match(r"/meet/\d+/?$",path):
        # The raw source uses nested tags and sometimes invalid nested <p>.
        # Extract the explicit event date; booking windows are distinct.
        raw_plain=tidy(re.sub(r"<[^>]*>"," ",raw))
        exact=re.search(r"\bFecha\s+del\s+evento\s+([0-3]?\d/[01]?\d/20\d{2})\s+"
                        r"((?:[01]?\d|2[0-3]):[0-5]\d)(?::[0-5]\d)?\b",
                        raw_plain,re.I)
        if exact:
            paras=[tidy(re.sub(r"<[^>]*>"," ",item))
                for item in re.findall(r"<p\b[^>]*>(.*?)</p\s*>",raw,re.I|re.S)]
            # A caption can contain pipes: "Concierto | Horacio ... | Martes".
            captions=[t for t in paras if "|" in t and
                re.search(r"obra|concierto|masterclass|teatro|funci[oó]n",t,re.I)]
            captions += [t for name,t in blocks.chunks if name=="p" and "|" in t]
            caption=next((t for t in captions if len(t)>10),None)
            if not caption:
                # Actual public pages sometimes render the caption in <div>
                # rather than <p>. Only take captions that contain a weekday,
                # explicit day/month and clock; do not take a promotional
                # sentence, a book/ticket deadline, or the baseline title.
                body_text=tidy(" ".join(blocks.text))
                # Anchor on the printed weekday/date/hour pair, then find the
                # *nearest explicit event type*. This prevents navigation like
                # "teatro Historia Salas TEMPORADA..." from leaking into titles.
                header=re.search(
                    r"\|\s*(?:lunes|martes|mi[eé]rcoles|jueves|viernes|"
                    r"s[aá]bado|domingo)\s+([0-3]?\d)/([01]?\d)"
                    r"\s*\|\s*((?:[01]?\d|2[0-3]):[0-5]\d)\b",
                    body_text,re.I)
                if header:
                    official_date=parse_dmy(exact.group(1))
                    if (official_date and int(header.group(1))==official_date.day
                        and int(header.group(2))==official_date.month
                        and header.group(3)==exact.group(2).zfill(5)):
                        before=body_text[max(0,header.start()-260):header.start()]
                        labels=list(re.finditer(
                            r"\b(?:Obra teatral|Concierto|Masterclass|"
                            r"Clase magistral|Charlas Magistrales|Espect[aá]culo|"
                            r"Ballet|Danza)\b",before,re.I))
                        if labels:
                            caption=before[labels[-1].start():].strip()
            pieces=[tidy(x) for x in caption.split("|")] if caption else []
            title=(pieces[1] if len(pieces)>1 and
                   pieces[0].casefold() in ("concierto","teatro","masterclass","obra teatral")
                   else pieces[0] if pieces else None)
            room=next((t for t in paras if re.match(r"^SALA\s+[a-záéíóúñ]+",t,re.I)),None)
            if not room:
                room=next((t for name,t in blocks.chunks
                    if name=="p" and re.match(r"^SALA\s+[a-záéíóúñ]+",t,re.I)),None)
            if not room:
                found_room=re.search(
                    r"\bSALA\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+"
                    r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b",visible)
                if found_room:room="SALA "+found_room.group(1)
            venue=("Teatro Argentino — "+room if room else "Teatro Argentino")
            if title:
                rec=make_record(title,parse_dmy(exact.group(1)),exact.group(2).zfill(5),venue,url,
                                "argentino_official_fecha_evento","primary_venue")
                if rec:records.append(rec)
    elif host.endswith("lumenartis.org") and (path=="/" and parse_qs(urlsplit(url).query).get("post_type")==["funcion"]):
        # WordPress can insert navigation paragraphs before the event article.
        # Prefer the original paragraph containing a concrete near-term date.
        paras=re.findall(r"<p\b[^>]*>(.*?)</p\s*>",raw,re.I|re.S)
        when=None
        event_para=None
        for paragraph in paras[:120]:
            text=tidy(re.sub(r"<[^>]*>"," ",paragraph))
            candidate=re.search(r"\b(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+"
                r"([0-3]?\d\s+de\s+[a-záéíóúñ]+)\s+a\s+las\s+"
                r"((?:[01]?\d|2[0-3])(?::[0-5]\d)?)\s*h\b",text,re.I)
            if candidate:
                when=candidate;event_para=paragraph;break
        if when:
            d=lumen_unyearred_date(when.group(1))
            clock=when.group(2)
            clock=(clock+":00" if ":" not in clock else clock).zfill(5)
            # Work title in the event paragraph; fallback to a real page title,
            # never to the unverified historical baseline name.
            em=re.search(r"<em\b[^>]*>(.*?)</em>",event_para,re.I|re.S)
            title=tidy(re.sub(r"<[^>]*>"," ",em.group(1))) if em else None
            if not title:
                head=next((t for tag,t in blocks.headings if tag=="h1"),None)
                if head: title=head
            if not title:
                head=re.search(r"<title\b[^>]*>(.*?)</title\s*>",raw,re.I|re.S)
                if head: title=tidy(re.sub(r"<[^>]*>"," ",head.group(1))).split(" – Teatro de Cámara")[0]
            if title and d:
                rec=make_record(title,d,clock,"Lumen Artis / Teatro de Cámara de City Bell",
                                url,"lumen_official_prose_date","primary_venue")
                if rec:records.append(rec)
    elif host in ("agendadecine.com","www.agendadecine.com") and (
        path.endswith("/octubre-en-cine-select") or path.endswith("/octubre-en-cine-ecoselect")):
        # Time/date from a specialized SECONDARY cinema programme, not
        # from a municipality/official owner. October-only historical URL.
        local_today=datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
        venue=("Cine Ecoselect (Espacio INCAA)"
               if path.endswith("cine-ecoselect") else "Cine Select (Espacio INCAA)")
        for t,paragraph in blocks.chunks[:250]:
            if t!="p":continue
            m=re.match(
                r"^(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+"
                r"([0-3]?\d)\s+de\s+octubre\s+"
                r"((?:[01]?\d|2[0-3]):[0-5]\d)\s+[—–-]\s+(.{6,340})$",
                paragraph,re.I)
            if not m:continue
            try: d=date(local_today.year,10,int(m.group(1)))
            except ValueError:continue
            tail=m.group(3)
            # "Espacio INCAA (entrada $5000): Película / Dir..."
            # or "Ciclo Freakshow: Película"; no inference of screening time.
            title=tail.split(": ",1)[1] if ": " in tail else tail
            title=title.split(" / Dir",1)[0].strip()
            title=title.lstrip("_ ")
            rec=make_record(title,d,m.group(2),venue,url,
                            "agendadecine_monthly_screening","secondary_cinema_agenda")
            if rec:records.append(rec)
    elif (host=="www.fcnym.unlp.edu.ar" and
          path=="/novedades/leccion-magistral-emilio-custodio-sobre-aguas-subterraneas-en-fcnym/"):
        # FCNyM publishes this event in a prose article, not a ticket
        # calendar. The body omits the year, so require an ORIGINAL
        # publication date from page metadata and agreement of weekday.
        # An unrelated '2026' in asset URLs or copyright is NOT evidence.
        published=re.search(
            r"""(?:["']datePublished["']\s*:\s*["']|"""
            r"""article:published_time[^>]*content\s*=\s*["']|"""
            r"""<time\b[^>]*datetime\s*=\s*["'])"""
            r"""(20\d{2}-[01]\d-[0-3]\d)""",
            raw[:150_000],re.I)
        heading=next((name for tag,name in blocks.headings if tag=="h1"),None)
        details=re.search(
            r"\bmi[eé]rcoles\s+([0-3]?\d)\s+de\s+noviembre\s+"
            r"a\s+las\s+((?:[01]?\d|2[0-3]))\s+horas?\s+"
            r"en\s+el\s+Auditorio\s+de\s+Planta\s+Baja\s+"
            r"de\s+la\s+Facultad\s+de\s+Ciencias\s+Naturales\s+y\s+Museo\b",
            visible,re.I)
        if published and heading and details and re.search(
                r"Lecci[oó]n Magistral Emilio Custodio",heading,re.I):
            try:
                publication=date.fromisoformat(published.group(1))
                day=date(publication.year,11,int(details.group(1)))
            except ValueError:
                publication=day=None
            if (publication and day and day.weekday()==2 and
                    0 <= (day-publication).days <= 90):
                record=make_record(
                    heading,day,details.group(2).zfill(2)+":00",
                    "Auditorio de Planta Baja · Facultad de Ciencias Naturales y Museo",
                    url,"fcnym_unlp_official_article_date_time","primary_organizer")
                if record: records.append(record)
    elif host=="gritos.planetario.unlp.edu.ar" and path=="/2026/index.html":
        # This official festival page states a RANGE, not a timetable.
        # Capture one umbrella programme at its start; never invent
        # screenings on each date or missing clocks.
        if (re.search(r"\bFestival Internacional de Cine de Horror\b",visible,re.I)
                and re.search(r"\bV Edici[oó]n\s*-\s*2026\b",visible,re.I)
                and re.search(r"\bPlanetario\b",visible,re.I)):
            dates=re.search(
                r"\bDel\s+([0-3]?\d)\s*/\s*OCT\s+al\s+([0-3]?\d)\s*/\s*NOV\s+2026\b",
                visible,re.I)
            if not dates:
                # The same original repeats the date RANGE in prose.
                dates=re.search(
                    r"\bentre\s+los\s+d[ií]as\s+([0-3]?\d)\s+de\s+octubre"
                    r"\s+y\s+([0-3]?\d)\s+de\s+noviembre\s+de\s+2026\b",
                    visible,re.I)
            if dates:
                try:
                    start=date(2026,10,int(dates.group(1)))
                    end=date(2026,11,int(dates.group(2)))
                except ValueError:
                    start=end=None
                if start and end and 1<=(end-start).days<=7:
                    rec=make_record(
                        "Gritos en el Planetario · Festival Internacional de Cine de Horror",
                        start,None,"Planetario UNLP · Paseo del Bosque",
                        url,"gritos_festival_official_date_range_start","primary_program")
                    if rec:records.append(rec)
    elif host.endswith("casametro.com.ar") and path.rstrip("/")=="/categoria-producto/casa-metro":
        # WooCommerce's official category page prints date, starting clock,
        # venue and title in EACH product card. Keep the fields scoped to
        # the same <li class="product">; never zip dates with other cards.
        # Ticket end time (often 00:00) is NOT a second performance.
        for card in re.findall(
                r"<li\b(?=[^>]*\bclass\s*=\s*['\"][^'\"]*\bproduct\b)[^>]*>"
                r"(.*?)</li\s*>",raw[:700_000],re.I|re.S)[:100]:
            heading=re.search(r"<h2\b[^>]*>(.*?)</h2\s*>",card,re.I|re.S)
            if not heading:
                continue
            title=tidy(re.sub(r"<[^>]+>"," ",heading.group(1)))
            card_text=tidy(re.sub(r"<[^>]+>"," ",card))
            dm=re.search(
                r"\bFecha\s*:\s*([a-záéíóúñ]+)\s+([0-3]?\d)\s*,?\s*(20\d{2})\b",
                card_text,re.I)
            tm=re.search(
                r"\bHorario\s*:\s*((?:[01]?\d|2[0-3]):[0-5]\d)\b",
                card_text,re.I)
            if not (dm and tm):
                continue
            month=MONTHS.get(dm.group(1).casefold())
            try:
                event_day=date(int(dm.group(3)),month,int(dm.group(2))) if month else None
            except ValueError:
                event_day=None
            venue=("Auditorio Charly García" if
                   re.search(r"\bAuditorio Charly García\b",card_text,re.I)
                   else "Casa Metro" if re.search(r"\bCasa Metro\b",card_text,re.I)
                   else None)
            if venue:
                record=make_record(
                    title,event_day,tm.group(1).zfill(5),venue,url,
                    "casa_metro_official_category_card","primary_program")
                if record: records.append(record)
    elif host.endswith("feriaedita.com.ar") and path in ("","/"):
        # Official 2026 homepage advertises "EDITA: 5 y 6 de diciembre",
        # with #EDITA2026 printed elsewhere. This establishes TWO dates but
        # never an opening hour; both remain unverified/without clock.
        if re.search(r"#EDITA\s*2026\b",visible,re.I):
            m=re.search(r"\bEDITA\s*:\s*([0-3]?\d)\s+y\s+([0-3]?\d)"
                        r"\s+de\s+diciembre\b",visible,re.I)
            if m and ("Museo" in visible or "La Plata" in visible):
                for val in (m.group(1),m.group(2)):
                    try:day=date(2026,12,int(val))
                    except ValueError:continue
                    rec=make_record(
                        "EDITA 10 años · Feria de Editoriales Independientes",
                        day,None,"Avenida 51 entre 5 y 6, frente al Museo Emilio Pettoruti",
                        url,"edita_official_explicit_dates","primary_program")
                    if rec:records.append(rec)
    return records

def extract_listings(raw,url):
    """Returns individual session observations; never returns verified status."""
    host,path=scope(url)
    if host not in SCOPED_HOSTS:
        return []
    blocks=visible_blocks(raw)
    out=structured_sessions(raw,url)
    out.extend(source_specific_sessions(raw,url,blocks))
    if "alternativateatral.com" in host and re.match(r"/obra\d+",path):
        title=next((t for tag,t in blocks.headings if tag=="h1"),None)
        if title:
            text=tidy(" ".join(blocks.text))
            # "Histórico de funciones" lists PAST VENUES, often immediately
            # after the current performance. Never use an archive room or
            # ticket date to describe an upcoming function.
            current_text=re.split(r"\bHist[oó]rico\s+de\s+funciones\b",
                                  text,maxsplit=1,flags=re.I)[0]
            # This HTML variant sometimes wraps venue/address in a <p>,
            # while responsive alternatives use <div> / plain text.
            mvenue=re.search(
                r"<p\b[^>]*>\s*([^<]{4,95})<br\s*/?>\s*"
                r"(?:Calle|Av\.?|Avenida|Diagonal|Diag\.?|"
                r"Ruta|Boulevard|Bulevar)\b",raw,re.I|re.S)
            venue=tidy(mvenue.group(1)) if mvenue else None
            if venue and venue.casefold() not in current_text.casefold():
                venue=None
            if not venue:
                # A specific venue MUST be printed in the CURRENT part of
                # this original. Neither a historical venue nor the URL
                # determines where today's performance takes place.
                known_room=re.search(
                    r"\b(TEATRO ESTUDIO DE LAS ARTES|ESPACIO 44|"
                    r"EN ESO ESTAMOS|ESCENARIO[- ]?40|"
                    r"CENTRO CULTURAL VIEJO ALMACEN EL OBRERO)\b",
                    current_text,re.I)
                if known_room:venue=tidy(known_room.group(1))
            if not venue and "av. 51 entre 9 y 10" in current_text.casefold():
                venue="Teatro Argentino"
            # 'Entrada:' can contain several clocks before a printed date.
            for m in re.finditer(r"Entrada:\s*.{0,220}?\b([0-3]?\d/[01]?\d/20\d{2})",current_text,re.I):
                d=parse_dmy(m.group(1))
                times=list(dict.fromkeys(CLOCK.findall(m.group(0))))
                for tm in times[:6]:
                    rec=make_record(title,d,tm,venue,url,
                                    "alternativa_obra_funcion_text","primary_ticket_listing")
                    if rec:out.append(rec)
            # Other works advertise explicit individual dates *without* an
            # Entrada label. 'Hasta el' is never expanded into recurring
            # Fridays/Sundays. Only printed dates are considered, with a
            # weekday/date agreement check before adding a session.
            weekdays={"lunes":0,"martes":1,"miercoles":2,"miércoles":2,
                      "jueves":3,"viernes":4,"sabado":5,"sábado":5,"domingo":6}
            for m in re.finditer(
                r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
                r"\s*-\s*((?:[01]?\d|2[0-3]):[0-5]\d)\s*hs"
                r"\s*-\s*(?:Hasta\s+el\s+)?"
                r"([0-3]?\d/[01]?\d/20\d{2})"
                r"(?:\s+y\s+([0-3]?\d/[01]?\d/20\d{2}))?",
                current_text,re.I):
                for value in (m.group(3),m.group(4)):
                    if not value:continue
                    d=parse_dmy(value)
                    if not d or d.weekday()!=weekdays[m.group(1).casefold()]:
                        continue
                    rec=make_record(title,d,m.group(2).zfill(5),venue,url,
                                    "alternativa_explicit_date_no_ticket_label",
                                    "primary_ticket_listing")
                    if rec and not any(x["title"]==rec["title"] and x["event_date"]==rec["event_date"]
                                       and x["event_time"]==rec["event_time"] for x in out):
                        out.append(rec)
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
        # Every heading is one dated performance on the official site. The
        # organizer's outbound ticket URL is the ORIGINAL click-through,
        # not a URL guessed from the title. Never infer a clock from a slug.
        headings=list(re.finditer(r"<h[234]\b[^>]*>(.*?)</h[234]\s*>",raw,re.I|re.S))
        for i,m in enumerate(headings[:60]):
            title=tidy(re.sub(r"<[^>]+>"," ",m.group(1)))
            end=headings[i+1].start() if i+1<len(headings) else len(raw)
            tail=raw[m.end():min(end,m.end()+4000)]
            d=parse_dmy(tidy(re.sub(r"<[^>]+>"," ",tail)))
            ticket=re.search(r'''href\s*=\s*["'](https://livepass\.com\.ar/events/[^"']+)["']''',
                             tail,re.I)
            proof_url=html.unescape(ticket.group(1)) if ticket else url
            r=make_record(title,d,None,"Teatro Ópera La Plata",proof_url,
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
            # Some responsive layouts put the cards in non-<p> wrappers.
            # Inspect human-visible line sequence; require actual time and
            # venue, never treat a page title or a generic CTA as an event.
            if not any(r["method"]=="genda_dated_listing" for r in out):
                lines=[tidy(x) for x in "".join(blocks.text).splitlines() if tidy(x)]
                for i,line in enumerate(lines):
                    # Only the row beginning with a clock can start a card.
                    # Otherwise look-ahead would duplicate its parent/title.
                    if not re.match(r"^\s*(?:[01]?\d|2[0-3]):[0-5]\d\s*hs?\b",line,re.I):
                        continue
                    m=re.search(r"\b((?:[01]?\d|2[0-3]):[0-5]\d)\s*hs?\s*\|\s*(.{3,160})",
                                " ".join(lines[i:i+3]),re.I)
                    if not m or i<1:continue
                    title=lines[i-1]
                    if (len(title)<6 or len(title)>180 or
                        re.search(r"avisame|con qui[eé]n|buscar evento|publicar|recib[ií]",
                                  title,re.I)):
                        continue
                    category=" ".join(lines[max(0,i-7):i-1])
                    if not re.search(r"Cine|Teatro|Música|Muestra|Expo|Taller|Ciencia|Danza|Literatura|Actividad|Fiesta",
                                     category,re.I):
                        continue
                    venue=re.split(r"\+\s*Info|Avisame!|¿Con quién",m.group(2),maxsplit=1,flags=re.I)[0].strip()
                    r=make_record(title,day,m.group(1).zfill(5),venue,url,
                                  "genda_dated_listing","secondary_agenda")
                    if r:out.append(r)
    seen=set()
    unique=[]
    for r in out:
        key=(r["title"].casefold(),r["event_date"],r["event_time"],(r["venue"] or "").casefold())
        if key not in seen:
            seen.add(key);unique.append(r)
    return unique[:100]

def special_links(url,page,at=None):
    """Verified source-specific discovery with near-date priority and rotation."""
    host,path=scope(url)
    if host in ("teatrometrolp.com.ar","www.teatrometrolp.com.ar") and (
            path.rstrip("/")=="/entradas/cartelera"):
        # La cartelera del Teatro Metro tiene a la vez indices paginados
        # y fichas /entrada/<slug>. Antes solo se leía la segunda página:
        # faltaban los originales de funciones próximas y se perdía el
        # primer E2E de Las Hijas 08/11 (dos funciones separadas).
        # Aperturas DENTRO de MAX_DETAILS_FULL=6, nunca cron adicional.
        discovered={}
        tickets={}
        for href,label in page.links:
            raw=(href or "").strip()
            if not raw or raw.startswith("//"):
                continue
            if raw.startswith("/"):
                absolute="https://"+host+raw
            elif raw.startswith("https://"):
                absolute=raw
            else:
                continue
            p=urlsplit(absolute)
            if (p.scheme!="https" or p.hostname not in (
                    "teatrometrolp.com.ar","www.teatrometrolp.com.ar")
                or p.username or p.password or p.port not in (None,443)
                or p.fragment):
                continue
            if re.fullmatch(r"/entradas/cartelera/([1-3])/?",p.path,re.I):
                if p.query and not re.fullmatch(
                        r"(?:anio=&mes=|mes=&anio=)",p.query):
                    continue
                number=int(re.search(r"/([1-3])/?$",p.path).group(1))
                discovered.setdefault(number,("https://"+p.hostname+
                                    "/entradas/cartelera/"+str(number)+"/",
                                    "cartelera oficial, pagina "+str(number)))
            elif (not p.query and re.fullmatch(
                    r"/entrada/[a-z0-9_.-]+/?",p.path,re.I)):
                # Sólo fichas realmente enlazadas DESDE la cartelera
                # oficial, nunca construir un slug desde el título.
                normalized="https://"+p.hostname+p.path.rstrip("/")
                tickets.setdefault(normalized,(normalized,"detalle oficial"))
        page_link=[discovered[min(discovered)]] if discovered else []
        if not page_link and tickets:
            # El original devuelve HTTP200 en /1/ pero no siempre ofrece
            # 'Siguiente'. Una apertura adicional sólo si hay fichas
            # /entrada/ en la portada (no generar paginación sin señal).
            page_link=[("https://"+host+"/entradas/cartelera/1/",
                        "cartelera oficial verificada, pagina 1")]
        ordered=list(tickets.values())   # Orden de cartelera, fechas próximas.
        slots=max(0,6-len(page_link))
        fixed=ordered[:min(2,slots)]
        later=ordered[len(fixed):]
        chosen=list(page_link)+fixed
        if later and len(chosen)<6:
            now=at or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
            offset=(now.date().toordinal()*3+now.hour//8)%len(later)
            chosen.extend(later[(offset+i)%len(later)]
                          for i in range(min(6-len(chosen),len(later))))
        return chosen[:6]
    if host in ("casametro.com.ar","www.casametro.com.ar") and (
            path in ("/","/cartelera/","/categoria-producto/casa-metro/")):
        # casa_metro_dated_links_rotating: the original category is ordered
        # by upcoming event date. Its ticket/product URLs carry the exact
        # clock in their own detail pages; at most 6 details can be opened
        # per FULL. Keep the first 3, rotate the rest between 8h slots.
        # Never traverse outbound links, images or unrelated WooCommerce URLs.
        by_url={}
        for href,label in page.links:
            raw=(href or "").strip()
            if not raw or raw.startswith("//"):
                continue
            if raw.startswith("/"):
                absolute="https://"+host+raw
            elif raw.startswith("https://"):
                absolute=raw
            else:
                continue
            p=urlsplit(absolute)
            if (p.scheme!="https" or p.hostname not in
                    ("casametro.com.ar","www.casametro.com.ar") or
                    p.port not in (None,443) or p.username or p.password or
                    p.query or p.fragment or
                    not re.fullmatch(r"/evento/[a-z0-9-]+/?",p.path,re.I)):
                continue
            by_url.setdefault(absolute,(absolute,"cartelera oficial, detalle"))
            if len(by_url)>=40:
                break
        ordered=list(by_url.values())
        now=at or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
        front=ordered[:3]
        later=ordered[3:]
        if later:
            offset=(now.date().toordinal()*3+now.hour//8)%len(later)
            front.extend(later[(offset+i)%len(later)]
                         for i in range(min(3,len(later))))
        return front[:6]
    if host.endswith("agendalaplata.ar") and path=="/":
        now=at or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
        today=now.date()
        date_links={}
        for raw,label in page.links:
            if not raw.startswith("https://") and not raw.startswith("/?") and not raw.startswith("?"):
                continue
            absolute=raw if raw.startswith("https://") else "https://agendalaplata.ar"+(raw if raw.startswith("/") else "/"+raw)
            h,p=scope(absolute)
            if h not in ("agendalaplata.ar","www.agendalaplata.ar") or p!="/":
                continue
            d=(parse_qs(urlsplit(absolute).query).get("fecha") or [None])[0]
            try: day=date.fromisoformat(d) if d else None
            except ValueError: day=None
            if day and today<=day<=today+timedelta(days=60):
                date_links[day]=absolute
        ordered=sorted(date_links)
        # Preserve near-term coverage; rotate the remaining three slots so
        # the distant concert/cinema dates are not starved by daily restarts.
        near=[d for d in ordered if d<=today+timedelta(days=1)][:2]
        later=[d for d in ordered if d not in near]
        selected=list(near)
        if later:
            offset=(today.toordinal()*3+now.hour//8)%len(later)
            for i in range(min(5-len(selected),len(later))):
                selected.append(later[(offset+i)%len(later)])
        return [(date_links[day],"agenda por fecha") for day in selected[:5]]
    if host.endswith("operalp.com.ar") and path.rstrip("/")=="/agenda":
        return [(href,"ticketera oficial enlazada")
                for href,label in page.links
                if re.match(r"^https://livepass\.com\.ar/events/[a-z0-9-]+/?(?:\?.*)?$",href,re.I)][:15]
    return []
