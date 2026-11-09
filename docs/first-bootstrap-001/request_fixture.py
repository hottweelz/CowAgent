import hashlib,json,os,sys,time,uuid
from pathlib import Path
root=Path(__file__).parent
sys.path.insert(0,str(root/'deployment'))
from agent.discovery.startup_observer import source_manifest,PROTOCOL
now=time.time(); request=root/'request/observation.json'
requirements=[]
for agent in ('testpilot','testpilot2'):
 requirements.append(dict(protocol='cow.discovery.task/1',task_id=str(uuid.uuid4()),policy_id='safe-default',category='analysis',input_contract='fictional_records.v1',output_contract='analysis_report.v1',persistent_memory='prohibited',persistent_context='prohibited',required_tools=[],max_authority=['fs.read','time','analyze_records'],approval='prohibited',verification='none',recovery='frozen_authority',cancellation='cooperative',deadline=now+240,timeout_seconds=20.0,concurrency=1,permitted_mechanisms=['native_isolated'],prohibited_mechanisms=[],task_spec_hash=hashlib.sha256(b'fictional no-model lifecycle observation').hexdigest(),requested_agent_id=agent))
value=dict(protocol=PROTOCOL,request_id=uuid.uuid4().hex,request_path=str(request),issued_at=now,expires_at=now+240,uid=os.getuid(),manifest=source_manifest(),interpreter={'executable':os.path.abspath(sys.executable),'prefix':os.path.abspath(sys.prefix)},data_root=str(root/'data'),contact_authorized=False,bindings=[],requirements=requirements)
fd=os.open(request,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as out:json.dump(value,out,sort_keys=True)
