"""Private fixture-only control of a real plugin callback; no production endpoint."""
import json
import runpy
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

root=Path(__file__).resolve().parent
source=root/'deployment'
sys.path.insert(0,str(source))


def controller():
    while not (root/'control/service.json').exists():
        time.sleep(.02)
    import requests
    from bridge.context import Context, ContextType
    from plugins import instance as manager
    from plugins.event import Event, EventAction, EventContext
    entered=threading.Event(); release=threading.Event(); completed=threading.Event()
    original=requests.get
    threads=[]; errors=[]

    def fake_get(url,**kwargs):
        assert url=='https://fictional.invalid/hold.pdf'
        entered.set()
        assert release.wait(30)
        return SimpleNamespace(status_code=503)

    def execute():
        try:
            context=Context(ContextType.TEXT,'fixture-hold')
            event=manager.emit_event(EventContext(Event.ON_HANDLE_CONTEXT,{'context':context}))
            assert event.is_pass() and event['reply'] is not None
        except Exception as exc:
            errors.append(type(exc).__name__)
        finally:
            completed.set()

    for line in sys.stdin:
        request=json.loads(line);result={'id':request['id']}
        try:
            if request['action']=='hold':
                assert {'COW_CLI','GODCMD','KEYWORD','BANWORDS','LINKAI','ROLE','FINISH'}.issubset(manager.instances)
                plugin=manager.instances['KEYWORD'];plugin.keyword['fixture-hold']='https://fictional.invalid/hold.pdf'
                requests.get=fake_get
                thread=threading.Thread(target=execute,daemon=True);threads.append(thread);thread.start()
                assert entered.wait(8) and not completed.is_set()
                result['held']=True
            elif request['action']=='release':
                release.set()
                for thread in threads:thread.join(8)
                assert completed.is_set() and not errors and all(not t.is_alive() for t in threads)
                requests.get=original;result['completed']=True
            elif request['action']=='unsupported':
                # Exercise runtime detection of an unknown instance handler.
                instance=manager.instances['KEYWORD']
                instance.handlers[Event.ON_HANDLE_CONTEXT]=lambda context: setattr(context,'action',EventAction.BREAK_PASS)
                manager.emit_event(EventContext(Event.ON_HANDLE_CONTEXT,{'context':Context(ContextType.TEXT,'fixture-unsupported')}))
                result['injected_unknown_handler']=True
            else:
                raise ValueError('unknown_action')
        except Exception as exc:
            result['error_type']=type(exc).__name__
        path=root/'responses'/f"{request['id']}.json"
        path.write_text(json.dumps(result))
    release.set()

threading.Thread(target=controller,daemon=True).start()
sys.argv=[str(source/'scripts/discovery_startup.py'),'--request',str(root/'request/observation.json'),'--control-dir',str(root/'control')]
runpy.run_path(str(source/'scripts/discovery_startup.py'),run_name='__main__')
