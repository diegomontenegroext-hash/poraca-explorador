"""Extract individual cultural proposals; articles remain documents, not events."""
import json,re
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from collector import norm,compact
from territory import event_location

MONTHS={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
PUBLISHERS={'que hacemos','eleven flow','pogo','saleplan','teatrina','marquesina'}

def category(text):
 # Explicit screening-series titles are stronger evidence than generic topic words.
 # Preserve source labels in revisions; never guess film from a venue or poster alone.
 if re.search(r'^\s*cine\s+(?:eco)?select\s*[:\-]\s*\S',text or '',re.I):
  return 'Cine'
 for pattern,label in [(r'vino|bodega|degustacion|cata\b','Vino'),(r'teatro|obra|escenario','Teatro'),(r'fotografia|exposicion|fotolibro|inauguracion|cianotipia|mosaico','Arte'),(r'taller|seminario','Taller especial'),(r'running|carrera|\bcorre\b|ciclismo|cicloturismo|kayak|rollers|senderismo','Deporte'),(r'electronica|techno|circus|intra|\b999\b','Electrónica'),(r'musica|recital|banda|concierto|guajira','Música')]:
  if re.search(pattern,norm(text)):return label
 return 'Cultura'

def account_links(text,accounts):
 n=' '+norm(text)+' ';out=[]
 for a in accounts:
  if a.get('identity')=='ambiguous':continue
  name=norm(a['entity']);handle=a['username'].lower()
  if len(name)>4 and (' '+name+' ' in n or ' '+name.replace(' ','')+' ' in n or '@'+handle in text.lower()):
   out.append({'username':a['username'],'entity':a['entity'],'basis':'explicit venue/name in acquired document','evidence':compact(text)[:1200]})
 return out

def day_from(text,year):
 text=re.sub(r'\b(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b','',text,flags=re.I)
 text=re.sub(r'\b(\d{1,2})\s+(?:al|y)\s+\d{1,2}\s+de\s+',r'\1 de ',text,flags=re.I)
 m=re.search(r'\b(\d{1,2})(?:\s+de)?\s+('+('|'.join(MONTHS))+r')(?:\s+(?:de\s+)?(20\d{2}))?',text,re.I)
 if not m:return None
 try:return datetime(int(m[3] or year),MONTHS[m[2].lower()],int(m[1])).date().isoformat()
 except ValueError:return None


LINKED_PROGRAM_VERSION='linked-cultural-program-v1'
_LINKED_WEEKDAYS=('lunes','martes','miercoles','jueves','viernes','sabado','domingo')
_LINKED_DAY=r'(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)'
_LINKED_FILM_VENUES={
 'cine select':'Cine Select',
 'cine municipal select espacio incaa':'Cine Select',
 'cc malvinas':'Centro Cultural Islas Malvinas',
 'islas malvinas':'Centro Cultural Islas Malvinas',
 'pasaje dardo rocha sala b':'Pasaje Dardo Rocha (Sala B)',
}
def linked_program_rows(d,method,now):
 """Exact public detail shapes, not a search/listing or a generic city guess.
 Return None outside scope; [] means scoped but no standalone current session.
 A film's production year is never a screening year.
 """
 if method!='public_linked_cultural_detail_v1' or d.get('final_url')!=d.get('url') or str(d.get('http_status'))!='200':return None
 u=urlsplit(d['url']);host=(u.hostname or '').removeprefix('www.')
 if u.scheme!='https' or u.username or u.password or u.query or u.fragment:return None
 raw=d.get('text','');title=d.get('title','').split(' | ')[0].strip()
 if not title or len(title)>180:return None
 def date_for(weekday,dd,mm):
  try:day=datetime(now.year,int(mm),int(dd)).date()
  except ValueError:return None
  return day.isoformat() if _LINKED_WEEKDAYS[day.weekday()]==norm(weekday) and now-timedelta(days=2)<=day<=now+timedelta(days=120) else None
 if host=='fesaalp.com' and d.get('source')=='FESAALP' and re.fullmatch(r'/peliculas/[a-z0-9-]+/?',u.path):
  # Exact local venue labels, not the festival's name, witness locality.
  # Cortometrajes share programme blocks: retain source, don't invent a
  # standalone screening or collapse several shorts into a feature.
  if not re.search(r'Competencia Largometrajes\s+'+re.escape(title)+r'\s+De\s+',raw,re.I):return []
  hits=list(re.finditer(re.escape(title)+r'\s+De\s+[^|]{2,180}?\s+'+_LINKED_DAY+r'\s+(\d{1,2})/(\d{1,2})\s*[-–]\s*([01]?\d|2[0-3]):([0-5]\d)\s*h\s*[-–]\s*([^|]{3,95}?)\s+Guardar en calendario',raw,re.I))
  rows=[]
  for m in hits:
   venue=_LINKED_FILM_VENUES.get(norm(m[6]))
   day=date_for(m[1],m[2],m[3])
   if not venue or not day:continue
   literal=m[0].rsplit(' Guardar en calendario',1)[0]
   rows.append(dict(title=title,date=day,time=f'{int(m[4]):02}:{m[5]}',venue=venue,category='Cine',block=literal,local_witness=m[6],date_literal=m[1]+' '+m[2]+'/'+m[3]))
  return rows
 if host=='dynamoteatro.com' and d.get('source')=='Dynamo Teatro' and re.fullmatch(r'/event/\d+-[a-z0-9-]+/?',u.path):
  if not re.search(r'\bDynamo Teatro\b.{0,150}\bLa Plata\b',raw,re.I):return []
  block=re.search(r'\bFunciones\s+(.{10,650}?)\s+Lugar:\s*Dynamo Teatro\b',raw,re.I)
  if not block:return []
  row_re=re.compile(_LINKED_DAY+r'\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s*[—–-]\s*([01]?\d|2[0-3]):([0-5]\d)\s*hs',re.I)
  matches=list(row_re.finditer(block[1]))
  if not matches or row_re.sub('',block[1]).strip():return []
  rows=[]
  for m in matches:
   day=date_for(m[1],m[2],MONTHS.get(m[3].lower(),0))
   if day:rows.append(dict(title=title,date=day,time=f'{int(m[4]):02}:{m[5]}',venue='Dynamo Teatro',category='Teatro',block=block[0],local_witness='Dynamo Teatro',date_literal=m[0]))
  return rows
 return None

def extract_document(c,d,accounts,method):
 from compound import interpret as compound_interpret,classify,VERSION as COMPOUND_VERSION
 if classify(d,accounts)['compound'] and any(p.get('document_url')==d['url'] and (json.loads(p['evidence']) if isinstance(p.get('evidence'),str) else p.get('evidence') or {}).get('parser_version')==COMPOUND_VERSION and (json.loads(p['evidence']) if isinstance(p.get('evidence'),str) else p.get('evidence') or {}).get('source_document_sha256')==d.get('sha256') for p in getattr(c,'baseline',[])):return []
 structured_first=c.structured(d)
 multi=None if any(re.search(r'Event$',str(item.get('@type',''))) for item in structured_first) else compound_interpret(c,d,accounts,getattr(c,'baseline',[])+list(c.proposals.values()))
 if multi is not None:return multi
 before=set(c.proposals);produced=set();tree=c.tree(d);items=c.structured(d)
 discarded_finished_detail=False
 now=datetime.fromisoformat(d['fetched_at']).date();published=next((x.get('datePublished') for x in items if x.get('datePublished')),None)
 if published:d['published_at']=published
 def add(title,day,hour,venue,evidence,original=None,organizer=None,kind='event',end_date=None,category_label=None,local_witness=None):
  if not day:return
  if (day< (now-timedelta(days=2)).isoformat() and not(end_date and end_date>=now.isoformat())) or day>(now+timedelta(days=120)).isoformat():
   c.checks.append({'url':d['url'],'status':'discarded_historical_or_outside_horizon','title':title,'date':day});return
  if not local_witness and not re.search(r'la plata|berisso|ensenada|gonnet|gorina|city bell|villa elisa|tolosa|punta lara|abasto',norm(d['text'])):return
  if re.search(r'\bberazategui\b|\bquilmes\b',norm(venue or '')+' '+norm(evidence)):
   c.checks.append({'url':d['url'],'status':'discarded_out_of_area','title':title});return
  related=account_links((venue or '')+' '+evidence,accounts)
  source=norm(urlsplit(d['url']).hostname)
  if organizer and (norm(organizer) in PUBLISHERS or norm(organizer).replace(' ','') in source.replace(' ','')):organizer=None
  state='fuente_original' if urlsplit(d['url']).hostname in ('www.passline.com','wearebombo.com','festival.freezer.com.ar','openhouselaplata.com.ar') else 'observado_agenda'
  key=c.add(d,title,day,hour,venue,category_label or category(title),state,evidence,related[0]['username'] if related else None)
  produced.add(key)
  p=c.proposals[key];p.update(kind=kind,organizer=organizer,related_accounts=related,acquisition_method=method,discovery=d.get('discovery'),original_url=original or d['final_url'],date_end=end_date)
  p['summary']=compact(f'{title}. '+(f'{venue}. ' if venue else '')+(f'{day}'+(f', {hour}.' if hour else '. Horario no informado.') )+(f' Organiza: {organizer}.' if organizer else ''))
  if organizer:p['entities'].append({'name':organizer,'role':'organizer','evidence':compact(evidence)[:1000]})
  p['date_basis']='source event/program date; publication date is never substituted'
  return key
 # Specialized public detail interpretation, after structured precedence.
 if not any(re.search(r'Event$',str(x.get('@type',''))) for x in items):
  linked=linked_program_rows(d,method,now)
  if linked is not None:
   for row in linked:
    key=add(row['title'],row['date'],row['time'],row['venue'],row['block'],category_label=row['category'],local_witness=row['local_witness'])
    if key:
     p=c.proposals[key]
     p.update(parser_version=LINKED_PROGRAM_VERSION,source_document_sha256=d.get('sha256'),document_type='programa_festival' if row['category']=='Cine' else 'cartelera',source_role='first_party',event_status='scheduled_pending_review',publication_approved=False,
       program_receipt={'activity_block':row['block'],'date_literal':row['date_literal'],'date':row['date'],'time':row['time'],'venue':row['venue'],'local_witness':row['local_witness']},
       field_evidence={'title':row['title'],'date':row['date_literal'],'time':row['time'],'venue':row['local_witness']},
       territory_resolution={'status':'source_stated_local','locality':'La Plata','basis':'explicit reviewed venue label in official detail'},
       date_basis='explicit detail weekday/day/month, acquisition-year horizon; never production year')
   if not produced:c.checks.append({'url':d['url'],'status':'linked_program_no_standalone_current_session'})
   return [c.proposals[k] for k in produced]
 # Explicit institutional program notices and multi-venue timetable rows.
 # This runs only for an already acquired current program, not for generic
 # search results, opening hours, old event pages or a publication date.
 if method in ('institutional_program_original_v1','dated_local_program_secondary_v1') and not any(re.search(r'Event$',str(x.get('@type',''))) for x in items):
  scope=next((n for n in tree.walk() if n.tag=='article'),None) or tree
  raw=scope.text()
  headings=[n.text() for n in scope.walk() if n.tag in ('h1','h2','h3','h4') and n.text()]
  blocks=[n.text() for n in scope.walk() if n.tag in ('p','h1','h2','h3','h4','li') and n.text()]
  year=int(str(published)[:4]) if published and re.match(r'20\d{2}',str(published)) else now.year
  weekdays=('lunes','martes','miercoles','jueves','viernes','sabado','domingo')
  def program_day(value):
   day=day_from(value,year)
   if not day:return None
   weekday=re.search(r'\b(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b',value,re.I)
   if weekday and weekdays[datetime.fromisoformat(day).weekday()]!=norm(weekday[1]):return None
   return day if abs((datetime.fromisoformat(day).date()-now).days)<=30 else None
  def program_add(title,day,hour,venue,block,role,details=None):
   key=add(title,day,hour,venue,block,category_label=category(title))
   if key:
    p=c.proposals[key];p.update(source_document_sha256=d.get('sha256'),document_type='programa_institucional' if role=='first_party' else 'cartelera',source_role=role,program_receipt={'date':day,'time':hour,'venue':venue,'scope':'literal_dated_program','details':details or block},publication_approved=False)
    p['field_evidence']={'title':title,'date':day,'time':hour,'venue':venue}
   return key
  # Labeled date / interval / place: the window belongs to this program,
  # not its constituent activities. Do not create fictitious timed sessions.
  if method=='institutional_program_original_v1':
   labeled=re.search(r'📆\s*([^📍🕐]{3,65})\s*🕐\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*(?:a|–|-)\s*(?:\d{1,2})(?::[0-5]\d)?\s*(?:hs|horas)\s*📍\s*([^.!?🌳🏛🎭]{3,120}?)(?=\s+(?:🏛|🎭|🌳|En la |En el )|$)',raw,re.I)
   if labeled:
    day=program_day(labeled[1])
    location=re.split(r'\s+[–—-]\s+',labeled[4].strip(),maxsplit=1)
    title=next((h for h in reversed(headings) if h and 'museos' in norm(h)),d['title'])
    # If a heading is absent, the explicit program name precedes the labels.
    before=raw[:labeled.start()].strip()
    name=re.search(r'([“"][^”"]+[”"]\s*\.?\s*(?:Noche|Jornada|Encuentro)[^.!?]{3,110})$',before,re.I)
    if name:title=name[1]
    if day and title and location[0]:program_add(title,day,f'{int(labeled[2]):02}:{labeled[3] or "00"}',location[0],raw,'first_party')
   # Narrative institutional notice with a named museum and explicit
   # venue address; a second clock for a subprogram remains in its evidence.
   if not produced:
    named=re.search(r'\b(Museo\s+[^.]{4,100}?)\s+de la Universidad\b',raw,re.I)
    date_window=re.search(r'(?:próximo\s+)?((?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+\d{1,2}\s+de\s+\w+(?:\s+de\s+20\d{2})?)\s*,?\s+entre las\s+([01]?\d|2[0-3])(?::([0-5]\d))?\s+y las\s+\d{1,2}(?::[0-5]\d)?\s+horas',raw,re.I)
    address=re.search(r'\bsede del Museo\s*\(([^)]+)\)',raw,re.I)
    if named and date_window and address:
     day=program_day(date_window[1]);title=next((h for h in headings if norm(named[1]) in norm(h) or 'museos a la luz' in norm(h)),d['title'])
     if day:program_add(title,day,f'{int(date_window[2]):02}:{date_window[3] or "00"}',named[1].strip(),raw,'first_party')
  if method=='dated_local_program_secondary_v1':
   current=None;in_schedule=False
   for block in blocks:
    if norm(block) in ('cronograma completo','programacion completa','programa completo'):in_schedule=True;current=None;continue
    if not in_schedule:continue
    if re.fullmatch(r'(?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+\d{1,2}\s+de\s+\w+(?:\s+de\s+20\d{2})?',block,re.I):
     current=program_day(block);continue
    row=re.match(r'^([01]?\d|2[0-3])(?::([0-5]\d))?\s*hs?\s*[–—-]\s*(.+)',block,re.I)
    if not current or not row:continue
    venue=re.search(r'(?:^|\.\s+)((?:Club|Centro Cultural|Museo|Teatro|Sala|Auditorio|Espacio|Biblioteca)\s+[^.()]{3,100})\s*\(([^)]{3,100})\)',row[3],re.I)
    if not venue or not re.search(r'la plata|berisso|ensenada|gonnet|gorina|city bell|villa elisa|tolosa',norm(venue[2])):continue
    title=row[3][:venue.start()].split('. ')[0].strip(' .')
    title=re.sub(r'^Show Musical:\s*','',title,flags=re.I)
    if title:program_add(title,current,f'{int(row[1]):02}:{row[2] or "00"}',venue[1].strip(),block,'secondary_publisher')
  if produced:return [c.proposals[k] for k in produced]
 # Structured events: capture each session, never NewsArticle.datePublished.
 for item in items:
  if not re.search(r'Event$',str(item.get('@type',''))) or not item.get('name') or not item.get('startDate'):continue
  try:
   dt=datetime.fromisoformat(item['startDate'].replace('Z','+00:00'))
   if dt.tzinfo:dt=dt.astimezone(ZoneInfo('America/Argentina/Buenos_Aires'))
  except ValueError:continue
  loc=item.get('location') or {};loc=loc[0] if isinstance(loc,list) and loc else loc
  if not isinstance(loc,dict):loc={}
  org=item.get('organizer') or {};org=org[0] if isinstance(org,list) and org else org
  venue=loc.get('name');ev=json.dumps(item,ensure_ascii=False)
  typ=item.get('@type','')
  label={'MusicEvent':'Música','TheaterEvent':'Teatro','DanceEvent':'Fiesta','VisualArtsEvent':'Arte','EducationEvent':'Taller especial'}.get(typ)
  end=None
  if item.get('endDate'):
   try:
    ending=datetime.fromisoformat(item['endDate'].replace('Z','+00:00'))
    if ending.tzinfo:ending=ending.astimezone(ZoneInfo('America/Argentina/Buenos_Aires'))
    if ending>=dt:end=ending.date().isoformat()
   except (ValueError,TypeError):pass
  title=item['name']
  territory=event_location(item,d.get('final_url'))
  if territory['status']=='source_stated_outside':
   # A directory headed "La Plata" can include unrelated CABA events.
   # An event's own structured locality outranks its directory page.
   c.checks.append({'url':d['url'],'status':'discarded_out_of_area_original_event',
     'title':title,'source_locality':territory.get('locality'),
     'territory_basis':territory['basis']})
   continue
  # The original ticket detail may emit the FETCH INSTANT as JSON-LD
  # startDate even when its own visible header says "Event finished".
  # This applies to finished editions from THIS year too, not only 2025.
  # A finished marker on some OTHER event lower in an active page does not
  # veto the current Event: require it near the start of the official detail.
  named_years={int(y) for y in re.findall(r'(?<![0-9])(20[0-9]{2})(?![0-9])',title)}
  first_text=norm(d.get('text','')[:260])
  ticket_host=(urlsplit(d['url']).hostname or '').lower()
  finished_tag=re.search(r'\b(?:event finished|evento finalizado|evento terminado)\b',first_text)
  prefix=first_text[:finished_tag.start()] if finished_tag else ''
  # The current detail's finished badge vetoes it, never a footer mention
  # of a DIFFERENT older event after this event's explicit date.
  footer_reference=bool(re.search(r'\b(?:mas informacion|otro evento)\b',prefix)
      or re.search(r'\b\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b',prefix))
  own_finished=bool(ticket_host=='tickets.sincroniadeportiva.com.ar'
      and finished_tag and not footer_reference)
  older_finished=bool(named_years and max(named_years)<dt.year
      and re.search(r'event finished|evento finalizado|evento terminado',norm(d.get('text',''))))
  if own_finished or older_finished:
   discarded_finished_detail=True
   c.checks.append({'url':d['url'],'status':'discarded_stale_structured_date',
     'title':title,'source_year':max(named_years) if named_years else None,
     'claimed_start':dt.date().isoformat(),
     'evidence':'official_detail_explicit_finished' if own_finished else 'explicit_finished_older_edition'})
   continue
  if re.search(r'venta de (?:tickets|entradas)',norm(title)):
   performers=item.get('performer') or [];performers=performers if isinstance(performers,list) else [performers]
   names=[a['name'] for a in performers if isinstance(a,dict) and a.get('name')]
   if names:title=', '.join(names)
   else:
    c.checks.append({'url':d['url'],'status':'generic_ticket_title_requires_review'});continue
  key=add(title,dt.date().isoformat(),dt.strftime('%H:%M') if 'T' in item['startDate'] else None,venue,ev,item.get('url'),org.get('name') if isinstance(org,dict) else None,end_date=end,category_label=label or category(title+' '+item.get('description','')))
  if key:
   # Geographic evidence belongs to this specific JSON-LD Event, not the
   # region of its publisher, a search result page, or an Instagram account.
   # A source assertion is NOT independent venue verification or admission.
   c.proposals[key]['territory_resolution']=territory
   for field,role in [('performer','performer'),('director','director')]:
    actors=item.get(field) or [];actors=actors if isinstance(actors,list) else [actors]
    for actor in actors:
     if isinstance(actor,dict) and actor.get('name'):c.proposals[key]['entities'].append({'name':actor['name'],'role':role,'evidence':json.dumps(actor,ensure_ascii=False)})
 # Single-announcement pages with labeled scheduling (not a list of nearby
 # recommendations). The year is explicitly inferred from the live program,
 # and the weekday must agree; historic film years are never used as event years.
 label=re.search(r'FECHA Y HORA\s+((?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+\d{1,2}\s+de\s+\w+(?:\s+de\s+20\d{2})?[, ]+\s*\d{1,2}:\d{2})',d['text'],re.I)
 if label and not produced:
  day=day_from(label[1],now.year);clock=re.search(r'(\d{1,2}):([0-5]\d)',label[1])
  weekdays=['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
  weekday=norm(label[1]).split()[0]
  title=next((n.text() for n in tree.walk() if n.tag=='h1'),None)
  if day and title and weekdays[datetime.fromisoformat(day).weekday()]==weekday:
   place=re.search(r'–\s*((?:Teatro|Centro|Sala|Galería|Espacio)[^|]+)',d['title'],re.I)
   venue=place[1].strip() if place else None
   org=next((m for n in tree.walk() if n.tag=='p' for m in [re.search(r'^([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ-]*(?: [A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ-]*){0,3}) presenta\b',n.text())] if m),None)
   key=add(title,day,clock[0] if clock else None,venue,d['text'],organizer=org[1] if org else None,category_label='Cine' if re.search(r'pel[ií]cula|proyecci[oó]n',d['text'],re.I) else None)
   if key:c.proposals[key]['date_basis']='labeled live program day/month/time; year inferred from acquisition year; weekday verified; not publication or historic work year'
 # Named credits are evidence even when the page remains an undated document.
 credits=[]
 for node in tree.walk():
  if node.tag not in ('p','li'):continue
  text=node.text()
  credit=re.search(r'^(Musicalizan|Actúan|Interpretes|Intérpretes|Dirección|Organiza):\s*(.{3,450})',text,re.I)
  if not credit:continue
  role='director' if norm(credit[1])=='direccion' else 'organizer' if norm(credit[1])=='organiza' else 'performer'
  names=re.split(r'\s*,\s*|\s+y\s+',credit[2].strip().rstrip('.'))
  for name in names:
   name=name.strip()
   if re.fullmatch(r'[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]*(?: [A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]*){1,4}',name):credits.append({'name':name,'role':role,'evidence':text})
 for key in produced:
  c.proposals[key]['entities'].extend(credits)
 # Public programs commonly group multiple <li><h3> events below a dated section.
 for section in tree.walk():
  if section.tag!='section':continue
  headings=[n.text() for n in section.walk() if n.tag=='h2']
  if not headings:continue
  scope=section.text();year_match=re.search(r'\b(20\d{2})\b',scope);year=int(year_match[1]) if year_match else None
  day=day_from(headings[0]+' '+scope[:180],year) if year else None
  if not day and year:
   month=next((k for k in MONTHS if k in norm(scope[:250])),None);num=re.search(r'\b([0-3]?\d)\b',headings[0])
   if month and num:
    try:day=datetime(year,MONTHS[month],int(num[1])).date().isoformat()
    except ValueError:pass
  if not day:continue
  for li in section.walk():
   if li.tag!='li':continue
   title=next((n.text() for n in li.walk() if n.tag=='h3'),None)
   if not title:continue
   text=li.text();clock=re.search(r'(?<![\d:.,])([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*(?:a\s*\d{1,2}(?:[:.]\d{2})?\s*)?hs\b',text,re.I)
   venue=re.search(r'📍\s*(.*?)(?:Ver en el mapa|Información|$)',text)
   source_type=next((n.text() for n in li.walk() if n.tag=='p' and 'uppercase' in n.a.get('class','')),'')
   label='Taller especial' if 'taller' in source_type.lower() else category(source_type+' '+title)
   add(title,day,f'{int(clock[1]):02}:{clock[2] or "00"}' if clock else None,venue[1].strip() if venue else None,text,category_label=label)
 # Multi-event editorial articles: headings delimit event identity. A dated
 # paragraph may inherit a day within that heading, never across headings.
 article=next((n for n in tree.walk() if n.tag=='article'),None)
 if article and not any(re.search(r'Event$',str(x.get('@type',''))) for x in items):
  year=int(str(published)[:4]) if published and re.match(r'20\d{2}',str(published)) else (now.year if str(now.year) in d['text'] else None)
  # A single-announcement article with no event subheadings can announce one
  # real activity. Read its first dated paragraph plus immediately adjacent
  # details; stop when a different day is mentioned rather than inventing a
  # second session for another festival referenced in the same article.
  article_headings=[n.text() for n in article.walk() if n.tag in ('h1','h2','h3')]
  # A timetable may put the date, clock and room on one line and the
  # activity title in the next paragraph. Bind only adjacent explicit blocks.
  schedule_rows=[]
  blocks=[node.text() for node in article.walk() if node.tag in ('p','h2','h3','h4','li')]
  heading_pattern=r'^(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+(\d{1,2}\s+de\s+\w+(?:\s+de\s+20\d{2})?)\s*\|\s*([01]?\d|2[0-3])[:.]([0-5]\d)\s*h(?:s)?\s*[-–—]\s*(.{3,140})$'
  weekdays=('lunes','martes','miercoles','jueves','viernes','sabado','domingo')
  for index,block in enumerate(blocks[:-1]):
   heading=re.fullmatch(heading_pattern,block.strip(),re.I)
   if not heading or not year:continue
   day=day_from(heading[2],year)
   if not day or weekdays[datetime.fromisoformat(day).weekday()]!=norm(heading[1]):continue
   title=blocks[index+1].strip()
   if not 4<=len(title)<=160 or re.search(r'\d\s*\||https?://',title):continue
   schedule_rows.append((title,day,f'{int(heading[3]):02}:{heading[4]}',heading[5],block+' '+title))
  if len(schedule_rows)>=2:
   for title,day,hour,room,evidence in schedule_rows:
    key=add(title,day,hour,room,evidence)
    if key:c.proposals[key]['source_document_sha256']=d.get('sha256')
  single_processed=len(schedule_rows)>=2
  if year and len(article_headings)==1 and not single_processed:
   title=article_headings[0]
   paragraphs=[n.text() for n in article.walk() if n.tag=='p']
   for index,text in enumerate(paragraphs):
    day=day_from(text,year)
    if not day:continue
    block=text
    for detail in paragraphs[index+1:index+3]:
     other_day=day_from(detail,year)
     if other_day and other_day!=day:break
     block+=' '+detail
    hour=re.search(r'(?:a las|desde las|de)\s+([01]?\d|2[0-3])(?:[:.]([0-5]\d))?(?:\s+a\s+\d{1,2}(?:[:.]\d{2})?)?\s*(?:hs|horas)',block,re.I)
    venue=re.search(r'en (?:el|la) ([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ-]*(?: [A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ-]*){0,4})',text)
    if title:
     add(title,day,f'{int(hour[1]):02}:{hour[2] or "00"}' if hour else None,venue[1] if venue else None,block)
     single_processed=True
    break
  heading=None;current_day=None
  for node in ([] if single_processed else article.walk()):
   if node.tag in ('h2','h3'):
    heading=node.text();current_day=None
   if node.tag!='p' or not heading or not year:continue
   text=node.text();day=day_from(text,year);current_day=day or current_day
   if not current_day:continue
   hour=re.search(r'\b(?:a\s+las|a\s+partir\s+de\s+las|desde\s+las)\s+(\d{1,2})(?::([0-5]\d))?\s*(?:horas|hs|h)\b',text,re.I)
   # A second time/venue in a new paragraph is a separate activity; keep its
   # own evidence and never carry an earlier paragraph's clock or place.
   venue=re.search(r'(?:en el |en la |en )(Pasaje Dardo Rocha|Ciudad de Gatos|Hipódromo de La Plata|Estación Provincial|Centro de Arte UNLP|Casa Curutchet)',text,re.I)
   if not (day or hour):continue
   clean=re.sub(r'\b(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\b','',text,flags=re.I)
   span=re.search(r'\b(\d{1,2})\s+(?:al|y)\s+(\d{1,2})\s+de\s+('+('|'.join(MONTHS))+')',clean,re.I)
   end_date=None
   if span:
    try:end_date=datetime(year,MONTHS[span[3].lower()],int(span[2])).date().isoformat()
    except ValueError:pass
   title=heading
   if hour and re.search(r'brindis|apertura oficial|inauguración',text,re.I):title+=' · '+('Brindis' if 'brindis' in text.lower() else 'Apertura')
   add(title,current_day,f'{int(hour[1]):02}:{hour[2] or "00"}' if hour else None,venue[1] if venue else None,text,kind='program' if end_date and end_date!=current_day else 'event',end_date=end_date)
 # Do not reintroduce an explicitly finished ticket as an undated lead.
 # Other current items on the page still produce their own events above.
 if not produced and discarded_finished_detail:
  c.checks.append({'url':d['url'],'status':'discarded_explicit_finished_original'})
  return []
 # Do not turn an unparsed article, homepage or old announcement into an event.
 if not produced:
  if not re.search(r'la plata|berisso|ensenada|gonnet|gorina|city bell|villa elisa|tolosa|punta lara|abasto',norm(d['text'])):
   c.checks.append({'url':d['url'],'status':'discarded_no_local_cultural_evidence'});return []
  historical=bool(published and str(published)[:10]<(now-timedelta(days=60)).isoformat())
  c.document_lead(d,state='historico' if historical else 'investigable')
  for key,p in c.proposals.items():
   if p['document_url']==d['url']:
    p['entities'].extend(credits)
    p.update(kind='historical' if historical else 'document',acquisition_method=method,discovery=d.get('discovery'),related_accounts=[])
    produced.add(key)
 return [c.proposals[k] for k in produced]
