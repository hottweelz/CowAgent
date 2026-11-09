#!/usr/bin/env python3
"""Private, fictional macOS first-bootstrap rehearsal; no live state is read."""
import hashlib, json, os, shutil, signal, socket, sqlite3, subprocess, tarfile, tempfile, time, urllib.error, urllib.request, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent
PYTHON = '/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python'
LEGACY = '90c3cd8f72ffe7a47cb20925fa538eda479317c6'
FALLBACK = 'f659349785acf98905901a5cc53921436a109dbc'
CANDIDATE = '8d182026be2380fc574eeecd13edcffa5ed1dcb1'
ROOT = Path(tempfile.mkdtemp(prefix='cow-first-bootstrap-')).resolve()
PORT = 19886
assert PORT != 9899 and ROOT.is_relative_to(Path('/private/var/folders'))
assert not any(str(ROOT).startswith(x) for x in ('/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData','/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime'))
os.chmod(ROOT, 0o700)
for name in ('data','home','workspace','request','responses','deployment'):
    (ROOT/name).mkdir(mode=0o700)
ENV = {'PATH':str(Path(PYTHON).parent)+':/usr/bin:/bin','HOME':str(ROOT/'home'), 'COW_DATA_DIR':str(ROOT/'data'), 'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8','BROWSER':'true'}
REPORT = {'schema':'cow.first-bootstrap.rehearsal/1','legacy_commit':LEGACY,'fallback_commit':FALLBACK,'candidate_head':CANDIDATE,'candidate_executable_commit':'005c1e4805c75017467b817baa2a8bbbe3f7511d','port':PORT,'steps':[], 'limitations':['Legacy is modeled by the reflog-bracketed launch baseline; loaded live commit is unknown.', 'Fixture plugins disabled and browser launch replaced by true; these settings do not establish live effects.', 'Fictional coordinator leases are not model runs or real external dispatch.', 'Outbound network is denied; absence of actual provider effects is not a general exactly-once guarantee.']}

def source(commit):
    dst=ROOT/'deployment'
    shutil.rmtree(dst); dst.mkdir()
    archive=ROOT/'source.tar'
    with archive.open('wb') as f: subprocess.run(['git','archive',commit],cwd=REPO,stdout=f,check=True)
    with tarfile.open(archive) as f: f.extractall(dst,filter='data')
    archive.unlink()
    shutil.copy2(ROOT/'disabled_plugins.json',dst/'plugins/plugins.json')

def database_snapshot(base):
    result={}
    for path in sorted(base.rglob('*.db')):
        conn=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
        try:
            assert conn.execute('pragma integrity_check').fetchone()[0]=='ok'
            dump='\n'.join(conn.iterdump()).encode()
            result[str(path.relative_to(base))]=hashlib.sha256(dump).hexdigest()
        finally: conn.close()
    return result

def backup(src,dst):
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns('*.db','*.db-wal','*.db-shm','*.db-journal','run.log','*.pid'))
    for path in src.rglob('*.db'):
        target=dst/path.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as a, sqlite3.connect(target) as b: a.backup(b)
    assert database_snapshot(src)==database_snapshot(dst)

def health(p):
    until=time.monotonic()+60
    while time.monotonic()<until:
        if p.poll() is not None: raise RuntimeError('process exited before health')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health',timeout=1) as r:
                if r.status==200 and json.load(r)['status']=='ok': return
        except (OSError,ValueError): pass
        time.sleep(.1)
    raise RuntimeError('health timeout')

def cmd(p,action,**kw):
    key=uuid.uuid4().hex;p.stdin.write(json.dumps({'id':key,'action':action,**kw})+'\n');p.stdin.flush()
    path=ROOT/'responses'/f'{key}.json'; end=time.monotonic()+10
    while time.monotonic()<end:
        if path.exists():
            try: result=json.loads(path.read_text())
            except ValueError: time.sleep(.02);continue
            assert 'error_type' not in result,result
            return result
        if p.poll() is not None: raise RuntimeError('controller exited')
        time.sleep(.02)
    raise RuntimeError('controller timeout')

def launch(label,candidate=False):
    step={'name':label};REPORT['steps'].append(step)
    if candidate:
        subprocess.run(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,str(ROOT/'make_request.py')],cwd=ROOT/'deployment',env=ENV,check=True)
    with (ROOT/(label+'.log')).open('wb') as log:
        p=subprocess.Popen(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,str(ROOT/'driver.py') if candidate else 'app.py'],cwd=ROOT/'deployment',env=ENV,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        try:
            health(p);step['health']='200/ok';step['pid']=p.pid
            if candidate:
                receipt=json.loads((ROOT/'request/observation.json.receipt.json').read_text())
                assert receipt['pid']==p.pid and not receipt['dispatch_permitted'] and not receipt['adapter_contact']
                assert [x['target_id'] for x in receipt['inventory']]==['default','testpilot','testpilot2']
                assert all(x['selection']['status']=='denied' and not x['selection']['dispatch_permitted'] for x in receipt['decisions'])
                assert not (ROOT/'request/observation.json').exists()
                assert (ROOT/'request'/('.cow-discovery-'+receipt['request_id']+'.consumed')).exists()
                step['observer']={'ids':[x['target_id'] for x in receipt['inventory']],'statuses':[x['selection']['status'] for x in receipt['decisions']],'dispatch_permitted':False,'adapter_contact':False,'one_shot_consumed':True,'manifest_sha256':receipt['manifest_sha256'],'initialization_epoch':receipt['initialization_epoch']}
                held=cmd(p,'hold')['receipt'];assert held['active']['fictional_run']==2
                busy=cmd(p,'drain',timeout=.05)['receipt'];assert busy['closed'] and not busy['drained']
                try:
                    urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{PORT}/message',data=b'{}',headers={'Content-Type':'application/json'}),timeout=2)
                    raise AssertionError('admission accepted')
                except urllib.error.HTTPError as e: assert e.code==503
                cmd(p,'release');settled=cmd(p,'drain',timeout=5)['receipt'];assert settled['drained'] and not settled['active']
                step.update(held=held,busy=busy,closed_request_status=503,settled=settled)
        finally:
            if p.poll() is None: p.send_signal(signal.SIGTERM)
            step['exit_code']=p.wait(timeout=20);p.stdin.close()
        assert step['exit_code']==0

