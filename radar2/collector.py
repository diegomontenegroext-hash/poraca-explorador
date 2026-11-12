#!/usr/bin/env python3
"""Por Acá: bounded acquisition, explicit evidence, no editorial publication.

Python standard library only. Instagram HTML is never fetched. Optional official
Business Discovery requires owner-supplied credentials; no fallback scraping.
"""
import argparse, csv, hashlib, html, json, os, re, time, unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs, urlencode
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser

UA = 'PorAcá/2.0 (+https://github.com/diegomontenegroext-hash/poraca-explorador; cultural research)'
UA = UA.encode('ascii','ignore').decode()
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
BLOCKED = {'instagram.com','facebook.com','imginn.com','pikory.com','pixnoy.com','pixwox.com'}
# Require identity AND a relevant activity term in indexed-source matches.
TARGETED_EVENT_SIGNALS=re.compile(
 r'teatro|recital|musica|electronica|fiesta|cultura|galeria|exposicion|'
 r'\barte\b|taller|feria|vino|cata|yoga|ceramica|'
 r'running|run club|pedalead|ciclismo|cicloturismo|biciclet|kayak|'
 r'travesia|rollers|patinaje|senderismo|caminata grupal|stand up paddle',re.I)

def platform_host(host):return any(host==base or (host or '').endswith('.'+base) for base in BLOCKED)

class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlsplit(newurl)
        if p.scheme!='https' or platform_host(p.hostname):raise ValueError('PLATFORM_OR_INSECURE_REDIRECT')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

public_open=build_opener(PublicRedirects()).open

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def norm(s): return re.sub(r'\W+',' ',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()).strip()
def compact(s): return re.sub(r'\s+',' ',s or '').strip()
def utc(): return datetime.now(ZoneInfo('UTC')).isoformat()

def genda_category(raw):
    """Normalize agenda tags; countdown badges are NOT cultural categories."""
    if not raw:return None
    cleaned=compact(re.sub(r'\bEn\s+\d+\s*h(?:\s+\d+\s*min)?\b',' ',raw,flags=re.I))
    cleaned=compact(re.sub(r'\bEn\s+\d+\s*min\b',' ',cleaned,flags=re.I))
    cleaned=compact(re.sub(r'\bEn\s+menos\s+de\s+\d+\s*min\b',' ',cleaned,flags=re.I))
    tag=norm(cleaned)
    # Match explicit topic tags, never the event title/venue/remaining countdown.
    taxonomy=(
        (r'\bteatro\b|\bstand up\b','Teatro'),
        (r'\bcine\b|\bpelicula\b','Cine'),
        (r'\bmusica\b|\brecital\b|\ben vivo\b','Música'),
        (r'\belectronica\b|\btechno\b','Electrónica'),
        (r'\bferia\b','Feria'),
        (r'\bcharla\b|\bconversatorio\b|\bdebate\b','Charlas'),
        (r'\bliteratura\b|\blibros\b','Literatura'),
        (r'\bmuestra\b|\bexpo\b|\bfotografia\b|\bartes visuales\b','Arte'),
        (r'\bdanza\b|\bbaile\b','Danza'),
        (r'\btaller\b|\bseminario\b','Taller especial'),
        (r'\bfiesta\b','Fiesta'),
        (r'\bvino\b|\bdegustacion\b|\bcata\b','Vino'),
        (r'\binfantil\b|\bninos\b','Infantiles'),
        (r'\bgastronomia\b','Gastronomía'),
    )
    for pattern,label in taxonomy:
        if re.search(pattern,tag):return label
    return 'Cultura' if tag else None

class Node:
    def __init__(self,tag='',attrs=(),parent=None):
        self.tag=tag; self.a=dict(attrs); self.parent=parent; self.parts=[]
    def walk(self):
        yield self
        for p in self.parts:
            if isinstance(p,Node): yield from p.walk()
    def text(self):
        if self.tag in {'script','style','noscript'}: return ''
        return compact(' '.join(p.text() if isinstance(p,Node) else p for p in self.parts))
    def cls(self,c): return c in self.a.get('class','').split()

class Tree(HTMLParser):
    def __init__(self,s):
        super().__init__(convert_charrefs=True); self.root=Node(); self.cur=self.root; self.feed(s)
    def handle_starttag(self,t,a):
        n=Node(t,a,self.cur); self.cur.parts.append(n)
        if t not in VOID:self.cur=n
    def handle_startendtag(self,t,a): self.handle_starttag(t,a); self.handle_endtag(t)
    def handle_endtag(self,t):
        n=self.cur
        while n.parent:
            if n.tag==t:self.cur=n.parent;break
            n=n.parent
    def handle_data(self,d):self.cur.parts.append(d)

