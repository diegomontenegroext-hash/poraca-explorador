#!/usr/bin/env python3
"""The existing daily job: acquire, rotate, explore, interpret, persist, read back."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

from persist import execute, SQL
from collector import Collector, sha, utc
from reconcile import reconcile
import rotation
from capabilities import PublicAccess, instagram_batch, public_search, discover_links, enrich_graph, persist_graph, carry_forward, supplement_representatives
from instagram_official_pilot import acquire as official_ig_pilot

PROJECT='frosty-union-52906378'
BRANCH='br-mute-recipe-b4odj2bl'
ROLE='poraca_radar_limited_prod'
ROOT=Path(__file__).resolve().parent.parent

# Mirrors private_discoveries exact-key ranking. The existing fuzzy reconciliation
# additionally points cross-source aliases at their visible representative.
NEW_DISCOVERY_METRICS_SQL="""
WITH ranked AS (
 SELECT p.proposal_id,p.last_run_id,p.first_seen_at,p.event_date,p.evidence,
 ROW_NUMBER() OVER (
  PARTITION BY lower(regexp_replace(p.title,'[^[:alnum:]]','','g')),
  p.event_date,p.event_time,lower(regexp_replace(coalesce(p.venue,''),'[^[:alnum:]]','','g'))
  ORDER BY CASE WHEN p.review_state='fuente_original' THEN 0 ELSE 1 END,p.first_seen_at,p.proposal_id
 ) rn FROM radar2.proposals p WHERE coalesce(p.evidence->>'duplicate_of','')=''
)
SELECT
 (SELECT count(*) FROM radar2.proposals WHERE last_run_id=$1 AND first_seen_at >= $2::timestamptz) new_ids,
 count(*) FILTER(WHERE rn=1 AND last_run_id=$1 AND first_seen_at >= $2::timestamptz) new_visible_unique,
 count(*) FILTER(WHERE rn=1 AND last_run_id=$1 AND first_seen_at >= $2::timestamptz AND event_date IS NOT NULL AND evidence->>'kind' IN ('event','program')) new_unique_dated_proposals
 FROM ranked
