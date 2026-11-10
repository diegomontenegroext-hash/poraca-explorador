"""Bounded autonomous discovery and evidence-backed cultural memory.

Runs in the existing GitHub job with Python's standard library. No Work-only
search, no new grants, no editorial admission. All ledgers use radar2.runs.
"""
import hashlib
import ipaddress
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from collector import UA, norm, compact, utc, sha, platform_host
from extract import extract_document
from persist import execute
from instagram import discover as meta_discover

SOURCE_STATE = 'radar2-source-discovery-state-v1'
GRAPH_STATE = 'radar2-cultural-memory-state-v1'
CULTURAL = re.compile(r'teatro|musica|music|recital|festival|cultur|galeria|exposici|arte\b|taller|ceramica|yoga|vino|wine|cata\b|fiesta|ciclo|entradas|tickets|eventos?|cartelera|agenda|programaci|residenc|artista|concierto|running|run club|carrera|ciclismo|cicloturismo|bicicleteada|salida en bicicleta|pedalead|kayak|remo|rollers|patinaje|senderismo|caminata grupal|travesia|stand up paddle|duatlon|triatlon', re.I)
LOCAL = re.compile(r'la plata|platense|berisso|ensenada|gonnet|gorina|city bell|villa elisa|tolosa', re.I)
REJECT = re.compile(r'/admin(?:/|$)|login|sign.?in|checkout|carrito|privacy|privacidad|terminos|terms|contact|/share/|/sharer|t\.me/|cookies|clasificad|funebre|tiendanube|mustang\.cloud|creativecommons|afip\.gov|\.pdf$|\.jpg$|\.png$|\.mp4$|\.zip$|/wp-json|/feed(?:/|$)', re.I)


# A link must carry its own cultural evidence; the page's subject alone cannot
# turn sponsors, footer services or sharing buttons into cultural sources.
UTILITY_HOSTS={'x.com','twitter.com','wa.me','t.me','telegram.me','wp.me','vimeo.com',
    'creativecommons.org','automattic.com','afip.gov.ar','argentina.gob.ar',
    'mustang.cloud','dosalcubo.com','dbyz.com.ar','solumedia.com','fanz.com.ar'}
UTILITY_TEXT=re.compile(r'cookie|privacidad|privacy|licen[cs]|legal|clasificado|funebre|publi(?:que|car)|cms|design|sponsor|auspici|share|compartir|contact|staff|estadistic|asociate|donar',re.I)

def cultural_link(url,label):
    p=urlsplit(url);host=p.hostname or ''
    if p.scheme!='https' or p.username or p.password or platform_host(host):return False
    if REJECT.search(url) or UTILITY_TEXT.search(norm(label)+' '+p.path):return False
    if any(host==h or host.endswith('.'+h) for h in UTILITY_HOSTS):return False
    if re.search(r'^(?:clasificados|funebres|club)\.',host):return False
    return bool(CULTURAL.search(norm(label)+' '+p.path+' '+host))


def safe_url(url):
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or p.username or p.password or p.port not in (None,443): return False
        host = p.hostname or ''
        if '.' not in host or host.endswith(('.local','.internal','.localhost','.neon.tech')): return False
        for result in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
            if not ipaddress.ip_address(result[4][0]).is_global: return False
        return True
    except (ValueError,OSError): return False


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not safe_url(newurl): raise ValueError('NON_PUBLIC_REDIRECT')
        if re.search(r'accounts/login|checkpoint|challenge|captcha',newurl,re.I): raise ValueError('AUTH_OR_CHALLENGE_STOP')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


OPEN = build_opener(SafeRedirects()).open