class Collector:
    def __init__(self,out,previous=None):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True)
        self.docs={};self.proposals={};self.checks=[];self.robots={};self.policy_errors={}
        self.source_followups=[]
        self.checkpoint=None;self.baseline=[]
        self.previous=previous or {};self.previous_docs={d['url']:d for d in self.previous.get('documents',[])}
        self.run_id='radar2-'+datetime.now(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')
        self.code_sha256=sha(Path(__file__).read_text())
    def allowed(self,url):
        p=urlsplit(url)
        if p.scheme!='https' or platform_host(p.hostname):
            self.policy_errors[url]='PLATFORM_PERMISSION_REQUIRED_OR_NON_HTTPS';return False
        root=f'https://{p.netloc}'
        if root not in self.robots:
            rp=RobotFileParser(); rp.set_url(root+'/robots.txt')
            try:
                with public_open(Request(root+'/robots.txt',headers={'User-Agent':UA}),timeout=12) as r:
                    rp.parse(r.read(100000).decode('utf-8','replace').splitlines())
            except HTTPError as e:
                rp.parse(['User-agent: *','Disallow: /'] if e.code in (401,403,429) else [])
                if e.code in (401,403,429):self.policy_errors[root]='ROBOTS_HTTP_'+str(e.code)
            except Exception as e:
                self.policy_errors[url]='ROBOTS_CHECK_UNAVAILABLE_'+type(e).__name__
                return False
            self.robots[root]=rp
        allowed=self.robots[root].can_fetch(UA,url)
        if not allowed:self.policy_errors[url]=self.policy_errors.get(root,'ROBOTS_DISALLOW')
        return allowed
    def fetch(self,url,source,origin=None):
        if url in self.docs:return self.docs[url]
        check={'url':url,'source':source,'checked_at':utc(),'origin':origin}
        if not self.allowed(url):
            check['error']=self.policy_errors.get(url,'ROBOTS_OR_PLATFORM_PERMISSION');self.checks.append(check);return None
        try:
            with public_open(Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'}),timeout=20) as r:
                raw=r.read(2500001)
                if len(raw)>2500000:raise ValueError('BODY_LIMIT')
                if platform_host(urlsplit(r.url).hostname):raise ValueError('PLATFORM_REDIRECT')
                s=raw.decode('utf-8','replace');t=Tree(s).root
                title=next((n.text() for n in t.walk() if n.tag=='title'),'')
                text=t.text()
                if re.search(r'verify you are human|checking your browser|just a moment|access denied|site unavailable',title,re.I):raise ValueError('ACCESS_BLOCK')
                h=sha(s); key=sha(url)
                (self.out/(key+'.html')).write_text(s)
                d={'url':url,'final_url':r.url,'source':source,'origin':origin,'fetched_at':utc(),'sha256':h,'text_sha256':sha(text),'title':title,'text':text,'html_file':key+'.html','http_status':r.status}
                self.docs[url]=d;check.update(status=r.status,sha256=h)
                article=next((n for n in t.walk() if n.tag=='article'),None)
                if article:d['content_blocks']=[{'tag':n.tag,'text':n.text()} for n in article.walk() if n.tag in ('h1','h2','h3','p','li') and n.text()][:500]
                d['structured_items']=self.structured(d)
                published=next((x.get('datePublished') for x in d['structured_items'] if x.get('datePublished')),None)
                if published:d['published_at']=published
                # Capture candidate photo URLs from this already permitted fetch.
                # The dossier review gate must resolve subject, image quality and
                # distribution rights; discovery does not download or publish.
                from media_source_leads import leads
                d['media_leads_v1']=leads(t,d)
        except Exception as e:
            check.update(error=type(e).__name__+': '+str(e)[:180]);d=None
        if d and self.checkpoint:self.checkpoint(d)
        self.checks.append(check);time.sleep(.25);return d
    def add(self,d,title,day=None,hour=None,venue=None,category=None,state='investigable',evidence='',origin_account=None,source_id=None):
        if not title:return
        key=sha('|'.join([d['url'],source_id or norm(title),day or '',hour or '']))
        self.proposals[key]={'id':key,'document_url':d['url'],'source':d['source'],'title':compact(title),'date':day,'time':hour,'venue':compact(venue) or None,'category':category,'state':state,'evidence':compact(evidence)[:8000],'origin_account':origin_account,'source_id':source_id,'discovered_at':d['fetched_at']}
        self.proposals[key]['entities']=([{'name':compact(venue),'role':'venue','evidence':compact(evidence)[:1000]}] if venue else [])
        self.proposals[key]['mentions']=sorted({m[1] for m in re.finditer(r'(?<!\w)@([a-zA-Z0-9_.]{2,30})',evidence) if not re.match(r'[\"\x27]\s*:',evidence[m.end():])})
        return key
    def discovery(self,manifest,accounts_path='radar2/accounts.json',limit_per_query=5):
        """Consume freshly executed search responses, not hand-entered event URLs."""
        from extract import extract_document
        from concurrent.futures import ThreadPoolExecutor
        accounts=json.loads(Path(accounts_path).read_text());selected={};per_query={}
        roster={a['handle']:a for a in json.loads(Path(__file__).with_name('instagram_roster.json').read_text())}
        rejected=('wikipedia.org','reddit.com','scribd.com','vlex.com.co','twstalker.com','threadreaderapp.com','docsity.com','paperzz.com')
        for row in manifest['documents']:
            u=row['url'];host=urlsplit(u).hostname or '';q=row['searches'][0]['query_id']
            if host=='instagram.com' or host.endswith('.instagram.com'):
                self.indexed_instagram(row)
                continue
            targeted=[roster[u] for search in row['searches'] for u in search.get('accounts',[]) if u in roster and search['query_id'].startswith('ig-')]
            if targeted:
                content=norm(row['title']+' '+row.get('excerpt','')+' '+u)
                identity=any(norm(a['handle']) in content or norm(a['name'].split(' — ')[0].split(' · ')[0]) in content for a in targeted)
                cultural=TARGETED_EVENT_SIGNALS.search(content)
                if not identity or not cultural:
                    self.checks.append({'url':u,'status':'discarded_unrelated_rotation_result','discovery':row['searches']});continue
            if any(host.endswith(x) for x in rejected) or re.search(r'/202[0-5](?:/|-)',urlsplit(u).path):
                self.checks.append({'url':u,'status':'discarded_historical_or_not_announcement','discovery':row['searches']});continue
            if host in ('agendalaplata.ar','www.agendalaplata.ar','teatrocerca.com.ar','www.0221.com.ar','www.eldia.com'):
                self.checks.append({'url':u,'status':'known_agenda_not_open_discovery'});continue
            if per_query.get(q,0)>=limit_per_query:continue
            selected[u]=row;per_query[q]=per_query.get(q,0)+1
        grouped={}
        for row in selected.values():grouped.setdefault(urlsplit(row['url']).hostname,[]).append(row)
        def acquire(rows):
            for row in rows:
                d=self.fetch(row['url'],urlsplit(row['url']).hostname,row['searches'][0]['query'])
                if not d:continue
                d['discovery']=row['searches'];d['acquisition_method']='public_search_then_http'
                if not self.reuse(d):extract_document(self,d,accounts,'public_search_then_http')
                event_items=[x for x in self.structured(d) if re.search(r'Event$',str(x.get('@type',''))) and x.get('startDate')]
                if len(event_items)>1:self.follow_ticket_originals(d,accounts,limit=2)
                # Follow a few publicly linked originals/program entries. No new
                # domain or permalink is supplied by a human to this step.
                if not any(p.get('kind')=='event' and p['document_url']==d['url'] for p in self.proposals.values()):
                    candidates=[]
                    for u in self.links(d):
                        if u==row['url'] or u in self.docs:continue
                        if re.search(r'/eventos/|/2026/talleres/|/2026/programacion/',u):candidates.append(u)
                    for u in candidates[:3]:
                        child=self.fetch(u,urlsplit(u).hostname,d['url'])
                        if child:
                            child['discovery']=[{'via_link':d['url'],'searches':row['searches']}]
                            extract_document(self,child,accounts,'public_search_then_public_link')
        with ThreadPoolExecutor(max_workers=4) as ex:
            for result in ex.map(acquire,grouped.values()):pass
    def indexed_instagram(self,row):
        """Search-engine excerpt only. Never fetch IG or infer unseen caption/date."""
        from extract import category
        excerpt=row.get('excerpt','').strip()
        if not excerpt:return
        at=row['searches'][0]['searched_at'];url=row['url']
        d={'url':url,'final_url':url,'source':'Instagram (índice público)',
           'title':row['title'],'text':excerpt,'sha256':sha(excerpt),'text_sha256':sha(excerpt),
           'fetched_at':at,'discovery':row['searches'],'acquisition_method':'public_search_index',
           'direct_profile_read':False,'content_scope':'search_excerpt_only'}
        self.docs[url]=d
        path=urlsplit(url).path.strip('/').split('/')
        profile=path[0] if path and path[0] not in ('p','reel','reels','explore','stories') else None
        # A result matching a query does not prove that account authored a post.
        key=self.add(d,row['title'],category=category(row['title']+' '+excerpt),state='investigable',evidence=excerpt)
        self.proposals[key].update(kind='document',acquisition_method='public_search_index',
            discovery=row['searches'],original_url=url,profile_username=profile,
            date_basis='no event date asserted from search metadata',content_scope='search_excerpt_only',
            direct_profile_read=False,related_accounts=[])
        self.checks.append({'url':url,'status':'indexed_excerpt_preserved','checked_at':at,'direct_profile_read':False})
    def follow_ticket_originals(self,d,accounts,limit=3):
        """Read original ticket links published in public structured event data."""
        from extract import extract_document
        links=self.links(d)
        for item in self.structured(d):
            offers=item.get('offers') or [];offers=offers if isinstance(offers,list) else [offers]
            links += [o['url'] for o in offers if isinstance(o,dict) and isinstance(o.get('url'),str)]
        selected=[]
        for u in dict.fromkeys(links):
            if u in self.docs or not re.search(r'/eventos/|/evento/|gotticket|tuentrada',u):continue
            if platform_host(urlsplit(u).hostname):continue
            selected.append(u)
        for u in selected[:limit]:
            child=self.fetch(u,urlsplit(u).hostname,d['url'])
            if child:
                child['discovery']=[{'via_link':d['url'],'searches':d.get('discovery',[])}]
                child['acquisition_method']='public_search_then_published_ticket_link'
                extract_document(self,child,accounts,child['acquisition_method'])
    def tree(self,d):
        path=self.out/d.get('html_file','__missing__')
        if path.is_file():return Tree(path.read_text()).root
        if d.get('content_blocks'):
            return Tree('<article>'+''.join('<'+b['tag']+'>'+html.escape(b['text'])+'</'+b['tag']+'>' for b in d['content_blocks'])+'</article>').root
        return Tree('<article><p>'+html.escape(d.get('text',''))+'</p></article>').root
    def reuse(self,d):
        if self.previous.get('collector_sha256')!=self.code_sha256:return False
        processor=Path(__file__).with_name('extract.py')
        if processor.exists() and self.previous.get('processor_sha256')!=sha(processor.read_text()):return False
        prev=self.previous_docs.get(d['url'])
        if not prev or sha(prev['text'])!=sha(d['text']):return False
        for p in self.previous.get('proposals',[]):
            if p['document_url']==d['url']:self.proposals[p['id']]=dict(p)
        d['unchanged_content_reused']=True
        return True
    def links(self,d):
        return list(dict.fromkeys(urljoin(d['final_url'],n.a['href']) for n in self.tree(d).walk() if n.tag=='a' and n.a.get('href')))
    def structured(self,d):
        if d.get('structured_items'):return d['structured_items']
        items=[]
        def visit(x):
            if isinstance(x,dict):
                items.append(x)
                for v in x.values():visit(v)
            elif isinstance(x,list):
                for v in x:visit(v)
        for n in self.tree(d).walk():
            if n.tag=='script' and n.a.get('type')=='application/ld+json':
                try:visit(json.loads(''.join(p for p in n.parts if isinstance(p,str))))
                except ValueError:pass
        return items
    def document_lead(self,d,account=None,state='investigable'):
        if self.reuse(d):return
        t=self.tree(d); title=next((n.text() for n in t.walk() if n.tag=='h1'),d['title'])
        articles=[n.text() for n in t.walk() if n.tag=='article']
        body=max(articles,key=len) if articles else d['text']
        d['original_links']=[u for u in self.links(d) if platform_host(urlsplit(u).hostname) or any(x in u for x in ['ticket','bombo','evento-simple','dogma'])]
        raw_path=self.out/d.get('html_file','__missing__')
        raw=raw_path.read_text() if raw_path.is_file() else d.get('text','')
        d['instagram_permalinks']=sorted(set(re.findall(r'https?://(?:www\.)?instagram.com/(?:p|reel)/[\w-]+/?',html.unescape(raw).replace('\\/','/'))))
        published=next((x.get('datePublished') for x in self.structured(d) if x.get('datePublished')),None)
        if published:d['published_at']=published
        self.add(d,title,state=state,evidence=body,origin_account=account)
    def teatrocerca(self):
        d=self.fetch('https://teatrocerca.com.ar/teatro-independiente','TeatroCerca')
        if not d:return
        links=[u for u in self.links(d) if '/funcion/la-plata/' in u]
        for u in links[:16]:
            item=self.fetch(u,'TeatroCerca',d['url'])
            if not item:continue
            if self.reuse(item):continue
            title=next((n.text() for n in self.tree(item).walk() if n.tag=='h1'),item['title'].split(' en ')[0])
            date=re.search(r'/(\d+)-(\w+)-(20\d{2})/?$',u)
            months={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
            day=f'{date[3]}-{months[date[2]]:02}-{int(date[1]):02}' if date and date[2] in months else None
            selected=re.search(r'Función seleccionada (.*?)(?:Más funciones|Compartir)',item['text'])
            block=selected[1] if selected else ''
            hour=re.search(r'(\d{1,2}:\d{2}) Hs\.',block)
            venue=re.search(r'Hs\. (.*?) · La Plata',block)
            self.add(item,title,day,hour[1] if hour else None,venue[1] if venue else None,'Teatro','observado_agenda',block or item['text'])
    def media_sources(self,max_articles=6,agendas_only=False):
        for url,source in [('https://www.eldia.com/espectaculos','El Día'),('https://www.0221.com.ar/que-hago','0221')]:
            d=self.fetch(url,source)
            if not d:continue
            links=self.links(d)
            if source=='El Día':
                links += [x['url'] for x in self.structured(d) if x.get('@type')=='ListItem' and x.get('url')]
                links=[u for u in dict.fromkeys(links) if re.search(r'/espectaculos/[^/]+_\d+',u) and re.search(r'agenda|platense|teatro|festival|concierto|recital|musica|muestra|cierre-de-ano',norm(u))]
                links=sorted(links,key=lambda u:(not bool(re.search(r'agenda|cartelera|programacion',norm(u))),-int(re.search(r'_(\d+)',u)[1])))[:6]
            else:links=sorted(dict.fromkeys(u for u in links if re.search(r'/que-hago/.+-n\d+$',u)),key=lambda u:(not bool(re.search(r'agenda|cartelera|programacion',norm(u))),-int(re.search(r'-n(\d+)$',u)[1])))[:6]
            if agendas_only:links=[u for u in links if re.search(r'agenda|cartelera|programacion',norm(u))]
            for u in links[:max_articles]:
                item=self.fetch(u,source,d['url'])
                if item:
                    from extract import extract_document
                    extract_document(self,item,json.loads(Path(__file__).with_name('accounts.json').read_text()),'public_media_discovery')
    def alternativa(self):
        d=self.fetch('https://www.alternativateatral.com/cartelera.asp?prov=Buenos+Aires','Alternativa Teatral')
        if not d:return
        links=[u for u in self.links(d) if re.search(r'/obra\d+',u)]
        if not links:
            self.checks.append({'url':d['url'],'error':'DYNAMIC_LISTING_NO_WORKS_IN_HTML'})
            # Official linked news channel is a separate discovery opportunity.
            n=self.fetch(urljoin(d['url'],'novedades.asp'),'Alternativa Teatral',d['url'])
            if n:
                links=[u for u in self.links(n) if re.search(r'/obra\d+',u)]
        for u in links[:8]:
            item=self.fetch(u,'Alternativa Teatral',d['url'])
            if item and 'La Plata' in item['text']:self.document_lead(item)
    def cultural_channels(self,only=None):
        channels=[
          ('https://compras.evento-simple.com/sunsetwinemix','Sunset Wine Mixology','sunsetwine.mixology'),
          ('https://circusproduce.com/','Circus','circus_ofc'),
          ('https://residenciacorazon.com.ar/','Residencia Corazón','residenciacorazon'),
          ('https://biblio.unlp.edu.ar/mes-de-la-plata-2026-2/','Biblioteca Pública UNLP · Mes de La Plata',None),
          ('https://reddemuseos.unlp.edu.ar/','Red de Museos UNLP',None),
          ('https://museo.fisica.unlp.edu.ar/','Museo de Física UNLP',None),
          ('https://www.ucalp.edu.ar/agenda/','Agenda UCALP',None),
          ('https://maclamuseo.com.ar/','MACLA original exhibitions','maclamuseo'),
          ('https://www.gba.gob.ar/museo_pettoruti/muestras','Pettoruti original exhibitions','museopettoruti'),
          ('https://institutocultural.gba.gob.ar/taxonomy/term/1746','Islas Malvinas institutional','laplata.ciudadcultural'),
          ('https://www.casadionisio.com.ar/expoarte','ExpoArte Casa Dionisio','dionisio_vinoteca'),
          ('https://www.casadionisio.com.ar/','Casa Dionisio','dionisio_vinoteca'),
          ('https://tickets.sincroniadeportiva.com.ar/','Sincronía Deportiva original',None),
          ('https://lauragan.com.ar/','Laura Gan institucional','lauraganceramica'),
          ('https://www.eventbrite.com.ar/o/sincronia-deportiva-eventos-17694669676','Sincronía Eventbrite organizador',None),
          ('https://linktr.ee/lutitravelguide','Luti','lutitravelguide'),
          ('https://linktr.ee/circus_ofc','Circus links','circus_ofc'),
          ('https://linktr.ee/guajirabar','Guajira','guajira.bar'),
          ('https://enesoestamosfc.wordpress.com/','En Eso Estamos','en_eso_estamos'),
          ('https://www.dynamoteatro.com/','Dynamo Teatro',None),
          ('https://jodify.com.ar/profiles/promoter/0244a70e-e89f-4adf-ac27-ae1ed2bce374','Nómade',None),
        ]
        # Exact current program leads discovered by the editorial review.
        # They use the same FULL collector, robots, original archive and interpreter.
        # Expire the edition-specific seeds, not the permanent institution roots.
        current_programs=[
          ('https://museo.fisica.unlp.edu.ar/noche-de-museos-a-la-luz-de-la-luna/','Museo de Física UNLP · programa',None,'2026-11-15','institutional_program_original_v1'),
          ('https://www.ucalp.edu.ar/el-beato-angelico-de-la-ucalp-se-suma-museos-la-luz-de-la-luna-con-arte-y-musica-coral/','UCALP · Beato Angélico programa',None,'2026-11-15','institutional_program_original_v1'),
          ('https://infolaplata.com/llega-el-11o-encuentro-de-acordeonistas-del-rio-de-la-plata/','Infolaplata · programa acordeonistas',None,'2026-11-15','dated_local_program_secondary_v1'),
        ]
        today=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat()
        for url,source,account,expires,method in current_programs:
            if today>expires or (only and source not in only):continue
            d=self.fetch(url,source)
            if not d or self.reuse(d):continue
            from extract import extract_document
            d['acquisition_method']=method
            extract_document(self,d,json.loads(Path(__file__).with_name('accounts.json').read_text()),method)
        for url,source,account in channels:
            if only and source not in only:continue
            if source=='Biblioteca Pública UNLP · Mes de La Plata' and datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat()>'2026-11-30':continue
            d=self.fetch(url,source)
            if not d:continue
            if source in ('Red de Museos UNLP','Museo de Física UNLP','Agenda UCALP'):
                from extract import extract_document
                accounts=json.loads(Path(__file__).with_name('accounts.json').read_text())
                if not self.reuse(d):
                    self.document_lead(d,state='investigable')
                host=urlsplit(d['final_url']).hostname
                ranked={}
                for node in self.tree(d).walk():
                    if node.tag!='a' or not node.a.get('href'):continue
                    link=urlsplit(urljoin(d['final_url'],node.a['href']))
                    if link.scheme!='https' or link.hostname!=host or link.username or link.password:continue
                    path=link.path.rstrip('/')
                    if not path or path==urlsplit(d['final_url']).path.rstrip('/'):continue
                    label=norm(path+' '+node.text())
                    if not re.search(r'noche de museos|museos a la luz|encuentro de coros|feria de artes|muestra temporal|inauguracion|intervencion artistica',label):continue
                    if re.search(r'\b20\d{2}\b',label) and str(datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).year) not in label:continue
                    if re.search(r'/category/|/tag/|/wp-content/|/page/|[.](?:pdf|png|jpg)$',path,re.I):continue
                    target=link._replace(query='',fragment='').geturl()
                    ranked.setdefault(target,0 if re.search(r'museos a la luz|noche de museos',label) else 1)
                for target in sorted(ranked,key=ranked.get)[:3]:
                    item=self.fetch(target,source,d['url'])
                    if item and not self.reuse(item):
                        item['acquisition_method']='institutional_art_original_v1'
                        extract_document(self,item,accounts,'institutional_art_original_v1')
                continue
            if source in ('Biblioteca Pública UNLP · Mes de La Plata','MACLA original exhibitions','Pettoruti original exhibitions',
                          'Islas Malvinas institutional','ExpoArte Casa Dionisio'):
                # Existing FULL only. An exhibition period must not be rewritten
                # into individual daily performances. The original yields an
                # evidence-backed research proposal, NEVER a confirmed event.
                if not self.reuse(d):
                    from extract import extract_document
                    method='institutional_program_original_v1' if source.startswith('Biblioteca Pública UNLP ·') else 'institutional_art_original_v1'
                    d['acquisition_method']=method
                    extract_document(self,d,json.loads(Path(__file__).with_name('accounts.json').read_text()),method)
                continue
            if source=='Sincronía Eventbrite organizador':
                # Only the producer's own linked event pages; HTTP/robots still
                # control every request. No fixed future dates or trust by label.
                if not self.reuse(d):
                    self.add(d,source,state='actor',evidence=d['text'][:4000])
                from extract import extract_document
                accounts=json.loads(Path(__file__).with_name('accounts.json').read_text())
                visited=set()
                for u in self.links(d):
                    if len(visited)>=4:break
                    p=urlsplit(u)
                    if p.scheme!='https' or p.hostname not in ('eventbrite.com.ar','www.eventbrite.com.ar'):continue
                    if not re.fullmatch(r'/e/[a-z0-9-]+-tickets-\d+/?',p.path,re.I):continue
                    u=p._replace(query='',fragment='').geturl()
                    if u in visited:continue
                    visited.add(u)
                    child=self.fetch(u,source,d['url'])
                    if not child or self.reuse(child):continue
                    if 'sincronía deportiva eventos' not in child['text'][:3500].lower() and 'sincronia deportiva eventos' not in child['text'][:3500].lower():
                        self.checks.append({'url':u,'status':'organizer_not_proven'})
                        continue
                    if re.search(r'evento finalizado|event finished|event ended',child['text'][:400],re.I):
                        self.checks.append({'url':u,'status':'organizer_event_already_finished'})
                        continue
                    child['acquisition_method']='original_eventbrite_organizer_v1'
                    extract_document(self,child,accounts,'original_eventbrite_organizer_v1')
                continue
            if source=='Sincronía Deportiva original':
                # Inside the existing daily FULL; only links published by the
                # organizer itself. No weekly events invented, no new workflow.
                from extract import extract_document
                accounts=json.loads(Path(__file__).with_name('accounts.json').read_text())
                if not self.reuse(d):
                    d['acquisition_method']='institutional_sports_original_v1'
                    extract_document(self,d,accounts,'institutional_sports_original_v1')
                visited=set()
                for u in self.links(d):
                    if len(visited)>=3:break
                    link=urlsplit(u)
                    if link.scheme!='https' or link.hostname!='tickets.sincroniadeportiva.com.ar' or not link.path.startswith('/event/'):continue
                    if u in visited:continue
                    visited.add(u)
                    child=self.fetch(u,source,d['url'])
                    if child and not self.reuse(child):
                        child['acquisition_method']='institutional_sports_original_detail_v1'
                        extract_document(self,child,accounts,'institutional_sports_original_detail_v1')
                continue
            if not self.reuse(d):self.add(d,source,state='actor',evidence=d['text'],origin_account=account)
            if source=='Sunset Wine Mixology':
                for u in [u for u in self.links(d) if '/sunsetwinemix/eventos/' in u][:3]:
                    item=self.fetch(u,source,d['url'])
                    if not item:continue
                    if self.reuse(item):continue
                    text=item['text'];m=re.search(r'Fecha (\d+)\.([A-Z]{3})\.(20\d{2}) (\d{1,2}:\d{2})hs',text)
                    venue=re.search(r'Lugar (.*?) Conseguí',text)
                    title=item['title'].split(' - ')[0]
                    month={'ENE':1,'FEB':2,'MAR':3,'ABR':4,'MAY':5,'JUN':6,'JUL':7,'AGO':8,'SEP':9,'OCT':10,'NOV':11,'DIC':12}
                    day=f'{m[3]}-{month[m[2]]:02}-{int(m[1]):02}' if m and m[2] in month else None
                    place=venue[1] if venue else None
                    # Ticket explicitly separates venue and street address in markup.
                    place=re.split(r' (?=\d{2,4} entre )',place,maxsplit=1)[0] if place else None
                    self.add(item,title,day,m[4] if m else None,place,'Vino / fiesta','fuente_original' if day else 'incompleto',text,account)
    def genda(self,start,days=7):
        for i in range(max(1,min(int(days),7))):
            day=(start+timedelta(days=i)).isoformat();url='https://agendalaplata.ar/?fecha='+day
            d=self.fetch(url,'Genda')
            if not d:continue
            tree=Tree((self.out/d['html_file']).read_text()).root
            canonical=next((n.a.get('href') for n in tree.walk() if n.tag=='link' and n.a.get('rel')=='canonical'),None)
            if not canonical or parse_qs(urlsplit(canonical).query).get('fecha')!=[day]:
                self.checks.append({'url':url,'error':'SELECTED_DATE_NOT_VERIFIED'});continue
            if self.reuse(d):continue
            for n in tree.walk():
                if not re.fullmatch(r'evento-\d+',n.a.get('id','')):continue
                nodes=list(n.walk());info=next((x for x in nodes if x.a.get('data-title') and 'evento.php' in x.a.get('data-url','')),n)
                title=info.a.get('data-title');venue=info.a.get('data-sitio')
                if not title:
                    title=next((x.text() for x in nodes if x.cls('lh-sm')),None)
                hour=re.search(r'\b([0-2]?\d:[0-5]\d)\b',n.text())
                raw_cats=next((x.text() for x in nodes if x.cls('evento-tabs')),None)
                cats=genda_category(raw_cats)
                evidence=n.text();ident=n.a['id'].removeprefix('evento-')
                # Keep missing venue and completed sessions; recommendations outside
                # the selected day have no evento-ID and cannot contaminate this set.
                self.add(d,title,day,hour[1] if hour else None,venue,cats,'observado_agenda',evidence,source_id=ident)
                key=sha('|'.join([d['url'],ident,day,hour[1] if hour else '']))
                if key in self.proposals:
                    # Public modal data-url contains an obsolete filesystem prefix.
                    # Use the site's own share link or its public search response.
                    pretty=next((m[0] for x in nodes for v in x.a.values() if isinstance(v,str) for m in [re.search(r'https://agendalaplata\.ar/evento/[a-z0-9-]+',v)] if m),None)
                    if not pretty:
                        lookup='https://agendalaplata.ar/agendalaplata.ar/components/buscador_result.php?'+urlencode({'search':title})
                        found=self.fetch(lookup,'Genda public search',d['url'])
                        if found:
                            try:
                                payload=json.loads((self.out/found['html_file']).read_text())
                                match=next((x for x in payload.get('eventos',[]) if str(x.get('id'))==ident),None)
                                if match:pretty=urljoin('https://agendalaplata.ar/',match.get('url') or ('/evento/'+match['slug']))
                            except (ValueError,KeyError):pass
                    self.proposals[key]['original_url']=pretty or d['url']
                    self.proposals[key]['kind']='event';self.proposals[key]['acquisition_method']='genda_seven_consecutive_days'
                    self.proposals[key]['category_source_raw']=raw_cats
                    if pretty and not cats:
                        detail=self.fetch(pretty,'Genda detail',d['url'])
                        if detail:
                            raw_cats=' '.join(x.text() for x in self.tree(detail).walk() if x.cls('tag-evento'))
                            self.proposals[key]['category_source_raw']=raw_cats
                            self.proposals[key]['category']=genda_category(raw_cats)
                    self.proposals[key]['link_resolution']='source_share_url' if pretty else 'listing_fallback_no_verified_detail'
    def genda_theatre(self):
        d=self.fetch('https://agendalaplata.ar/teatro','Genda teatro')
        if not d:return
        if self.reuse(d):return
        # The site's JSON-LD is truncated to 30 while 37 cards are visible.
        # Read ALL date groups, including the final seven, from the public DOM.
        months={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
        at=datetime.fromisoformat(d['fetched_at']).astimezone(ZoneInfo('America/Argentina/Buenos_Aires')).date()
        day=None;label=''
        for n in self.tree(d).walk():
            if n.cls('titulo-fecha'):
                label=n.text();m=re.search(r'(\d{1,2}) de (\w+)',label,re.I);day=None
                if m and m[2].lower() in months:
                    month=months[m[2].lower()];year=at.year+(1 if month<at.month and at.month==12 else 0)
                    candidate=at.replace(year=year,month=month,day=int(m[1]))
                    if at<=candidate<=at+timedelta(days=90):day=candidate.isoformat()
            if n.tag!='a' or not n.cls('card-evento') or not day:continue
            nodes=list(n.walk());title=next((x.text() for x in nodes if x.cls('titulo')),None)
            venue=next((x.text() for x in nodes if x.cls('lugar')),None)
            hour=re.search(r'(\d{1,2}:\d{2})',next((x.text() for x in nodes if x.cls('pill-hora')),''))
            hour=hour[1] if hour else None
            self.add(d,title,day,hour,venue,'Teatro','observado_agenda',label+' | '+n.text()+' | Año inferido del contexto de la cartelera actual, no impreso en el rótulo del día.')
            key=sha('|'.join([d['url'],norm(title),day,hour or '']))
            if key in self.proposals:self.proposals[key]['original_url']=n.a.get('href')
    def save(self):
        result={'run_id':self.run_id,'collector_sha256':self.code_sha256,'finished_at':utc(),'documents':list(self.docs.values()),'proposals':list(self.proposals.values()),'checks':self.checks,
                'source_followups':list(self.source_followups)}
        processor=Path(__file__).with_name('extract.py')
        if processor.exists():result['processor_sha256']=sha(processor.read_text())
        (self.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='radar2-run');p.add_argument('--start');p.add_argument('--web',action='store_true');p.add_argument('--previous');p.add_argument('--discovery');p.add_argument('--baseline');p.add_argument('--legacy-baseline');p.add_argument('--run-id');a=p.parse_args()
    start=datetime.fromisoformat(a.start).date() if a.start else datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
    previous=json.loads(Path(a.previous).read_text()) if a.previous else None
    c=Collector(a.out,previous)
    if a.run_id:c.run_id=a.run_id
    c.genda(start);c.save()
    if a.discovery:c.discovery(json.loads(Path(a.discovery).read_text()));c.save()
    if a.web:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as ex:
            tasks=[ex.submit(f) for f in [c.teatrocerca,c.media_sources,c.alternativa,c.cultural_channels,c.genda_theatre]]
            for t in tasks:t.result();c.save()
    r=c.save()
    if a.baseline:
        from reconcile import reconcile
        r=reconcile(r,json.loads(Path(a.baseline).read_text()))
        if a.legacy_baseline:
            from reconcile import mark_previous_knowledge
            r=mark_previous_knowledge(r,json.loads(Path(a.legacy_baseline).read_text()))
        (c.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({'run_id':r['run_id'],'documents':len(r['documents']),'proposals':len(r['proposals']),'errors':[x for x in r['checks'] if x.get('error')]},ensure_ascii=False))
if __name__=='__main__':main()
