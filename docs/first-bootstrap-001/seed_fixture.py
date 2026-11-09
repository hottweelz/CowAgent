"""Create fresh fictional conversation, memory and recovery state using native schemas."""
import json,sqlite3,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from agent.memory.conversation_store import ConversationStore
from agent.memory.storage import MemoryChunk,MemoryStorage
from agent.recovery.store import TaskStore
root=Path(sys.argv[1]); workspace=root/'workspace'; index=workspace/'memory/long-term/index.db'
ids={key:str(uuid.uuid4()) for key in ('task','attempt','effect','verification','session','chunk','testpilot_chunk','testpilot2_chunk')}
(root/'fixture_ids.json').write_text(json.dumps(ids))
for agent in ('default','testpilot','testpilot2'):
    store=ConversationStore(index,agent_id='' if agent=='default' else agent)
    assert store.append_messages(str(uuid.uuid4()),[{'role':'user','content':'Fictional clover note.'}],channel_type='web')
mem=MemoryStorage(index)
mem.save_chunk(MemoryChunk(id=ids['chunk'],user_id=None,scope='shared',source='memory',path='MEMORY.md',start_line=1,end_line=2,text='Blue cow prefers clover.',embedding=None,hash='fictional-hash'))
mem.update_file_metadata('MEMORY.md','memory','fictional-hash',1,30);mem.close()
for agent in ('testpilot','testpilot2'):
    agent_root=workspace/'agents'/agent
    (agent_root/'memory/long-term').mkdir(parents=True)
    path=agent_root/'memory/long-term/index.db'
    memory=MemoryStorage(path)
    memory.save_chunk(MemoryChunk(id=ids[agent+'_chunk'],user_id=None,scope='shared',source='memory',path='MEMORY.md',start_line=1,end_line=1,text='Fictional memory for '+agent,embedding=None,hash='fictional-'+agent))
    memory.update_file_metadata('MEMORY.md','memory','fictional-'+agent,1,25)
    memory.close()
TaskStore(workspace/'memory/recovery/tasks.db')
with sqlite3.connect(workspace/'memory/recovery/tasks.db') as db:
 db.execute("INSERT INTO recovery_tasks(task_id,owner_id,session_id,kind,spec,state,attempt_id,attempt_count,generation,result) VALUES(?,?,?,?,?,?,?,?,?,?)",(ids['task'],'default',ids['session'],'fixture','{}','completed',ids['attempt'],1,1,'{}'))
 db.execute("INSERT INTO recovery_attempts(attempt_id,task_id,number,state,ended_at) VALUES(?,?,?,?,?)",(ids['attempt'],ids['task'],1,'completed','2026-01-01'))
 db.execute("INSERT INTO recovery_verifications(verification_id,task_id,attempt_id,contract_hash,report,observed_at) VALUES(?,?,?,?,?,?)",(ids['verification'],ids['task'],ids['attempt'],'fictional-contract','{}','2026-01-01'))
 db.execute("INSERT INTO recovery_effects(effect_id,attempt_id,name,mutating,result,completed_at) VALUES(?,?,?,?,?,?)",(ids['effect'],ids['attempt'],'fictional',0,'{}','2026-01-01'))
