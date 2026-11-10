import json
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from agent.memory.conversation_store import ConversationStore
from agent.personal import collaboration as module
from agent.personal.collaboration import CollaborationService, _validate
from agent.registry import AgentProfile


@pytest.fixture
def setup(tmp_path, monkeypatch):
    owner = AgentProfile('owner', 'Owner', str(tmp_path / 'owner'), model='owner-model', bot_type='openai')
    target = AgentProfile('analyst', 'Analyst', str(tmp_path / 'analyst'), description='Research', model='model-x', bot_type='openai')
    profiles = {'owner': owner, 'analyst': target}
    class Registry:
        def get_addressed(self, key):
            p = profiles[key]
            if not p.enabled:
                raise ValueError('disabled')
            return p
        def list(self, include_disabled=False):
            return [p for p in profiles.values() if p.enabled or include_disabled]
    registry = Registry()
    native = ConversationStore(tmp_path / 'owner.db', agent_id='owner')
    native.append_messages('session', [{'role':'user','content':'Track news'}])
    import agent.personal.service as service
    monkeypatch.setattr(service, 'get_agent_registry', lambda: registry)
    monkeypatch.setattr(service, 'get_conversation_store', lambda workspace: native)
    monkeypatch.setattr(module, 'get_agent_registry', lambda: registry)
    obj = CollaborationService('owner','session')
    commitment = obj.store.create('session', {'objective':'Track news','endpoint':'https://example.com/news','read_authorized':True}, 0)
    cid = commitment['commitment_id']
    article = {'article_id':'one','headline':'A story', 'description':'Exact delivered source text.', 'publisher':'Pub','source_url':'https://example.com/one'}
    run = obj.store.claim_run(cid,'first')
    obj.store.complete_run(run['run_id'],[article],[article],'A briefing',{})
    return obj, cid, native, profiles, registry


def proposal(obj,cid):
    return obj.prepare(cid,'analyst',['one'],'Assess relevance',0)


def test_decision_revocation_and_binding(setup):
    obj,cid,_,profiles,_ = setup
    item = proposal(obj,cid)
    rid = item['research_id']
    assert obj.execute(rid,0)['status'] == 'pending'
    assert obj.decide(rid,'deny',0)['status'] == 'denied'
    assert obj.execute(rid,0)['status'] == 'denied'
    item = proposal(obj,cid); rid = item['research_id']
    assert obj.decide(rid,'approve',0)['status'] == 'approved'
    assert obj.decide(rid,'revoke',0)['status'] == 'denied'
    assert obj.execute(rid,0)['status'] == 'denied'
    item = proposal(obj,cid); rid = item['research_id']
    obj.decide(rid,'approve',0)
    obj.store.update('session',cid,{'priority':4},0,1)
    assert obj.execute(rid,0)['status'] == 'failed'
    item = proposal(obj,cid); rid = item['research_id']
    obj.decide(rid,'approve',0)
    profiles['analyst'] = AgentProfile('analyst','Changed',profiles['analyst'].workspace, model='model-x', bot_type='openai')
    assert obj.execute(rid,0)['status'] == 'failed'
    assert obj.prepare(cid,'missing',['one'],'Question',0)['status'] == 'unavailable'
    with pytest.raises(ValueError):
        obj.prepare(cid,'analyst',['invented'],'Question',0)