class PublicAccess:
    """One truthful policy receipt per origin; never treat an HTML login as robots."""
    def __init__(self): self.cache = {}; self.stopped = set()
    def policy(self,url):
        root = 'https://' + urlsplit(url).netloc
        if root not in self.cache:
            receipt = {'robots_url':root+'/robots.txt','checked_at':utc()}
            try:
                with OPEN(Request(receipt['robots_url'],headers={'User-Agent':UA}),timeout=12) as r:
                    raw = r.read(150001)
                    receipt.update(http_status=r.status,final_url=r.url,sha256=hashlib.sha256(raw).hexdigest())
                    text = raw.decode('utf-8','replace')
                    if len(raw)>150000 or r.url!=receipt['robots_url'] or not re.search(r'^\s*(User-agent|Sitemap):',text,re.I|re.M):
                        raise ValueError('ROBOTS_NOT_VERIFIABLE')
                    rp = RobotFileParser(); rp.parse(text.splitlines())
                    receipt['permission_notice'] = compact(' '.join(x.lstrip('# ') for x in text.splitlines() if x.startswith('#')))[:900]
                    self.cache[root]=(rp,receipt)
            except HTTPError as e:
                receipt.update(http_status=e.code,error='ROBOTS_HTTP_'+str(e.code)); self.cache[root]=(None,receipt)
            except Exception as e:
                receipt['error']=type(e).__name__+': '+str(e)[:100];self.cache[root]=(None,receipt)
        rp,receipt=self.cache[root]
        allowed=bool(rp and rp.can_fetch(UA,url))
        # Instagram's explicit written-permission requirement remains binding
        # even if an individual robots path happens to be open.
        if 'instagram.com' in root and 'express written permission' in receipt.get('permission_notice','').lower(): allowed=False
        return dict(receipt,allowed=allowed,reason=receipt.get('error') or ('ALLOWED_BY_ROBOTS' if allowed else 'ROBOTS_OR_EXPLICIT_PERMISSION_REQUIRED'))
    def get(self,url):
        p=self.policy(url);root='https://'+urlsplit(url).netloc
        if root in self.stopped:return None,dict(p,error='ORIGIN_STOPPED_AFTER_RESTRICTION')
        if not p['allowed']:return None,dict(p,error=p['reason'])
        if not safe_url(url):return None,dict(p,error='NON_PUBLIC_URL')
        try:
            with OPEN(Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xml,text/xml'}),timeout=15) as r:
                raw=r.read(2000001)
                if len(raw)>2000000:raise ValueError('BODY_LIMIT')
                text=raw.decode('utf-8','replace')
                if re.search(r'captcha|verify you are human|checking your browser',text[:6000],re.I):
                    self.stopped.add(root);raise ValueError('CHALLENGE_STOP')
                return text,dict(p,http_status=r.status,final_url=r.url,body_sha256=sha(text),profile_http_requested=True)
        except HTTPError as e:
            if e.code in (401,403,429):self.stopped.add(root)
            return None,dict(p,http_status=e.code,error='HTTP_'+str(e.code),profile_http_requested=True)
        except Exception as e:return None,dict(p,error=type(e).__name__+': '+str(e)[:100],profile_http_requested=True)


def load_state(conn,key,kind):
    rows=execute(conn,'SELECT summary FROM radar2.runs WHERE run_id=$1',[key])['rows']
    if not rows:return {'type':kind,'status':'control_state','version':0}
    return json.loads(rows[0]['summary']) if isinstance(rows[0]['summary'],str) else rows[0]['summary']


def save_state(conn,key,state):
    # Existing job's concurrency group serializes acquisition; CAS still protects
    # manual overlaps. No owner, DDL, new permissions, deletions or canonicals.
    old=state.get('version',0);state['version']=old+1
    rows=execute(conn,"INSERT INTO radar2.runs(run_id,finished_at,summary) VALUES($1,now(),$2::jsonb) ON CONFLICT(run_id) DO UPDATE SET summary=excluded.summary,finished_at=now() WHERE (radar2.runs.summary->>'version')::int=$3 RETURNING run_id",[key,json.dumps(state,ensure_ascii=False),old])['rows']
    if len(rows)!=1:raise RuntimeError('CAPABILITY_STATE_CONCURRENT_UPDATE')


def parse_profile(raw,username):
    """Only an explicit username + its own timeline proves profile attribution."""
    from collector import Tree
    tree=Tree(raw).root;posts={}
    def walk(x):
        if isinstance(x,dict):
            if str(x.get('username','')).lower()==username.lower():
                timeline=x.get('edge_owner_to_timeline_media',{}).get('edges',[])
                for edge in timeline:
                    n=edge.get('node',{});short=n.get('shortcode');owner=n.get('owner',{}).get('username')
                    if not short or (owner and owner.lower()!=username.lower()):continue
                    captions=n.get('edge_media_to_caption',{}).get('edges',[])
                    caption=' '.join(e.get('node',{}).get('text','') for e in captions)
                    if not caption:continue
                    posts[short]={'permalink':'https://www.instagram.com/p/'+short+'/', 'caption':caption,'timestamp':n.get('taken_at_timestamp'),'username':username}
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    for node in tree.walk():
        if node.tag!='script':continue
        content=''.join(x for x in node.parts if isinstance(x,str)).strip()
        if content.startswith('window._sharedData = '):content=content.split('=',1)[1].strip().rstrip(';')
        try:walk(json.loads(content))
        except (ValueError,TypeError):pass
    return list(posts.values())[:12]


def instagram_batch(c,batch,access):
    manifest={'searches':[],'documents':[],'instagram_attempts':[]}
    for account in batch['accounts']:
        u=account['username'];url='https://www.instagram.com/'+u+'/'
        raw,receipt=access.get(url)
        posts=parse_profile(raw,u) if raw else []
        # Official API queries are limited to the separate four-account daily pilot.
        official={'status':'OFFICIAL_HANDLED_BY_DAILY_FOUR_ACCOUNT_PILOT','posts':[]}
        if official.get('posts'):posts+=official['posts']
        received=[]
        for post in posts:
            link=post.get('permalink','');caption=post.get('caption','')
            if not re.fullmatch(r'https://(?:www\.)?instagram.com/(?:p|reel)/[\w-]+/?',link) or not caption:continue
            d={'url':link,'final_url':link,'source':'Instagram','title':'Publicación de @'+u,'text':caption,'fetched_at':utc(),'sha256':sha(caption),'text_sha256':sha(caption),'acquisition_method':'official_meta_api' if post in official.get('posts',[]) else 'permitted_public_profile','content_scope':'caption','profile_username':u,'published_at':post.get('timestamp')}
            c.docs[link]=d
            if CULTURAL.search(norm(caption)):
                key=c.add(d,d['title'],state='investigable',evidence=caption,origin_account=u)
                c.proposals[key].update(kind='document',acquisition_method=d['acquisition_method'],date_basis='post timestamp is not an event date',related_accounts=[])
            received.append(link)
        receipt.update(username=u,profile_url=url,profile_accessible=bool(raw),posts_recovered=len(received),urls=received,official_status=official['status'],official_error_type=official.get('error_type'),checked_at=utc())
        # A fetched empty profile is explicitly not a successful post acquisition.
        receipt['result']='posts_recovered' if received else ('profile_without_posts' if raw else 'access_blocked')
        manifest['instagram_attempts'].append(receipt)
    return manifest


def public_search(c,access,batch,limit=4,focus=None):
    """Optional public RSS lookup; existing robots/HTTP gate, no paid search.

    For the natural FULL only, four bounded topical queries close documented
    blind spots. These are REQUESTS, not evidence of a successful search or
    an approved event. Never fan out account queries in this mode.
    """
    manifest={'searches':[],'documents':[]}
    month=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y-%m')
    if focus=='activity_gaps':
        terms=[
          ('open-art','inauguracion exposicion galeria'),
          ('open-yoga','yoga masterclass encuentro taller'),
          ('open-ceramica','ceramica alfareria taller intensivo'),
          ('open-outdoors','running ciclismo pedaleada kayak rollers senderismo')
        ]
        queries=[{'id':key,'query':'"La Plata" '+month+' '+phrase,'accounts':[]}
                 for key,phrase in terms]
    else:
        topics=['teatro independiente cartelera','exposiciones galerías inauguración','cata vinos feria','taller especial cerámica yoga','música ciclos recitales']
        day=datetime.now(timezone.utc).day
        queries=[{'id':'open-'+str(day%len(topics)),'query':'"La Plata" '+month+' '+topics[day%len(topics)],'accounts':[]}]
        for a in batch.get('accounts',[]):
            queries.append({'id':'ig-public-index-'+a['username'],
                'query':'site:instagram.com "'+a['username']+'" "La Plata"','accounts':[a['username']]})
    for q in queries:
        url='https://www.bing.com/search?'+urlencode({'q':q['query'],'format':'rss'})
        raw,receipt=access.get(url);row={'query':q,'receipt':receipt,'searched_at':utc()}
        if not raw:row['error']=receipt.get('error');manifest['searches'].append(row);continue
        try:
            rss=ElementTree.fromstring(raw)
            for item in rss.findall('.//item')[:limit]:
                link=item.findtext('link') or ''
                if not safe_url(link):continue
                doc={'url':link,'title':item.findtext('title') or link,'excerpt':item.findtext('description') or '', 'searches':[{'query_id':q['id'],'query':q['query'],'accounts':q['accounts'],'searched_at':row['searched_at']}]}
                if 'instagram.com' in (urlsplit(link).hostname or ''):doc['acquisition_method']='public_search_index'
                manifest['documents'].append(doc)
        except (ValueError,ElementTree.ParseError) as e:row['error']=type(e).__name__
        manifest['searches'].append(row)
    if manifest['documents']:c.discovery(manifest,limit_per_query=2)
    return manifest


def normalized_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc.lower(),p.path,p.query,''))


