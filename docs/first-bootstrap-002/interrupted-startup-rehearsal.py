#!/usr/bin/env python3
"""Interrupt a fictional launch after control publication; recover with fresh authority."""
import hashlib,json,os,shutil,signal,socket,sqlite3,subprocess,tarfile,tempfile,time,urllib.request
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent; OLD=REPO/'docs/first-bootstrap-001'
PYTHON='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python'
CANDIDATE='f59a6e91152900d709cad1775b2756cf25b316c0'
ROOT=Path(tempfile.mkdtemp(prefix='cow-bootstrap-interrupted-')).resolve(); PORT=19890
assert ROOT.is_relative_to(Path('/private/var/folders')) and PORT!=9899
os.chmod(ROOT,0o700)
for n in ('data','home','workspace','request','deployment','control-old','control-new'):(ROOT/n).mkdir(mode=0o700)
ENV={'PATH':str(Path(PYTHON).parent)+':/usr/bin:/bin','HOME':str(ROOT/'home'),'COW_DATA_DIR':str(ROOT/'data'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8','BROWSER':'true'}
REPORT={'schema':'cow.bootstrap.interrupted-startup/1','candidate':CANDIDATE,'port':PORT,'limitations':['Fictional data only; BROWSER=true and network-outbound denied.','Interruption occurs between control publication and observer execution, not mid-transaction.','Same-UID control does not prove human presence; no external exactly-once claim.','Live private restoration and old-service state are not tested.']}
BASE=['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON]


def snapshot():
    root=ROOT/'workspace'; values={}
    targets={'memory/long-term/index.db':['sessions','messages','files','chunks'], 'memory/recovery/tasks.db':['recovery_tasks','recovery_attempts','recovery_effects','recovery_verifications'], 'agents/testpilot/memory/long-term/index.db':['files','chunks'],'agents/testpilot2/memory/long-term/index.db':['files','chunks']}
    for rel,tables in targets.items():
        with sqlite3.connect('file:'+str(root/rel)+'?mode=ro',uri=True) as db:
            assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
            for table in tables:
                rows=db.execute('select * from '+table+' order by rowid').fetchall()
                values[rel+':'+table]=hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()
    values['team.json']=hashlib.sha256((root/'agents/team.json').read_bytes()).hexdigest()
    values['memory.md']=hashlib.sha256((root/'memory/MEMORY.md').read_bytes()).hexdigest()
    return values


def make_request():
    subprocess.run(BASE+[str(ROOT/'make_request.py')],cwd=ROOT/'deployment',env=ENV,check=True)
    value=json.loads((ROOT/'request/observation.json').read_text())
    return value['request_id']


def operator(directory,timeout):
    p=subprocess.run(BASE+['scripts/maintenance_drain.py','--control-dir',str(directory),'--grant','close-admission-and-observe','--timeout',str(timeout)],cwd=ROOT/'deployment',env=ENV,text=True,capture_output=True,timeout=timeout+15)
    return p.returncode,json.loads(p.stdout)


def main():
    with socket.socket() as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',PORT))
    tar=ROOT/'source.tar'
    with tar.open('wb') as f:subprocess.run(['git','archive',CANDIDATE],cwd=REPO,stdout=f,check=True)
    with tarfile.open(tar) as f:f.extractall(ROOT/'deployment',filter='data')
    enabled=('cow_cli','Godcmd','Keyword','Banwords','linkai','Role','Finish'); names=(*enabled,'Dungeon','Hello','tool')
    (ROOT/'deployment/plugins/plugins.json').write_text(json.dumps({'plugins':{n:{'enabled':n in enabled,'priority':0,'desc':'fictional'} for n in names}}))
    (ROOT/'workspace/agents').mkdir();(ROOT/'workspace/memory').mkdir()
    agents=[{'id':n,'name':'Fixture '+n,'model':'fixture-'+n,'bot_type':'openai'} for n in ('default','testpilot','testpilot2')]
    (ROOT/'workspace/agents/team.json').write_text(json.dumps({'agents':agents,'default_agent_id':'default'}))
    (ROOT/'workspace/memory/MEMORY.md').write_text('# Fictional memory\nBlue cow prefers clover.\n')
    config={'channel_type':'web','web_host':'127.0.0.1','web_port':PORT,'web_console':True,'self_evolution_enabled':False,'agent_workspace':str(ROOT/'workspace'),'model':'fixture-model','bot_type':'openai','agent_permission_mode':'read-only','agent_delegation':{'enabled':True},'mcp_servers':[],'linkai_api_key':'fictional-only'}
    (ROOT/'data/config.json').write_text(json.dumps(config))
    (ROOT/'rehearsal.sb').write_text('(version 1)\n(allow default)\n(deny network-outbound)\n(deny file-read* file-write* (subpath "/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData") (subpath "/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime"))\n')
    shutil.copy2(HERE/'interrupted-startup-driver.py',ROOT/'driver.py');shutil.copy2(OLD/'request_fixture.py',ROOT/'make_request.py')
    subprocess.run(BASE+[str(OLD/'seed_fixture.py'),str(ROOT)],cwd=ROOT/'deployment',env=ENV,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    original=snapshot();request_id=make_request()
    with (ROOT/'interrupted.log').open('wb') as log:
        p=subprocess.Popen(BASE+[str(ROOT/'driver.py')],cwd=ROOT/'deployment',env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+45
            while not (ROOT/'bound-before-observation').exists() and time.monotonic()<deadline:
                if p.poll() is not None:raise RuntimeError('interrupted launch exited early')
                time.sleep(.05)
            assert (ROOT/'bound-before-observation').exists()
            descriptor=json.loads((ROOT/'control-old/service.json').read_text())
            assert descriptor['pid']==p.pid and not (ROOT/'request/observation.json').exists()
            claim=ROOT/'request'/('.cow-discovery-'+request_id+'.consumed')
            assert claim.exists() and not (ROOT/'request/observation.json.receipt.json').exists()
            assert not list((ROOT/'control-old').glob('receipt-*.json'))
            with socket.socket() as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',PORT))
            REPORT['first_process']={'pid':p.pid,'service_published':True,'startup_claim_retained':True,'startup_receipt_absent':True,'control_receipt_absent':True,'listener_absent_at_boundary':True}
        finally:
            if p.poll() is None:p.send_signal(signal.SIGTERM)
            REPORT['first_process_exit']=p.wait(timeout=20)
    assert REPORT['first_process_exit']==0 and claim.exists() and not (ROOT/'request/observation.json.receipt.json').exists()
    (ROOT/'request').rename(ROOT/'request-old');(ROOT/'request').mkdir(mode=0o700)
    new_request=make_request();assert request_id!=new_request
    with (ROOT/'replacement.log').open('wb') as log:
        p=subprocess.Popen(BASE+['scripts/discovery_startup.py','--request',str(ROOT/'request/observation.json'),'--control-dir',str(ROOT/'control-new')],cwd=ROOT/'deployment',env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            assert p.pid!=descriptor['pid']
            end=time.monotonic()+60
            while time.monotonic()<end:
                if p.poll() is not None:raise RuntimeError('replacement exited')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health',timeout=1) as q:
                        if json.load(q)['status']=='ok':break
                except (OSError,ValueError):time.sleep(.1)
            else:raise RuntimeError('replacement health timeout')
            observer=json.loads((ROOT/'request/observation.json.receipt.json').read_text())
            assert observer['pid']==p.pid and not observer['dispatch_permitted'] and not observer['adapter_contact']
            assert [x['target_id'] for x in observer['inventory']]==['default','testpilot','testpilot2']
            configured=json.loads((ROOT/'deployment/plugins/plugins.json').read_text())['plugins']
            assert all(configured[name]['enabled'] for name in enabled)
            code,stale=operator(ROOT/'control-old',.1)
            assert code==2 and stale['status']=='unavailable' and not stale['drained']
            assert not (ROOT/'control-new/request.json').exists() and not list((ROOT/'control-new').glob('claimed-*.json')) and not list((ROOT/'control-new').glob('receipt-*.json'))
            code,fresh=operator(ROOT/'control-new',8)
            assert code==0 and fresh['closed'] and fresh['drained'] and fresh['binding']['pid']==p.pid
            assert fresh['binding']['runtime_epoch']==observer['initialization_epoch']
            assert fresh['binding']['service_id']!=descriptor['service_id']
            assert (ROOT/'control-new'/('receipt-'+fresh['request_id']+'.json')).exists()
            REPORT['replacement']={'pid':p.pid,'health':'200/ok','startup_ids':[x['target_id'] for x in observer['inventory']],'startup_dispatch_permitted':False,'old_control_result':stale,'new_control_receipt':fresh,'fresh_request_distinct':True,'fresh_service_distinct':True,'seven_plugins_enabled':list(enabled),'old_control_did_not_submit_to_replacement':True}
        finally:
            if p.poll() is None:p.send_signal(signal.SIGTERM)
            REPORT['replacement_exit']=p.wait(timeout=20)
    assert REPORT['replacement_exit']==0
    after=snapshot();assert original==after
    assert len({key.split(':')[0] for key in after if '.db:' in key})==4
    with socket.socket() as sock:sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',PORT))
    REPORT['port_released']=True
    REPORT.update(durable_metadata_digest_before=original,durable_metadata_digest_after=after,integrity_and_four_db_metadata_match=True,status='passed')

try:main()
except Exception as exc:
    REPORT.update(status='failed',error_type=type(exc).__name__)
    raise
finally:
    (ROOT/'result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('private rehearsal root:',ROOT,flush=True)
