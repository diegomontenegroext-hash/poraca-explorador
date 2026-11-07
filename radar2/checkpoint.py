"""Bounded original journal in the existing job; Neon first, artifact on outage.
No credentials in journal. Artifact recovery is limited to this repository and
exact artifact name, never executes artifact content or extracts arbitrary paths.
"""
import json,os,zipfile,io
from pathlib import Path
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from urllib.parse import urlsplit
from collector import sha
from persist import execute

UPSERT="""INSERT INTO radar2.documents(url,source,sha256,fetched_at,last_run_id,payload)
VALUES($1,$2,$3,$4::timestamptz,$5,$6::jsonb)
ON CONFLICT(url) DO UPDATE SET sha256=excluded.sha256,fetched_at=excluded.fetched_at,last_run_id=excluded.last_run_id,payload=excluded.payload"""

class Journal:
 def __init__(self,root,conn,run_id):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.conn=conn;self.run_id=run_id
 def save(self,d):
  # Disk before network. A failed SQL cannot discard the newly acquired original.
  dest=self.root/(sha(d['url']+d['sha256'])+'.json');tmp=dest.with_suffix('.tmp')
  tmp.write_text(json.dumps(d,ensure_ascii=False));tmp.replace(dest)
  execute(self.conn,UPSERT,[d['url'],d['source'],d['sha256'],d['fetched_at'],self.run_id,json.dumps(d,ensure_ascii=False)])
 def recover(self,collector):
  recovered=0
  for path in sorted(self.root.glob('*.json'))[:1000]:
   if path.stat().st_size>4_000_000:raise ValueError('JOURNAL_BODY_LIMIT')
   d=json.loads(path.read_text())
   known=execute(self.conn,'SELECT sha256,fetched_at::text FROM radar2.documents WHERE url=$1',[d['url']])['rows']
   if known and (known[0]['sha256']==d['sha256'] or known[0]['fetched_at']>d['fetched_at']):continue
   self.save(d);collector.docs[d['url']]=d;recovered+=1
  return recovered

def restore_artifact(root):
 """One bounded previous artifact. Existing Neon hash prevents stale overwrites."""
 token=os.environ.get('GITHUB_TOKEN');repo=os.environ.get('GITHUB_REPOSITORY')
 if not token or not repo:return {'status':'not_in_github'}
 class ArtifactRedirect(HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,newurl):
   redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
   if redirected and urlsplit(newurl).hostname!='api.github.com':redirected.remove_header('Authorization')
   return redirected
 opener=build_opener(ArtifactRedirect()).open
 def get(url,max_bytes):
  req=Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
  with opener(req,timeout=30) as r:
   data=r.read(max_bytes+1)
   if len(data)>max_bytes:raise ValueError('ARTIFACT_LIMIT')
   return data
 # Artifact URL comes from GitHub's response for this repository, not user data.
 data=json.loads(get('https://api.github.com/repos/'+repo+'/actions/artifacts?name=radar2-acquisition-checkpoints&per_page=1',100000))
 artifacts=[a for a in data.get('artifacts',[]) if not a.get('expired')]
 if not artifacts:return {'status':'no_prior_artifact'}
 a=artifacts[0]
 if a['size_in_bytes']>40_000_000:raise ValueError('ARTIFACT_LIMIT')
 raw=get('https://api.github.com/repos/'+repo+'/actions/artifacts/'+str(a['id'])+'/zip',40_000_000)
 root=Path(root);root.mkdir(parents=True,exist_ok=True);count=0;total=0
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  for entry in z.infolist():
   if not entry.filename.endswith('.json'):continue
   total+=entry.file_size
   if count>=1000 or entry.file_size>4_000_000 or total>80_000_000:raise ValueError('ARTIFACT_EXPANSION_LIMIT')
   d=json.loads(z.read(entry));url=d.get('url','')
   if not url.startswith('https://') or not all(k in d for k in ('sha256','text','fetched_at','source')):raise ValueError('INVALID_JOURNAL')
   dest=root/(sha(url+d['sha256'])+'.json')
   if not dest.exists():dest.write_text(json.dumps(d,ensure_ascii=False))
   count+=1
 return {'status':'restored','artifact_id':a['id'],'documents':count}