def discover_links(c,conn,known_urls,limit=12,refresh_candidates=False):
    """Public-link frontier expands known sources; new candidates are not certified."""
    accounts=json.loads(__import__('pathlib').Path(__file__).with_name('accounts.json').read_text())
    state=load_state(conn,SOURCE_STATE,'source_discovery_control');frontier=state.setdefault('sources',{})
    at=utc();known_hosts={urlsplit(u).hostname for u in known_urls};seen=set(c.docs);candidates=[]
    def harvest(doc):
        if not doc.get('html_file'):return
        for n in c.tree(doc).walk():
            if n.tag!='a' or not n.a.get('href'):continue
            url=normalized_url(urljoin(doc['final_url'],n.a['href']));p=urlsplit(url)
            label=compact(n.text() or n.a.get('aria-label') or n.a.get('title') or ' '.join((x.a.get('alt') or '') for x in n.walk()))[:240]
            if url in seen or not cultural_link(url,label):continue
            if url not in frontier and (len(frontier)>=1500 or len(candidates)>=60):continue
            if p.scheme!='https' or p.username or p.password:continue
            foreign=p.hostname!=urlsplit(doc['url']).hostname
            score=5*int(p.hostname not in known_hosts)+2*int(foreign)+2*int(bool(LOCAL.search(norm(doc['text'][:10000]))))+int(bool(re.search(r'event|obra|program|cartel|ticket|festival',p.path,re.I)))
            item=frontier.setdefault(url,{'url':url,'first_discovered_at':at,'discovered_by_run':c.run_id,'via_url':doc['url'],'link_label':label,'status':'candidate','checks':0,'new_domain_at_discovery':p.hostname not in known_hosts})
            item['score']=max(score,item.get('score',0));seen.add(url);candidates.append(url)
    for doc in list(c.docs.values()):harvest(doc)
    # Previously discovered sources are revisited; productive does not imply
    # editorial authority. Unknown-domain candidates get a bounded fair turn.
    for item in frontier.values():
        if not cultural_link(item['url'],item.get('link_label','')):item.update(status='rejected_non_cultural_link',next_check_at='9999',monitoring_certified=False)
    due=[s for s in frontier.values() if s['url'] not in c.docs and not s['status'].startswith('rejected_') and cultural_link(s['url'],s.get('link_label','')) and (not s.get('next_check_at') or s['next_check_at']<=at or (refresh_candidates and s['status'] in ('cultural_candidate','productive_observed')))]
    due.sort(key=lambda s:(0 if (refresh_candidates and s['status'] in ('cultural_candidate','productive_observed')) or s['status']=='productive_observed' else 1,s['checks'],-s['score'],s['first_discovered_at'],s['url']))
    checked=[]
    # At most two pages per domain; not a crawl of the open web.
    per_host={}
    for item in due:
        if len(checked)>=limit:break
        host=urlsplit(item['url']).hostname
        if per_host.get(host,0)>=2:continue
        per_host[host]=per_host.get(host,0)+1
        if not safe_url(item['url']):item.update(status='rejected_non_public',next_check_at='9999');continue
        d=c.fetch(item['url'],host,item['via_url']);item['checks']+=1;item['last_check_at']=utc()
        if d:
            d['discovery']=[{'via_link':item['via_url'],'link_label':item['link_label'],'discovered_at':item['first_discovered_at'],'method':'autonomous_public_link_frontier'}]
            d['acquisition_method']='autonomous_public_link_frontier'
            before=set(c.proposals)
            cultural_local=bool(CULTURAL.search(norm(d.get('title',''))) and LOCAL.search(norm(d['text'][:24000])))
            if cultural_local:extract_document(c,d,accounts,d['acquisition_method'])
            else:c.checks.append({'url':d['url'],'status':'rejected_no_local_cultural_evidence'})
            produced=[c.proposals[k] for k in set(c.proposals)-before]
            events=[p for p in produced if p.get('date') and p.get('kind') in ('event','program')]
            cultural_local=bool(CULTURAL.search(norm(d.get('title',''))) and LOCAL.search(norm(d['text'][:24000])))
            item.update(status='productive_observed' if events else 'cultural_candidate' if cultural_local else 'rejected_no_local_cultural_evidence',http_status=d['http_status'],sha256=d['sha256'],event_proposals=len(events),proposal_ids=[p['id'] for p in produced])
            if cultural_local:
                harvest(d)
                # If the new source's front page supplies links rather than
                # events, retain those links for the next bounded pass.
                item['last_productive_at']=utc() if events else item.get('last_productive_at')
                runs=item.setdefault('productive_runs',[])
                if events and c.run_id not in runs:runs.append(c.run_id)
                days=item.setdefault('productive_days',[])
                day=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat()
                if events and day not in days:days.append(day)
                item['extraction_verified_repeatedly']=len(runs)>=2
                item['monitoring_certified']=len(days)>=2
        else:
            last=next((x for x in reversed(c.checks) if x.get('url')==item['url']),{})
            item.update(status='inaccessible',error=last.get('error','FETCH_FAILED'),monitoring_certified=False)
        item['quiet_streak']=0 if item.get('event_proposals',0)>0 else item.get('quiet_streak',0)+1
        item['next_check_at']=(datetime.now(timezone.utc)+timedelta(hours=24 if item['status']=='productive_observed' else min(336,96+24*item['quiet_streak']))).isoformat()
        checked.append(dict(item))
    # Persist the evaluated frontier even when all sources are inaccessible.
    save_state(conn,SOURCE_STATE,state)
    return {'status':'completed','candidates_discovered':len(candidates),'candidates_total':len(frontier),'checked':checked,'new_domains_observed':sorted({urlsplit(s['url']).hostname for s in checked if s['new_domain_at_discovery'] and s['status'] in ('cultural_candidate','productive_observed')}),'productive_sources':[s['url'] for s in checked if s['status']=='productive_observed']}


