"""Pause only this fictional launch after control binding, before observation."""
import runpy
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parent
source=root/'deployment'
sys.path.insert(0,str(source))

def pause(frame,event,arg):
    if (event=='call' and frame.f_code.co_name=='observe_and_publish'
            and Path(frame.f_code.co_filename).resolve()==source/'agent/discovery/startup_observer.py'):
        assert (root/'control-old/service.json').is_file()
        (root/'bound-before-observation').write_text('fixture boundary reached')
        while True:time.sleep(.05)
    return pause

sys.settrace(pause)
sys.argv=[str(source/'scripts/discovery_startup.py'),'--request',str(root/'request/observation.json'),'--control-dir',str(root/'control-old')]
runpy.run_path(str(source/'scripts/discovery_startup.py'),run_name='__main__')
