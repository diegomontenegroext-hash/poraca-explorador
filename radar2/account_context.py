"""Evidence-bounded Instagram profile intelligence, loaded BEFORE fetching captions.

The limited Radar Neon role deliberately cannot SELECT the editorial venue table.
This is a versioned, read-only snapshot of approved entity + official handle links.
Profiles identify a possible home venue; account identity alone is not event evidence.
"""
import json
import hashlib
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

SNAPSHOT=Path(__file__).with_name('account_profiles.json')
ROLE_VENUE='venue'
_LIVE_PROFILES=None
_LIVE_STATUS='offline_snapshot'
# Explicit, non-generic local aliases; never treat a profile alone as location.
LIVE_ALIASES={'estacion-provincial':['Estación Provincial'],'teatro-argentino':['Teatro Argentino','Centro Provincial de las Artes'],'teatro-opera-laplata':['Teatro Ópera','El Ópera'],'macla':['MACLA','Museo de Arte Contemporáneo Latinoamericano'],'museo-pettoruti':['Museo Pettoruti'],'cine-select':['Cine Select'],'espacio-moliere':['Espacio Molière'],'gasav-club':['GASAV'],'hipodromo-la-plata':['Hipódromo de La Plata']}

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

def configure_live_profiles(conn, executor=None):
 """Load once per authenticated Radar run. The narrow function exposes only
 accepted local venue identities, not the knowledge tables or event approvals.
 On failure continue discovery without asserting stale venue identities."""
 global _LIVE_PROFILES,_LIVE_STATUS
 _LIVE_PROFILES=None;_LIVE_STATUS='offline_snapshot';read_profiles.cache_clear()
 static=read_profiles()
 try:
  if executor is None:
   from persist import execute as executor
  result=executor(conn,"SELECT current_user AS role,current_setting('neon.project_id',true) AS project,current_setting('neon.branch_id',true) AS branch,public.poraca_radar2_live_account_profiles_v1() AS profiles")
  row=result['rows'][0]
  if (row['role'],row['project'],row['branch'])!=('poraca_radar_limited_prod','frosty-union-52906378','br-mute-recipe-b4odj2bl'):
   raise ValueError('identity_fence')
  data=row['profiles'];data=json.loads(data) if isinstance(data,str) else data
  if data.get('schema')!='radar2-live-account-profiles-v1' or not isinstance(data.get('entries'),list):
   raise ValueError('schema')
  fresh={h:dict(p) for h,p in static.items() if p.get('role')!='venue'}
  seen=set()
  for p in data['entries']:
   h=p.get('handle','')
   if (not re.fullmatch(r'[a-z0-9_.]{2,30}',h) or h in seen or p.get('role')!='venue' or
       p.get('identity_state')!='approved_public' or not p.get('entity_id') or not p.get('venue_name') or
       not str(p.get('account_evidence_url','')).startswith('https://')):
    raise ValueError('invalid_identity')
   seen.add(h)
   old=static.get(h,{})
   # A contradictory documented non-venue role needs editorial reconciliation.
   if old.get('role') not in (None,'venue','venue_candidate'):continue
   aliases=list(old.get('aliases',[])) if old.get('entity_id')==p['entity_id'] else []
   aliases += LIVE_ALIASES.get(p['entity_id'],[])
   fresh[h]=dict(p,aliases=sorted(set(aliases+[p['venue_name']])))
  _LIVE_PROFILES=fresh;_LIVE_STATUS='live_accepted_crosswalk'
 except Exception:
  # Do not use revoked/stale approvals on an unavailable live connection.
  # Keep known role hints for collection; no new factual venue inference.
  _LIVE_PROFILES={h:(dict(p,role='venue_candidate',identity_state='live_identity_unavailable') if p.get('role')=='venue' else dict(p)) for h,p in static.items()}
  _LIVE_STATUS='live_unavailable_discovery_only'
 read_profiles.cache_clear()
 return {'status':_LIVE_STATUS,'approved_venues':sum(p.get('role')=='venue' for p in _LIVE_PROFILES.values()),'profiles':len(_LIVE_PROFILES)}

def identity_refresh_report():
 return {'status':_LIVE_STATUS,'approved_venues':sum(p.get('role')=='venue' for p in read_profiles().values()),'profiles':len(read_profiles())}

def reset_live_profiles():
 global _LIVE_PROFILES,_LIVE_STATUS
 _LIVE_PROFILES=None;_LIVE_STATUS='offline_snapshot';read_profiles.cache_clear()

def profile_fingerprint(handle):
 if _LIVE_STATUS!='live_accepted_crosswalk':return None
 p=profile_for(handle) or {}
 fields={k:p.get(k) for k in ('role','entity_id','venue_name','identity_state','location_scope','account_evidence_url','aliases')}
 return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def identity_changed(d,previous,proposals):
 """An unchanged caption must be reinterpreted after its identity changes,
 without asking Meta again or overwriting on a transient identity-read failure."""
 if _LIVE_STATUS!='live_accepted_crosswalk':return False
 handle=d.get('profile_username');fingerprint=profile_fingerprint(handle)
 if previous and previous.get('account_identity_fingerprint') is not None:
  return previous['account_identity_fingerprint']!=fingerprint
 current=preflight(handle)
 contexts=[p.get('account_context') for p in proposals if isinstance(p.get('account_context'),dict)]
 if not contexts:return current.get('account_verified') is True
 return any(any(c.get(k)!=current.get(k) for k in ('role','venue_entity_id','account_verified')) for c in contexts)

@lru_cache(maxsize=1)
def read_profiles():
 if _LIVE_PROFILES is not None:return _LIVE_PROFILES
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
         'snapshot':'radar2-account-preflight-v1','identity_status':_LIVE_STATUS}

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
 handle=str(username or '').strip().lower()
 match=re.search(r'\b(?:en|desde)\s+@?'+re.escape(handle)+r'(?![\w.])',block,re.I) if handle else None
 if match:
  return dict(base,venue=venue,basis='explicit_name_in_owned_caption',quote=match[0])
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
 if address and re.search(r'\b(?:sala|nos vemos|encontramos|cineclub|funci[oó]n|proyecci[oó]n|abrimos nuestra casa)\b',fold(block),re.I):
  return dict(base,venue=venue,basis='owned_venue_with_explicit_address',
              quote=address['loc'],candidate=None)
 # Host owns the profile, but could be announcing someone else's activity.
 return dict(base,candidate=venue,basis='verified_home_venue_only_not_event_proof')