def test_atomic_claim_completion_and_restart(setup,monkeypatch):
    obj,cid,native,_,_ = setup
    rid = proposal(obj,cid)['research_id']
    obj.decide(rid,'approve',0)
    calls = []
    def run(p):
        calls.append(p['run_id'])
        time.sleep(.05)
        return {'findings':[]}, {'run_id':p['run_id'],'tool_count':0}
    monkeypatch.setattr(obj,'_run',run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:obj.execute(rid,0),range(2)))
    assert len(calls) == 1
    assert {r['status'] for r in results} <= {'executing','completed'}
    assert obj.execute(rid,0)['status'] == 'completed'
    restarted = CollaborationService('owner','session')
    assert restarted.execute(rid,0)['status'] == 'completed'
    conn = native._connect()
    assert conn.execute('SELECT COUNT(*) FROM messages WHERE run_id=?',(calls[0],)).fetchone()[0] == 1
    conn.close()
    rid = proposal(obj,cid)['research_id']; obj.decide(rid,'approve',0)
    monkeypatch.setattr(obj,'_run',lambda p: (_ for _ in ()).throw(TimeoutError()))
    assert obj.execute(rid,0)['status'] == 'uncertain'
    assert restarted.execute(rid,0)['status'] == 'uncertain'
    rid = proposal(obj,cid)['research_id']; obj.decide(rid,'approve',0)
    conn = native._connect()
    conn.execute("UPDATE personal_research SET status='executing',updated_at=? WHERE research_id=?",(int(time.time())-121,rid)); conn.commit(); conn.close()
    assert restarted.execute(rid,0)['status'] == 'uncertain'


def test_validation_exact_quotes_and_duplicate_keys():
    sources = {'one':{'headline':'Heading','description':'Exact quote here', 'content':'','publisher':'Pub','source_url':'https://example.com'}}
    item = {'source_id':'one','excerpt':'Exact quote','classification':'relevant','priority':'high'}
    result = _validate(json.dumps({'findings':[item]}),sources)
    assert result['findings'][0]['source_url'] == 'https://example.com'
    for bad in ('{"findings":[],"findings":[]}', json.dumps({'findings':[{**item,'excerpt':'invented'}]}),json.dumps({'findings':[{**item,'source_id':'fake'}]}),json.dumps({'findings':[{**item,'extra':'leak'}]})):
        with pytest.raises(ValueError):
            _validate(bad,sources)


def test_native_target_context_and_empty_tools(setup,monkeypatch,tmp_path):
    obj,cid,_,profiles,_ = setup
    target_store = ConversationStore(tmp_path/'target.db',agent_id='analyst')
    calls = []
    class Model:
        model = 'model-x'
        def _primary_provider_id(self, model): return 'openai'
        def call_stream(self, request):
            calls.append(request)
            assert request.tools == []
            assert request.messages[0]['content'] == 'Native target persona and memory'
            payload = json.dumps({'findings':[{'source_id':'one','excerpt':'Exact delivered','classification':'relevant','priority':'high'}]})
            return iter([{'choices':[{'delta':{'content':payload},'finish_reason':'stop'}]}])
    from common import state_dir
    target = profiles['analyst']
    db = state_dir.memory_index_db(base=target.workspace, ensure=False)
    class Native:
        model = Model()
        agent_profile = target
        workspace_dir = target.workspace
        messages = []
        skip_context_files = False
        memory_manager = SimpleNamespace(config=SimpleNamespace(get_workspace=lambda:target.workspace, get_db_path=lambda:db), storage=SimpleNamespace(db_path=db))
        def effective_permission_mode(self): return 'read-only'
        def get_full_system_prompt(self, **kw):
            assert kw == {'skill_filter':[], 'tools_override':[]}
            return 'Native target persona and memory'
    native_agent = Native()
    class Bridge:
        def get_cached_agent(self, sid, agent_id): return None
        def get_agent(self, sid, **kw):
            assert kw == {'agent_id':'analyst','host_agent_id':'analyst','permission_mode':'read-only'}
            return native_agent
        def sync_session_messages_from_store(self, sid, agent_id):
            assert agent_id == 'analyst'
            native_agent.messages = target_store.load_messages(sid)
            return len(native_agent.messages)
        def get_conversation_store(self, agent_id):
            assert agent_id == 'analyst'
            return target_store
    import bridge.bridge
    monkeypatch.setattr(bridge.bridge,'Bridge',lambda:SimpleNamespace(get_agent_bridge=lambda:Bridge()))
    rid = proposal(obj,cid)['research_id']; obj.decide(rid,'approve',0)
    result = obj.execute(rid,0)
    assert result['status'] == 'completed' and result['receipt']['tool_count'] == 0
    assert result['result']['findings'][0]['excerpt'] == 'Exact delivered'
    assert len(calls) == 1
    assert len(target_store.load_messages(result['receipt']['session_id'])) == 2
    assert len(native_agent.messages) == 2
    assert native_agent.messages[0]['role'] == 'user' and native_agent.messages[1]['role'] == 'assistant'
    native_agent.messages = []
    monkeypatch.setattr(Bridge,'sync_session_messages_from_store',lambda *args, **kwargs:-1)
    second = proposal(obj,cid)['research_id']; obj.decide(second,'approve',0)
    assert obj.execute(second,0)['status'] == 'uncertain'
    assert obj.execute(second,0)['status'] == 'uncertain' and len(calls) == 2


