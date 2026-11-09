"""Instagram index rotation in Radar 2's existing Neon ledger and limited role.

One reserved control row; CAS prevents overlapping workers claiming the same
accounts. A lease is an attempt, never a successful review. No schema/grants.
"""
import argparse,json,os,re
from pathlib import Path
from datetime import datetime,timedelta,timezone
from persist import execute

STATE_ID='radar2-instagram-rotation-state-v1'
MAX_ROTATING_ACCOUNTS=20

def adaptive_query_budget(due_count):
    """Bounded backlog recovery: normal=10, moderate=15, high=20 per natural run.

    No additional runs or parallel API calls; official collector still stops at
    the first Meta rate/auth error. Only accounts whose review is due count.
    """
    return 10 if due_count<=20 else 15 if due_count<=40 else MAX_ROTATING_ACCOUNTS
PRIORITY={'lutitravelguide','residenciacorazon','sunsetwine.mixology','dionisio_vinoteca',
          'guajira.bar','escenario40','centrodearteunlp','ciudaddegatos','circus_ofc','intra.prod'}

def now():return datetime.now(timezone.utc)
def timestamp(t):return t.isoformat()
def initial(roster):
    accounts={a['handle'].lower():dict(a,username=a['handle'].lower(),priority=1 if a['handle'].lower() in PRIORITY else 2,
        review_count=0,last_review_at=None,last_attempt_at=None,next_review_at=None,result='never_reviewed') for a in roster}
    if len(accounts)!=129 or any(not re.fullmatch(r'[a-z0-9_.]{1,30}',u) for u in accounts):raise ValueError('ROSTER_129_FENCE')
    return {'type':'instagram_rotation_control','status':'control_state','version':0,'accounts':accounts,'batches':{}}

def eligible_accounts(state,at):
    eligible=[a for a in state['accounts'].values() if (not a.get('next_review_at') or a['next_review_at']<=timestamp(at))
        and (not a.get('lease_until') or a['lease_until']<=timestamp(at))]
    # Fairness first: all accounts in a sweep, cultural priority within a sweep.
    return sorted(eligible,key=lambda a:(a.get('official_attempt_count',0),a.get('attempt_count',a['review_count']),a['priority'],a.get('last_review_at') or '',a['username']))

