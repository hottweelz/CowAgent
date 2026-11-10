"""Select and observe seven real neutral callbacks in one private service."""
import json
import runpy
import sys
import threading
import time
from pathlib import Path

root=Path(__file__).resolve().parent
source=root/'deployment'
sys.path.insert(0,str(source))


def control():
    while not (root/'control/service.json').exists():
        time.sleep(.02)
    from bridge.context import Context, ContextType
    from common.runtime_drain import AdmissionClosed, current
    from plugins import instance as manager
    from plugins.event import Event, EventContext
    names=['COW_CLI','GODCMD','KEYWORD','BANWORDS','LINKAI','ROLE','FINISH']
    for line in sys.stdin:
        request=json.loads(line); output={'id':request['id'],'cases':{}}
        original=list(manager.listening_plugins[Event.ON_HANDLE_CONTEXT])
        try:
            for name in names:
                instance=manager.instances[name]
                function=instance.handlers[Event.ON_HANDLE_CONTEXT].__func__
                manager.listening_plugins[Event.ON_HANDLE_CONTEXT]=[name]
                observed=[]
                def trace(frame,event,arg):
                    if event=='call' and frame.f_code is function.__code__:
                        observed.append(current().snapshot()['active'].get('plugins',0))
                event=EventContext(Event.ON_HANDLE_CONTEXT,{'context':Context(ContextType.VOICE,'fictional-neutral')})
                sys.setprofile(trace)
                try:
                    manager.emit_event(event)
                    assert request['action']=='admitted' and observed and min(observed)>=1
                    output['cases'][name]={'callback_entered':True,'lease_observed':True}
                except AdmissionClosed:
                    assert request['action']=='closed' and not observed
                    output['cases'][name]={'callback_entered':False,'admission_closed':True}
                finally:
                    sys.setprofile(None)
        except Exception as exc:
            output['error_type']=type(exc).__name__
        finally:
            manager.listening_plugins[Event.ON_HANDLE_CONTEXT]=original
        (root/'responses'/f"{request['id']}.json").write_text(json.dumps(output))

threading.Thread(target=control,daemon=True).start()
sys.argv=[str(source/'scripts/discovery_startup.py'),'--request',str(root/'request/observation.json'),'--control-dir',str(root/'control')]
runpy.run_path(str(source/'scripts/discovery_startup.py'),run_name='__main__')