def enrich_graph(result,baseline):
    """Identity within explicit type; handles/mentions alone never prove a role."""
    from reconcile import venue_name
    def identity(role,name):return venue_name(name) if role=='venue' else norm(name)
    known=set()
    for p in baseline:
        e=p.get('evidence') or {};e=json.loads(e) if isinstance(e,str) else e
        known.update((n.get('role'),identity(n.get('role'),n.get('name'))) for n in e.get('entities',[]) if n.get('name'))
    nodes={};edges={}
    for p in result['proposals']:
        p.setdefault('kind','event' if p.get('date') else 'actor' if p['state']=='actor' else 'document')
        p['certainty']='source_observed_pending_editorial_review'
        p['publication_approved']=False
        p['validity']={'date_known':bool(p.get('date')),'time_known':bool(p.get('time')),'observed_at':p.get('discovered_at'),'date_end':p.get('date_end')}
        if p.get('category') and re.search(r'(?:clases? regulares?|horarios? de clases?|todos los (?:lunes|martes|miercoles|jueves|viernes))',norm(p['title'])):
            p.update(kind='document',state='investigable',date=None,time=None)
        if '/obra/' in p.get('original_url',p['document_url']) and p.get('kind')=='event':
            origin=p.get('original_url') or p['document_url']
            p['work_identity_key']=sha(origin+'|'+norm(p['title'])+'|'+norm(p.get('venue')))
            p['event_identity_key']=p['work_identity_key']
            p['identity_scope']='same_work_url_title_venue_pending_identity_review'
        p['entities']=list(p.get('entities',[]));p['relationships']=[]
        event_id='event:'+ (p.get('duplicate_of') or p['id'])
        accepted=[]
        for e in p['entities']:
            name=compact(e.get('name',''));role=e.get('role');evidence=e.get('evidence') or p.get('evidence','')
            if not name or len(name)<2 or len(name)>160 or role not in ('venue','organizer','performer','director','cycle','collective','curator'):continue
            # Only explicit parser evidence can create nodes and role edges.
            if norm(name) not in norm(evidence):continue
            proof_url=e.get('evidence_url') or p['document_url']
            nid=sha(role+'|'+identity(role,name));e.update(node_id=nid,evidence_url=proof_url,identity_status='normalized_name_within_role_pending_identity_review')
            accepted.append(e)
            n=nodes.setdefault(nid,{'node_id':nid,'name':name,'role':role,'new_to_radar_evidence':(role,identity(role,name)) not in known,'evidence':[]})
            n['evidence'].append({'proposal_id':p['id'],'url':proof_url,'excerpt':compact(evidence)[:1000]})
            if p.get('kind') not in ('event','program') or not p.get('date'):continue
            predicate={'venue':'takes_place_at','organizer':'organized_by','performer':'features','director':'directed_by','cycle':'part_of_cycle','collective':'organized_by','curator':'recommended_by'}[role]
            edge={'subject':event_id,'predicate':predicate,'object':nid,'proposal_id':p['id'],'evidence_url':proof_url,'excerpt':compact(evidence)[:1000],'status':'observed_pending_editorial_review'}
            e['event_relationship']=edge;p['relationships'].append(edge);edges[sha(event_id+predicate+nid)]=edge
        p['entities']=list({(e['node_id'],e['role']):e for e in accepted}.values())
    return {'nodes':list(nodes.values()),'relationships':list(edges.values()),'new_nodes':sum(n['new_to_radar_evidence'] for n in nodes.values())}


