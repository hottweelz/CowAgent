#!/usr/bin/env python3
"""Observe normal candidate plugin discovery with no prior plugin config."""
import json,os,signal,shutil,subprocess,sys,tarfile,time,urllib.request,uuid
from pathlib import Path
R=Path(sys.argv[1]).resolve();assert R.is_relative_to(Path('/private/var/folders')) and R.name.startswith('cow-first-bootstrap-') and R.stat().st_uid==os.getuid() and (R/'result.json').is_file()
P='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python'
E={'PATH':str(Path(P).parent)+':/usr/bin:/bin','HOME':str(R/'home'),'COW_DATA_DIR':str(R/'data'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8','BROWSER':'true'}
shutil.rmtree(R/'deployment');(R/'deployment').mkdir()
with (R/'candidate.tar').open('wb') as f:subprocess.run(['git','archive','8d182026be2380fc574eeecd13edcffa5ed1dcb1'],cwd=Path(__file__).resolve().parents[2],stdout=f,check=True)
with tarfile.open(R/'candidate.tar') as f:f.extractall(R/'deployment',filter='data')
# Copy fictional metadata, then apply only the observed enablement booleans.
shutil.copy2(R/'disabled_plugins.json',R/'deployment/plugins/plugins.json')
p=R/'deployment/plugins/plugins.json'; config=json.loads(p.read_text())
enabled={'cow_cli','Godcmd','Keyword','Banwords','linkai','Role','Finish'}
for name,value in config['plugins'].items(): value['enabled']=name in enabled
p.write_text(json.dumps(config))
# Fictional local placeholder only; never a live credential.
p=R/'data/config.json';config=json.loads(p.read_text());config['linkai_api_key']='fictional-only';p.write_text(json.dumps(config))
(R/'request/observation.json.receipt.json').unlink(missing_ok=True)
command=['/usr/bin/sandbox-exec','-f',str(R/'rehearsal.sb'),P]
subprocess.run(command+[str(R/'make_request.py')],cwd=R/'deployment',env=E,check=True)
with (R/'plugins.log').open('wb') as log:
 p=subprocess.Popen(command+[str(R/'driver.py')],cwd=R/'deployment',env=E,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
 try:
  end=time.monotonic()+60
  while time.monotonic()<end:
   if p.poll() is not None:raise RuntimeError('plugin fixture exited')
   try:
    with urllib.request.urlopen('http://127.0.0.1:19886/api/health',timeout=1) as q:
     if json.load(q)['status']=='ok':break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('health timeout')
  key=uuid.uuid4().hex;p.stdin.write(json.dumps({'id':key,'action':'drain','timeout':1})+'\n');p.stdin.flush()
  path=R/'responses'/f'{key}.json';end=time.monotonic()+10
  while not path.exists() and time.monotonic()<end:time.sleep(.05)
  reply=json.loads(path.read_text());assert 'receipt' in reply,reply
  receipt=reply['receipt'];assert not receipt['drained'] and receipt['blockers']
  result={'health':'200/ok','drained':receipt['drained'],'blockers':receipt['blockers'],'requested_enabled':sorted(enabled)}
 finally:
  if p.poll() is None:p.send_signal(signal.SIGTERM)
  result_exit=p.wait(timeout=20);p.stdin.close()
assert result_exit==0
result['exit_code']=result_exit
(R/'plugins-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
