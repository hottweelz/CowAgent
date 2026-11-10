#!/usr/bin/env python3
"""Run frozen candidate process, real operator CLI and fictional plugin work.

Usage: python integration_rehearsal.py FULL_FROZEN_COMMIT
All generated files and processes are private fixtures. No live data is read.
"""
import hashlib
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OLD=REPO/'docs/first-bootstrap-001'
PYTHON='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python'
LEGACY='90c3cd8f72ffe7a47cb20925fa538eda479317c6'
FALLBACK='f659349785acf98905901a5cc53921436a109dbc'
assert len(sys.argv)==2 and len(sys.argv[1])==40 and all(c in '0123456789abcdef' for c in sys.argv[1])
CANDIDATE=sys.argv[1]
ROOT=Path(tempfile.mkdtemp(prefix='cow-bootstrap-002-')).resolve();PORT=19890
assert PORT!=9899 and ROOT.is_relative_to(Path('/private/var/folders'))
os.chmod(ROOT,0o700)
for name in ('data','home','workspace','request','responses','deployment','control'):
    (ROOT/name).mkdir(mode=0o700)
ENV={'PATH':str(Path(PYTHON).parent)+':/usr/bin:/bin','HOME':str(ROOT/'home'),'COW_DATA_DIR':str(ROOT/'data'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8','BROWSER':'true'}
ENABLED=('cow_cli','Godcmd','Keyword','Banwords','linkai','Role','Finish')
REPORT={'schema':'cow.bootstrap.integration/1','candidate':CANDIDATE,'legacy':LEGACY,'fallback':FALLBACK,'port':PORT,'steps':[], 'limits':['Fictional state only; legacy commit is modeled and does not attest live loaded modules.','BROWSER=true; no actual browser launch.','Real Keyword callback invokes a fixture requests.get stand-in; no real model, network request or provider effect.','Private same-UID control is not a human-presence check.','Snapshot restore would discard later changes and cannot undo external effects.']}


def source(commit, plugins_enabled):
    shutil.rmtree(ROOT/'deployment');(ROOT/'deployment').mkdir()
    tar=ROOT/'source.tar'
    with tar.open('wb') as stream:subprocess.run(['git','archive',commit],cwd=REPO,stdout=stream,check=True)
    with tarfile.open(tar) as stream:stream.extractall(ROOT/'deployment',filter='data')
    tar.unlink()
    names=(*ENABLED,'Dungeon','Hello','tool')
    config={'plugins':{name:{'enabled':plugins_enabled and name in ENABLED,'priority':100 if name=='Keyword' else 0,'desc':'fictional'} for name in names}}
    (ROOT/'deployment/plugins/plugins.json').write_text(json.dumps(config))


def snapshots(root):
    hashes={}
    for path in sorted(root.rglob('*.db')):
        with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
            assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
            hashes[str(path.relative_to(root))]=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
    return hashes


def backup(src,dst):
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns('*.db','*.db-wal','*.db-shm','*.db-journal','run.log','*.pid'))
    for db in src.rglob('*.db'):
        target=dst/db.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as a,sqlite3.connect(target) as b:a.backup(b)
    assert snapshots(src)==snapshots(dst)


def health(process):
    end=time.monotonic()+60
    while time.monotonic()<end:
        if process.poll() is not None:raise RuntimeError('process exited before health')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health',timeout=1) as response:
                if json.load(response)['status']=='ok':return
        except (OSError,ValueError):pass
        time.sleep(.1)
    raise RuntimeError('health timeout')


def command(process,action):
    identifier=uuid.uuid4().hex
    process.stdin.write(json.dumps({'id':identifier,'action':action})+'\n');process.stdin.flush()
    path=ROOT/'responses'/f'{identifier}.json';end=time.monotonic()+12
    while time.monotonic()<end:
        if path.exists():
            try:result=json.loads(path.read_text())
            except ValueError:time.sleep(.02);continue
            assert 'error_type' not in result,result
            return result
        if process.poll() is not None:raise RuntimeError('fixture controller exited')
        time.sleep(.02)
    raise RuntimeError('fixture command timed out')


def operator(timeout):
    cp=subprocess.run(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,'scripts/maintenance_drain.py','--control-dir',str(ROOT/'control'),'--grant','close-admission-and-observe','--timeout',str(timeout)],cwd=ROOT/'deployment',env=ENV,capture_output=True,text=True,timeout=timeout+15)
    result=json.loads(cp.stdout);assert cp.returncode in (0,1),(cp.returncode,result)
    assert (ROOT/'control'/('receipt-'+result['request_id']+'.json')).is_file()
    return result