"""


def baseline(conn):
    return execute(conn,"SELECT proposal_id,title,to_char(event_date,'YYYY-MM-DD') event_date,event_time,venue,document_url,evidence FROM radar2.proposals ORDER BY first_seen_at,proposal_id LIMIT 10000")['rows']


def certification_batches():
    # A single authorized push groups two ten-account batches, not two FULLs.
    # Daily schedule and workflow_dispatch always keep one batch.
    if os.environ.get('GITHUB_EVENT_NAME')!='push':return 1
    trigger=dict(line.split('=',1) for line in (ROOT/'ops/radar-fallback-trigger.txt').read_text().splitlines() if '=' in line and not line.startswith('#'))
    return 2 if trigger.get('certification_batches')=='2' else 1


def run_batch(conn,run_id,work,full,access,corrective=False):
    if execute(conn,'SELECT run_id FROM radar2.runs WHERE run_id=$1',[run_id])['rows']:raise RuntimeError('RUN_ID_ALREADY_EXISTS_NO_REPLAY')
    started_at=execute(conn,'SELECT clock_timestamp()::text started_at')['rows'][0]['started_at']
    old=baseline(conn)
    known_urls={r['url'] for r in execute(conn,'SELECT url FROM radar2.documents')['rows']}
    out=work/run_id;out.mkdir()
    c=Collector(out);c.run_id=run_id
    # Preserve working daily acquisition. The second certification batch only
    # explores the frontier and Instagram, never repeats the full agenda sweep.
    if full:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        c.genda(datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date())
        with ThreadPoolExecutor(max_workers=4) as ex:
            for f in ex.map(lambda f:f(),[c.teatrocerca,c.media_sources,c.alternativa,c.cultural_channels,c.genda_theatre]):pass
        if len(c.docs)<2 or not c.proposals:raise RuntimeError('BASE_ACQUISITION_FAILED')
    # The official pilot reuses the same persisted ten-account selection.
    official_pilot={'status':'SKIPPED_NOT_DAILY'}
    rotation_status={'status':'not_executed'};batch={'accounts':[]}
    try:
        if corrective:raise RuntimeError('ROTATION_NOT_REPEATED_IN_FRONTIER_CORRECTION')
        rotation.initialize(conn,json.loads((ROOT/'radar2/instagram_roster.json').read_text()))
        batch=rotation.claim(conn,run_id,10)
        manifest=instagram_batch(c,batch,access)
        search=public_search(c,access,batch)
        manifest['searches']=search['searches'];manifest['documents']=search['documents']
        rotation_status={'status':'acquired_or_blocked_with_receipts','accounts':len(batch['accounts'])}
    except Exception as e:
        manifest={'searches':[],'documents':[],'instagram_attempts':[]}
        rotation_status={'status':'not_repeated_in_corrective' if corrective else 'phase_failed','error':type(e).__name__+': '+str(e)[:160]}
    if full and not corrective:
        try:
            official_pilot=official_ig_pilot(c,known_urls,
                [a['username'] for a in batch.get('accounts',[])])
        except Exception as e:
            official_pilot={'status':'FAILED','error_type':type(e).__name__}
        manifest['official_results']=official_pilot.get('results',[])
    try:source_report=discover_links(c,conn,known_urls,limit=12 if full else 6,refresh_candidates=corrective)
    except Exception as e:source_report={'status':'phase_failed','error':type(e).__name__+': '+str(e)[:160]}
    # Rejected non-cultural documents remain auditable but leave the private
    # active feed, using its existing archive state. No row is deleted.
    excluded=execute(conn,"SELECT summary->'sources' sources FROM radar2.runs WHERE run_id='radar2-source-discovery-state-v1'")['rows']
    archived=[]
    if excluded:
        sources=excluded[0]['sources'];sources=json.loads(sources) if isinstance(sources,str) else sources
        rejected=[u for u,x in sources.items() if x['status'].startswith('rejected_')]
        archived=execute(conn,"UPDATE radar2.proposals SET review_state='historico',evidence=evidence || jsonb_build_object('state','historico','kind','rejected_document','editorial_exclusion','not a local cultural source','exclusion_run_id',$2::text) WHERE event_date IS NULL AND document_url IN (SELECT jsonb_array_elements_text($1::jsonb)) AND evidence->>'acquisition_method'='autonomous_public_link_frontier' AND review_state<>'historico' RETURNING proposal_id",[json.dumps(rejected),run_id])['rows']
    result=c.save();result=reconcile(result,old);result=carry_forward(result,old)
    # Collect graph evidence before writing proposals so the API sees the same
    # node IDs and event relationships persisted in the cultural memory ledger.
    graph=enrich_graph(result,old)
    result['finished_at']=utc()
    # If a formerly unparsed page is now an individual dated event, archive
    # only its same-title undated precursor; preserve the original evidence.
    dated=[p for p in result['proposals'] if p.get('date')]
    superseded=execute(conn,"WITH incoming AS (SELECT x->>'document_url' url,x->>'title' title,x->>'id' id FROM jsonb_array_elements($1::jsonb) x) UPDATE radar2.proposals p SET review_state='historico',evidence=p.evidence || jsonb_build_object('kind','superseded_document','superseded_by',i.id) FROM incoming i WHERE p.document_url=i.url AND p.title=i.title AND p.event_date IS NULL AND p.review_state='investigable' RETURNING p.proposal_id",[json.dumps(dated,ensure_ascii=False)])['rows']
    write=execute(conn,SQL,[json.dumps(result,ensure_ascii=False)])['rows'][0]
    supplemented=supplement_representatives(conn,result)
    read=execute(conn,"SELECT (SELECT count(*) FROM radar2.proposals WHERE last_run_id=$1) proposals,(SELECT count(*) FROM radar2.documents WHERE last_run_id=$1) documents,(SELECT summary->>'status' FROM radar2.runs WHERE run_id=$1) status",[run_id])['rows'][0]
    if read['status']!='completed' or int(read['proposals'])!=int(write['proposals_written']) or int(read['documents'])!=int(write['documents_written']):raise RuntimeError('SAME_RUN_READBACK_MISMATCH')
    try:graph_report=persist_graph(conn,run_id,graph)
    except Exception as e:graph_report={'status':'memory_write_failed','error':type(e).__name__}
    if batch['accounts']:
        try:
            completed=rotation.complete(conn,run_id,manifest)
            rotation_status.update(status=completed['status'],results=completed.get('results',[]))
        except Exception as e:rotation_status.update(status='completion_failed',error=type(e).__name__+': '+str(e)[:160])
    m=execute(conn,NEW_DISCOVERY_METRICS_SQL,[run_id,started_at])['rows'][0]
    metrics={k:int(v) for k,v in m.items()}
    attempts=manifest['instagram_attempts']
    ig={'accounts_attempted':len(attempts),'accounts_with_profile_http_request':sum(bool(a.get('profile_http_requested')) for a in attempts),'profiles_accessible':sum(bool(a['profile_accessible']) for a in attempts),'accounts_with_posts':sum(a['posts_recovered']>0 for a in attempts),'posts_recovered':sum(a['posts_recovered'] for a in attempts),'errors_or_restrictions':sum(bool(a.get('error')) for a in attempts),'receipts':attempts,'index_searches':len(manifest['searches']),'search_failures':sum(bool(s.get('error')) for s in manifest['searches']),'search_receipts':manifest['searches']}
    report={'execution_context':'GitHub Actions','github_run_id':os.environ['GITHUB_RUN_ID'],'commit':os.environ.get('GITHUB_SHA'),'started_at':started_at,'run_id':run_id,'scope':'daily_acquisition_and_exploration' if full else 'bounded_frontier_parser_correction' if corrective else 'bounded_second_rotation_and_frontier','neon_readback':read,'discovery_metrics_v1':metrics,'instagram':ig,'instagram_official_pilot':official_pilot,'rotation':rotation_status,'source_discovery':source_report,'cultural_memory':graph_report,'archived_non_cultural_proposals':[r['proposal_id'] for r in archived],'superseded_documents':[r['proposal_id'] for r in superseded],'supplemented_representatives':supplemented,'checks_errors':sum(bool(x.get('error')) for x in c.checks),'proposal_ids':[p['id'] for p in result['proposals']],'publications_approved':0}
    saved=execute(conn,"UPDATE radar2.runs SET summary=summary || $2::jsonb WHERE run_id=$1 RETURNING run_id",[run_id,json.dumps(report,ensure_ascii=False)])['rows']
    if len(saved)!=1:raise RuntimeError('RUN_SUMMARY_NOT_SAVED')
    print(json.dumps({k:v for k,v in report.items() if k not in ('proposal_ids','rotation','instagram','source_discovery')}))
    print(json.dumps({'run_id':run_id,'instagram':{k:v for k,v in ig.items() if 'receipts' not in k},'new_sources':source_report.get('new_domains_observed',[]),'rotation_status':rotation_status['status']}))
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
            f.write('## Radar 2: '+run_id+'\n\n')
            f.write('Neon readback: '+json.dumps(read)+'. New unique proposals: '+str(metrics['new_visible_unique'])+'; dated: '+str(metrics['new_unique_dated_proposals'])+'.\n\n')
            f.write('Instagram: '+str(ig['accounts_attempted'])+' policy/access attempts, '+str(ig['profiles_accessible'])+' accessible profiles, '+str(ig['posts_recovered'])+' actual posts. Rotation: '+rotation_status['status']+'.\n\n')
            f.write('Instagram piloto Meta (4 cuentas): '+str(official_pilot.get('status'))+', nuevos documentos '+str(official_pilot.get('new_documents',0))+'.\n\n')
            f.write('New source domains observed: '+', '.join(source_report.get('new_domains_observed',[]))+'. Graph: '+json.dumps(graph_report)+'.\n\n')
            f.write('No editorial promotion. API HTTP verification is a separate authenticated check.\n\n')
    return report


def main():
    conn=os.environ.get('NEON_RADAR_LIMITED_DATABASE_URL','')
    if not conn or not (urlsplit(conn).hostname or '').endswith('.neon.tech'):raise RuntimeError('MISSING_OR_INVALID_LIMITED_NEON_SECRET')
    row=execute(conn,"SELECT current_user role,current_setting('neon.project_id',true) project,current_setting('neon.branch_id',true) branch,has_table_privilege(current_user,'radar2.proposals','INSERT') can_write")['rows'][0]
    if (row['role'],row['project'],row['branch'])!=(ROLE,PROJECT,BRANCH) or row['can_write'] not in ('t',True):raise RuntimeError('LIMITED_WRITER_IDENTITY_FENCE')
    prefix='radar2-ghdaily-' if os.environ.get('GITHUB_EVENT_NAME')=='schedule' else 'radar2-ghpilot-'
    run_id=prefix+os.environ['GITHUB_RUN_ID'];access=PublicAccess();reports=[]
    corrective=os.environ.get('GITHUB_EVENT_NAME')=='push' and 'trigger_scope=frontier_corrective' in (ROOT/'ops/radar-fallback-trigger.txt').read_text()
    with tempfile.TemporaryDirectory(prefix='radar2-gh-') as temp:
        for i in range(1 if corrective else certification_batches()):reports.append(run_batch(conn,run_id+('-batch2' if i else ''),Path(temp),i==0 and not corrective,access,corrective))
    if len(reports)==2:
        sets=[{x['username'] for x in r['instagram']['receipts']} for r in reports]
        if sets[0]&sets[1] or any(len(s)!=10 for s in sets):raise RuntimeError('TWO_BATCH_ROTATION_ACCEPTANCE_FAILED')
        print(json.dumps({'certification':'two_distinct_ten_account_batches','accounts':20,'overlap':0,'github_run_id':os.environ['GITHUB_RUN_ID']}))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('RADAR2_BLOCKED: '+type(exc).__name__+' '+str(exc),file=sys.stderr);sys.exit(1)
