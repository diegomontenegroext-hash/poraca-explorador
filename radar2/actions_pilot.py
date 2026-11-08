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
from caption import interpret, VERSION as CAPTION_VERSION
from runtime import resolve_mode, credential_health,announce_credential_health
from checkpoint import Journal,restore_artifact
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
    if execute(conn,"SELECT run_id FROM radar2.runs WHERE run_id=$1 AND summary->>'status'='completed'",[run_id])['rows']:return {'run_id':run_id,'status':'already_completed'}
    execute(conn,"INSERT INTO radar2.runs(run_id,finished_at,summary) VALUES($1,now(),jsonb_build_object('status','running','mode',$2::text)) ON CONFLICT DO NOTHING",[run_id,'full' if full else 'incremental'])
    started_at=execute(conn,'SELECT clock_timestamp()::text started_at')['rows'][0]['started_at']
    old=baseline(conn)
    known_urls={r['url'] for r in execute(conn,'SELECT url FROM radar2.documents')['rows']}
    out=work/run_id;out.mkdir()
    c=Collector(out);c.run_id=run_id;c.baseline=old
    journal=Journal(ROOT/".radar2-checkpoints",conn,run_id);c.checkpoint=journal.save
    recovered=journal.recover(c)
    # Preserve working daily acquisition. The second certification batch only
    # explores the frontier and Instagram, never repeats the full agenda sweep.
    if full:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        try:c.genda(datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date())
        except Exception as exc:c.checks.append({'phase':'genda','error':type(exc).__name__})
        with ThreadPoolExecutor(max_workers=4) as ex:
            tasks=[ex.submit(f) for f in [c.teatrocerca,c.media_sources,c.alternativa,c.cultural_channels,c.genda_theatre]]
            for task in tasks:
                try:task.result()
                except Exception as exc:c.checks.append({'phase':'agenda_source','error':type(exc).__name__})
        if len(c.docs)<2 or not c.proposals:c.checks.append({'phase':'base_acquisition','error':'BASE_ACQUISITION_INSUFFICIENT'})
    else:
        # Incrementals acquire only the current agenda, not all historical sources.
        from datetime import datetime
        from zoneinfo import ZoneInfo
        try:c.genda(datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date(),days=1)
        except Exception as exc:c.checks.append({'phase':'incremental_agenda','error':type(exc).__name__})
    urgent_refresh={'status':'full_covered' if full else 'not_checked','selected':0,'fetched':0,'parsed':0,'checks':[]}
    if not full:
        from source_cadence import media_due,urgent_source_rechecks
        if media_due(conn):c.media_sources(max_articles=2,agendas_only=True)
        # Re-read a few existing original sources for events happening now.
        # No new scheduler, no approval, no duplicate sweep, no special bypass.
        if not corrective:
            try:
                from extract import extract_document
                due=urgent_source_rechecks(conn,limit=3)
                accounts=json.loads((ROOT/'radar2/accounts.json').read_text())
                urgent_refresh.update(status='bounded_existing_incremental',selected=len(due))
                for item in due:
                    d=c.fetch(item['url'],item['source'])
                    if not d:
                        urgent_refresh['checks'].append({'url':item['url'],'status':'blocked_or_unavailable'})
                        continue
                    urgent_refresh['fetched']+=1
                    before=len(c.proposals)
                    try:
                        extract_document(c,d,accounts,'near_term_source_refresh_v1')
                        urgent_refresh['parsed']+=1
                        urgent_refresh['checks'].append({'url':item['url'],'status':'parsed_or_reused',
                                                         'proposal_delta':len(c.proposals)-before})
                    except Exception as exc:
                        c.checks.append({'phase':'urgent_source_parse','url':item['url'],
                                         'error':type(exc).__name__})
                        urgent_refresh['checks'].append({'url':item['url'],'status':'parse_failed',
                                                         'error_type':type(exc).__name__})
            except Exception as exc:
                urgent_refresh.update(status='selection_failed',error_type=type(exc).__name__)
                c.checks.append({'phase':'urgent_source_selection','error':type(exc).__name__})
    # The official pilot reuses the same persisted ten-account selection.
    official_pilot={'status':'SKIPPED_NOT_DAILY'}
    rotation_status={'status':'not_executed'};batch={'accounts':[]}
    try:
        if corrective:raise RuntimeError('ROTATION_NOT_REPEATED_IN_FRONTIER_CORRECTION')
        rotation.initialize(conn,json.loads((ROOT/'radar2/instagram_roster.json').read_text()))
        batch=rotation.claim(conn,run_id,10)
        manifest={'searches':[],'documents':[],'instagram_attempts':[]}
        rotation_status={'status':'acquired_or_blocked_with_receipts','accounts':len(batch['accounts'])}
    except Exception as e:
        manifest={'searches':[],'documents':[],'instagram_attempts':[]}
        rotation_status={'status':'not_repeated_in_corrective' if corrective else 'phase_failed','error':type(e).__name__+': '+str(e)[:160]}
    if not corrective:
        try:
            if credential_health().get('credential_usable') is False:
                official_pilot={'status':'META_AUTH_ERROR','queries_sent':0}
            else:
                official_pilot=official_ig_pilot(c,known_urls,
                    [a['username'] for a in batch['accounts']],include_controls=False)
        except Exception as e:
            official_pilot={'status':'FAILED','error_type':type(e).__name__}
        # Report independent rotation errors instead of silently saying there were no posts.
        official_pilot['rotation_accounts_selected']=len(batch['accounts'])
        official_pilot['rotation_accounts_due']=batch.get('batch',{}).get('eligible_at_claim')
        official_pilot['rotation_state']=rotation_status['status']
        if rotation_status['status']=='phase_failed':
            print('::warning title=Instagram rotation::ROTATION_FAILED during selection')
            official_pilot['rotation_error']=rotation_status.get('error','ROTATION_PHASE_FAILED')
            if not official_pilot.get('queries_sent',0):
                official_pilot['status']='ROTATION_FAILED'
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
    # Reprocess original captions from Neon, without extra Meta downloads.
    # Both modes reinterpret only new/changed documents or a changed parser version.
    corpus=execute(conn,"SELECT payload FROM radar2.documents WHERE payload->>'acquisition_method'='official_meta_api' ORDER BY url")['rows']
    accounts=json.loads((ROOT/'radar2/accounts.json').read_text())
    from compound import classify,effective_version,requires_interpretation,VERSION as COMPOUND_VERSION
    prior={}
    for p in old:
        e=json.loads(p['evidence']) if isinstance(p.get('evidence'),str) else p.get('evidence') or {}
        if not e.get('interpretation_superseded_by'):prior.setdefault(p['document_url'],[]).append(e)
    previous_docs={}
    for row in corpus:
        saved=json.loads(row['payload']) if isinstance(row['payload'],str) else row['payload'];previous_docs[saved['url']]=saved
    def needs(d):return requires_interpretation(d,accounts,previous_docs.get(d['url']),prior.get(d['url'],[]))
    reprocessed=0
    for row in corpus:
        d=row['payload'];d=json.loads(d) if isinstance(d,str) else d
        if needs(d):c.docs.setdefault(d['url'],d)
    for d in list(c.docs.values()):
        if d.get('acquisition_method')!='official_meta_api':continue
        for key in [k for k,p in c.proposals.items() if p['document_url']==d['url']]:c.proposals.pop(key)
        if needs(d):
            interpret(c,d,accounts);reprocessed+=1
            for p in c.proposals.values():
                if p['document_url']==d['url']:p['source_document_sha256']=d.get('sha256')
        d['interpretation_version']=effective_version(d,accounts)
    # Follow only event-specific external originals from Genda's individual
    # secondary detail pages. Bounded to eight per ordinary run;
    # not a publication or an independent editorial decision.
    primary_handoff={'status':'not_checked_corrective','selected':0}
    if not corrective:
        try:
            from primary_followups import follow_secondary
            primary_handoff=follow_secondary(conn,c,limit=8)
            primary_handoff['status']='evidence_collected_not_published'
        except Exception as exc:
            primary_handoff={'status':'followup_failed','error_type':type(exc).__name__}
            c.checks.append({'phase':'primary_followup','error':type(exc).__name__})
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
    if result.get('source_followups'):
        from primary_followups import stage_followups
        primary_handoff['persistedFollowups']=stage_followups(conn,run_id,result['source_followups'])
        primary_handoff['receiptsStaged']=len([x for x in result['source_followups'] if x.get('secondarySha256')])
    else:primary_handoff['persistedFollowups']=0
    execute(conn,"UPDATE radar2.proposals p SET review_state='historico',evidence=evidence || jsonb_build_object('interpretation_superseded_by',$1::text) WHERE coalesce(evidence->>'parser_version','')='' AND evidence->>'kind'='document' AND EXISTS(SELECT 1 FROM radar2.proposals q WHERE q.document_url=p.document_url AND q.evidence->>'parser_version'=$2)",[run_id,CAPTION_VERSION])
    from compound_replay import retire as retire_compound
    retire_compound(conn,result)
    from maturity import retire_interpretations
    retire_interpretations(conn,result)
    supplemented=supplement_representatives(conn,result)
    read=execute(conn,"SELECT (SELECT count(*) FROM radar2.proposals WHERE last_run_id=$1) proposals,(SELECT count(*) FROM radar2.documents WHERE last_run_id=$1) documents,(SELECT summary->>'status' FROM radar2.runs WHERE run_id=$1) status",[run_id])['rows'][0]
    if read['status']!='completed' or int(read['proposals'])!=int(write['proposals_written']) or int(read['documents'])!=int(write['documents_written']):raise RuntimeError('SAME_RUN_READBACK_MISMATCH')
    try:graph_report=persist_graph(conn,run_id,graph)
    except Exception as e:graph_report={'status':'memory_write_failed','error':type(e).__name__}
    if 'batch' in batch:
        try:
            completed=rotation.complete(conn,run_id,manifest)
            rotation_status.update(status=completed['status'],results=completed.get('results',[]))
        except Exception as e:
            rotation_status.update(status='completion_failed',error=type(e).__name__)
            official_pilot['rotation_state']='ROTATION_FAILED'
            print('::warning title=Instagram rotation::ROTATION_FAILED during finalization')
    admissions=rotation.admit_discovered(conn,baseline(conn)) if full else {'status':'full_only_no_extra_acquisition'}
    m=execute(conn,NEW_DISCOVERY_METRICS_SQL,[run_id,started_at])['rows'][0]
    metrics={k:int(v) for k,v in m.items()}
    attempts=manifest['instagram_attempts']
    ig={'accounts_attempted':len(attempts),'accounts_with_profile_http_request':sum(bool(a.get('profile_http_requested')) for a in attempts),'profiles_accessible':sum(bool(a['profile_accessible']) for a in attempts),'accounts_with_posts':sum(a['posts_recovered']>0 for a in attempts),'posts_recovered':sum(a['posts_recovered'] for a in attempts),'errors_or_restrictions':sum(bool(a.get('error')) for a in attempts),'receipts':attempts,'index_searches':len(manifest['searches']),'search_failures':sum(bool(s.get('error')) for s in manifest['searches']),'search_receipts':manifest['searches']}
    report={'execution_context':'GitHub Actions','github_event':os.environ.get('GITHUB_EVENT_NAME'),'github_schedule':os.environ.get('RADAR2_SCHEDULE'),'github_run_id':os.environ['GITHUB_RUN_ID'],'commit':os.environ.get('GITHUB_SHA'),'started_at':started_at,'run_id':run_id,'mode':'full' if full else 'incremental','caption_documents_processed':reprocessed,'journal_recovered_documents':recovered,'credential_health':credential_health(),'scope':'full' if full else 'incremental','neon_readback':read,'discovery_metrics_v1':metrics,'instagram':ig,'instagram_official_pilot':official_pilot,'rotation':rotation_status,'source_discovery':source_report,'cultural_memory':graph_report,'source_admission':admissions,'urgent_source_refresh':urgent_refresh,'primary_source_followup':primary_handoff,'archived_non_cultural_proposals':[r['proposal_id'] for r in archived],'superseded_documents':[r['proposal_id'] for r in superseded],'supplemented_representatives':supplemented,'checks_errors':sum(bool(x.get('error')) for x in c.checks),'proposal_ids':[p['id'] for p in result['proposals']],'publications_approved':0}
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
            f.write('Instagram Meta oficial (rotacion): '+str(official_pilot.get('status'))+', cuentas seleccionadas '+str(official_pilot.get('rotation_accounts_selected',0))+', consultas '+str(official_pilot.get('queries_sent',0))+', exitosas '+str(official_pilot.get('accounts_successful',0))+', fallidas '+str(official_pilot.get('accounts_failed',0))+', documentos nuevos '+str(official_pilot.get('new_documents',0))+'.\n\n')
            f.write('New source domains observed: '+', '.join(source_report.get('new_domains_observed',[]))+'. Graph: '+json.dumps(graph_report)+'.\n\n')
            f.write('No editorial promotion. API HTTP verification is a separate authenticated check.\n\n')
    return report