def launch(label,candidate=False,unsupported=False):
    step={'name':label};REPORT['steps'].append(step)
    if candidate:
        subprocess.run(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,str(ROOT/'make_request.py')],cwd=ROOT/'deployment',env=ENV,check=True)
    with (ROOT/(label+'.log')).open('wb') as log:
        process=subprocess.Popen(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,str(ROOT/'controller.py') if candidate else 'app.py'],cwd=ROOT/'deployment',env=ENV,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        try:
            health(process);step.update(health='200/ok',pid=process.pid)
            if candidate:
                observed=json.loads((ROOT/'request/observation.json.receipt.json').read_text())
                assert observed['pid']==process.pid and not observed['dispatch_permitted'] and not observed['adapter_contact']
                assert [item['target_id'] for item in observed['inventory']]==['default','testpilot','testpilot2']
                assert all(item['selection']['status']=='denied' for item in observed['decisions'])
                assert not (ROOT/'request/observation.json').exists()
                step['observer']={'ids':[item['target_id'] for item in observed['inventory']],'denied':True,'dispatch_permitted':False,'adapter_contact':False,'runtime_epoch':observed['initialization_epoch'],'manifest_sha256':observed['manifest_sha256']}
                if unsupported:
                    command(process,'unsupported');response=operator(1)
                    assert response['closed'] and not response['drained'] and 'plugin_runtime_untracked' in response['blockers']
                    step['unsupported']=response
                else:
                    command(process,'hold');first=operator(.2)
                    assert first['closed'] and not first['drained'] and first['active'].get('plugins',0)>0
                    try:
                        urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{PORT}/message',data=b'{}',headers={'Content-Type':'application/json'}),timeout=2)
                        raise AssertionError('closed admission accepted')
                    except urllib.error.HTTPError as exc:assert exc.code==503
                    health(process)
                    assert command(process,'release')['completed']
                    second=operator(8)
                    assert second['closed'] and second['drained'] and not second['active']
                    assert first['binding']==second['binding'] and first['binding']['pid']==process.pid
                    assert first['binding']['runtime_epoch']==observed['initialization_epoch']
                    assert first['request_id']!=second['request_id']
                    step.update(while_held=first,closed_http_status=503,health_after_close='200/ok',after_completion=second)
        finally:
            if process.poll() is None:process.send_signal(signal.SIGTERM)
            step['exit_code']=process.wait(timeout=20);process.stdin.close()
        assert step['exit_code']==0


def reset_candidate():
    shutil.rmtree(ROOT/'control');(ROOT/'control').mkdir(mode=0o700)
    for f in (ROOT/'request').iterdir():f.unlink()
    source(CANDIDATE,True)


def main():
    with socket.socket() as sock:sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',PORT))
    shutil.copy2(HERE/'controller_integration_fixture.py',ROOT/'controller.py')
    shutil.copy2(OLD/'request_fixture.py',ROOT/'make_request.py')
    (ROOT/'workspace/agents').mkdir();(ROOT/'workspace/memory').mkdir()
    agents=[{'id':name,'name':'Fixture '+name,'model':'fixture-'+name,'bot_type':'openai'} for name in ('default','testpilot','testpilot2')]
    (ROOT/'workspace/agents/team.json').write_text(json.dumps({'agents':agents,'default_agent_id':'default'}))
    (ROOT/'workspace/memory/MEMORY.md').write_text('# Fictional memory\nBlue cow prefers clover.\n')
    (ROOT/'workspace/unknown-sentinel.txt').write_text('fictional independent file\n')
    config={'channel_type':'web','web_host':'127.0.0.1','web_port':PORT,'web_console':True,'self_evolution_enabled':False,'agent_workspace':str(ROOT/'workspace'),'model':'fixture-model','bot_type':'openai','agent_permission_mode':'read-only','agent_delegation':{'enabled':True},'mcp_servers':[],'linkai_api_key':'fictional-only'}
    (ROOT/'data/config.json').write_text(json.dumps(config))
    (ROOT/'rehearsal.sb').write_text('(version 1)\n(allow default)\n(deny network-outbound)\n(deny file-read* file-write* (subpath "/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData") (subpath "/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime"))\n')
    source(LEGACY,False)
    subprocess.run(['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON,str(OLD/'seed_fixture.py'),str(ROOT)],cwd=ROOT/'deployment',env=ENV,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    launch('legacy')
    before=snapshots(ROOT/'workspace');assert len(before)==4
    backup(ROOT/'workspace',ROOT/'workspace-backup');backup(ROOT/'data',ROOT/'data-backup')
    reset_candidate();launch('candidate',True)
    REPORT['candidate_database_digests']=snapshots(ROOT/'workspace')
    # A separate process is needed: close is irreversible and an unknown handler
    # must never be installed into the positive-drain process.
    shutil.rmtree(ROOT/'workspace');shutil.copytree(ROOT/'workspace-backup',ROOT/'workspace')
    shutil.rmtree(ROOT/'data');shutil.copytree(ROOT/'data-backup',ROOT/'data')
    reset_candidate();launch('unsupported',True,True)
    shutil.rmtree(ROOT/'workspace');shutil.copytree(ROOT/'workspace-backup',ROOT/'workspace')
    shutil.rmtree(ROOT/'data');shutil.copytree(ROOT/'data-backup',ROOT/'data')
    source(FALLBACK,False);launch('fallback')
    after=snapshots(ROOT/'workspace');assert after==before
    assert (ROOT/'workspace/unknown-sentinel.txt').read_text()=='fictional independent file\n'
    REPORT.update(snapshot=before,fallback_snapshot=after,unknown_file_preserved=True,status='passed')


try:main()
except Exception as exc:
    REPORT.update(status='failed',error_type=type(exc).__name__)
    raise
finally:
    (ROOT/'integration-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('private rehearsal root:',ROOT,flush=True)
