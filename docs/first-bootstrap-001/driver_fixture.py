"""Owned disposable test controller; not a shipped maintenance endpoint."""
import json,os,runpy,sys,threading
from pathlib import Path
root=Path(__file__).parent; source=root/'deployment'
sys.path.insert(0,str(source))
def control():
 held=[]; finishes=[]
 try:
  from common import runtime_drain,service_lifecycle
  for line in sys.stdin:
   command=json.loads(line); result={"id":command['id'],"action":command['action']}
   try:
    coordinator=runtime_drain.current()
    if coordinator is None or coordinator._owner is None:raise RuntimeError('runtime_not_initialized')
    if command['action']=='hold':
     for agent in ('testpilot','testpilot2'):
      lease=coordinator.reserve('fictional_run',agent); done=threading.Event(); entered=threading.Event()
      def work(done=done,entered=entered):
       entered.set();done.wait()
      thread=threading.Thread(target=lease.run,args=(work,),daemon=True);thread.start()
      held.append(thread);finishes.append(done);assert entered.wait(2)
     result['receipt']=coordinator.snapshot()
    elif command['action']=='release':
     for event in finishes:event.set()
     for thread in held:thread.join(3)
     assert all(not thread.is_alive() for thread in held)
     result['released']=True
    elif command['action']=='drain':
     result['receipt']=service_lifecycle.drain(coordinator._owner.owner,float(command.get('timeout',2)))
    else:raise ValueError('unknown_action')
   except Exception as exc:result['error_type']=type(exc).__name__
   fd=os.open(root/'responses'/(command['id']+'.json'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(fd,'w') as out:json.dump(result,out,sort_keys=True)
 finally:
  for event in finishes:event.set()
threading.Thread(target=control,daemon=True,name='owned-fixture-controller').start()
sys.argv=[str(source/'scripts/discovery_startup.py'),'--request',str(root/'request/observation.json')]
runpy.run_path(str(source/'scripts/discovery_startup.py'),run_name='__main__')
