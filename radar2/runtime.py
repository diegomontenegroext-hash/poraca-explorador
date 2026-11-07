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
