"""Schedule resolution and safe credential diagnostics for the existing job."""
import json,os
from datetime import datetime,timezone
from urllib.request import Request,urlopen

def resolve_mode(event,schedule='',manual=''):
 if event=='schedule':
  if schedule=='27 8 * * *':return 'full'
  if schedule in ('27 16 * * *','27 23 * * *'):return 'incremental'
  raise ValueError('UNKNOWN_SCHEDULE')
 if manual in ('full','incremental'):return manual
 return 'full'

def credential_health():
 token=os.environ.get('META_ACCESS_TOKEN');version=os.environ.get('META_GRAPH_VERSION')
 if not token or not version:return {'status':'NOT_CONFIGURED','renewal':'NOT_AUTOMATED'}
 # No token/URL/raw error payload is printed or persisted.
 try:
  req=Request('https://graph.facebook.com/'+version+'/me/permissions',headers={'Authorization':'Bearer '+token})
  with urlopen(req,timeout=20) as r:data=json.load(r)
  granted={x['permission'] for x in data.get('data',[]) if x.get('status')=='granted'}
  required={'instagram_basic','instagram_manage_insights','pages_read_engagement'}
  return {'status':'PERMISSIONS_VALID' if required<=granted else 'PERMISSIONS_MISSING','missing':sorted(required-granted),
   'checked_at':datetime.now(timezone.utc).isoformat(),'expires_at':os.environ.get('META_TOKEN_EXPIRES_AT') or None,
   'data_access_expires_at':None,'expiry_introspected':False,'renewal':'NOT_AUTOMATED_REAUTHORIZATION_OR_COMPATIBLE_PAGE_TOKEN_REQUIRED'}
 except Exception as e:return {'status':'HEALTH_CHECK_FAILED','error_type':type(e).__name__,'renewal':'NOT_AUTOMATED'}

# This Facebook Login flow has no generic unattended Instagram refresh grant.
# Inspect with the app developer token when no app credential is configured.
def inspect_token(token,version):
 from urllib.parse import urlencode
 app_id=os.environ.get('META_APP_ID');secret=os.environ.get('META_APP_SECRET')
 auth=app_id+'|'+secret if app_id and secret else token
 req=Request('https://graph.facebook.com/'+version+'/debug_token?'+urlencode({'input_token':token}),headers={'Authorization':'Bearer '+auth})
 try:
  with urlopen(req,timeout=20) as r:data=json.load(r).get('data',{})
  if 'is_valid' not in data:return {'expiry_introspected':False,'inspection_status':'NOT_AVAILABLE'}
  if app_id and str(data.get('app_id'))!=app_id:return {'expiry_introspected':False,'inspection_status':'APP_ID_MISMATCH','credential_usable':False}
  out={'expiry_introspected':True,'inspection_status':'INSPECTED','token_type':data.get('type'),'is_valid':data['is_valid'],'credential_usable':bool(data['is_valid'])}
  warnings=[];now=datetime.now(timezone.utc).timestamp()
  for source,target in [('expires_at','expires_at'),('data_access_expires_at','data_access_expires_at')]:
   value=data.get(source)
   out[target]=datetime.fromtimestamp(value,timezone.utc).isoformat() if isinstance(value,(int,float)) and value>0 else None
   out[source+'_reported_zero']=value==0
   if value and value<=now:out['credential_usable']=False;warnings.append(source.upper()+'_EXPIRED')
   elif value and value-now<=14*86400:warnings.append(source.upper()+'_WITHIN_14_DAYS')
  out['warnings']=warnings;return out
 except Exception as exc:
  # Never include exception text: its URL can contain input_token.
  return {'expiry_introspected':False,'inspection_status':'FAILED','inspection_error_type':type(exc).__name__,'warnings':['TOKEN_EXPIRY_UNKNOWN_REVIEW_REQUIRED']}

_original_credential_health=credential_health
from functools import lru_cache
@lru_cache(maxsize=1)
def credential_health():
 health=_original_credential_health()
 token=os.environ.get('META_ACCESS_TOKEN');version=os.environ.get('META_GRAPH_VERSION')
 if token and version:health.update(inspect_token(token,version))
 return health

def announce_credential_health():
 health=credential_health()
 for warning in health.get('warnings',[]):print('::warning title=Meta credential::'+warning)
 if health.get('credential_usable') is False:print('::warning title=Meta credential::Acquisition halted; operator renewal required')
 return health
