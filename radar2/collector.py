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
BLOCKED = {'instagram.com','www.instagram.com','facebook.com','www.facebook.com'}

class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlsplit(newurl)
        if p.scheme!='https' or p.hostname in BLOCKED:raise ValueError('PLATFORM_OR_INSECURE_REDIRECT')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

public_open=build_opener(PublicRedirects()).open

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def norm(s): return re.sub(r'\W+',' ',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()).strip()
def compact(s): return re.sub(r'\s+',' ',s or '').strip()
def utc(): return datetime.now(ZoneInfo('UTC')).isoformat()

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
        self.previous=previous or {};self.previous_docs={d['url']:d for d in self.previous.get('documents',[])}
        self.run_id='radar2-'+datetime.now(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')
        self.code_sha256=sha(Path(__file__).read_text())
    def allowed(self,url):
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname in BLOCKED:
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
                if urlsplit(r.url).hostname in BLOCKED:raise ValueError('PLATFORM_REDIRECT')
                s=raw.decode('utf-8','replace');t=Tree(s).root
                title=next((n.text() for n in t.walk() if n.tag=='title'),'')
                text=t.text()
                if re.search(r'verify you are human|checking your browser|just a moment|access denied|site unavailable',title,re.I):raise ValueError('ACCESS_BLOCK')
                h=sha(s); key=sha(url)
                (self.out/(key+'.html')).write_text(s)
                d={'url':url,'final_url':r.url,'source':source,'origin':origin,'fetched_at':utc(),'sha256':h,'text_sha256':sha(text),'title':title,'text':text,'html_file':key+'.html','http_status':r.status}
                self.docs[url]=d;check.update(status=r.status,sha256=h)
        except Exception as e:
            check.update(error=type(e).__name__+': '+str(e)[:180]);d=None
        self.checks.append(check);time.sleep(.25);return d
    def add(self,d,title,day=None,hour=None,venue=None,category=None,state='investigable',evidence='',origin_account=None,source_id=None):
        if not title:return
        key=sha('|'.join([d['url'],source_id or norm(title),day or '',hour or '']))
        self.proposals[key]={'id':key,'document_url':d['url'],'source':d['source'],'title':compact(title),'date':day,'time':hour,'venue':compact(venue) or None,'category':category,'state':state,'evidence':compact(evidence)[:8000],'origin_account':origin_account,'source_id':source_id,'discovered_at':d['fetched_at']}
        self.proposals[key]['entities']=([{'name':compact(venue),'role':'venue','evidence':compact(evidence)[:1000]}] if venue else [])
        self.proposals[key]['mentions']=sorted(set(re.findall(r'(?<!\w)@([a-zA-Z0-9_.]{2,30})',evidence)))
    def tree(self,d):return Tree((self.out/d['html_file']).read_text()).root
    def reuse(self,d):
        prev=self.previous_docs.get(d['url'])
        if not prev or sha(prev['text'])!=sha(d['text']):return False
        for p in self.previous.get('proposals',[]):
            if p['document_url']==d['url']:self.proposals[p['id']]=dict(p)
        d['unchanged_content_reused']=True
        return True
    def links(self,d):
        return list(dict.fromkeys(urljoin(d['final_url'],n.a['href']) for n in self.tree(d).walk() if n.tag=='a' and n.a.get('href')))
    def structured(self,d):
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
        d['original_links']=[u for u in self.links(d) if urlsplit(u).hostname in BLOCKED or any(x in u for x in ['ticket','bombo','evento-simple','dogma'])]
        d['instagram_permalinks']=sorted(set(re.findall(r'https?://(?:www\.)?instagram.com/(?:p|reel)/[\w-]+/?',html.unescape((self.out/d['html_file']).read_text()).replace('\\/','/'))))
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
    def media_sources(self):
        for url,source in [('https://www.0221.com.ar/que-hago','0221'),('https://www.eldia.com/espectaculos','El Día')]:
            d=self.fetch(url,source)
            if not d:continue
            links=self.links(d)
            if source=='El Día':
                links += [x['url'] for x in self.structured(d) if x.get('@type')=='ListItem' and x.get('url')]
                links=[u for u in dict.fromkeys(links) if re.search(r'/espectaculos/[^/]+_\d+',u) and re.search(r'agenda|platense|teatro|festival|concierto|recital|musica|muestra|cierre-de-ano',norm(u))]
                links=sorted(links,key=lambda u:int(re.search(r'_(\d+)',u)[1]),reverse=True)[:6]
            else:links=[u for u in links if re.search(r'/que-hago/.+-n\d+$',u)][:6]
            for u in links:
                item=self.fetch(u,source,d['url'])
                if item:self.document_lead(item)
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
          ('https://www.casadionisio.com.ar/','Casa Dionisio','dionisio_vinoteca'),
          ('https://linktr.ee/lutitravelguide','Luti','lutitravelguide'),
          ('https://linktr.ee/circus_ofc','Circus links','circus_ofc'),
          ('https://linktr.ee/guajirabar','Guajira','guajira.bar'),
          ('https://enesoestamosfc.wordpress.com/','En Eso Estamos','en_eso_estamos'),
          ('https://www.dynamoteatro.com/','Dynamo Teatro',None),
          ('https://jodify.com.ar/profiles/promoter/0244a70e-e89f-4adf-ac27-ae1ed2bce374','Nómade',None),
        ]
        for url,source,account in channels:
            if only and source not in only:continue
            d=self.fetch(url,source)
            if not d:continue
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
    def genda(self,start):
        for i in range(7):
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
                cats=next((x.text() for x in nodes if x.cls('evento-tabs')),None)
                evidence=n.text();ident=n.a['id'].removeprefix('evento-')
                # Keep missing venue and completed sessions; recommendations outside
                # the selected day have no evento-ID and cannot contaminate this set.
                self.add(d,title,day,hour[1] if hour else None,venue,cats,'observado_agenda',evidence,source_id=ident)
                key=sha('|'.join([d['url'],ident,day,hour[1] if hour else '']))
                if key in self.proposals and info.a.get('data-url'):
                    self.proposals[key]['original_url']=urljoin(d['final_url'],info.a['data-url'])
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
        result={'run_id':self.run_id,'collector_sha256':self.code_sha256,'finished_at':utc(),'documents':list(self.docs.values()),'proposals':list(self.proposals.values()),'checks':self.checks}
        (self.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='radar2-run');p.add_argument('--start');p.add_argument('--web',action='store_true');p.add_argument('--previous');a=p.parse_args()
    start=datetime.fromisoformat(a.start).date() if a.start else datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
    previous=json.loads(Path(a.previous).read_text()) if a.previous else None
    c=Collector(a.out,previous);c.genda(start);c.save()
    if a.web:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as ex:
            tasks=[ex.submit(f) for f in [c.teatrocerca,c.media_sources,c.alternativa,c.cultural_channels,c.genda_theatre]]
            for t in tasks:t.result();c.save()
    r=c.save()
    print(json.dumps({'run_id':r['run_id'],'documents':len(r['documents']),'proposals':len(r['proposals']),'errors':[x for x in r['checks'] if x.get('error')]},ensure_ascii=False))
if __name__=='__main__':main()