def carry_forward(result,baseline):
    old={p['proposal_id']:(json.loads(p['evidence']) if isinstance(p.get('evidence'),str) else p.get('evidence') or {}) for p in baseline}
    for p in result['proposals']:
        previous=old.get(p['id'],{})
        entities={((e.get('node_id') or norm(e.get('name'))),e.get('role')):dict(e) for e in previous.get('entities',[])}
        entities.update({((e.get('node_id') or norm(e.get('name'))),e.get('role')):e for e in p.get('entities',[])})
        p['entities']=list(entities.values())
        if previous.get('supporting_evidence'):
            p['supporting_evidence']=previous['supporting_evidence']
            if not p.get('organizer') and previous.get('organizer'):p['organizer']=previous['organizer']
    return result


def supplement_representatives(conn,result):
    supplements={}
    for p in result['proposals']:
        target=p.get('duplicate_of')
        if not target or not p.get('entities'):continue
        supplements.setdefault(target,[]).append(p)
    for target,aliases in supplements.items():
        rows=execute(conn,'SELECT evidence FROM radar2.proposals WHERE proposal_id=$1',[target])['rows']
        if not rows:raise RuntimeError('MISSING_ALIAS_REPRESENTATIVE')
        evidence=rows[0]['evidence'];evidence=json.loads(evidence) if isinstance(evidence,str) else evidence
        entities={((e.get('node_id') or norm(e.get('name'))),e.get('role')):e for e in evidence.get('entities',[])}
        proofs={x['proposal_id']:x for x in evidence.get('supporting_evidence',[])}
        for alias in aliases:
            for e in alias['entities']:entities[((e.get('node_id') or norm(e.get('name'))),e.get('role'))]=e
            proofs[alias['id']]={'proposal_id':alias['id'],'url':alias['document_url'],'basis':'same date, time, equivalent venue and title; roles explicitly credited by source'}
        addition={'entities':list(entities.values()),'supporting_evidence':list(proofs.values())}
        organizers={norm(e['name']):e['name'] for e in entities.values() if e.get('role')=='organizer'}
        if not evidence.get('organizer') and len(organizers)==1:addition['organizer']=next(iter(organizers.values()))
        execute(conn,'UPDATE radar2.proposals SET evidence=evidence || $2::jsonb WHERE proposal_id=$1',[target,json.dumps(addition,ensure_ascii=False)])
    return list(supplements)