def test_expiry_isolation_and_late_change(setup, monkeypatch):
    obj,cid,native,_,_ = setup
    item = proposal(obj,cid); rid = item['research_id']
    conn = native._connect()
    conn.execute('UPDATE personal_research SET expires_at=? WHERE research_id=?',(int(time.time())-1,rid)); conn.commit(); conn.close()
    assert obj.decide(rid,'approve',0)['status'] == 'expired'
    assert obj.execute(rid,0)['status'] == 'expired'
    native.append_messages('other', [{'role':'user','content':'Other session'}])
    other = CollaborationService('owner','other')
    history = other.snapshot()['research']
    assert history[0]['research_id'] == rid and history[0]['source_session_id'] == 'session'
    assert history[0]['can_mutate'] is False
    with pytest.raises(ValueError):
        other.execute(rid,0)
    item = proposal(obj,cid); rid = item['research_id']; obj.decide(rid,'approve',0)
    def change_before_completion(p):
        obj.store.update('session',cid,{'priority':5},0,1)
        return {'findings':[]}, {'run_id':p['run_id'],'tool_count':0}
    monkeypatch.setattr(obj,'_run',change_before_completion)
    result = obj.execute(rid,0)
    assert result['status'] == 'failed' and result['result'] == {} and result['message_seq'] is None


def test_stream_rejects_tool_calls():
    from agent.personal.interpretation import _collect_stream, InterpretationError
    chunks = iter([{'choices':[{'delta':{'tool_calls':[{'id':'1'}]},'finish_reason':'tool_calls'}]}])
    with pytest.raises(InterpretationError):
        _collect_stream(chunks,time.monotonic()+1)


def test_process_restart_marks_claim_uncertain_without_replay(setup, monkeypatch):
    obj,cid,native,_,_ = setup
    rid = proposal(obj,cid)['research_id']
    obj.decide(rid,'approve',0)
    conn = native._connect()
    conn.execute("UPDATE personal_research SET status='executing',updated_at=?,process_nonce=? WHERE research_id=?",
                 (int(time.time()),module._PROCESS_NONCE,rid))
    conn.commit(); conn.close()
    assert obj.snapshot()['research'][0]['status'] == 'executing'
    monkeypatch.setattr(module,'_PROCESS_NONCE','new-process')
    monkeypatch.setattr(obj,'_run',lambda _:pytest.fail('abandoned action replayed'))
    assert obj.snapshot()['research'][0]['status'] == 'uncertain'
    assert obj.execute(rid,0)['status'] == 'uncertain'


def test_owner_message_renders_verified_findings(setup, monkeypatch):
    obj,cid,native,_,_ = setup
    rid = proposal(obj,cid)['research_id']; obj.decide(rid,'approve',0)
    def run(p):
        finding = {'source_id':'one','excerpt':'Exact delivered source text.','classification':'relevant',
                   'priority':'high','publisher':'Pub','source_url':'https://example.com/one'}
        return {'findings':[finding]}, {'run_id':p['run_id'],'tool_count':0}
    monkeypatch.setattr(obj,'_run',run)
    result = obj.execute(rid,0)
    conn = native._connect()
    raw = conn.execute('SELECT content FROM messages WHERE session_id=? AND seq=?',('session',result['message_seq'])).fetchone()[0]
    conn.close()
    content = json.loads(raw)
    assert 'Specialist research: Analyst' in content
    assert 'Relevant · High priority' in content and 'Exact delivered source text.' in content
    assert '[Pub](<https://example.com/one>)' in content
    assert '"findings"' not in content and 'not independently verified' in content