def main():
    conn=os.environ.get('NEON_RADAR_LIMITED_DATABASE_URL','')
    if not conn or not (urlsplit(conn).hostname or '').endswith('.neon.tech'):raise RuntimeError('MISSING_OR_INVALID_LIMITED_NEON_SECRET')
    row=execute(conn,"SELECT current_user role,current_setting('neon.project_id',true) project,current_setting('neon.branch_id',true) branch,has_table_privilege(current_user,'radar2.proposals','INSERT') can_write")['rows'][0]
    if (row['role'],row['project'],row['branch'])!=(ROLE,PROJECT,BRANCH) or row['can_write'] not in ('t',True):raise RuntimeError('LIMITED_WRITER_IDENTITY_FENCE')
    health=announce_credential_health()
    trigger=(ROOT/'ops/radar-fallback-trigger.txt').read_text() if os.environ.get('GITHUB_EVENT_NAME')=='push' else ''
    if 'trigger_scope=maturity_replay' in trigger:
        from maturity import replay
        rid='radar2-maturity-'+os.environ['GITHUB_RUN_ID']
        before=execute(conn,'SELECT count(*) n FROM radar2.proposals')['rows'][0]['n']
        first=replay(conn,rid)
        middle=execute(conn,'SELECT count(*) n FROM radar2.proposals')['rows'][0]['n']
        second=replay(conn,rid+'-idempotence')
        after=execute(conn,'SELECT count(*) n FROM radar2.proposals')['rows'][0]['n']
        if middle!=after:raise RuntimeError('REPROCESSING_IDEMPOTENCE_FAILED')
        admissions=rotation.admit_discovered(conn,baseline(conn))
        report={'first':first,'second':second,'source_admission':admissions,'counts':{'before':before,'after_first':middle,'after_second':after},'credential_health':health,'github_run_id':os.environ['GITHUB_RUN_ID'],'commit':os.environ.get('GITHUB_SHA'),'mode':'preserved_originals_replay_no_acquisition'}
        execute(conn,"UPDATE radar2.runs SET summary=summary || $2::jsonb WHERE run_id=$1",[rid,json.dumps(report)])
        print(json.dumps(report));return

    prefix='radar2-ghdaily-' if os.environ.get('GITHUB_EVENT_NAME')=='schedule' else 'radar2-ghpilot-'
    run_id=prefix+os.environ['GITHUB_RUN_ID']+'-attempt'+os.environ.get('GITHUB_RUN_ATTEMPT','1');access=PublicAccess();reports=[]
    mode=resolve_mode(os.environ.get('GITHUB_EVENT_NAME'),os.environ.get('RADAR2_SCHEDULE',''),os.environ.get('RADAR2_MODE',''))
    corrective=os.environ.get('GITHUB_EVENT_NAME')=='push' and 'trigger_scope=frontier_corrective' in (ROOT/'ops/radar-fallback-trigger.txt').read_text()
    restored=restore_artifact(ROOT/'.radar2-checkpoints')
    print(json.dumps({'acquisition_journal_restore':restored}))
    with tempfile.TemporaryDirectory(prefix='radar2-gh-') as temp:
        trigger=(ROOT/'ops/radar-fallback-trigger.txt').read_text() if os.environ.get('GITHUB_EVENT_NAME')=='push' else ''
        if 'trigger_scope=compound_acceptance' in trigger:
            from compound_replay import recover
            recovered= recover(conn,run_id+'-compound-recovery')
            before=execute(conn,'SELECT count(*) n FROM radar2.proposals')['rows'][0]['n']
            repeated=recover(conn,run_id+'-compound-idempotence')
            after=execute(conn,'SELECT count(*) n FROM radar2.proposals')['rows'][0]['n']
            if before!=after:raise RuntimeError('COMPOUND_IDEMPOTENCE_FAILED')
            print(json.dumps({'compound_recovery':recovered,'idempotence':repeated,'proposal_count_before_repeat':before,'proposal_count_after_repeat':after}))
        modes=['incremental'] if 'certification_modes=incremental' in trigger else ['full','incremental'] if 'certification_modes=full,incremental' in trigger and 'full,incremental,incremental' not in trigger else ['full','incremental','incremental'] if 'certification_modes=full,incremental,incremental' in trigger else [mode]* (1 if corrective else certification_batches())
        for i,current_mode in enumerate(modes):
            current_id=run_id+('-batch'+str(i+1) if i else '')
            try:reports.append(run_batch(conn,current_id,Path(temp),current_mode=='full' and i==0 and not corrective,access,corrective))
            except Exception as exc:
                execute(conn,"UPDATE radar2.runs SET finished_at=now(),summary=summary || jsonb_build_object('status','failed','error_type',$2::text) WHERE run_id=$1",[current_id,type(exc).__name__])
                raise
    for path in (ROOT/'.radar2-checkpoints').glob('*.json'):path.unlink()
    if len(reports)==2 and 'trigger_scope=compound_acceptance' not in trigger:
        sets=[{x['username'] for x in r['instagram']['receipts']} for r in reports]
        if sets[0]&sets[1] or any(len(s)!=10 for s in sets):raise RuntimeError('TWO_BATCH_ROTATION_ACCEPTANCE_FAILED')
        print(json.dumps({'certification':'two_distinct_ten_account_batches','accounts':20,'overlap':0,'github_run_id':os.environ['GITHUB_RUN_ID']}))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('RADAR2_BLOCKED: '+type(exc).__name__+' '+str(exc),file=sys.stderr);sys.exit(1)
