"""Evidence-bounded segmentation. No network, editorial approval or inferred identities."""
import re,unicodedata
from collector import compact,norm,sha

# Do not let entry deadlines or a drink promotion create a second performance.
PROMO=re.compile(r'hasta las|lista.*hasta|2\s*x\s*1|descuento.*hasta|entrada.*hasta',re.I)
CANCEL=re.compile(r'\b(?:fecha|funcion|evento|actividad)\s+(?:cancelad[ao]|suspendid[ao])\b|\b(?:se cancela|se suspende)\b',re.I)

def clean_title(s):
 return compact(s).strip(' |⊹✶✧•-:✨🔥📚💃🦚⭐️🎬🌼❤️‍!')[:160]

def normalized_original(raw):
 """NFKC view and offsets into the untouched source, including styled digits."""
 out=[];positions=[]
 for i,char in enumerate(raw):
  for c in unicodedata.normalize('NFKC',char):out.append(c);positions.append(i)
 return ''.join(out),positions

def proof(raw,positions,start,end):
 if start>=end or not positions:return None
 a=positions[start];b=positions[min(end,len(positions))-1]+1
 return {'start':a,'end':b,'quote':raw[a:b]}

def clocks_in(block,clock):
 matches=[]
 for m in clock.finditer(block):
  line=block[block.rfind('\n',0,m.start())+1:m.start()]
  if PROMO.search(line):continue
  matches.append(m)
 return matches

def activity_title(block,clock,next_start,fallback,multiple):
 if not clock:return fallback
 tail=block[clock.end():next_start]
 # A range end and pricing lines are not program titles.
 after=clean_title(re.split(r'\n|//',tail)[0])
 if after and not re.match(r'[/]|(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b',norm(after) if not after.startswith('/') else after) and len(norm(after))>3 and (multiple or re.match(r'\s*[-|]',tail)) and not re.search(r'entrada|reserva|merienda|cupos|valor',norm(after)):
  return after
 if multiple and ('|' in block[:clock.start()].split('\n')[-1]):
  # A title may precede its clock, e.g. a film/lecture program.
  prefix=block[:clock.start()]
  last=prefix.split('\n')[-1]
  if '|' in last and len(norm(last.split('|')[-1]))>3:return clean_title(last.split('|')[-1])
  lines=[clean_title(s) for s in prefix.splitlines() if s.strip()]
  candidates=[s for s in lines[-3:] if len(norm(s))>3 and not re.search(r'^\d|^dir\b|^por\b|retrospectiva|cine nacional',norm(s))]
  if candidates:return clean_title(candidates[-1].split('|')[-1])
 return fallback

def credits(text):
 """Explicit line credit labels only; no identity inferred from bare mentions."""
 out=[]
 labels={'organiza':'organizer','produce':'organizer','produccion':'organizer','direccion':'director','director':'director','directora':'director','dirige':'director','dir':'director','actuan':'performer','actua':'performer','musicalizan':'performer','musicaliza':'performer','facilitan':'performer','profe':'performer','profes':'performer','coordina':'performer'}
 lines=text.splitlines();i=0
 while i<len(lines):
  line=lines[i];m=re.match(r'^\W{0,5}(organiza|produce|producci[oó]n|direcci[oó]n|director[ao]?|dirige|dir\.|act[uú]an?|musicalizan?|facilitan|profes?|coordina)\s*(?::\s*|(?<=dirige)\s+|(?<=Profe)\s+)(.*)$',line,re.I)
  i+=1
  if not m:continue
  role=labels.get(norm(m[1]));values=[m[2]]
  if not m[2].strip():
   while i<len(lines) and lines[i].strip():
    if re.search(r'escenograf|operacion tecnica|direccion|vestuario|iluminacion|diseno|produccion',norm(lines[i])):break
    values.append(lines[i]);i+=1
  for value in values:
   if re.search(r'profesor|instructor|licenci',norm(value)):value=value.split(',')[0]
   for name in re.split(r'\s+y\s+|,|\s+\+\s+',value,flags=re.I):
    name=re.sub(r'^[^\w]+|[^\w]+$','',clean_title(re.sub(r'\([^)]*\)','',name)))
    if role and 3<len(name)<70 and len(name.split())<=6 and not re.search(r'\d|profesor|licenci|instructor',norm(name)):
     out.append({'name':name,'role':role,'evidence':line+'\n'+value})
 return out

def identity(p):
 # Document-scoped work identity: functions share a work without globally merging
 # homonyms. Cross-source identity is still the existing conservative reconciler.
 return sha('|'.join([p['document_url'],norm(p['title']),norm(p.get('venue'))]))