def test_default_target_uses_global_model(setup, monkeypatch):
    _,_,_,profiles,registry = setup
    import bridge.agent_bridge as agent_bridge
    registry.default_agent_id = 'analyst'
    profiles['analyst'] = AgentProfile('analyst','Analyst',profiles['analyst'].workspace,
                                       model='gpt-5.6-luna',bot_type='old-provider')
    monkeypatch.setattr(agent_bridge,'conf',lambda: {'model':'gpt-6-luna','bot_type':'openai'})
    target = module._target(profiles['analyst'])
    assert target['model'] == 'gpt-6-luna' and target['provider'] == 'openai'
    registry.default_agent_id = 'owner'
    assert module._target(profiles['analyst'])['model'] == 'gpt-5.6-luna'


def test_completed_history_owner_scope(setup,monkeypatch):
    from agent.memory.commitments import CommitmentStore
    obj,cid,native,profiles,_ = setup
    rid = proposal(obj,cid)['research_id']; obj.decide(rid,'approve',0)
    monkeypatch.setattr(obj,'_run',lambda p: ({'findings':[]},{'run_id':p['run_id'],'tool_count':0}))
    assert obj.execute(rid,0)['status'] == 'completed'
    native.append_messages('next',[{'role':'user','content':'Continue'}])
    next_chat = CollaborationService('owner','next')
    record = next(x for x in next_chat.snapshot()['research'] if x['research_id'] == rid)
    assert record['status'] == 'completed' and record['result'] == {'findings':[]}
    assert record['source_session_id'] == 'session' and not record['can_mutate']
    with pytest.raises(ValueError):
        next_chat.execute(rid,0)
    guest_store = ConversationStore(native._db_path, agent_id='analyst')
    guest_store.append_messages('guest',[{'role':'user','content':'Guest'}])
    guest = CollaborationService.__new__(CollaborationService)
    guest.profile, guest.session_id = profiles['analyst'], 'guest'
    guest.store = CommitmentStore(guest_store, owner_agent_id='analyst')
    assert guest.snapshot()['research'] == []
    with pytest.raises(ValueError):
        guest.execute(rid,0)


@pytest.mark.parametrize('escape', ['memory_db_symlink','memory_file_symlink','memory_file_hardlink','nested_root'])
def test_private_context_escape_fails_before_bridge(setup, monkeypatch, escape):
    import os
    from pathlib import Path
    obj,cid,_,profiles,registry = setup
    owner, target = Path(profiles['owner'].workspace), Path(profiles['analyst'].workspace)
    owner.mkdir(parents=True); target.mkdir(parents=True)
    if escape == 'memory_db_symlink':
        owner_db = owner/'memory'/'long-term'/'index.db'
        owner_db.parent.mkdir(parents=True); owner_db.touch()
        target_db = target/'memory'/'long-term'/'index.db'
        target_db.parent.mkdir(parents=True); target_db.symlink_to(owner_db)
    elif escape in ('memory_file_symlink','memory_file_hardlink'):
        owner_file = owner/'MEMORY.md'; owner_file.touch()
        target_file = target/'MEMORY.md'
        if escape == 'memory_file_symlink':
            target_file.symlink_to(owner_file)
        else:
            os.link(owner_file,target_file)
    else:
        profiles['owner'] = AgentProfile('owner','Owner',str(target/'nested'),model='owner-model',bot_type='openai',enabled=False)
    import bridge.bridge
    calls = []
    monkeypatch.setattr(bridge.bridge,'Bridge',lambda: calls.append('bridge'))
    rid = proposal(obj,cid)['research_id']; obj.decide(rid,'approve',0)
    assert obj.execute(rid,0)['status'] == 'uncertain'
    assert calls == []
    assert obj.execute(rid,0)['status'] == 'uncertain' and calls == []
