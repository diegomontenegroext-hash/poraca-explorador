"""Instagram index rotation in Radar 2's existing Neon ledger and limited role.

One reserved control row; CAS prevents overlapping workers claiming the same
accounts. A lease is an attempt, never a successful review. No schema/grants.
"""
import argparse,json,os,re
from pathlib import Path
from datetime import datetime,timedelta,timezone
from persist import execute

STATE_ID='radar2-instagram-rotation-state-v1'
PRIORITY={'lutitravelguide','residenciacorazon','sunsetwine.mixology','dionisio_vinoteca',
          'guajira.bar','escenario40','centrodearteunlp','ciudaddegatos','circus_ofc','intra.prod'}

def now():return datetime.now(timezone.utc)
def timestamp(t):return t.isoformat()
def initial(roster):
    accounts={a['handle'].lower():dict(a,username=a['handle'].lower(),priority=1 if a['handle'].lower() in PRIORITY else 2,
        review_count=0,last_review_at=None,last_attempt_at=None,next_review_at=None,result='never_reviewed') for a in roster}
    if len(accounts)!=123 or any(not re.fullmatch(r'[a-z0-9_.]{1,30}',u) for u in accounts):raise ValueError('ROSTER_123_FENCE')
    return {'type':'instagram_rotation_control','status':'control_state','version':0,'accounts':accounts,'batches':{}}

def select(state,at,limit=10):
    eligible=[a for a in state['accounts'].values() if (not a.get('next_review_at') or a['next_review_at']<=timestamp(at))
        and (not a.get('lease_until') or a['lease_until']<=timestamp(at))]
    # Fairness first: all accounts in a sweep, cultural priority within a sweep.
    return sorted(eligible,key=lambda a:(a['review_count'],a['priority'],a.get('last_review_at') or '',a['username']))[:max(0,min(limit,10))]

def read(conn):
    rows=execute(conn,'SELECT summary FROM radar2.runs WHERE run_id=$1',[STATE_ID])['rows']
    if not rows:raise RuntimeError('ROTATION_NOT_INITIALIZED')
    value=rows[0]['summary'];return json.loads(value) if isinstance(value,str) else value

def cas(conn,state,version):
    state['version']=version+1
    return bool(execute(conn,"UPDATE radar2.runs SET summary=$1::jsonb,finished_at=now() WHERE run_id=$2 AND (summary->>'version')::int=$3 RETURNING run_id",
                        [json.dumps(state,ensure_ascii=False),STATE_ID,version])['rows'])

def initialize(conn,roster):
    return execute(conn,'INSERT INTO radar2.runs(run_id,finished_at,summary) VALUES($1,now(),$2::jsonb) ON CONFLICT DO NOTHING RETURNING run_id',
        [STATE_ID,json.dumps(initial(roster),ensure_ascii=False)])

def claim(conn,run_id,limit=10):
    for _ in range(4):
        state=read(conn);version=state['version'];at=now()
        if run_id in state['batches']:
            batch=state['batches'][run_id]
            owned=[state['accounts'][u] for u in batch['usernames'] if state['accounts'][u].get('lease_run_id')==run_id
                   and (state['accounts'][u].get('lease_until') or '')>timestamp(at)]
            return dict(run_id=run_id,accounts=owned if batch['status']!='completed' else [],batch=batch,replayed=True)
        selected=select(state,at,limit)
        for a in selected:a.update(lease_run_id=run_id,lease_until=timestamp(at+timedelta(hours=2)),last_attempt_at=timestamp(at))
        batch={'usernames':[a['username'] for a in selected],'claimed_at':timestamp(at),'status':'claimed'}
        state['batches'][run_id]=batch
        # Keep resumable audit for recent runs; finished attempts are also in their run summaries.
        if len(state['batches'])>60:
            old=sorted(state['batches'],key=lambda k:state['batches'][k]['claimed_at'])
            for k in old[:-60]:
                if state['batches'][k]['status']=='completed':state['batches'].pop(k)
        if cas(conn,state,version):return dict(run_id=run_id,accounts=selected,batch=batch,replayed=False)
    raise RuntimeError('ROTATION_CONCURRENT_UPDATE_RETRY_LATER')