def persist_graph(conn,run_id,graph):
    state=load_state(conn,GRAPH_STATE,'cultural_memory_control');nodes=state.setdefault('nodes',{});edges=state.setdefault('relationships',{})
    from reconcile import venue_name
    identities={}
    for item in execute(conn,'SELECT entity_key,name,entity_type FROM radar_definitivo.entities')['rows']:
        identities.setdefault(norm(item['name']),[]).append({'entity_key':item['entity_key'],'entity_type':item['entity_type'],'basis':'normalized_name_candidate_requires_review'})
    new=0;new_edges=0
    for n in graph['nodes']:
        n['existing_identity_candidates']=identities.get(norm(n['name']),[])
        key=n['node_id'];new+=int(key not in nodes)
        if n['role']=='venue':
            for oldkey,oldnode in nodes.items():
                if oldkey!=key and oldnode['role']=='venue' and venue_name(oldnode['name'])==venue_name(n['name']):oldnode.update(alias_of=key,identity_status='equivalent_venue_spelling')
        old=nodes.get(key,{});n['first_run_id']=old.get('first_run_id',run_id);n['last_run_id']=run_id
        proofs={x['proposal_id']:x for x in old.get('evidence',[])+n['evidence']};n['evidence']=list(proofs.values())[-20:];nodes[key]=n
    for e in graph['relationships']:
        key=sha(e['subject']+e['predicate']+e['object'])
        for oldkey,old in list(edges.items()):
            if oldkey!=key and old.get('proposal_id')==e['proposal_id'] and old.get('predicate')==e['predicate'] and nodes.get(old.get('object'),{}).get('alias_of',old.get('object'))==e['object']:
                old.update(status='superseded_by_reconciliation',superseded_by=key)
        new_edges+=int(key not in edges);edges[key]=dict(e,last_run_id=run_id)
    save_state(conn,GRAPH_STATE,state)
    return {'nodes_observed':len(graph['nodes']),'new_to_radar_evidence':graph['new_nodes'],'new_to_memory':new,'relationships_observed':len(graph['relationships']),'new_relationships_in_memory':new_edges,'total_nodes':len(nodes),'active_nodes':sum(not n.get('alias_of') for n in nodes.values()),'total_relationships':len(edges),'active_relationships':sum(e.get('status')!='superseded_by_reconciliation' for e in edges.values())}
