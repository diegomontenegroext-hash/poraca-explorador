"""Content-shaped compound interpretation; independent of publisher identity.
Specialized structured adapters retain precedence. Unknown fields remain unknown.
"""
import re,json
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from collector import norm,compact,sha
from semantics import normalized_original,proof,credits,clean_title

VERSION='compound-v1.2'
ZONE=ZoneInfo('America/Argentina/Buenos_Aires')
DAYS=['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
CATS={'musica':'Música','teatro':'Teatro','cine':'Cine','literarias':'Literatura','charlas':'Charlas','eventos':'Cultura','infantiles':'Infantiles','opera':'Música','zarzuela':'Teatro','exposiciones':'Arte'}
DAY=r'lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo'
CLOCK=r'(?<![\d/.])(?:2[0-3]|[01]?\d)(?:[.:][0-5]\d)?(?!\d)'


def anchor(d):
 try:return datetime.fromisoformat(d['published_at'].replace('Z','+00:00')).astimezone(ZONE).date()
 except (KeyError,ValueError,TypeError):return None


def curator(d,accounts):
 if d.get('source_role')=='curator' or re.search(r'^(?:planes recomendados|anticipo de planes|recomendaciones para el fin de semana)',norm(d.get('text',''))):return True
 return any(a.get('username')==d.get('profile_username') and norm(a.get('circuit','')) in ('curaduria','curador') for a in accounts)


def classify(d,accounts=()):
 text=d.get('text','');n=norm(text)
 if len(re.findall(r'\.\s*[-–]\s*(?:A las|Desde las|De)\s+\d',text,re.I))>=3:return {'type':'cartelera','shape':'bullet_schedule','compound':True,'source_role':'secondary_publisher'}
 if re.search(r'agenda cultural(?: completa)?\s+(?:'+DAY+r')\b',text,re.I) and len(re.findall(r'\b\d{1,2}(?:[.:]\d{2})?\s*[-–]\s*\S',text))>=3:return {'type':'agenda_compuesta','shape':'time_rows','compound':True,'source_role':'secondary_publisher'}
 date_heads=len(re.findall(r'(?:^|\n)\s*[^\w\n📍]{0,8}(?:(?:el|desde el|del)\s+)?(?:'+DAY+r')\b',text,re.I))
 calendars=len(re.findall('🗓',text))
 if calendars>=3 and not curator(d,accounts) and re.search(r'(?m)^\s*•',text):
  return {'type':'cartelera','shape':'specialized_caption_program','compound':False,'source_role':'source_observed'}
 if (date_heads>=3 and curator(d,accounts)) or calendars>=3:
  return {'type':'curaduria_cultural' if curator(d,accounts) else 'programa_festival' if 'festival' in n else 'agenda_compuesta','shape':'paragraph_schedule','compound':True,'source_role':'curator' if curator(d,accounts) else 'source_observed'}
 if re.search(r'(?:todos los|cada) (?:lunes|martes|miercoles|jueves|viernes)|clases regulares',n):typ='programacion_recurrente'
 elif re.search(r'asi vivimos|postales|el pasado|gracias por acompan',n):typ='retrospectiva'
 elif curator(d,accounts) and not re.search(r'\b\d{1,2}[/.]\d{1,2}\b',text):typ='recomendacion_permanente'
 else:typ='evento_individual'
 return {'type':typ,'shape':None,'compound':False,'source_role':'curator' if curator(d,accounts) else 'source_observed'}


def dates_for_heading(s,base):
 """Explicit list vs interval; bare weekday in a weekly program uses that week."""
 from caption import dates
 from extract import MONTHS
 n=norm(s);result=[];basis=None;ending=None
 # Shared month: 16 y 17 de octubre, not a continuous festival.
 shared=re.search(r'\b(\d{1,2})\s+y\s+(\d{1,2})\s+de\s+('+('|'.join(MONTHS))+')',s,re.I)
 if shared and base:
  for day in (shared[1],shared[2]):
   try:result.append(base.replace(month=MONTHS[shared[3].lower()],day=int(day)))
   except ValueError:pass
  return result,None,'explicit_shared_month_year_from_publication'
 explicit=dates(s,base)
 if explicit:
  result=[x[2] for x in explicit];basis=explicit[0][3]
  if len(result)>1 and re.search(r'\b(?:del|desde|hasta|al)\b',n):ending=result[-1].isoformat();result=result[:1]
  return list(dict.fromkeys(result)),ending,basis
 if not base:return [],None,'publication_date_missing'
 relative=re.search(r'\b(hoy|manana)\b',n)
 if relative:return [base+timedelta(days=int(relative[1]=='manana'))],None,'relative_to_publication_art'
 partial=re.search(r'\b('+DAY+r')\s+(\d{1,2})\b',s,re.I)
 if partial:
  for offset in (0,1,-1):
   month=(base.month-1+offset)%12+1;year=base.year+(base.month-1+offset)//12
   try:day=base.replace(year=year,month=month,day=int(partial[2]))
   except ValueError:continue
   if day.weekday()==DAYS.index(norm(partial[1])):return [day],None,'weekday_day_month_verified_from_publication'
  return [],None,'weekday_day_conflict'
 names=[norm(m[0]) for m in re.finditer(DAY,s,re.I)]
 if names:
  start=base-timedelta(days=base.weekday())
  result=[start+timedelta(days=DAYS.index(name)) for name in names]
  if 'proximo' in n:result=[x+timedelta(days=7) if x<=base else x for x in result]
  if re.search(r'desde|hasta',n) and len(result)>1:return [result[0]],result[-1].isoformat(),'publication_week_interval'
  return list(dict.fromkeys(result)),None,'publication_week_weekdays'
 return [],None,'unresolved'


def timing(s):
 m=re.search(r'(?:(?:a las|desde las|de)\s+)?('+CLOCK+r')(?:\s+a\s+('+CLOCK+r'))?\s*(?:hs?\b|horas\b)',s,re.I)
 if not m:return None,None
 raw=m[1].replace('.',':');parts=raw.split(':');hour=f'{int(parts[0]):02}:{parts[1] if len(parts)>1 else "00"}'
 if re.search(r'hasta las|gratis hasta|2x1',norm(s[:m.start(1)])):return None,None
 return (None if hour=='00:00' else hour),m[0]


def known_places(accounts,baseline):
 values={a['entity'] for a in accounts if a.get('identity')!='ambiguous' and norm(a.get('circuit',''))!='curaduria'}
 values.update(p['venue'] for p in baseline if p.get('venue'))
 for p in baseline:
  evidence=p.get('evidence') or {}
  if isinstance(evidence,str):
   try:evidence=json.loads(evidence)
   except ValueError:evidence={}
  if isinstance(evidence,dict):
   for e in evidence.get('entities',[]):
    if e.get('role')=='venue' and e.get('name'):values.add(e['name'])
 # Only word-boundary spelling variants. The emitted value is always literal
 # text from this document, not a substituted canonical name.
 for name in list(values):
  if name.startswith(('El ','La ')):values.add(name.split(' ',1)[1])

 return sorted(values,key=len,reverse=True)


def emit(c,d,title,day,hour,venue,segment,source_role,classification,date_basis,end=None,category=None,address=None,organizer=None,source_id=None):
 from extract import category as categorize
 if not title or len(norm(title))<3:return None
 now=datetime.now(ZONE).date();state='historico' if day and day<now else 'incompleto' if not(day and hour and venue) else 'observado_agenda'
 key=c.add(d,title,day.isoformat() if day else None,hour,venue,category or categorize(title),state,segment,origin_account=d.get('profile_username'),source_id=source_id)
 p=c.proposals[key];start=d['text'].find(segment)
 p.update(parser_version=VERSION,source_document_sha256=d.get('sha256'),kind='event' if day else 'cultural_recommendation',document_type=classification,
  source_role=source_role,source_url=d['url'],publication_approved=False,date_basis=date_basis,date_end=end,address=address,
  temporal_state='past' if day and day<now else 'future_or_today' if day else 'unknown',organizer=organizer,
  missing_fields=[field for field,value in [('date',day),('time',hour),('venue',venue)] if value is None],
  field_evidence={'title':title,'date':segment if day else None,'time':None,'venue':venue,'address':address,'organizer':organizer},
  evidence_spans={'block':{'start':start,'end':start+len(segment),'quote':segment} if start>=0 else None},
  ambiguities=[] if day else ['date_unresolved'],acquisition_method=d.get('acquisition_method') or 'preserved_public_document',
  event_identity_key=sha(d['url']+'|'+norm(title)+'|'+norm(venue)),identity_scope='same_document_activity_title_venue')
 for field in ('title','venue','address','organizer'):
  value=p['field_evidence'].get(field)
  at=d['text'].find(value) if isinstance(value,str) else -1
  p['evidence_spans'][field]={'start':at,'end':at+len(value),'quote':value} if at>=0 else None
 p['entities']+=credits(segment)
 if organizer:p['entities'].append({'name':organizer,'role':'organizer','evidence':segment})
 if source_role=='curator' and d.get('profile_username'):
  p['entities'].append({'name':d['profile_username'],'role':'curator','evidence':json.dumps({'profile_username':d['profile_username'],'source_url':d['url']})})
 # Curator/publication identity is not an organizer credit.
 return p


def narrative_activities(c,d,parent,day,segment,classification):
 """Explicit future subprogram announcements; no inferred start times.
 Parent location is inherited only without a relocation cue, with its evidence.
 Descriptive present/past text and artist lists do not create occurrences.
 """
 out=[]
 patterns=[
  re.compile(r'(?<!\w)A las\s+('+CLOCK+r')\s+(?:habrá|se realizará|tendrá lugar)\s+([^.!?]+)',re.I),
  re.compile(r'\b(?:Luego|Después|A continuación|Más tarde)\s+(?:se\s+)?(?:presentará|realizará|inaugurará)\s+([^.!?]+)',re.I)]
 for index,pattern in enumerate(patterns):
  for m in pattern.finditer(segment):
   statement=m[0];description=m[2] if index==0 else m[1]
   # A quoted work names the activity; otherwise retain its literal description.
   quoted=re.search(r'[“"]([^”"]+)[”"]',description)
   title=quoted[1] if quoted and index==1 else re.split(r',|\ben las?\b|\bque\b',description)[0].strip()
   if not title:continue
   hour=None
   if index==0:
    parts=m[1].replace('.',':').split(':');hour=f'{int(parts[0]):02}:{parts[1] if len(parts)>1 else "00"}'
   explicit=re.search(r'\ben\s+(?:(?-i:el|la)\s+)?(.+?)(?:,|$)',description,re.I)
   location=explicit[1].strip() if explicit else None
   anaphoric=bool(location and re.search(r'\b(?:del museo|del teatro|del centro|del lugar|allí|mismo)\b',location,re.I))
   relocation=bool(re.search(r'\b(?:otro|otra|online|virtual|traslad|posteriormente en)\b',description,re.I))
   venue=location if location and not anaphoric else parent.get('venue') if not relocation else None
   p=emit(c,d,title,day,None if hour=='00:00' else hour,venue,statement,classification['source_role'],classification['type'],
    'parent_program_day_with_explicit_narrative_activity',source_id=sha(parent['id']+'|'+title+'|'+str(hour)))
   if not p:continue
   p.update(parent_program_id='proposal:'+parent['id'],parent_relationship='part_of_program',
    relationship_evidence_status='observed',subactivity_evidence=statement,
    venue_basis='explicit_subactivity_location' if location and not anaphoric else 'parent_program_context' if venue else 'unresolved',
    sublocation=location if anaphoric else None)
   p['field_evidence']['date']=parent['field_evidence']['date']
   p['field_evidence']['time']=m[1] if index==0 else None
   p['field_evidence']['parent_program']=segment
   for entity in p['entities']:
    if entity.get('role')=='venue':entity['evidence']=segment
   start=d['text'].find(statement)
   p['evidence_spans']['subactivity']={'start':start,'end':start+len(statement),'quote':statement}
   if hour=='00:00':p.update(announced_time=hour,ambiguities=p['ambiguities']+['midnight_calendar_day_requires_review'])
   out.append(p)
 return sorted(out,key=lambda p:p['evidence_spans']['subactivity']['start'])


def bullet_schedule(c,d,classification):
 text=d['text'];base=anchor(d)
 if not base:return []
 # Each .- schedule is a record boundary; source text retains exact evidence.
 # Keep only markers whose following text begins with a schedule.
 markers=[m for m in re.finditer(r'\.\s*[-–]\s*(?=(?:A las|Desde las|De)\s+\d)',text,re.I)]
 bounds=[];previous=0
 for m in markers:
  prefix=text[previous:m.start()];last=prefix.rfind('. ');start=previous+last+2 if last>=0 else previous
  candidate=text[start:m.start()]
  # Day/category headings occur between records, not in an artist's identity.
  headings=list(re.finditer(r'\b(Hoy|Mañana|'+DAY+r')\s+(Música|Teatro|Cine|Literarias|Charlas|Eventos|Infantiles|Ópera|Zarzuela|Exposiciones)\s+',candidate,re.I))
  if headings:start+=headings[-1].end()
  # A category heading may precede a title. Teatro Comunitario/Estatal
  # and Domingo de folclore are actual names, not headings.
  cat=re.match(r'^(Música|Teatro|Cine|Literarias|Charlas|Eventos|Infantiles|Ópera|Zarzuela|Exposiciones)\s+(?!Comunitario|Estatal)',text[start:m.start()],re.I)
  if cat:start+=cat.end()
  bounds.append((start,m.start(),m.end()));previous=m.end()
 out=[];current=None;label=None;previous=0
 for ix,(a,b,sched) in enumerate(bounds):
  prefix=text[previous:a]
  # A category is a real section heading, NOT any matching word in the
  # previous event's description, artist name or venue ("Teatro Bar").
  # HTML is flattened by the collector: genuine headings look like
  # "... . Teatro Obra..." or "... Mañana Música Banda...".
  section=r'Música|Teatro|Cine|Literarias|Eventos|Charlas|Infantiles|Ópera|Zarzuela|Exposiciones'
  day_sections=list(re.finditer(r'\b(Hoy|Mañana|'+DAY+r')\s+('+section+r')\b',prefix,re.I))
  if day_sections:
   day_heading=day_sections[-1]
   label_day=norm(day_heading[1])
   current=base+timedelta(days=(DAYS.index(label_day)-base.weekday())%7) if label_day in DAYS else base+timedelta(days=int(label_day=='manana'))
   label=CATS.get(norm(day_heading[2]),label)
  # The title starts AFTER the heading because its prefix was stripped
  # when locating the ".-" schedule marker. Only a trailing standalone
  # category token is accepted: names such as "Teatro Comunitario" and
  # venues mentioned earlier in a paragraph cannot change the section.
  bare=re.search(r'(?:^|[.!?]\s+)('+section+r')\s*
  end=bounds[ix+1][0] if ix+1<len(bounds) else len(text)
  block=text[sched:end];stop=re.search(r'Las noticias locales nunca|Notas relacionadas|PUBLICIDAD',block)
  if stop:block=block[:stop.start()];end=sched+len(block)
  title=text[a:b].strip();segment=text[a:end].strip()
  en=re.search(r'\ben\s+(?:(?-i:el|la)\s+)?(.+?)(?:,|\. |$)',block,re.I)
  venue=en[1].strip() if en else None
  if venue and re.search(r'diferentes|varias|distintas',norm(venue)):venue=None
  schedule=block[:en.start()] if en else block.split('. ')[0]
  times=re.findall(CLOCK,schedule)
  if not times:
   p=emit(c,d,title,current,None,venue,segment,classification['source_role'],classification['type'],'editorial_day_heading_from_publication_art',category=label)
   if p:p['ambiguities'].append('unresolved_clock');out.append(p)
   previous=end;continue
  # Ranges are one interval; an explicit 'y' separates multiple functions.
  times=times if re.search(r'\d\s+y\s+\d',schedule) else times[:1]
  address=None
  if en:
   after=block[en.end():];address=after.split('. ')[0].strip(' ,') or None
  for raw in times:
   parts=raw.replace('.',':').split(':');hour=f'{int(parts[0]):02}:{parts[1] if len(parts)>1 else "00"}'
   conflict='horario no informado' in norm(block)
   p=emit(c,d,title,current,None if hour=='00:00' or conflict else hour,venue,segment,classification['source_role'],classification['type'],'editorial_day_heading_from_publication_art',category=label,address=address)
   if p:
    p['field_evidence']['time']=raw
    if conflict:p['ambiguities'].append('conflicting_time_statement')
    if hour=='00:00':p.update(announced_date=p['date'],announced_time=hour,ambiguities=p['ambiguities']+['midnight_calendar_day_requires_review'])
    out.append(p)
  if p:out.extend(narrative_activities(c,d,p,current,segment,classification))
  previous=b
 return out


def row_schedule(c,d,classification,places):
 text=d['text'];base=anchor(d)
 if not base:return []
 begin=re.search(r'Agenda cultural(?: completa)?\s+(?=(?:'+DAY+r')\b)',text,re.I);tail=re.search(r'\bTemas:',text[begin.end():]) if begin else None
 if not begin:return []
 offset=begin.end();body=text[offset:offset+tail.start()] if tail else text[offset:]
 days=list(re.finditer(r'\b('+DAY+r')\s+([0-3]?\d)\b',body,re.I));out=[]
 for ix,m in enumerate(days):
  resolved,_,basis=dates_for_heading(m[0],base);day=resolved[0] if resolved else None
  a=m.end();b=days[ix+1].start() if ix+1<len(days) else len(body);scope=body[a:b]
  rows=list(re.finditer(r'(?<!\S)('+CLOCK+r')(?:\s+a\s+('+CLOCK+r'))?\s*[-–]\s*',scope))
  for j,r in enumerate(rows):
   end=rows[j+1].start() if j+1<len(rows) else len(scope)
   entry=scope[r.end():end].strip();venue=None;title=entry;address=None
   for name in places:
    at=entry.lower().rfind(name.lower())
    if at>0 and len(entry[at+len(name):].strip(' .'))<30:
     venue=entry[at:at+len(name)];title=entry[:at].strip();break
   if not venue:
    location=re.search(r'\b(?:Centro Cultural|Teatro|Camping|Basílica|Piedra Fundacional de|Facultad de|Museo y Archivo de|Auditorio de|Terraza de)\s+.+$',entry)
    if location and location.start()>0:
     venue=location[0].strip(' .');title=entry[:location.start()].strip()
   if not venue:
    address_match=re.search(r'\bCalle\s+\d.+$',entry)
    if address_match:address=address_match[0];title=entry[:address_match.start()].strip()
   parts=r[1].replace('.',':').split(':');hour=f'{int(parts[0]):02}:{parts[1] if len(parts)>1 else "00"}'
   segment=body[a+r.start():a+end].strip()
   p=emit(c,d,title,day,None if hour=='00:00' else hour,venue,segment,classification['source_role'],classification['type'],basis,address=address)
   if p:
    p['field_evidence']['date']=m[0];p['field_evidence']['time']=r[1]
    if not venue and not address:p['ambiguities'].append('title_venue_boundary_unresolved');p['title_precision']='unresolved_title_place_boundary'
    out.append(p)
 return out


def paragraph_schedule(c,d,classification):
 from caption import CLOCK
 raw=d['text'];text,positions=normalized_original(raw);base=anchor(d)
 if not base:return []
 paragraphs=list(re.finditer(r'\S[^\n]*(?:\n(?!\s*\n)[^\n]*)*',text))
 units=[]
 for paragraph in paragraphs:
  if paragraph[0].lstrip().startswith('🗓'):
   units.append(paragraph);continue
  for line in re.finditer(r'[^\n]+',paragraph[0]):
   a=paragraph.start()+line.start();b=paragraph.start()+line.end()
   split=re.search(r'\s+y\s+(?=a las\s+\d)',text[a:b],re.I)
   if split:
    for sa,sb in [(a,a+split.start()),(a+split.end(),b)]:
     match=re.compile(r'.+',re.S).search(text,sa,sb)
     if match:units.append(match)
   else:
    match=re.compile(r'.+').search(text,a,b)
    if match:units.append(match)
 paragraphs=units
 out=[];current=[];ending=None;basis='unresolved';previous_heading=None
 for m in paragraphs:
  content=m[0].strip();lines=content.splitlines();first=lines[0].strip(' 🗓️✨')
  if re.search(r'^#|merci|gracias|comentar|compartir|planes recomendados|anticipo de planes|aprovechen|donde nos vemos|^y a la vuelta',norm(first)):continue
  # Giveaways can mention a real activity without announcing its schedule.
  giveaway=re.match(r'^(?:dos|tres|cuatro|\d+) entradas para (.+)',first,re.I)
  if giveaway:
   schedule=re.search(r'\bel ('+DAY+r')\b',giveaway[1],re.I)
   ds,_,gbasis=dates_for_heading(schedule[1],base) if schedule else ([],None,'giveaway_without_event_date')
   title=re.sub(r'^el (?:'+DAY+r') en\s+','',giveaway[1],flags=re.I)
   for day in ds or [None]:
    span=proof(raw,positions,m.start(),m.end())
    p=emit(c,d,title,day,None,None,span['quote'],classification['source_role'],classification['type'],gbasis)
    if p:out.append(p)
   continue
  # Only heading-like date expressions establish scope; dates in an offer do not.
  headed=bool(re.match(r'^(?:(?:el|desde el|del)\s+)?(?:'+DAY+r')\b',first,re.I) or re.match(r'^\d{1,2}\s+(?:de|y)\s+',first) or content.startswith('🗓'))
  if headed:
   resolved,ending,basis=dates_for_heading(first,base)
   if resolved:current=resolved
   else:current=[]
   previous_heading=first
   remainder=re.sub(r'^(?:(?:el|desde el|del)\s+)?(?:'+DAY+r')(?:\s*(?:,|y)?\s*(?:'+DAY+r'))*\s*:?\s*','',first,flags=re.I)
   if content.startswith('🗓') or re.fullmatch(r'(?:'+DAY+r')(?:\s*(?:y|,)?\s*(?:'+DAY+r'))*\s*:?',first,re.I):
    body='\n'.join(lines[1:]).strip()
   else:body='\n'.join([remainder]+lines[1:]).strip()
  else:body=content
  if not current or not body or re.match(r'^#',body):continue
  # A separate paragraph starting 'y' inherits the previous explicit day only.
  body=re.sub(r'^y\s+','',body,flags=re.I)
  body_lines=[l.strip() for l in body.splitlines() if l.strip()]
  if not body_lines:continue
  title=body_lines[0]
  if len(body_lines)>1 and re.search(r'presenta\s*$',norm(title)):title=body_lines[1]
  elif len(body_lines)>1 and re.fullmatch(r'[a-z0-9_.]+',title) and not body_lines[1].startswith('📍'):title=body_lines[1]
  title=re.split(r'\btenemos c[oó]digo|\bc[oó]digo de descuento|\bconsegu[ií]|\bentradas gratuitas',title,flags=re.I)[0].strip()
  marker=re.search(r'📍\s*([^\n]+)',body);venue=marker[1].strip() if marker else None
  if not venue:
   explicit_place=re.search(r'\ben\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\b',body)
   venue=explicit_place[1] if explicit_place and ('.' in explicit_place[1] or '_' in explicit_place[1] or re.search(r'lp$|laplata$|delasartes$|degatos$|winehouse$|8y61$',explicit_place[1])) else None
  hour,clock=timing(body)
  organizer=re.search(r'(?:^|\n)([\w.]+)\s+presenta\b',body,re.I)
  for day in current:
   # Evidence uses the untouched source, not the normalized Unicode view.
   span=proof(raw,positions,m.start(),m.end());segment=span['quote']
   p=emit(c,d,clean_title(title),day,hour,venue,segment,classification['source_role'],classification['type'],basis,ending,organizer=organizer[1] if organizer else None)
   if p:
    if venue and ' y ' in venue and all(re.search(r'[A-Za-z]{3}',v) for v in venue.split(' y ')):
     p['venue']=None;p['kind']='program';p['multiple_places']=venue.split(' y ');p['ambiguities'].append('multiple_places_program_occurrences_unresolved');p['entities']=[e for e in p['entities'] if e['role']!='venue']+[{'name':v,'role':'venue','evidence':segment} for v in p['multiple_places']]
    p['field_evidence']['date']=first if headed else None;p['date_heading_evidence']=first if headed else previous_heading
    p['field_evidence']['time']=clock
    if len(current)>1:p['multiple_explicit_days']=True
    out.append(p)
  if headed:previous_heading=first
 return out


def interpret(c,d,accounts,baseline=()):
 info=classify(d,accounts)
 if not info['compound']:return None
 d['document_type']=info['type'];d['source_role']=info['source_role']
 if info['shape']=='bullet_schedule':return bullet_schedule(c,d,info)
 if info['shape']=='time_rows':return row_schedule(c,d,info,known_places(accounts,baseline))
 return paragraph_schedule(c,d,info)

def permanent_recommendations(c,d,accounts):
 info=classify(d,accounts)
 if not curator(d,accounts) or info['compound'] or info['type'] not in ('recomendacion_permanente','retrospectiva'):return None
 out=[]
 for block in re.split(r'\n\s*\n',d['text']):
  lines=block.strip().splitlines()
  handles=[l.strip() for l in lines if re.fullmatch(r'[a-z][a-z0-9_.]{2,40}',l.strip())]
  for name in handles:
   if name in ('laplata','planazo','recomendado'):continue
   marker=re.search(r'📍\s*([^\n]+)',block)
   p=emit(c,d,name,None,None,name,block,'curator',info['type'],'permanent_recommendation_not_an_event',address=marker[1] if marker else None)
   if p:p.update(kind='place_recommendation',geographic_scope='outside_local_area_explicit' if re.search(r'Castelli|ruta 2',d['text'],re.I) else 'pending_locality_review');out.append(p)
 return out or None


def effective_version(d,accounts):
 info=classify(d,accounts)
 if info['compound'] or (curator(d,accounts) and info['type'] in ('recomendacion_permanente','retrospectiva') and re.search(r'^[a-z][a-z0-9_.]{2,40}$',d.get('text',''),re.M)):return VERSION
 from caption import VERSION as caption_version
 return caption_version


def requires_interpretation(d,accounts,previous,proposals):
 version=effective_version(d,accounts)
 if previous and previous.get('published_at')!=d.get('published_at'):return True
 if previous and previous.get('sha256')==d.get('sha256') and previous.get('published_at')==d.get('published_at') and previous.get('interpretation_version')==version:return False
 return not any(p.get('parser_version')==version and p.get('source_document_sha256')==d.get('sha256') for p in proposals)
,prefix,re.I)
  if bare and (not day_sections or bare.start()>day_sections[-1].start()):
   label=CATS.get(norm(bare[1]),label)
  end=bounds[ix+1][0] if ix+1<len(bounds) else len(text)
  block=text[sched:end];stop=re.search(r'Las noticias locales nunca|Notas relacionadas|PUBLICIDAD',block)
  if stop:block=block[:stop.start()];end=sched+len(block)
  title=text[a:b].strip();segment=text[a:end].strip()
  en=re.search(r'\ben\s+(?:(?-i:el|la)\s+)?(.+?)(?:,|\. |$)',block,re.I)
  venue=en[1].strip() if en else None
  if venue and re.search(r'diferentes|varias|distintas',norm(venue)):venue=None
  schedule=block[:en.start()] if en else block.split('. ')[0]
  times=re.findall(CLOCK,schedule)
  if not times:
   p=emit(c,d,title,current,None,venue,segment,classification['source_role'],classification['type'],'editorial_day_heading_from_publication_art',category=label)
   if p:p['ambiguities'].append('unresolved_clock');out.append(p)
   previous=end;continue
  # Ranges are one interval; an explicit 'y' separates multiple functions.
  times=times if re.search(r'\d\s+y\s+\d',schedule) else times[:1]
  address=None
  if en:
   after=block[en.end():];address=after.split('. ')[0].strip(' ,') or None
  for raw in times:
   parts=raw.replace('.',':').split(':');hour=f'{int(parts[0]):02}:{parts[1] if len(parts)>1 else "00"}'
   conflict='horario no informado' in norm(block)
   p=emit(c,d,title,current,None if hour=='00:00' or conflict else hour,venue,segment,classification['source_role'],classification['type'],'editorial_day_heading_from_publication_art',category=label,address=address)
   if p:
    p['field_evidence']['time']=raw
    if conflict:p['ambiguities'].append('conflicting_time_statement')
    if hour=='00:00':p.update(announced_date=p['date'],announced_time=hour,ambiguities=p['ambiguities']+['midnight_calendar_day_requires_review'])
    out.append(p)
  if p:out.extend(narrative_activities(c,d,p,current,segment,classification))
  previous=b
 return out


def row_schedule(c,d,classification,places):
 text=d['text'];base=anchor(d)
 if not base:return []
 begin=re.search(r'Agenda cultural(?: completa)?\s+(?=(?:'+DAY+r')\b)',text,re.I);tail=re.search(r'\bTemas:',text[begin.end():]) if begin else None
 if not begin:return []
 offset=begin.end();body=text[offset:offset+tail.start()] if tail else text[offset:]
 days=list(re.finditer(r'\b('+DAY+r')\s+([0-3]?\d)\b',body,re.I));out=[]
 for ix,m in enumerate(days):
  resolved,_,basis=dates_for_heading(m[0],base);day=resolved[0] if resolved else None
  a=m.end();b=days[ix+1].start() if ix+1<len(days) else len(body);scope=body[a:b]
  rows=list(re.finditer(r'(?<!\S)('+CLOCK+r')(?:\s+a\s+('+CLOCK+r'))?\s*[-–]\s*',scope))
  for j,r in enumerate(rows):
   end=rows[j+1].start() if j+1<len(rows) else len(scope)
   entry=scope[r.end():end].strip();venue=None;title=entry;address=None
   for name in places:
    at=entry.lower().rfind(name.lower())
    if at>0 and len(entry[at+len(name):].strip(' .'))<30:
     venue=entry[at:at+len(name)];title=entry[:at].strip();break
   if not venue:
    location=re.search(r'\b(?:Centro Cultural|Teatro|Camping|Basílica|Piedra Fundacional de|Facultad de|Museo y Archivo de|Auditorio de|Terraza de)\s+.+$',entry)
    if location and location.start()>0:
     venue=location[0].strip(' .');title=entry[:location.start()].strip()
   if not venue:
    address_match=re.search(r'\bCalle\s+\d.+$',entry)
    if address_match:address=address_match[0];title=entry[:address_match.start()].strip()
   parts=r[1].replace('.',':').split(':');hour=f'{int(parts[0]):02}:{parts[1] if len(parts)>1 else "00"}'
   segment=body[a+r.start():a+end].strip()
   p=emit(c,d,title,day,None if hour=='00:00' else hour,venue,segment,classification['source_role'],classification['type'],basis,address=address)
   if p:
    p['field_evidence']['date']=m[0];p['field_evidence']['time']=r[1]
    if not venue and not address:p['ambiguities'].append('title_venue_boundary_unresolved');p['title_precision']='unresolved_title_place_boundary'
    out.append(p)
 return out


def paragraph_schedule(c,d,classification):
 from caption import CLOCK
 raw=d['text'];text,positions=normalized_original(raw);base=anchor(d)
 if not base:return []
 paragraphs=list(re.finditer(r'\S[^\n]*(?:\n(?!\s*\n)[^\n]*)*',text))
 units=[]
 for paragraph in paragraphs:
  if paragraph[0].lstrip().startswith('🗓'):
   units.append(paragraph);continue
  for line in re.finditer(r'[^\n]+',paragraph[0]):
   a=paragraph.start()+line.start();b=paragraph.start()+line.end()
   split=re.search(r'\s+y\s+(?=a las\s+\d)',text[a:b],re.I)
   if split:
    for sa,sb in [(a,a+split.start()),(a+split.end(),b)]:
     match=re.compile(r'.+',re.S).search(text,sa,sb)
     if match:units.append(match)
   else:
    match=re.compile(r'.+').search(text,a,b)
    if match:units.append(match)
 paragraphs=units
 out=[];current=[];ending=None;basis='unresolved';previous_heading=None
 for m in paragraphs:
  content=m[0].strip();lines=content.splitlines();first=lines[0].strip(' 🗓️✨')
  if re.search(r'^#|merci|gracias|comentar|compartir|planes recomendados|anticipo de planes|aprovechen|donde nos vemos|^y a la vuelta',norm(first)):continue
  # Giveaways can mention a real activity without announcing its schedule.
  giveaway=re.match(r'^(?:dos|tres|cuatro|\d+) entradas para (.+)',first,re.I)
  if giveaway:
   schedule=re.search(r'\bel ('+DAY+r')\b',giveaway[1],re.I)
   ds,_,gbasis=dates_for_heading(schedule[1],base) if schedule else ([],None,'giveaway_without_event_date')
   title=re.sub(r'^el (?:'+DAY+r') en\s+','',giveaway[1],flags=re.I)
   for day in ds or [None]:
    span=proof(raw,positions,m.start(),m.end())
    p=emit(c,d,title,day,None,None,span['quote'],classification['source_role'],classification['type'],gbasis)
    if p:out.append(p)
   continue
  # Only heading-like date expressions establish scope; dates in an offer do not.
  headed=bool(re.match(r'^(?:(?:el|desde el|del)\s+)?(?:'+DAY+r')\b',first,re.I) or re.match(r'^\d{1,2}\s+(?:de|y)\s+',first) or content.startswith('🗓'))
  if headed:
   resolved,ending,basis=dates_for_heading(first,base)
   if resolved:current=resolved
   else:current=[]
   previous_heading=first
   remainder=re.sub(r'^(?:(?:el|desde el|del)\s+)?(?:'+DAY+r')(?:\s*(?:,|y)?\s*(?:'+DAY+r'))*\s*:?\s*','',first,flags=re.I)
   if content.startswith('🗓') or re.fullmatch(r'(?:'+DAY+r')(?:\s*(?:y|,)?\s*(?:'+DAY+r'))*\s*:?',first,re.I):
    body='\n'.join(lines[1:]).strip()
   else:body='\n'.join([remainder]+lines[1:]).strip()
  else:body=content
  if not current or not body or re.match(r'^#',body):continue
  # A separate paragraph starting 'y' inherits the previous explicit day only.
  body=re.sub(r'^y\s+','',body,flags=re.I)
  body_lines=[l.strip() for l in body.splitlines() if l.strip()]
  if not body_lines:continue
  title=body_lines[0]
  if len(body_lines)>1 and re.search(r'presenta\s*$',norm(title)):title=body_lines[1]
  elif len(body_lines)>1 and re.fullmatch(r'[a-z0-9_.]+',title) and not body_lines[1].startswith('📍'):title=body_lines[1]
  title=re.split(r'\btenemos c[oó]digo|\bc[oó]digo de descuento|\bconsegu[ií]|\bentradas gratuitas',title,flags=re.I)[0].strip()
  marker=re.search(r'📍\s*([^\n]+)',body);venue=marker[1].strip() if marker else None
  if not venue:
   explicit_place=re.search(r'\ben\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\b',body)
   venue=explicit_place[1] if explicit_place and ('.' in explicit_place[1] or '_' in explicit_place[1] or re.search(r'lp$|laplata$|delasartes$|degatos$|winehouse$|8y61$',explicit_place[1])) else None
  hour,clock=timing(body)
  organizer=re.search(r'(?:^|\n)([\w.]+)\s+presenta\b',body,re.I)
  for day in current:
   # Evidence uses the untouched source, not the normalized Unicode view.
   span=proof(raw,positions,m.start(),m.end());segment=span['quote']
   p=emit(c,d,clean_title(title),day,hour,venue,segment,classification['source_role'],classification['type'],basis,ending,organizer=organizer[1] if organizer else None)
   if p:
    if venue and ' y ' in venue and all(re.search(r'[A-Za-z]{3}',v) for v in venue.split(' y ')):
     p['venue']=None;p['kind']='program';p['multiple_places']=venue.split(' y ');p['ambiguities'].append('multiple_places_program_occurrences_unresolved');p['entities']=[e for e in p['entities'] if e['role']!='venue']+[{'name':v,'role':'venue','evidence':segment} for v in p['multiple_places']]
    p['field_evidence']['date']=first if headed else None;p['date_heading_evidence']=first if headed else previous_heading
    p['field_evidence']['time']=clock
    if len(current)>1:p['multiple_explicit_days']=True
    out.append(p)
  if headed:previous_heading=first
 return out


def interpret(c,d,accounts,baseline=()):
 info=classify(d,accounts)
 if not info['compound']:return None
 d['document_type']=info['type'];d['source_role']=info['source_role']
 if info['shape']=='bullet_schedule':return bullet_schedule(c,d,info)
 if info['shape']=='time_rows':return row_schedule(c,d,info,known_places(accounts,baseline))
 return paragraph_schedule(c,d,info)

def permanent_recommendations(c,d,accounts):
 info=classify(d,accounts)
 if not curator(d,accounts) or info['compound'] or info['type'] not in ('recomendacion_permanente','retrospectiva'):return None
 out=[]
 for block in re.split(r'\n\s*\n',d['text']):
  lines=block.strip().splitlines()
  handles=[l.strip() for l in lines if re.fullmatch(r'[a-z][a-z0-9_.]{2,40}',l.strip())]
  for name in handles:
   if name in ('laplata','planazo','recomendado'):continue
   marker=re.search(r'📍\s*([^\n]+)',block)
   p=emit(c,d,name,None,None,name,block,'curator',info['type'],'permanent_recommendation_not_an_event',address=marker[1] if marker else None)
   if p:p.update(kind='place_recommendation',geographic_scope='outside_local_area_explicit' if re.search(r'Castelli|ruta 2',d['text'],re.I) else 'pending_locality_review');out.append(p)
 return out or None


def effective_version(d,accounts):
 info=classify(d,accounts)
 if info['compound'] or (curator(d,accounts) and info['type'] in ('recomendacion_permanente','retrospectiva') and re.search(r'^[a-z][a-z0-9_.]{2,40}$',d.get('text',''),re.M)):return VERSION
 from caption import VERSION as caption_version
 return caption_version


def requires_interpretation(d,accounts,previous,proposals):
 version=effective_version(d,accounts)
 if previous and previous.get('published_at')!=d.get('published_at'):return True
 if previous and previous.get('sha256')==d.get('sha256') and previous.get('published_at')==d.get('published_at') and previous.get('interpretation_version')==version:return False
 return not any(p.get('parser_version')==version and p.get('source_document_sha256')==d.get('sha256') for p in proposals)
