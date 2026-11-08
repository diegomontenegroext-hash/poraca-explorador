"""Official Facebook Login Business Discovery, disabled without credentials.

No public profile scraper, no oEmbed analytics, no third-party access tokens.
The owner supplies META_IG_USER_ID, META_ACCESS_TOKEN and META_GRAPH_VERSION.
Professional target eligibility is determined by Meta, never inferred from bio.
"""
import json,os
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from collector import utc

def discover(username):
    own=os.environ.get('META_IG_USER_ID');token=os.environ.get('META_ACCESS_TOKEN');version=os.environ.get('META_GRAPH_VERSION')
    if not (own and token and version):
        return {'username':username,'checked_at':utc(),'status':'NOT_EXECUTED_MISSING_OFFICIAL_ACCESS','posts':[],
          'requirement':'Own eligible professional Instagram account, Meta app, token with instagram_basic, instagram_manage_insights, pages_read_engagement, applicable Page access and access level. Facebook Login implementation; version supplied explicitly from app configuration.'}
    if not __import__('re').fullmatch(r'[A-Za-z0-9_.]{1,30}',username):raise ValueError('USERNAME')
    fields='business_discovery.username('+username+'){username,media.limit(12){id,caption,permalink,timestamp,media_type}}'
    url=f'https://graph.facebook.com/{version}/{own}?'+urlencode({'fields':fields})
    try:
        with urlopen(Request(url,headers={'Authorization':'Bearer '+token}),timeout=20) as response:
            http_status = response.status
            data = json.load(response)
        discovery = data.get('business_discovery') if isinstance(data, dict) else None
        media = discovery.get('media') if isinstance(discovery, dict) else None
        posts = media.get('data') if isinstance(media, dict) else None
        receipt = {'username': username, 'checked_at': utc(), 'http_status': http_status}
        if not isinstance(posts, list) or any(not isinstance(post, dict) for post in posts):
            return dict(receipt, status='OFFICIAL_API_ERROR', error_type='InvalidMediaResponse', posts=[])
        paging = media.get('paging') or {}
        return dict(receipt, status='MEDIA_RETURNED' if posts else 'NO_MEDIA_RETURNED',
                    posts=posts, has_more=bool(paging.get('next') or (paging.get('cursors') or {}).get('after')),
                    limit=12, stories='THIRD_PARTY_STORIES_NOT_SUPPORTED')
    except HTTPError as e:
        # Only structured status/codes reach logs and Neon; never persist raw Meta error text.
        try:
            payload=json.loads(e.read(8192).decode('utf-8'))
            error=payload.get('error',{}) if isinstance(payload,dict) else {}
        except (ValueError,UnicodeError,OSError):
            error={}
        if not isinstance(error,dict):error={}
        return {'username':username,'checked_at':utc(),'status':'OFFICIAL_API_ERROR',
                'error_type':'HTTPError','http_status':e.code,
                'meta_error_code':error.get('code') if isinstance(error.get('code'),int) else None,
                'meta_error_subcode':error.get('error_subcode') if isinstance(error.get('error_subcode'),int) else None,
                'meta_error_type':error.get('type') if error.get('type') in ('OAuthException','GraphMethodException') else None,
                'posts':[]}
    except Exception as e:
        return {'username':username,'checked_at':utc(),'status':'OFFICIAL_API_ERROR','error_type':type(e).__name__,'posts':[]}

if __name__=='__main__':
    import sys
    from pathlib import Path
    accounts=json.loads(Path(sys.argv[1]).read_text());out=[discover(a['username']) if a.get('username') and a.get('identity')!='ambiguous' else {'username':a.get('username'),'status':'IDENTITY_UNRESOLVED','posts':[]} for a in accounts]
    Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps({'accounts':len(out),'posts':sum(len(x['posts']) for x in out),'statuses':{s:sum(x['status']==s for x in out) for s in {x['status'] for x in out}}}))