def select(state,at,limit=10):
    eligible=eligible_accounts(state,at)
    budget=max(0,min(limit,adaptive_query_budget(len(eligible)),MAX_ROTATING_ACCOUNTS))
    return eligible[:budget]

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
        eligible=eligible_accounts(state,at)
        budget=max(0,min(limit,adaptive_query_budget(len(eligible)),MAX_ROTATING_ACCOUNTS))
        selected=eligible[:budget]
        for a in selected:a.update(lease_run_id=run_id,lease_until=timestamp(at+timedelta(hours=2)))
        batch={'eligible_at_claim':len(eligible),'usernames':[a['username'] for a in selected],
               'budget':budget,'due_remaining_at_claim':len(eligible)-len(selected),
               'claimed_at':timestamp(at),'status':'claimed'}
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
            official=next((item for item in manifest.get('official_results',[]) if item.get('username')==u),None)
            if 'official_results' in manifest and official is None and not (manifest.get('searches') or manifest.get('instagram_attempts')):
                a.update(lease_until=None,lease_run_id=None)
                results.append(dict(username=u,run_id=run_id,result='not_queried',next_review_at=a.get('next_review_at')))
                continue
            a['last_attempt_at']=(official or {}).get('checked_at') or batch['claimed_at']
            searches=[s for s in manifest.get('searches',[]) if u in s['query'].get('accounts',[])]
            docs=[d for d in manifest.get('documents',[]) if any(u in s.get('accounts',[]) for s in d['searches'])]
            success=any(not s.get('error') for s in searches)
            ig_docs=[d for d in docs if d.get('acquisition_method')=='public_search_index']
            index_searches=[s for s in searches if s['query']['id'].startswith('ig-public-index-')]
            index_status=('not_queried' if not index_searches else 'search_failed' if all(s.get('error') for s in index_searches)
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
            attempt=next((x for x in manifest.get('instagram_attempts',[]) if x['username']==u),None)
            a['attempt_count']=a.get('attempt_count',a['review_count']-int(success))+1
            if attempt is not None:
                a['last_visit_at']=attempt['checked_at']
                a['result']=attempt['result'] if not ig_docs else 'instagram_indexed'
                a['last_result'].update(direct_access=attempt,posts_recovered=attempt['posts_recovered'],
                    direct_profiles_read=int(attempt['profile_accessible']))
                # An unsuccessful access check advances the rotation, but is not
                # called a successful source review or publication acquisition.
                if attempt['posts_recovered']:
                    a['last_successful_post_at']=attempt['checked_at']
                a['next_review_at']=timestamp(at+timedelta(hours=24 if attempt['posts_recovered'] else 96))
            # Persist official results distinctly from public index/access checks.
            if official:
                safe={'status':official['status'],'items_returned':official.get('items_returned',0),
                      'new_documents':official.get('new_documents',0),
                      'new_candidates':official.get('new_candidates',0),
                      'latest_publication_at':official.get('latest_publication_at'),
                      'http_status':official.get('http_status'),
                      'meta_error_code':official.get('meta_error_code'),
                      'meta_error_subcode':official.get('meta_error_subcode'),
                      'operational_status':official.get('operational_status')}
                a['official_last_result']=dict(safe,checked_at=official.get('checked_at') or timestamp(at),run_id=run_id)
                a['official_attempt_count']=a.get('official_attempt_count',0)+1
                a['last_result']['official']=safe
                if official['status'] in ('MEDIA_RETURNED','NO_MEDIA_RETURNED'):
                    a['last_review_at']=timestamp(at)
                    a['review_count']+=int(not success)
                a['official_eligibility']='eligible_observed' if official['status'] in ('MEDIA_RETURNED','NO_MEDIA_RETURNED') else 'restricted_or_unknown'
                if official['status'] not in ('MEDIA_RETURNED','NO_MEDIA_RETURNED'):
                    a['result']='official_query_failed'
                previous=a.get('productive_observations',0)
                a['productive_observations']=previous+int(official.get('new_candidates',0)>0)
                if official['status'] in ('MEDIA_RETURNED','NO_MEDIA_RETURNED'):
                    a['quiet_streak']=0 if official.get('new_documents',0)>0 else a.get('quiet_streak',0)+1
                    a['official_success_count']=a.get('official_success_count',0)+1
                    if official['status']=='MEDIA_RETURNED':
                        a['last_successful_post_at']=a['official_last_result']['checked_at']
                    a['result']='official_posts_recovered' if official.get('new_documents') else 'official_queried_no_new'
                    a['next_review_at']=timestamp(at+timedelta(hours=min(72,24 if a['priority']==1 else 48+8*min(a['quiet_streak'],3))))
                elif official.get('meta_error_code')==110:
                    a['next_review_at']=timestamp(at+timedelta(days=14))
            results.append(dict(username=u,**a['last_result'],result=a['result'],next_review_at=a['next_review_at']))
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

def source_hints(proposals):
    """Explicit structured organizer links at a local dated event, not co-mentions."""
    from urllib.parse import urlsplit
    hints={}
    for p in proposals:
        if not (p.get('event_date') or p.get('date')) or not p.get('venue'):continue
        evidence=p.get('evidence') or {};evidence=json.loads(evidence) if isinstance(evidence,str) else evidence
        if not isinstance(evidence,dict):continue
        for e in evidence.get('entities',[]):
            if e.get('role')!='organizer':continue
            try:event=json.loads(e.get('evidence',''))
            except (ValueError,TypeError):continue
            if not isinstance(event,dict):continue
            organizer=event.get('organizer') or {};location=event.get('location') or {}
            if not isinstance(organizer,dict) or not isinstance(location,dict):continue
            address=location.get('address') or {}
            if not isinstance(address,dict) or address.get('addressLocality','').lower() not in ('la plata','city bell','gonnet','tolosa'):continue
            if organizer.get('name')!=e.get('name'):continue
            url=organizer.get('url') or '';link=urlsplit(url);username=link.path.strip('/').lower()
            if link.hostname not in ('instagram.com','www.instagram.com') or not re.fullmatch(r'[a-z0-9_.]{1,30}',username) or username in ('p','reel','explore'):continue
            hints[username]={'username':username,'handle':username,'name':e['name'],'evidence_url':e.get('evidence_url') or p.get('document_url'),'evidence':organizer,'discovery_state':'explicit_local_organizer_link_pending_meta_eligibility'}
    return hints

def admit_discovered(conn,proposals):
    """At most one new source per ART day, cap 200; preserve original roster.
    Discovery authorizes a bounded official attempt, never identity approval.
    """
    from zoneinfo import ZoneInfo
    day=now().astimezone(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat()
    hints=source_hints(proposals)
    for _ in range(4):
        state=read(conn);version=state['version'];candidates=state.setdefault('discovered_candidates',{})
        for u,h in sorted(hints.items()):
            if u not in state['accounts'] and len(candidates)<200:candidates[u]=h
        admitted=[]
        days=state.setdefault('source_admissions',{})
        if day not in days and len(state['accounts'])<200:
            for u,h in sorted(candidates.items()):
                if u in state['accounts']:continue
                state['accounts'][u]=dict(h,priority=2,review_count=0,last_review_at=None,last_attempt_at=None,next_review_at=None,result='discovered_not_attempted',official_eligibility='not_checked')
                days[day]=u;admitted.append(h);break
        if cas(conn,state,version):return {'explicit_new_source_candidates':len(candidates),'admitted':admitted,'roster_size':len(state['accounts']),'daily_admission_limit':1,'max_accounts':200}
    raise RuntimeError('SOURCE_ADMISSION_CAS_RETRY_LATER')