def main():
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('127.0.0.1',PORT))
    shutil.copy2(FIX/'driver_fixture.py',ROOT/'driver.py');shutil.copy2(FIX/'request_fixture.py',ROOT/'make_request.py')
    workspace=ROOT/'workspace'; (workspace/'agents').mkdir(); (workspace/'memory').mkdir()
    agents=[{'id':name,'name':'Fixture '+name,'model':'fixture-'+name,'bot_type':'openai'} for name in ('default','testpilot','testpilot2')]
    (workspace/'agents/team.json').write_text(json.dumps({'agents':agents,'default_agent_id':'default'}))
    (workspace/'memory/MEMORY.md').write_text('# Fictional memory\nBlue cow prefers clover.\n')
    names=('cow_cli','Godcmd','Keyword','Banwords','linkai','Role','Finish','Dungeon','Hello','tool')
    (ROOT/'disabled_plugins.json').write_text(json.dumps({'plugins':{n:{'enabled':False,'priority':0,'desc':'Disabled fixture extension'} for n in names}}))
    config={'channel_type':'web','web_host':'127.0.0.1','web_port':PORT,'web_console':True,'self_evolution_enabled':False,'agent_workspace':str(ROOT/'workspace'),'model':'fixture-model','bot_type':'openai','agent_permission_mode':'read-only','agent_delegation':{'enabled':True},'mcp_servers':[]}
    (ROOT/'data/config.json').write_text(json.dumps(config))
    (ROOT/'rehearsal.sb').write_text('(version 1)\n(allow default)\n(deny network-outbound)\n(deny file-read* file-write* (subpath "/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData") (subpath "/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime"))\n')
    source(LEGACY)
    subprocess.run(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,str(FIX/'seed_fixture.py'),str(ROOT)],cwd=ROOT/'deployment',env=ENV,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    ids=json.loads((ROOT/'fixture_ids.json').read_text())
    launch('legacy')
    before=database_snapshot(ROOT/'workspace');backup(ROOT/'workspace',ROOT/'workspace-backup');backup(ROOT/'data',ROOT/'data-backup')
    assert set(before)=={'memory/long-term/index.db','memory/recovery/tasks.db','agents/testpilot/memory/long-term/index.db','agents/testpilot2/memory/long-term/index.db'}
    REPORT['closed_interval_backup_databases']=before
    source(CANDIDATE);launch('candidate',True)
    REPORT['candidate_database_digests']=database_snapshot(ROOT/'workspace')
    # Restore the entire closed-interval file set and SQLite snapshots, not source alone.
    shutil.rmtree(ROOT/'workspace');shutil.copytree(ROOT/'workspace-backup',ROOT/'workspace')
    shutil.rmtree(ROOT/'data');shutil.copytree(ROOT/'data-backup',ROOT/'data')
    assert database_snapshot(ROOT/'workspace')==before
    source(FALLBACK);launch('fallback')
    REPORT['fallback_database_digests']=database_snapshot(ROOT/'workspace')
    REPORT['fallback_matches_backup']=REPORT['fallback_database_digests']==before
    assert REPORT['fallback_matches_backup']
    assert (ROOT/'workspace/memory/MEMORY.md').read_text()=='# Fictional memory\nBlue cow prefers clover.\n'
    REPORT['fictional_memory_file_preserved']=True
    with sqlite3.connect(ROOT/'workspace/memory/long-term/index.db') as db:
        assert db.execute("select count(*) from chunks where id=?",(ids['chunk'],)).fetchone()[0]==1
        assert db.execute("select count(*) from files where path='MEMORY.md'").fetchone()[0]==1
    with sqlite3.connect(ROOT/'workspace/memory/recovery/tasks.db') as db:
        assert db.execute("select count(*) from recovery_verifications where verification_id=?",(ids['verification'],)).fetchone()[0]==1
    for agent in ('testpilot','testpilot2'):
        with sqlite3.connect(ROOT/'workspace/agents'/agent/'memory/long-term/index.db') as db:
            rows=db.execute('select id,text,hash from chunks').fetchall()
            assert rows==[(ids[agent+'_chunk'],'Fictional memory for '+agent,'fictional-'+agent)]
            assert db.execute('select path,hash from files').fetchall()==[('MEMORY.md','fictional-'+agent)]
    REPORT['per_agent_scopes_preserved']=['testpilot','testpilot2']
    REPORT['indexed_memory_and_verification_preserved']=True
    REPORT['status']='passed'

try: main()
except Exception as e:
    REPORT['status']='failed';REPORT['error']=repr(e)
    raise
finally:
    (ROOT/'result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('private rehearsal root:',ROOT,flush=True)