def complete(conn,run_id,manifest):
    persisted=execute(conn,"SELECT run_id FROM radar2.runs WHERE run_id=$1 AND summary->>'status'='completed'",[run_id])['rows']
    if not persisted:raise RuntimeError('PERSISTENCE_MUST_COMPLETE_BEFORE_ROTATION_FINALIZATION')
    for _ in range(4):
        state=read(conn);version=state['version'];at=now();batch=state['batches'].get(run_id)
        if not batch:raise ValueError('UNKNOWN_ROTATION_BATCH')
        if batch['status']=='completed':return batch
        results=[]
        for u in batch['usernames']:
            a=state['accounts'][u]
            if a.get('lease_run_id')!=run_id:continue # expired/reclaimed lease cannot be finalized by an old worker
            searches=[s for s in manifest['searches'] if u in s['query'].get('accounts',[])]
            docs=[d for d in manifest['documents'] if any(u in s.get('accounts',[]) for s in d['searches'])]
            success=any(not s.get('error') for s in searches)
            ig_docs=[d for d in docs if d.get('acquisition_method')=='public_search_index']
            index_searches=[s for s in searches if s['query']['id'].startswith('ig-public-index-')]
            index_status=('search_failed' if not index_searches or all(s.get('error') for s in index_searches)
                          else 'instagram_results' if ig_docs else 'no_instagram_results')
            status=('instagram_indexed' if ig_docs else 'web_references_only' if docs else 'no_indexed_results') if success else 'search_failed'
            delay=24 if docs and a['priority']==1 else 72 if docs else 96 if success else 8
            a.update(last_review_at=timestamp(at) if success else a.get('last_review_at'),
                next_review_at=timestamp(at+timedelta(hours=delay)),result=status,
                review_count=a['review_count']+int(success),lease_until=None,lease_run_id=None,
                last_result={'run_id':run_id,'checked_at':timestamp(at),'queries':len(searches),'indexed_documents':len(docs),
                    'instagram_results':len(ig_docs),'instagram_index_status':index_status,
                    'failed_queries':sum(bool(s.get('error')) for s in searches),
                    'urls':[d['url'] for d in docs],'direct_profiles_read':0})
            results.append(dict(username=u,**a['last_result'],result=status,next_review_at=a['next_review_at']))
        batch.update(status='completed',finished_at=timestamp(at),results=results)
        if cas(conn,state,version):return batch
    raise RuntimeError('ROTATION_CONCURRENT_UPDATE_RETRY_LATER')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['init','claim','complete','preview']);p.add_argument('--run-id');p.add_argument('--manifest');p.add_argument('--out',required=True);p.add_argument('--limit',type=int,default=10);a=p.parse_args()
    conn=json.loads(Path(os.environ['RADAR2_CONNECTION_FILE']).read_text())['url']
    ident=execute(conn,"SELECT current_user AS role,current_setting('neon.project_id',true) AS project,current_setting('neon.branch_id',true) AS branch")['rows'][0]
    if ident!={'role':'poraca_radar_limited_prod','project':'frosty-union-52906378','branch':'br-mute-recipe-b4odj2bl'}:raise ValueError('LIMITED_WRITER_IDENTITY_FENCE')
    if a.action=='init':result=initialize(conn,json.loads(Path(__file__).with_name('instagram_roster.json').read_text()))
    elif a.action=='claim':result=claim(conn,a.run_id,a.limit)
    elif a.action=='complete':result=complete(conn,a.run_id,json.loads(Path(a.manifest).read_text()))
    else:result={'accounts':select(read(conn),now(),a.limit)}
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'action':a.action,'accounts':len(result.get('accounts',result.get('results',[]))),'out':a.out}))

if __name__=='__main__':main()
