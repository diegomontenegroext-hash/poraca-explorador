"""Evidence-bounded Instagram profile intelligence, loaded BEFORE fetching captions.

The limited Radar Neon role deliberately cannot SELECT the editorial venue table.
This is a versioned, read-only snapshot of approved entity + official handle links.
Profiles identify a possible home venue; account identity alone is not event evidence.
"""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

SNAPSHOT=Path(__file__).with_name('account_profiles.json')
ROLE_VENUE='venue'
OFFSITE=re.compile(
 r'\b(?:en\s+(?:otro|otra)\s+(?:lugar|espacio|sala|ciudad)|'
 r'fuera\s+de\s+(?:la\s+)?(?:sala|ciudad)|'
 r'(?:gira|tour)\s+por|en\s+(?:bs\s?as|caba|capital\s+federal)|'
 r'\b(?:streaming|por\s+canal|por\s+youtube|transmisi[oó]n\s+online)\b)',
 re.I
)
ADDRESS=re.compile(r'(?P<loc>(?:📍|📌)\s*(?:calle|av(?:enida)?\.?|diag(?:onal)?\.?)\s*\d{1,3}[^\n]{1,88})',re.I)

def fold(s):
 return ''.join(c for c in unicodedata.normalize('NFKD',str(s or '')).casefold() if not unicodedata.combining(c))

@lru_cache(maxsize=1)
def read_profiles():
 data=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
 if data.get('schema')!='radar2-account-preflight-v1':raise ValueError('INVALID_ACCOUNT_PROFILE_SCHEMA')
 profiles={}
 for p in data['entries']:
  handle=p.get('handle','').lower()
  if not re.fullmatch(r'[a-z0-9_.]{2,30}',handle) or handle in profiles:raise ValueError('ACCOUNT_PROFILE_DUPLICATE_OR_INVALID')
  profiles[handle]=p
 return profiles

def profile_for(handle):
 return read_profiles().get(str(handle or '').strip().lower())

def preflight(handle):
 """Small provenance receipt, safe even for an unknown rotating account."""
 handle=str(handle or '').strip().lower()
 p=profile_for(handle)
 if not p:return {'handle':handle,'role':'unclassified','venue_entity_id':None,
                  'context_status':'needs_profile_research','account_verified':False}
 verified=p.get('role')=='venue' and p.get('identity_state')=='approved_public'
 return {'handle':handle,'role':p.get('role'),'name':p.get('name'),
         'venue_entity_id':p.get('entity_id'),
         'venue_name':p.get('venue_name'),
         'context_status':'approved_venue_profile' if verified else 'nonvenue_or_pending_identity',
         'account_verified':bool(verified),
         'evidence_url':p.get('account_evidence_url'),
         'evidence_basis':p.get('account_evidence_basis'),
         'snapshot':'radar2-account-preflight-v1'}

def location_for(d,block):
 """Return verified explicit venue or *candidate*, with exact evidence.

    An organizer, a curator, an unconfirmed venue identity or mere account ownership
    cannot supply a factual event location. Offsite / streaming announcements abstain.
 """
 username=d.get('profile_username')
 p=profile_for(username)
 if not p:return {'basis':'unknown_account','candidate':None,'venue':None}
 base={'venue':None,'candidate':None,'basis':'account_is_not_event_location',
       'profile_role':p.get('role'),'venue_entity_id':p.get('entity_id'),
       'profile_evidence_url':p.get('account_evidence_url')}
 if p.get('role')!='venue' or p.get('identity_state')!='approved_public':
  if p.get('role')=='venue_candidate':base.update(candidate=p.get('venue_name'),basis='venue_identity_not_publicly_approved')
  return base
 if OFFSITE.search(block):return dict(base,basis='offsite_or_remote_requires_review')
 venue=p.get('venue_name')
 if not venue:return base
 aliases=sorted(set([venue]+p.get('aliases',[])),key=len,reverse=True)
 for alias in aliases:
  if len(alias)<6:continue
  m=re.search(r'(?<![\w])'+re.escape(alias)+r'(?![\w])',block,re.I)
  if m:
   # Hashtags / textual credits alone need other location evidence. A caption
   # from the owning venue with an exact venue name is still source evidence,
   # but the source/role is preserved for editorial decision.
   if m.start()>0 and block[m.start()-1]=='#':continue
   return dict(base,venue=venue,basis='explicit_name_in_owned_caption',
               quote=m[0],candidate=None)
 # Physical address + "in the room" is stronger than a profile-only guess.
 address=ADDRESS.search(block)
 if address and re.search(r'\b(?:sala|nos vemos|encontramos|cineclub|funci[oó]n|proyecci[oó]n)\b',fold(block),re.I):
  return dict(base,venue=venue,basis='owned_venue_with_explicit_address',
              quote=address['loc'],candidate=None)
 # Host owns the profile, but could be announcing someone else's activity.
 return dict(base,candidate=venue,basis='verified_home_venue_only_not_event_proof')
