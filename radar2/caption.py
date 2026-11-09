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
from semantics import normalized_original,proof,clocks_in,activity_title,credits,identity,CANCEL,clean_title
from account_context import location_for,preflight
VERSION='caption-v2.5'
ZONE=ZoneInfo('America/Argentina/Buenos_Aires')
WEEK=['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
DATE=re.compile(r'\b([0-3]?\d)\s*(?:[/.]+\s*(1[0-2]|0?[1-9])\b|(?:de\s+)?('+('|'.join(MONTHS))+r')\b)(?:\s*(?:de\s+|/)(20\d{2}))?',re.I)
CLOCK=re.compile(r'(?<![\d.])([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*(?:a\s*\d{1,2}(?:[:.]\d{2})?\s*)?(?:hs?\b|horas\b)|\b(medianoche)\b',re.I)
PAST=re.compile(r'\b(postales|pasado|vivimos|presentaron|presento|nos quedaron|gracias por acompanarnos|asi vivimos|despide)\b')
CULTURE=re.compile(r'proyeccion|tango|ceramica|cine|obra|teatro|taller|workshop|masterclass|milonga|fiesta|ciclo|concierto|recital|inaugur|muestra|festival|musica|musicaliza|libros|lectura|banda|entrada|cabina|en vivo')

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
 if out:
  # "viernes 28, sábado 29 y domingo 30 de abril" shares one explicit month.
  for start,end,day,basis in list(out):
   prefix=n[:start]
   chain=re.search(r'((?:(?:'+('|'.join(WEEK))+r')\s+\d{1,2}\s*(?:,|y)\s*)+)(?:'+('|'.join(WEEK))+r')\s+$',prefix)
   if not chain:continue
   for item in re.finditer(r'('+('|'.join(WEEK))+r')\s+(\d{1,2})',chain[1]):
    try:earlier=day.replace(day=int(item[2]))
    except ValueError:continue
    if earlier<day and earlier.weekday()==WEEK.index(item[1]):
     out.append((chain.start()+item.start(),chain.start()+item.end(),earlier,'shared_explicit_month_weekday_verified'))
  return sorted(out)
 if re.search(r'\besta semana\b',n[:100]):
  weekdays=list(re.finditer(r'^(?:[^\w\n]{0,4})('+('|'.join(WEEK))+r')\b',n,re.M))
  if len({m[1] for m in weekdays})>=2:
   monday=base-timedelta(days=base.weekday())
   return [(m.start(),m.end(),monday+timedelta(days=WEEK.index(m[1])),'weekday_in_explicit_publication_week') for m in weekdays]
 # A named month plus a day without month is ambiguous: leave for review.
 if re.search(r'\b(hoy|manana)\b',n[:300]) and not re.search(r'hoy y siempre',n) and not re.search(r'hoy (?:compartimos|mostramos|recordamos)',n):
  m=re.search(r'\b(hoy|manana)\b',n[:300]);return [(m.start(),m.end(),base+timedelta(days=int(m[1]=='manana')),'relative_to_publication')]
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
 from compound import interpret as compound_interpret,permanent_recommendations,classify
 info=classify(d,accounts);d['document_type']=info['type'];d['source_role']=info['source_role']
 multi=compound_interpret(c,d,accounts,getattr(c,'baseline',[])+list(c.proposals.values()))
 if multi is not None:return multi
 permanent=permanent_recommendations(c,d,accounts)
 if permanent is not None:return []
 raw=d.get('text','');text,positions=normalized_original(raw);n=norm(text)
 base=anchor(d);schedules=dates(text,base);now=datetime.now(ZONE).date()
 retrospective=bool(PAST.search(norm(text[:schedules[0][0]] if schedules else text[:300])))
 cancelled=bool(CANCEL.search(text))
 regular=bool(re.search(r'horarios disponibles|clases regulares|(?:todos los|cada) (?:lunes|martes|miercoles|jueves|viernes|sabados?|domingos?)',n))
 cultural=bool(CULTURE.search(n))
 kind='retrospective' if retrospective else 'regular_class' if regular else 'cultural_document' if cultural else 'irrelevant'
 produced=[]
 # Actor catalog is evidence of account identity, not evidence of event venue.
 # Generic terms in the cultural graph are never sufficient venue identities.
 generic_venue_labels={'espacio','sala','teatro','casa','centro','bar','club','galpon','auditorio'}
 venues=[a for a in accounts if a.get('identity')!='ambiguous' and len(a.get('entity',''))>3 and norm(a['entity']) in n and a['entity'] not in ('Luti','Genda') and norm(a['entity']) not in generic_venue_labels]
 venue=next((a['entity'] for a in venues),None)
 venue_proof=text if venue else None
 # Explicit named places unknown to the catalog remain identity candidates.
 if not venue:
  m=re.search(r'(?:en |📍\s*)(Casa Mandala|Taller Laura Gan|Espacio E MACLA|Sala Ginastera|Sala Piazzolla|Miraflores)\b',text,re.I)
  if m:venue=m[1];venue_proof=m[0]
 if not venue:
  marker=re.search(r'📍\s*([^\n]{3,120})',text)
  if marker:
   value=re.split(r'[|,;🚫]| —|\(',marker[1],maxsplit=1)[0].strip()
   sala=re.match(r'Sala\s+\d+\b',value,re.I) or re.fullmatch(r'(?:Espacio|Casa|Galpón|Centro Cultural)\s+\d+',value.strip(),re.I)
   candidate=sala[0] if sala else re.split(r'\s+(?:Av\.?|Calle|Diag\.?|Diagonal|[0-9])',value,maxsplit=1)[0].strip()
   candidate=candidate.rstrip(' .—')
   invalid=re.search(r'calle|avenida|^diag|^av\b|^en |youtube|esperamos|\bfue\b|\b(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b',norm(candidate))
   # A marker may introduce a list (e.g. "Librerías participantes:"),
   # not a physical venue. Keep the source while withholding location.
   is_list_heading=bool(candidate.endswith(':') or re.search(
    r'\b(?:participantes|sedes participantes|lugares adheridos)\b', norm(candidate)))
   if 5<len(candidate)<75 and len(candidate.split())<=8 and re.match(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]',candidate) and not invalid and not is_list_heading and candidate.lower() not in ('sala','lugar'):
    venue=candidate;venue_proof=marker[0]
 title=next((compact(l).strip(' ✨🔥📚💃🦚⭐️✶⊹!') for l in text.splitlines() if l.strip()),d.get('title',''))[:160]
 heading=re.search(r'(?:^|\n|Primer )[^\w\n]{0,3}((?:Workshop de|Festival de|Taller de) [^\n]+)',text,re.I)
 if heading:title=heading[1][:160]
 quoted=re.search(r'(?:obra|comedia|presenta)\b[^\n“\"]{0,80}[“\"]([^”\"]+)[”\"]',text,re.I)
 if quoted:title=quoted[1]
 # Never manufacture identities from a date-only heading or a generic teaser.
 if len(norm(title))<7 or re.fullmatch(r'(?:este |el )?(?:'+('|'.join(WEEK))+r').*',norm(title)):
  lines=[compact(l) for l in text.splitlines() if l.strip() and not re.search(r'link|entrada|anticipad|bio|^\W*(?:'+('|'.join(WEEK))+')',norm(l))]
  title=next((l for l in lines if len(norm(l))>6),title)[:160]
 if norm(title) in ('volvemos','con una nueva fecha'):title=next((compact(l) for l in text.splitlines() if re.search(r'milonga|concierto|taller|fiesta',norm(l))),title)[:160]
 # Interview teasers are not event names: accept a literal branded label only
 # when the caption also contains an event date; keep the original permalink.
 if schedules and re.search(r'\bhoy hablamos con\b',n[:160]):
  branded=re.search(r'(?m)^#([A-Za-z][A-Za-z0-9_.-]{1,30}):\s*([^\n]{3,90})',text)
  if branded:
   proper=re.split(r'[⚛✨💫🎵🎶🌳]',branded[2],maxsplit=1)[0].strip(' .—:-')
   if 3<=len(proper)<=70:title=(branded[1]+': '+proper)[:160]
 commemorative=bool(re.search(r'aniversario del|anos de (?:su muerte|su partida|su fallecimiento)|hoy se cumplen',n)) and not bool(re.search(r'te esperamos|veni|inauguracion|a las \d',n))
 retail_relative=bool(re.search(r'(?:manana|hoy).{0,30}(?:subo|subimos|tienda|catalogo)',n))
 if commemorative or retail_relative:schedules=[]
 if (retrospective and not re.search(r'te esperamos|veni|proxim|se presenta|ultima funcion',n)) or regular or not cultural or re.search(r'hoy (?:compartimos|mostramos|recordamos)',n):schedules=[]
 rescheduled=bool(re.search(r'\b(?:se reprograma|reprogramad[ao]|cambio de fecha|se posterga|se pospone)\b',n))
 if rescheduled and len(schedules)>1:schedules=[]
 for ix,(start,end,day,basis) in enumerate(schedules):
  block_end=schedules[ix+1][0] if ix+1<len(schedules) else len(text)
  block=text[start:block_end]
  # On-sale windows, not event schedules. Keep their source as a pending document.
  if re.search(r'habilitara|boleteria|venta de entradas|cyber week',norm(text[max(0,start-100):start])) or re.search(r'se habilitara|venta de entradas|cyber week',norm(block[:100])):continue
  clocks=clocks_in(block,CLOCK)
  clock_origin=start
  if len(schedules)==1 and not clocks:
   clocks=clocks_in(text,CLOCK);clock_origin=0
  for ci,clock in enumerate(clocks or [None]):
   hour=(f'{int(clock[1]):02}:{clock[2] or "00"}' if clock and clock[1] else '00:00' if clock else None)
   ambiguous_midnight=hour=='00:00'
   announced_time=hour
   if ambiguous_midnight:hour=None
   scope=text[clock_origin:block_end] if clock_origin==0 else block
   next_clock=clocks[ci+1].start() if ci+1<len(clocks) else len(scope)
   local_title=activity_title(scope,clock,next_clock,title,len(clocks)>1 or len(schedules)>2)
   # In a dated itinerary the first line may describe a previous performance.
   # Keep each title attached to its own dated section, including untimed stops.
   territory_review=False
   if len(schedules)>1 and re.match(r'^\s*\|',text[end:block_end]):
    lines=text[end:block_end].strip().splitlines()
    labels=[part.strip().strip('#').strip() for part in lines[0].split('|') if part.strip(' #')]
    if labels:
     locality=norm(labels[0])
     territory_review=locality in ('bsas','buenos aires','azul','caba','tv','youtube','lanzamientoalbum')
     if locality in ('lp','la plata','bsas','buenos aires','azul','caba','tv','youtube','lanzamientoalbum'):
      description=next((line.strip(' 🌹') for line in lines[1:] if re.match(r'^[\s🌹"“]*[A-Za-zÁÉÍÓÚÑáéíóúñ]',line) and not re.match(r'^\s*(junto|invitad|gratis|entrada)',line,re.I)),None)
      if description:local_title=description[:160]
     elif not clock and len(labels[0].split())>=3:
      local_title=labels[0][:160]
   if basis=='weekday_in_explicit_publication_week':
    local_title=text[end:block_end].strip().splitlines()[0][:160] if text[end:block_end].strip() else title
   if not local_title:local_title=title
   # Multiple dates of the same work keep one title. Never deduplicate by date alone.
   local_venues=[a for a in venues if norm(a['entity']) in norm(scope)]
   if len(venues)>1:
    venue=local_venues[0]['entity'] if len(local_venues)==1 else None
    venue_proof=scope if venue else None
   # First understand whether this account is a venue, organizer or curator.
   # Match a real venue name/address inside THIS activity scope; profile ownership
   # alone produces a candidate, never a confirmed event place.
   host_location=location_for(d,scope)
   # A bare catalogue mention from an unverified source is not a venue fact.
   # Preserve the location as a candidate unless this block says "en X" or "📍 X".
   venue_mention_only=bool(venue and not host_location.get('venue')
     and not preflight(d.get('profile_username')).get('account_verified')
     and not re.search(r'(?:\ben(?:\s+el|\s+la)?|📍)\s+'+re.escape(venue)+r'\b',scope,re.I))
   # Accounts pending verification may name a room explicitly, but that
   # identifies a candidate, not an approved canonical place relationship.
   pending_profile_venue=bool(venue and not host_location.get('venue')
     and preflight(d.get('profile_username')).get('role')=='venue_candidate')
   local_venue=host_location['venue'] or (None if venue_mention_only or pending_profile_venue else venue)
   local_venue_proof=host_location.get('quote') if host_location['venue'] else venue_proof if local_venue else None
   state='historico' if day<now else 'incompleto' if ambiguous_midnight or not local_venue or cancelled or territory_review else 'observado_agenda'
   key=c.add(d,local_title,day.isoformat(),hour,local_venue,category(n),state,raw,origin_account=d.get('profile_username'))
   p=c.proposals[key]
   title_at=text.find(local_title)
   title_proof=proof(raw,positions,title_at,title_at+len(local_title)) if title_at>=0 else None
   p.update(source_document_sha256=d.get('sha256'),document_type=info['type'],source_role=info['source_role'],kind='event',acquisition_method='official_meta_api',parser_version=VERSION,date_basis=basis,
    content_type='festival' if 'festival' in n else 'workshop' if re.search(r'taller|workshop|masterclass',n) else 'exhibition' if 'muestra' in n else 'party' if re.search(r'fiesta|milonga',n) else 'program' if len(schedules)>1 else 'event',
    temporal_state='past' if day<now else 'today' if day==now else 'future',publication_approved=False,
    event_status='cancelled' if cancelled else 'scheduled_pending_review',announced_date=day.isoformat(),announced_time=announced_time,
    field_evidence={'date':raw[positions[start]:positions[end-1]+1],
     'time':(proof(raw,positions,clock_origin+clock.start(),clock_origin+clock.end()) or {}).get('quote') if clock else None,
     'venue':local_venue_proof,'title':(title_proof or {}).get('quote')},
    account_context=preflight(d.get('profile_username')),
    venue_basis=host_location['basis'] if host_location.get('venue') or host_location.get('candidate') else 'existing_literal_heuristic' if local_venue else host_location['basis'],
    venue_candidate=(venue if pending_profile_venue else host_location.get('candidate') or (venue if venue_mention_only else None)) if not local_venue else None,
    venue_candidate_basis=('explicit_literal_venue_pending_profile_identity' if pending_profile_venue else 'unverified_text_mention' if venue_mention_only else host_location.get('basis') if host_location.get('candidate') else None) if not local_venue else None,
    venue_candidate_evidence=venue_proof if pending_profile_venue else None,
    venue_entity_id=host_location.get('venue_entity_id') if host_location.get('venue') else None,
    venue_profile_evidence_url=host_location.get('profile_evidence_url') if host_location.get('venue') or host_location.get('candidate') else None,
    evidence_spans={'date':proof(raw,positions,start,end),'time':proof(raw,positions,clock_origin+clock.start(),clock_origin+clock.end()) if clock else None,'title':title_proof},
    ambiguities=(['nonlocal_or_digital_program_section'] if territory_review else [])+(['midnight_calendar_day_requires_review'] if ambiguous_midnight else [])+(['venue_unresolved'] if not local_venue else []))
   p['event_identity_key']=identity(p)
   p['identity_scope']='same_document_title_venue_pending_editorial_review'
   p['work_identity_key']=p['event_identity_key'] if re.search(r'obra|funciones|funcion',n) else None
   p['entities']+=credits(scope[clock.end():next_clock] if clock and len(clocks)>1 else text)
   cycle=re.search(r'\bCiclo\s+([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)',local_title)
   if cycle:p['entities'].append({'name':cycle[0],'role':'cycle','evidence':local_title})
   if key not in [x['id'] for x in produced]:produced.append(p)
 # Repeated summary dates with no new schedule enrich an existing timed slot.
 for pending in list(produced):
  if pending.get('time') or pending.get('ambiguities') and 'midnight_calendar_day_requires_review' in pending['ambiguities']:continue
  matches=[p for p in produced if p['date']==pending['date'] and p['title']==pending['title'] and p.get('time')]
  if len(matches)==1:
   c.proposals.pop(pending['id'],None);produced.remove(pending)
 # Narrative programs may contain titled sections without individual clocks.
 # Keep their source fragments as pending components rather than assigning
 # the parent's start time to each activity.
 if produced and len({p['date'] for p in produced})==1:
  narrative=list(re.finditer(r'(?:Un rato m[aá]s tarde|Para terminar la noche)[^\n]+',text,re.I))
  for match in narrative:
   component=clean_title(match[0]);key=c.add(d,component,state='incompleto',evidence=match[0],origin_account=d.get('profile_username'))
   c.proposals[key].update(kind='program_component',parser_version=VERSION,acquisition_method='official_meta_api',
    parent_document_url=d['url'],parent_announced_date=produced[0]['date'],publication_approved=False,
    date_basis='narrative_component_pending_schedule_review',ambiguities=['component_identity_and_schedule_require_review'])
 if not produced and not retrospective and not schedules and re.search(r'actividades.*dia',n):
  # A festival's DAY 1 is not a calendar date. Preserve titled components
  # for review without expanding unspecified days into invented occurrences.
  for match in re.finditer(r'🖤\s*([^\n]+)([^🖤]*)',text):
   local_title=clean_title(match[1])
   if re.search(r'actividades',norm(local_title)):continue
   segment=match[0];clock=CLOCK.search(segment)
   hour=f'{int(clock[1]):02}:{clock[2] or "00"}' if clock and clock[1] else None
   key=c.add(d,local_title,hour=hour,state='incompleto',evidence=segment,origin_account=d.get('profile_username'))
   c.proposals[key].update(kind='program_component',parser_version=VERSION,acquisition_method='official_meta_api',
    date_basis='festival_day_without_resolved_calendar_date',parent_document_url=d['url'],publication_approved=False,
    field_evidence={'title':match[1],'time':clock[0] if clock else None,'date':None,'venue':None},
    ambiguities=['calendar_date_unresolved'],entities=credits(segment))
 if not produced:
  key=c.add(d,title,state='historico' if retrospective else 'investigable',evidence=text,origin_account=d.get('profile_username'))
  c.proposals[key].update(kind='historical' if retrospective else 'document',content_type=kind,parser_version=VERSION,acquisition_method='official_meta_api',date_basis='no_resolved_event_date',publication_approved=False,recurrence_rule=text if regular else None,event_status='cancelled' if cancelled else 'rescheduled_pending_review' if rescheduled else 'undetermined')
 return produced
,candidate) or re.search(r'\b(?:participantes|sedes participantes|lugares adheridos)\b',norm(candidate)))
   if 5<len(candidate)<75 and len(candidate.split())<=8 and re.match(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]',candidate) and not invalid and not is_list_heading and candidate.lower() not in ('sala','lugar'):
    venue=candidate;venue_proof=marker[0]
 title=next((compact(l).strip(' ✨🔥📚💃🦚⭐️✶⊹!') for l in text.splitlines() if l.strip()),d.get('title',''))[:160]
 heading=re.search(r'(?:^|\n|Primer )[^\w\n]{0,3}((?:Workshop de|Festival de|Taller de) [^\n]+)',text,re.I)
 if heading:title=heading[1][:160]
 quoted=re.search(r'(?:obra|comedia|presenta)\b[^\n“\"]{0,80}[“\"]([^”\"]+)[”\"]',text,re.I)
 if quoted:title=quoted[1]
 # Never manufacture identities from a date-only heading or a generic teaser.
 if len(norm(title))<7 or re.fullmatch(r'(?:este |el )?(?:'+('|'.join(WEEK))+r').*',norm(title)):
  lines=[compact(l) for l in text.splitlines() if l.strip() and not re.search(r'link|entrada|anticipad|bio|^\W*(?:'+('|'.join(WEEK))+')',norm(l))]
  title=next((l for l in lines if len(norm(l))>6),title)[:160]
 if norm(title) in ('volvemos','con una nueva fecha'):title=next((compact(l) for l in text.splitlines() if re.search(r'milonga|concierto|taller|fiesta',norm(l))),title)[:160]
 # Interview teasers are not event names: accept a literal branded label only
 # when the caption also contains an event date; keep the original permalink.
 if schedules and re.search(r'\bhoy hablamos con\b',n[:160]):
  branded=re.search(r'(?m)^#([A-Za-z][A-Za-z0-9_.-]{1,30}):\s*([^\n]{3,90})',text)
  if branded:
   proper=re.split(r'[⚛✨💫🎵🎶🌳]',branded[2],maxsplit=1)[0].strip(' .—:-')
   if 3<=len(proper)<=70:title=(branded[1]+': '+proper)[:160]
 commemorative=bool(re.search(r'aniversario del|anos de (?:su muerte|su partida|su fallecimiento)|hoy se cumplen',n)) and not bool(re.search(r'te esperamos|veni|inauguracion|a las \d',n))
 retail_relative=bool(re.search(r'(?:manana|hoy).{0,30}(?:subo|subimos|tienda|catalogo)',n))
 if commemorative or retail_relative:schedules=[]
 if (retrospective and not re.search(r'te esperamos|veni|proxim|se presenta|ultima funcion',n)) or regular or not cultural or re.search(r'hoy (?:compartimos|mostramos|recordamos)',n):schedules=[]
 rescheduled=bool(re.search(r'\b(?:se reprograma|reprogramad[ao]|cambio de fecha|se posterga|se pospone)\b',n))
 if rescheduled and len(schedules)>1:schedules=[]
 for ix,(start,end,day,basis) in enumerate(schedules):
  block_end=schedules[ix+1][0] if ix+1<len(schedules) else len(text)
  block=text[start:block_end]
  # On-sale windows, not event schedules. Keep their source as a pending document.
  if re.search(r'habilitara|boleteria|venta de entradas|cyber week',norm(text[max(0,start-100):start])) or re.search(r'se habilitara|venta de entradas|cyber week',norm(block[:100])):continue
  clocks=clocks_in(block,CLOCK)
  clock_origin=start
  if len(schedules)==1 and not clocks:
   clocks=clocks_in(text,CLOCK);clock_origin=0
  for ci,clock in enumerate(clocks or [None]):
   hour=(f'{int(clock[1]):02}:{clock[2] or "00"}' if clock and clock[1] else '00:00' if clock else None)
   ambiguous_midnight=hour=='00:00'
   announced_time=hour
   if ambiguous_midnight:hour=None
   scope=text[clock_origin:block_end] if clock_origin==0 else block
   next_clock=clocks[ci+1].start() if ci+1<len(clocks) else len(scope)
   local_title=activity_title(scope,clock,next_clock,title,len(clocks)>1 or len(schedules)>2)
   # In a dated itinerary the first line may describe a previous performance.
   # Keep each title attached to its own dated section, including untimed stops.
   territory_review=False
   if len(schedules)>1 and re.match(r'^\s*\|',text[end:block_end]):
    lines=text[end:block_end].strip().splitlines()
    labels=[part.strip().strip('#').strip() for part in lines[0].split('|') if part.strip(' #')]
    if labels:
     locality=norm(labels[0])
     territory_review=locality in ('bsas','buenos aires','azul','caba','tv','youtube','lanzamientoalbum')
     if locality in ('lp','la plata','bsas','buenos aires','azul','caba','tv','youtube','lanzamientoalbum'):
      description=next((line.strip(' 🌹') for line in lines[1:] if re.match(r'^[\s🌹"“]*[A-Za-zÁÉÍÓÚÑáéíóúñ]',line) and not re.match(r'^\s*(junto|invitad|gratis|entrada)',line,re.I)),None)
      if description:local_title=description[:160]
     elif not clock and len(labels[0].split())>=3:
      local_title=labels[0][:160]
   if basis=='weekday_in_explicit_publication_week':
    local_title=text[end:block_end].strip().splitlines()[0][:160] if text[end:block_end].strip() else title
   if not local_title:local_title=title
   # Multiple dates of the same work keep one title. Never deduplicate by date alone.
   local_venues=[a for a in venues if norm(a['entity']) in norm(scope)]
   if len(venues)>1:
    venue=local_venues[0]['entity'] if len(local_venues)==1 else None
    venue_proof=scope if venue else None
   # First understand whether this account is a venue, organizer or curator.
   # Match a real venue name/address inside THIS activity scope; profile ownership
   # alone produces a candidate, never a confirmed event place.
   host_location=location_for(d,scope)
   # A bare catalogue mention from an unverified source is not a venue fact.
   # Preserve the location as a candidate unless this block says "en X" or "📍 X".
   venue_mention_only=bool(venue and not host_location.get('venue')
     and not preflight(d.get('profile_username')).get('account_verified')
     and not re.search(r'(?:\ben(?:\s+el|\s+la)?|📍)\s+'+re.escape(venue)+r'\b',scope,re.I))
   # Accounts pending verification may name a room explicitly, but that
   # identifies a candidate, not an approved canonical place relationship.
   pending_profile_venue=bool(venue and not host_location.get('venue')
     and preflight(d.get('profile_username')).get('role')=='venue_candidate')
   local_venue=host_location['venue'] or (None if venue_mention_only or pending_profile_venue else venue)
   local_venue_proof=host_location.get('quote') if host_location['venue'] else venue_proof if local_venue else None
   state='historico' if day<now else 'incompleto' if ambiguous_midnight or not local_venue or cancelled or territory_review else 'observado_agenda'
   key=c.add(d,local_title,day.isoformat(),hour,local_venue,category(n),state,raw,origin_account=d.get('profile_username'))
   p=c.proposals[key]
   title_at=text.find(local_title)
   title_proof=proof(raw,positions,title_at,title_at+len(local_title)) if title_at>=0 else None
   p.update(source_document_sha256=d.get('sha256'),document_type=info['type'],source_role=info['source_role'],kind='event',acquisition_method='official_meta_api',parser_version=VERSION,date_basis=basis,
    content_type='festival' if 'festival' in n else 'workshop' if re.search(r'taller|workshop|masterclass',n) else 'exhibition' if 'muestra' in n else 'party' if re.search(r'fiesta|milonga',n) else 'program' if len(schedules)>1 else 'event',
    temporal_state='past' if day<now else 'today' if day==now else 'future',publication_approved=False,
    event_status='cancelled' if cancelled else 'scheduled_pending_review',announced_date=day.isoformat(),announced_time=announced_time,
    field_evidence={'date':raw[positions[start]:positions[end-1]+1],
     'time':(proof(raw,positions,clock_origin+clock.start(),clock_origin+clock.end()) or {}).get('quote') if clock else None,
     'venue':local_venue_proof,'title':(title_proof or {}).get('quote')},
    account_context=preflight(d.get('profile_username')),
    venue_basis=host_location['basis'] if host_location.get('venue') or host_location.get('candidate') else 'existing_literal_heuristic' if local_venue else host_location['basis'],
    venue_candidate=(venue if pending_profile_venue else host_location.get('candidate') or (venue if venue_mention_only else None)) if not local_venue else None,
    venue_candidate_basis=('explicit_literal_venue_pending_profile_identity' if pending_profile_venue else 'unverified_text_mention' if venue_mention_only else host_location.get('basis') if host_location.get('candidate') else None) if not local_venue else None,
    venue_candidate_evidence=venue_proof if pending_profile_venue else None,
    venue_entity_id=host_location.get('venue_entity_id') if host_location.get('venue') else None,
    venue_profile_evidence_url=host_location.get('profile_evidence_url') if host_location.get('venue') or host_location.get('candidate') else None,
    evidence_spans={'date':proof(raw,positions,start,end),'time':proof(raw,positions,clock_origin+clock.start(),clock_origin+clock.end()) if clock else None,'title':title_proof},
    ambiguities=(['nonlocal_or_digital_program_section'] if territory_review else [])+(['midnight_calendar_day_requires_review'] if ambiguous_midnight else [])+(['venue_unresolved'] if not local_venue else []))
   p['event_identity_key']=identity(p)
   p['identity_scope']='same_document_title_venue_pending_editorial_review'
   p['work_identity_key']=p['event_identity_key'] if re.search(r'obra|funciones|funcion',n) else None
   p['entities']+=credits(scope[clock.end():next_clock] if clock and len(clocks)>1 else text)
   cycle=re.search(r'\bCiclo\s+([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)',local_title)
   if cycle:p['entities'].append({'name':cycle[0],'role':'cycle','evidence':local_title})
   if key not in [x['id'] for x in produced]:produced.append(p)
 # Repeated summary dates with no new schedule enrich an existing timed slot.
 for pending in list(produced):
  if pending.get('time') or pending.get('ambiguities') and 'midnight_calendar_day_requires_review' in pending['ambiguities']:continue
  matches=[p for p in produced if p['date']==pending['date'] and p['title']==pending['title'] and p.get('time')]
  if len(matches)==1:
   c.proposals.pop(pending['id'],None);produced.remove(pending)
 # Narrative programs may contain titled sections without individual clocks.
 # Keep their source fragments as pending components rather than assigning
 # the parent's start time to each activity.
 if produced and len({p['date'] for p in produced})==1:
  narrative=list(re.finditer(r'(?:Un rato m[aá]s tarde|Para terminar la noche)[^\n]+',text,re.I))
  for match in narrative:
   component=clean_title(match[0]);key=c.add(d,component,state='incompleto',evidence=match[0],origin_account=d.get('profile_username'))
   c.proposals[key].update(kind='program_component',parser_version=VERSION,acquisition_method='official_meta_api',
    parent_document_url=d['url'],parent_announced_date=produced[0]['date'],publication_approved=False,
    date_basis='narrative_component_pending_schedule_review',ambiguities=['component_identity_and_schedule_require_review'])
 if not produced and not retrospective and not schedules and re.search(r'actividades.*dia',n):
  # A festival's DAY 1 is not a calendar date. Preserve titled components
  # for review without expanding unspecified days into invented occurrences.
  for match in re.finditer(r'🖤\s*([^\n]+)([^🖤]*)',text):
   local_title=clean_title(match[1])
   if re.search(r'actividades',norm(local_title)):continue
   segment=match[0];clock=CLOCK.search(segment)
   hour=f'{int(clock[1]):02}:{clock[2] or "00"}' if clock and clock[1] else None
   key=c.add(d,local_title,hour=hour,state='incompleto',evidence=segment,origin_account=d.get('profile_username'))
   c.proposals[key].update(kind='program_component',parser_version=VERSION,acquisition_method='official_meta_api',
    date_basis='festival_day_without_resolved_calendar_date',parent_document_url=d['url'],publication_approved=False,
    field_evidence={'title':match[1],'time':clock[0] if clock else None,'date':None,'venue':None},
    ambiguities=['calendar_date_unresolved'],entities=credits(segment))
 if not produced:
  key=c.add(d,title,state='historico' if retrospective else 'investigable',evidence=text,origin_account=d.get('profile_username'))
  c.proposals[key].update(kind='historical' if retrospective else 'document',content_type=kind,parser_version=VERSION,acquisition_method='official_meta_api',date_basis='no_resolved_event_date',publication_approved=False,recurrence_rule=text if regular else None,event_status='cancelled' if cancelled else 'rescheduled_pending_review' if rescheduled else 'undetermined')
 return produced
