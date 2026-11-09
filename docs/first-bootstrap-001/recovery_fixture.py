#!/usr/bin/env python3
"""Additional disposable WAL and interrupted-startup checks for a finished rehearsal."""
import json, os, signal, sqlite3, subprocess, sys, time, urllib.request
from pathlib import Path
R=Path(sys.argv[1]).resolve()
assert R.is_relative_to(Path('/private/var/folders')) and R.name.startswith('cow-first-bootstrap-') and R.stat().st_uid==os.getuid() and (R/'result.json').is_file()
P='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python'
E={'PATH':str(Path(P).parent)+':/usr/bin:/bin','HOME':str(R/'home'),'COW_DATA_DIR':str(R/'data'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8','BROWSER':'true'}
report={}
# Keep a live reader and writer open so committed frames remain in WAL.
db=R/'wal-test.db'
for name in ('wal-test.db','wal-test.db-wal','wal-test.db-shm','wal-backup.db'):(R/name).unlink(missing_ok=True)
writer=sqlite3.connect(db); writer.execute('pragma journal_mode=wal');writer.execute('pragma wal_autocheckpoint=0')
writer.execute('create table evidence(value text)');writer.commit()
reader=sqlite3.connect(db);reader.execute('begin');reader.execute('select * from evidence').fetchall()
writer.execute("insert into evidence values('committed')");writer.commit()
writer.execute('begin immediate');writer.execute("insert into evidence values('pending')")
assert (R/'wal-test.db-wal').stat().st_size>0
with sqlite3.connect(db) as source, sqlite3.connect(R/'wal-backup.db') as dest: source.backup(dest)
with sqlite3.connect(R/'wal-backup.db') as b:
    assert b.execute('pragma integrity_check').fetchone()[0]=='ok'
    assert b.execute('select value from evidence').fetchall()==[('committed',)]
writer.rollback();writer.close();reader.close();report['wal']='online backup includes committed WAL frame and excludes uncommitted transaction'
# Run actual candidate in the same isolated deployment. Interrupt after team
# migration returns and before conversation migration starts, then restart.
with (R/'candidate.tar').open('wb') as f: subprocess.run(['git','archive','8d182026be2380fc574eeecd13edcffa5ed1dcb1'],cwd=Path(__file__).resolve().parents[2],stdout=f,check=True)
import tarfile,shutil
shutil.rmtree(R/'deployment');(R/'deployment').mkdir()
with tarfile.open(R/'candidate.tar') as f:f.extractall(R/'deployment',filter='data')
shutil.copy2(R/'disabled_plugins.json',R/'deployment/plugins/plugins.json')
tracer=R/'interrupt.py'
tracer.write_text('''import os,runpy,signal,sys\nfrom pathlib import Path\ndef trace(frame,event,arg):\n if event == "call" and frame.f_code.co_name == "_migrate_conversations" and frame.f_code.co_filename.endswith("app.py"):\n  Path(os.environ["HOME"]).joinpath("interrupt-boundary").write_text("team-returned-before-conversation")\n  os.kill(os.getpid(),signal.SIGTERM)\n return trace\nsys.path.insert(0,os.getcwd())\nsys.settrace(trace)\nrunpy.run_path("app.py",run_name="__main__")\n''')
command=['/usr/bin/sandbox-exec','-f',str(R/'rehearsal.sb'),P]
with (R/'interrupted.log').open('wb') as log:
    p=subprocess.Popen(command+[str(tracer)],cwd=R/'deployment',env=E,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try: code=p.wait(timeout=45)
    except subprocess.TimeoutExpired:
        p.send_signal(signal.SIGTERM);p.wait(timeout=15);raise
assert code==-signal.SIGTERM and (R/'home/interrupt-boundary').exists()
report['interruption']='SIGTERM after team migration returned, immediately before conversation migration; no claim of mid-transaction crash'
with (R/'restart.log').open('wb') as log:
    p=subprocess.Popen(command+['app.py'],cwd=R/'deployment',env=E,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        end=time.monotonic()+60
        while time.monotonic()<end:
            if p.poll() is not None:raise RuntimeError('restart exited')
            try:
                with urllib.request.urlopen('http://127.0.0.1:19886/api/health',timeout=1) as response:
                    if json.load(response)['status']=='ok':break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('restart health timeout')
        report['restart_health']='200/ok'
    finally:
        if p.poll() is None:p.send_signal(signal.SIGTERM)
        report['restart_exit']=p.wait(timeout=20)
assert report['restart_exit']==0
for p in (R/'workspace').rglob('*.db'):
    with sqlite3.connect(p) as c:assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
assert (R/'workspace/memory/MEMORY.md').read_text()=='# Fictional memory\nBlue cow prefers clover.\n'
with sqlite3.connect(R/'workspace/memory/recovery/tasks.db') as c:
    assert c.execute("select state from recovery_tasks where task_id=?",(json.loads((R/'fixture_ids.json').read_text())['task'],)).fetchone()==('completed',)
report['post_restart']='SQLite integrity, fictional memory and completed recovery history verified'
(R/'extra-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
# Recover the last closed-interval snapshot and repeat the modeled fallback.
shutil.rmtree(R/'workspace');shutil.copytree(R/'workspace-backup',R/'workspace')
shutil.rmtree(R/'data');shutil.copytree(R/'data-backup',R/'data')
shutil.rmtree(R/'deployment');(R/'deployment').mkdir()
with (R/'legacy.tar').open('wb') as f:subprocess.run(['git','archive','f659349785acf98905901a5cc53921436a109dbc'],cwd=Path(__file__).resolve().parents[2],stdout=f,check=True)
with tarfile.open(R/'legacy.tar') as f:f.extractall(R/'deployment',filter='data')
shutil.copy2(R/'disabled_plugins.json',R/'deployment/plugins/plugins.json')
with (R/'fallback-repeat.log').open('wb') as log:
 p=subprocess.Popen(command+['app.py'],cwd=R/'deployment',env=E,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  end=time.monotonic()+60
  while time.monotonic()<end:
   if p.poll() is not None:raise RuntimeError('fallback exited')
   try:
    with urllib.request.urlopen('http://127.0.0.1:19886/api/health',timeout=1) as response:
     if json.load(response)['status']=='ok':break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('fallback health timeout')
 finally:
  if p.poll() is None:p.send_signal(signal.SIGTERM)
  code=p.wait(timeout=20)
assert code==0
for src in (R/'workspace-backup').rglob('*.db'):
 target=R/'workspace'/src.relative_to(R/'workspace-backup')
 with sqlite3.connect(src) as a,sqlite3.connect(target) as b:
  assert a.execute('pragma integrity_check').fetchone()[0]=='ok' and b.execute('pragma integrity_check').fetchone()[0]=='ok'
  assert '\n'.join(a.iterdump())=='\n'.join(b.iterdump())
assert (R/'workspace/memory/MEMORY.md').read_bytes()==(R/'workspace-backup/memory/MEMORY.md').read_bytes()
report['fallback_repeat']='restored closed-interval backup; health 200; exit 0; SQLite logical dumps and fictional memory match'
(R/'extra-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'fallback_repeat':report['fallback_repeat']}))
