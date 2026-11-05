"""Extract individual cultural proposals; articles remain documents, not events."""
import json,re
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from collector import norm,compact

MONTHS={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
PUBLISHERS={'que hacemos','eleven flow','pogo','saleplan','teatrina','marquesina'}

def category(text):
 for pattern,label in [(r'vino|bodega|degustacion|cata\b','Vino'),(r'teatro|obra|escenario','Teatro'),(r'fotografia|exposicion|fotolibro|inauguracion|cianotipia|mosaico','Arte'),(r'taller|seminario','Taller especial'),(r'electronica|techno|circus|intra|\b999\b','Electrónica'),(r'musica|recital|banda|concierto|guajira','Música')]:
  if re.search(pattern,norm(text)):return label
 return 'Cultura'

def account_links(text,accounts):
 n=' '+norm(text)+' ';out=[]
 for a in accounts:
  if a.get('identity')=='ambiguous':continue
  name=norm(a['entity']);handle=a['username'].lower()
  if len(name)>4 and (' '+name+' ' in n or name.replace(' ','') in n.replace(' ','') or '@'+handle in text.lower()):
   out.append({'username':a['username'],'entity':a['entity'],'basis':'explicit venue/name in acquired document','evidence':compact(text)[:1200]})
 return out

def day_from(text,year):
 text=re.sub(r'\b(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b','',text,flags=re.I)
 text=re.sub(r'\b(\d{1,2})\s+(?:al|y)\s+\d{1,2}\s+de\s+',r'\1 de ',text,flags=re.I)
 m=re.search(r'\b(\d{1,2})(?:\s+de)?\s+('+('|'.join(MONTHS))+r')(?:\s+(?:de\s+)?(20\d{2}))?',text,re.I)
 if not m:return None
 try:return datetime(int(m[3] or year),MONTHS[m[2].lower()],int(m[1])).date().isoformat()
 except ValueError:return None

def extract_document(c,d,accounts,method):
 before=set(c.proposals);produced=set();tree=c.tree(d);items=c.structured(d)
 now=datetime.fromisoformat(d['fetched_at']).date();published=next((x.get('datePublished') for x in items if x.get('datePublished')),None)
 if published:d['published_at']=published
 def add(title,day,hour,venue,evidence,original=None,organizer=None,kind='event',end_date=None,category_label=None):
  if not day:return
  if (day< (now-timedelta(days=2)).isoformat() and not(end_date and end_date>=now.isoformat())) or day>(now+timedelta(days=120)).isoformat():
   c.checks.append({'url':d['url'],'status':'discarded_historical_or_outside_horizon','title':title,'date':day});return
  if not re.search(r'la plata|berisso|ensenada|gonnet|gorina|city bell|villa elisa',norm(d['text'])):return
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
  key=add(item['name'],dt.date().isoformat(),dt.strftime('%H:%M') if 'T' in item['startDate'] else None,venue,ev,item.get('url'),org.get('name') if isinstance(org,dict) else None,end_date=end,category_label=label or category(item['name']+' '+item.get('description','')))
  if key:
   for field,role in [('performer','performer'),('director','director')]:
    actors=item.get(field) or [];actors=actors if isinstance(actors,list) else [actors]
    for actor in actors:
     if isinstance(actor,dict) and actor.get('name'):c.proposals[key]['entities'].append({'name':actor['name'],'role':role,'evidence':json.dumps(actor,ensure_ascii=False)})
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
  single_processed=False
  if year and len(article_headings)==1:
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
 # Do not turn an unparsed article, homepage or old announcement into an event.
 if not produced:
  if not re.search(r'la plata|berisso|ensenada|gonnet|gorina|city bell|villa elisa',norm(d['text'])):
   c.checks.append({'url':d['url'],'status':'discarded_no_local_cultural_evidence'});return []
  historical=bool(published and str(published)[:10]<(now-timedelta(days=60)).isoformat())
  c.document_lead(d,state='historico' if historical else 'investigable')
  for key,p in c.proposals.items():
   if p['document_url']==d['url']:
    p.update(kind='historical' if historical else 'document',acquisition_method=method,discovery=d.get('discovery'),related_accounts=[])
    produced.add(key)
 return [c.proposals[k] for k in produced]
