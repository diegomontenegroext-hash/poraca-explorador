"""Bounded media leads from HTML ALREADY fetched by Radar 2.

Discovery-only. No image download, no attribution of a photo to a place,
no acceptance of usage rights and no publication. A follow-up stage must
match the entity ID and inspect the subject before it may become a card photo.
"""
from hashlib import sha256
from html import unescape
from ipaddress import ip_address
from urllib.parse import urljoin, urlsplit
import re

SOURCE_VERSION = 'radar2-media-leads-v1'
TAGS = {'og:image': 3, 'og:image:secure_url': 3,
        'twitter:image': 2, 'twitter:image:src': 2}
IMAGE_TYPES = {'ImageObject', 'Photograph'}


def safe_image_url(value, page):
    if not isinstance(value, str) or len(value) > 1800:
        return None
    s = unescape(value).strip()
    if not s or re.match(r'^(?:data|javascript|blob|file):', s, re.I):
        return None
    try:
        url = urljoin(page, s)
        p = urlsplit(url)
        host = p.hostname
        if p.scheme != 'https' or not host or p.username or p.password or p.port not in (None, 443):
            return None
        if host in {'localhost', 'localhost.localdomain'} or host.endswith(('.local', '.internal', '.test')):
            return None
        try:
            ip_address(host)
            return None
        except ValueError:
            pass
        if any(c in url for c in ('<', '>', '"', "'", '\n', '\r', '\t')):
            return None
        return url
    except (ValueError, TypeError):
        return None


def image_role(url, hint=''):
    words = (url + ' ' + hint).lower()
    if re.search(r'(?:^|[/_.-])(?:logo|icon|favicon|brand|avatar)(?:[/_.-]|$)', words):
        return 'brand_graphic_candidate'
    if re.search(r'(?:poster|flyer|afiche|banner|cartel)', words):
        return 'event_poster_possible'
    return 'documentary_image_candidate'


def leads(tree, document):
    """Maximum three ranked URL references. No remote media requests."""
    page = document.get('final_url') or document.get('url', '')
    scored = {}
    def add(raw, method, weight, label=''):
        url = safe_image_url(raw, page)
        if not url:
            return
        role = image_role(url, label)
        weight += 3 if role == 'documentary_image_candidate' else -2 if role == 'brand_graphic_candidate' else 0
        current = scored.get(url)
        if current is not None and current['weight'] >= weight:
            return
        scored[url] = {'url': url, 'method': method, 'weight': weight, 'roleHint': role}

    for node in tree.walk():
        if node.tag == 'meta':
            key = (node.a.get('property') or node.a.get('name') or '').lower().strip()
            if key in TAGS:
                add(node.a.get('content'), key, TAGS[key] * 10)
        elif node.tag == 'link' and 'image_src' in node.a.get('rel', '').lower().split():
            add(node.a.get('href'), 'rel_image_src', 20)
    for item in document.get('structured_items', []):
        if not isinstance(item, dict):
            continue
        raw = item.get('image')
        if isinstance(raw, dict):
            raw = raw.get('contentUrl') or raw.get('url')
        if isinstance(raw, list):
            raw = next((v for v in raw if isinstance(v, str)), None)
        if raw:
            add(raw, 'schema_org_image', 16)
    ordered = sorted(scored.values(), key=lambda x: (-x['weight'], x['url']))[:3]
    proof = document.get('sha256', '')
    return [{
        'imageUrl': c['url'],
        'sourcePageUrl': document.get('url', ''),
        'documentSha256': proof,
        'retrievedAt': document.get('fetched_at'),
        'discoveryMethod': c['method'],
        'roleHint': c['roleHint'],
        'entityId': None,
        'subjectVerified': False,
        'rightsStatus': 'not_assessed',
        'cardSafe': False,
        'publicReleaseEligible': False,
        'assetFetched': False,
        'reviewState': 'candidate_only',
        'schema': SOURCE_VERSION
    } for c in ordered]
