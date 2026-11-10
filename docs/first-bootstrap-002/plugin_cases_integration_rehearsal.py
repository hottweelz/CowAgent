#!/usr/bin/env python3
"""Fictional seven-plugin neutral callbacks against a fresh frozen service."""
import json,os,signal,socket,subprocess,tarfile,tempfile,time,urllib.request,uuid
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OLD=REPO/'docs/first-bootstrap-001'
PYTHON='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python'
CANDIDATE='f59a6e91152900d709cad1775b2756cf25b316c0'
ROOT=Path(tempfile.mkdtemp(prefix='cow-bootstrap-002-cases-')).resolve();PORT=19890
assert PORT!=9899 and ROOT.is_relative_to(Path('/private/var/folders'))
os.chmod(ROOT,0o700)
for name in ('data','home','workspace','request','responses','deployment','control'):(ROOT/name).mkdir(mode=0o700)
ENV={'PATH':str(Path(PYTHON).parent)+':/usr/bin:/bin','HOME':str(ROOT/'home'),'COW_DATA_DIR':str(ROOT/'data'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8','BROWSER':'true'}
ENABLED=('cow_cli','Godcmd','Keyword','Banwords','linkai','Role','Finish')
REPORT={'schema':'cow.bootstrap.plugin-neutral-cases/1','candidate':CANDIDATE,'port':PORT,'scope':'Actual manager and registered callbacks; neutral VOICE input reaches each selected callback guard, no commands or provider execution. Fixture temporarily selects one registered listener at a time.','limits':['VOICE callbacks cover neutral guard paths only, not text commands, child workers, network actions, or every plugin event.','BROWSER=true; network outbound and identified live data paths denied.','Same-UID control does not prove human authorization or legacy quiescence.']}


def command(process,action):
    identifier=uuid.uuid4().hex;process.stdin.write(json.dumps({'id':identifier,'action':action})+'\n');process.stdin.flush()
    path=ROOT/'responses'/f'{identifier}.json';deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        if path.exists():
            try:r=json.loads(path.read_text())
            except ValueError:time.sleep(.02);continue
            assert 'error_type' not in r,r
            return r['cases']
        if process.poll() is not None:raise RuntimeError('controller exited')
        time.sleep(.02)
    raise RuntimeError('controller timeout')


def main():
    with socket.socket() as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',PORT))
    archive=ROOT/'source.tar'
    with archive.open('wb') as f:subprocess.run(['git','archive',CANDIDATE],cwd=REPO,stdout=f,check=True)
    with tarfile.open(archive) as f:f.extractall(ROOT/'deployment',filter='data')
    names=(*ENABLED,'Dungeon','Hello','tool')
    config={'plugins':{n:{'enabled':n in ENABLED,'priority':0,'desc':'fictional'} for n in names}}
    (ROOT/'deployment/plugins/plugins.json').write_text(json.dumps(config))
    (ROOT/'workspace/agents').mkdir();agents=[{'id':n,'name':'Fixture '+n,'model':'fixture-'+n,'bot_type':'openai'} for n in ('default','testpilot','testpilot2')]
    (ROOT/'workspace/agents/team.json').write_text(json.dumps({'agents':agents,'default_agent_id':'default'}))
    config={'channel_type':'web','web_host':'127.0.0.1','web_port':PORT,'web_console':True,'self_evolution_enabled':False,'agent_workspace':str(ROOT/'workspace'),'model':'fixture-model','bot_type':'openai','agent_delegation':{'enabled':True},'mcp_servers':[],'linkai_api_key':'fictional-only'}
    (ROOT/'data/config.json').write_text(json.dumps(config))
    (ROOT/'rehearsal.sb').write_text('(version 1)\n(allow default)\n(deny network-outbound)\n(deny file-read* file-write* (subpath "/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData") (subpath "/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime"))\n')
    import shutil
    shutil.copy2(HERE/'plugin_cases_integration_fixture.py',ROOT/'controller.py');shutil.copy2(OLD/'request_fixture.py',ROOT/'make_request.py')
    base=['/usr/bin/sandbox-exec','-f',str(ROOT/'rehearsal.sb'),PYTHON]
    subprocess.run(base+[str(ROOT/'make_request.py')],cwd=ROOT/'deployment',env=ENV,check=True)
    with (ROOT/'candidate.log').open('wb') as log:
        process=subprocess.Popen(base+[str(ROOT/'controller.py')],cwd=ROOT/'deployment',env=ENV,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        try:
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('service exited')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health',timeout=1) as response:
                        if json.load(response)['status']=='ok':break
                except (OSError,ValueError):time.sleep(.1)
            else:raise RuntimeError('health timeout')
            REPORT['pid']=process.pid;REPORT['admitted_cases']=command(process,'admitted')
            cp=subprocess.run(base+['scripts/maintenance_drain.py','--control-dir',str(ROOT/'control'),'--grant','close-admission-and-observe','--timeout','8'],cwd=ROOT/'deployment',env=ENV,capture_output=True,text=True,timeout=20)
            receipt=json.loads(cp.stdout);assert cp.returncode==0 and receipt['closed'] and receipt['drained'] and not receipt['blockers']
            assert receipt['binding']['pid']==process.pid
            REPORT['drain_receipt']=receipt;REPORT['closed_cases']=command(process,'closed')
            REPORT['status']='passed'
        finally:
            if process.poll() is None:process.send_signal(signal.SIGTERM)
            REPORT['exit_code']=process.wait(timeout=20);process.stdin.close()
        assert REPORT['exit_code']==0

try:main()
except Exception as exc:
    REPORT.update(status='failed',error_type=type(exc).__name__)
    raise
finally:
    (ROOT/'result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('private rehearsal root:',ROOT,flush=True)
