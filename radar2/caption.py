"""Conservative caption interpretation. Original text is always retained.
Date inference is anchored to publication in Argentina, never acquisition time.
Unresolved schedules, midnight and cross-post host identity require review.
"""
import re
import unicodedata
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from collector import norm, compact
from extract import MONTHS,category
VERSION='caption-v1'
ZONE=ZoneInfo('America/Argentina/Buenos_Aires')
WEEK=['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
DATE=re.compile(r'\b([0-3]?\d)\s*(?:[/.]\s*(1[0-2]|0?[1-9])\b|(?:de\s+)?('+('|'.join(MONTHS))+r')\b)(?:\s*(?:de\s+|/)(20\d{2}))?',re.I)
CLOCK=re.compile(r'(?<![\d.])([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*(?:a\s*\d{1,2}(?:[:.]\d{2})?\s*)?(?:hs?\b|horas\b)',re.I)
PAST=re.compile(r'\b(postales|pasado|vivimos|presentaron|presento|nos quedaron|gracias por acompanarnos|asi vivimos|despide)\b')
CULTURE=re.compile(r'obra|teatro|taller|workshop|masterclass|milonga|fiesta|ciclo|concierto|recital|inaugur|muestra|festival|musica|musicaliza|libros|lectura|banda|entradas|en vivo')

def anchor(d):
 try:return datetime.fromisoformat(d['published_at'].replace('Z','+00:00')).astimezone(ZONE).date()
 except (KeyError,ValueError,TypeError):return None

def fold(text):
 return ''.join(c for c in unicodedata.normalize('NFKD',text).lower() if not unicodedata.combining(c))

def dates(text,base):
 out=[]
 if not base:return out
 n=fold(text)
 for m in DATE.finditer(n):
  try:
   month=int(m[2]) if m[2] else MONTHS[m[3].lower()]
   # Year close to publication, including December announcements for January.
   year=int(m[4]) if m[4] else base.year+int(base.month==12 and month==1)
   day=datetime(year,month,int(m[1])).date()
   out.append((m.start(),m.end(),day,'explicit_day_month' if m[4] else 'day_month_year_from_publication'))
  except ValueError:pass
 if out:return out
 # A named month plus a day without month is ambiguous: leave for review.
 if re.search(r'\b(hoy|manana)\b',n) and not re.search(r'hoy (?:compartimos|mostramos|recordamos)',n):
  m=re.search(r'\b(hoy|manana)\b',n);return [(m.start(),m.end(),base+timedelta(days=int(m[1]=='manana')),'relative_to_publication')]
 partial=re.search(r'\b('+('|'.join(WEEK))+r')\s+([0-3]?\d)(?![\d:.])\b',n)
 if partial:
  try:
   day=base.replace(day=int(partial[2]))
   if day<base:
    month=base.month%12+1;day=day.replace(year=base.year+int(month==1),month=month)
   if day.weekday()==WEEK.index(partial[1]):return [(partial.start(),partial.end(),day,'day_month_from_publication_weekday_verified')]
  except ValueError:pass
  return []
 m=re.search(r'\b(?:este|proximo|el)\s+('+('|'.join(WEEK))+r')\b',n)
 if m:
  day=base+timedelta(days=(WEEK.index(m[1])-base.weekday())%7)
  return [(m.start(),m.end(),day,'weekday_relative_to_publication')]
 return out

def interpret(c,d,accounts):
 text=unicodedata.normalize('NFKC',d.get('text','')).replace('*','');n=norm(text)
 base=anchor(d);schedules=dates(text,base);now=datetime.now(ZONE).date()
 retrospective=bool(PAST.search(n))
 regular=bool(re.search(r'horarios disponibles|clases regulares|todos los|cada (?:lunes|martes|miercoles|jueves|viernes)',n))
 cultural=bool(CULTURE.search(n))
 kind='retrospective' if retrospective else 'regular_class' if regular else 'cultural_document' if cultural else 'irrelevant'
 produced=[]
 # Actor catalog is evidence of account identity, not evidence of event venue.
 venues=[a for a in accounts if a.get('identity')!='ambiguous' and len(a.get('entity',''))>3 and norm(a['entity']) in n and a['entity'] not in ('Luti','Genda')]
 venue=next((a['entity'] for a in venues),None)
 venue_proof=text if venue else None
 # Explicit named places unknown to the catalog remain identity candidates.
 if not venue:
  m=re.search(r'(?:en |📍\s*)(Casa Mandala|Taller Laura Gan|Espacio E MACLA|Sala Ginastera|Sala Piazzolla|Miraflores)\b',text,re.I)
  if m:venue=m[1];venue_proof=m[0]
 title=next((compact(l).strip(' ✨🔥📚💃🦚⭐️✶⊹!') for l in text.splitlines() if l.strip()),d.get('title',''))[:160]
 # Never manufacture identities from a date-only heading or a generic teaser.
 if len(norm(title))<7 or re.fullmatch(r'(?:este |el )?(?:'+('|'.join(WEEK))+r').*',norm(title)):
  lines=[compact(l) for l in text.splitlines() if l.strip() and not re.search(r'link|entrada|anticipad|bio|^\W*(?:'+('|'.join(WEEK))+')',norm(l))]
  title=next((l for l in lines if len(norm(l))>6),title)[:160]
 if norm(title) in ('volvemos','con una nueva fecha'):title=next((compact(l) for l in text.splitlines() if re.search(r'milonga|concierto|taller|fiesta',norm(l))),title)[:160]
 if retrospective or regular or not cultural or re.search(r'hoy (?:compartimos|mostramos|recordamos)',n):schedules=[]
 for ix,(start,end,day,basis) in enumerate(schedules):
  # Duplicated dates within a caption do not create duplicate sessions.
  if day.isoformat() in [p['date'] for p in produced]:continue
  block=text[start:(schedules[ix+1][0] if ix+1<len(schedules) else len(text))]
  # An on-sale date is not a performance date.
  if re.search(r'habilitara|reserva|boleteria',n[max(0,start-55):start]) or re.search(r'funciones del|para funciones',n[:start]) and 'habilitara' in n:continue
  clock=CLOCK.search(block)
  if len(schedules)==1 and not clock:clock=CLOCK.search(text)
  hour=f'{int(clock[1]):02}:{clock[2] or "00"}' if clock else None
  ambiguous_midnight=hour=='00:00'
  if ambiguous_midnight:hour=None
  local_title=title
  if len(schedules)>2 and clock:
   tail=block[clock.end():].strip(' |⊹✶\n')
   candidate=re.split(r'\n|//',tail)[0].strip()
   if len(norm(candidate))>4 and not re.search(r'entrada|boleteria|link',norm(candidate)):local_title=candidate[:160]
  state='historico' if day<now else 'incompleto' if ambiguous_midnight or not venue else 'observado_agenda'
  key=c.add(d,local_title,day.isoformat(),hour,venue,category(n),'%s'%state,text,origin_account=d.get('profile_username'))
  p=c.proposals[key]
  p.update(kind='event',acquisition_method='official_meta_api',parser_version=VERSION,date_basis=basis,
   content_type='festival' if 'festival' in n else 'workshop' if re.search(r'taller|workshop|masterclass',n) else 'exhibition' if 'muestra' in n else 'party' if re.search(r'fiesta|milonga',n) else 'program' if len(schedules)>1 else 'event',
   temporal_state='past' if day<now else 'today' if day==now else 'future',publication_approved=False,
   field_evidence={'date':text[start:end],'time':clock[0] if clock else None,'venue':venue_proof,'title':local_title},
   ambiguities=(['midnight_calendar_day_requires_review'] if ambiguous_midnight else [])+(['venue_unresolved'] if not venue else []))
  produced.append(p)
 if not produced:
  key=c.add(d,title,state='historico' if retrospective else 'investigable',evidence=text,origin_account=d.get('profile_username'))
  c.proposals[key].update(kind='historical' if retrospective else 'document',content_type=kind,parser_version=VERSION,acquisition_method='official_meta_api',date_basis='no_resolved_event_date',publication_approved=False)
 return produced
