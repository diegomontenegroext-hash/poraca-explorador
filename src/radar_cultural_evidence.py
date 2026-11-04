"""Literal cultural leads from opened articles; no publication or inferred sessions."""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import json
import re

PRESS_HOSTS = {'0221.com.ar', 'eldia.com'}
CULTURE = re.compile(r'agenda|festival|teatro|recital|concierto|muestra|exposici[oó]n|'
                     r'fiesta|librer[ií]a|cer[aá]mica|vino|yoga|arquitectura|'
                     r'cultural|cantautora|m[uú]sica|galer[ií]a|patrimonio', re.I)


def article_metadata(raw):
    for script in re.findall(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', raw[:450000], re.I|re.S):
        try: pending = [json.loads(script)]
        except ValueError: continue
        for _ in range(100):
            if not pending: break
            node = pending.pop(0)
            if isinstance(node, list): pending.extend(node[:100]); continue
            if not isinstance(node, dict): continue
            typ = node.get('@type', [])
            if isinstance(typ, str): typ = [typ]
            if any(t in ('NewsArticle', 'Article') for t in typ): return node
            for key in ('@graph', 'mainEntity'):
                if isinstance(node.get(key), (dict, list)): pending.append(node[key])
    return {}


class ArticleBlocks(HTMLParser):
    """Only visible content inside article-body sections, not related cards/footer."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tag = None
        self.text = []
        self.blocks = []
        self.links = []
        self.href = None
        self.anchor = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'article' and 'article-body' in a.get('class', ''): self.depth += 1
        if not self.depth: return
        if tag in ('h2','h3','li','p') and self.tag is None:
            self.tag = tag; self.text = []
        if tag == 'br' and self.tag: self.text.append('\n')
        if tag == 'a': self.href = a.get('href'); self.anchor = []
    def handle_data(self, text):
        if self.depth and self.tag: self.text.append(text)
        if self.depth and self.href: self.anchor.append(text)
    def handle_endtag(self, tag):
        if tag == self.tag:
            self.blocks.append((tag, ''.join(self.text).strip()))
            self.tag = None; self.text = []
        if tag == 'a' and self.href:
            self.links.append((self.href, ' '.join(self.anchor).strip())); self.href = None
        if tag == 'article': self.depth = max(0,self.depth-1)


def press_evidence(raw, url, page):
    host = (urlsplit(url).hostname or '').removeprefix('www.')
    if host not in PRESS_HOSTS: return None
    meta = article_metadata(raw)
    title = meta.get('headline') or meta.get('name') or page.meta.get('og:title') or page.title
    if not meta or not CULTURE.search((title or '')+' '+(page.meta.get('og:description') or '')): return None
    parsed = ArticleBlocks(); parsed.feed(raw)
    fragments = [re.sub(r'\s+', ' ',v)[:600] for t,v in parsed.blocks
                 if t in ('p','li') and CULTURE.search(v)][:8]
    # El Día can expose a public excerpt without a semantic article-body.
    # Its public description is a lead only; never fetch hidden/paywalled text.
    if not fragments:
        description = page.meta.get('og:description') or page.meta.get('description') or ''
        if CULTURE.search(description): fragments = [description[:500]]
    if not fragments: return None
    refs = []
    for href,label in parsed.links:
        target = urljoin(url, href)
        p = urlsplit(target)
        if (p.scheme != 'https' or not p.hostname or p.username or p.password
                or p.port not in (None,443) or p.hostname.removeprefix('www.') == host): continue
        if p.hostname in ('www.instagram.com','instagram.com'):
            kind = 'exact_post' if re.fullmatch(r'/(?:[\w.]+/)?(?:p|reel)/[\w-]+/?',p.path) else 'account_reference'
        elif any(x in p.hostname for x in ('facebook.','twitter.','whatsapp.','t.me','google.')): continue
        else: kind = 'linked_original_needs_review'
        if target not in [r['url'] for r in refs]: refs.append({'url':target,'label':label[:180],'kind':kind})
    return {'state':'review_only','source_role':'secondary_press',
            'publication':meta.get('datePublished'), 'fragments':fragments,
            'original_references':refs[:12], 'auto_accept':False}


def cultural_yield(check, candidates):
    """Acquisition outcomes, separate from HTTP and editorial/publication success."""
    captions = sum(c.get('evidence',{}).get('caption_readable') is True for c in candidates)
    leads = sum(bool(c.get('evidence',{}).get('cultural_article_v1') or
                     c.get('evidence',{}).get('identity_review')) for c in candidates)
    sessions = len(check.get('_listings',[]))
    state = ('useful_content_for_review' if captions or leads or sessions else
             'unreadable' if check.get('status')=='failed' else 'read_without_cultural_extraction')
    return {'state':state,'sessions_observed':sessions,'captions_read':captions,
            'cultural_documents':leads,'profile_scanned':False if check.get('_seed_only') else None,
            'editorially_resolved':False,'published':False}
