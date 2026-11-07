from types import SimpleNamespace

import pytest

from agent.permission.authority import Authority
from agent.protocol.agent import Agent
from agent.recovery import runtime
from agent.recovery.store import TaskStore
from agent.tools.write.write import Write


@pytest.fixture
def setup_worker(tmp_path, monkeypatch):
    profile = SimpleNamespace(id='owner', enabled=True, workspace=str(tmp_path),
                              bot_type='fixture', model='fixture-model')
    profiles = [profile]
    monkeypatch.setattr(runtime, '_registry_profiles', lambda: profiles)
    monkeypatch.setattr('agent.permission.authority._registry_profiles', lambda: profiles)
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict', lambda *_: {'permission': 'workspace-write'})
    monkeypatch.setattr(runtime.project_store, 'get_project_dir_strict', lambda *_: str(tmp_path))
    child = Agent('task system', tools=[Write({'cwd': str(tmp_path)})], workspace_dir=str(tmp_path),
                  enable_skills=False, skip_context_files=True)
    child.project_dir = str(tmp_path)
    child.permission_mode = 'workspace-write'
    child.authority = Authority('workspace-write', frozenset({'fs.write', 'fs.read'}),
                                (str(tmp_path),), (str(tmp_path),))
    child._current_agent_id = 'owner'
    spec = runtime.snapshot_child(child, 'task text', owner_id='owner', session_id='s',
                                  kind='subagent', source_agent_id='owner', target_agent_id='owner')
    return child, spec, profiles


def test_restore_fresh_and_revocation(tmp_path, setup_worker, monkeypatch):
    _, spec, profiles = setup_worker
    restored = runtime.restore_child(spec, object())
    assert restored.messages == [] and restored.memory_manager is None and restored.skill_manager is None
    assert type(restored.tools[0]) is Write
    assert restored.authority.write_roots == (str(tmp_path),)
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict', lambda *_: {'permission': 'read-only'})
    restricted = runtime.restore_child(spec, object())
    assert not restricted.authority.write_roots and 'fs.write' not in restricted.authority.capabilities
    profiles.clear()
    with pytest.raises(ValueError):
        runtime.restore_child(spec, object())


def test_completed_cached_and_guard_receipt(tmp_path, setup_worker):
    child, spec, _ = setup_worker
    store = TaskStore(tmp_path / 'journal' / 'tasks.db')
    task = store.submit('owner', 's', 'subagent', spec)
    calls = []
    def run(*args, **kwargs):
        calls.append(1)
        effect = child.recovery_attempt.before_tool('write', True, 'call-1')
        child.recovery_attempt.after_tool(effect, {'ok': True})
        return 'done'
    child.run_stream = run
    result = runtime.execute_task(store, task['task_id'], lambda: child)
    assert result['status'] == 'completed' and result['summary'] == 'done'
    assert runtime.execute_task(store, task['task_id']) == result
    assert calls == [1]
    assert TaskStore(store.path).get(task['task_id'])['attempts'][0]['effects'][0]['mutating']


def test_model_change_fails_before_run(tmp_path, setup_worker):
    child, spec, profiles = setup_worker
    store = TaskStore(tmp_path / 'journal' / 'tasks.db')
    task = store.submit('owner', 's', 'subagent', spec)
    profiles[0].model = 'different'
    result = runtime.execute_task(store, task['task_id'], lambda: child)
    assert result['status'] == 'failed'


def test_delegation_revocation_and_fallback_configuration(tmp_path, setup_worker, monkeypatch):
    child, _, profiles = setup_worker
    profiles.append(SimpleNamespace(id='receiver', enabled=True, workspace=str(tmp_path),
                                    bot_type='fixture', model='receiver-model'))
    settings = {'agent_delegation': {}, 'chat_fallback': {'enabled': True,
                'chain': [{'provider': 'second', 'model': 'backup'}]}}
    monkeypatch.setattr('config.conf', lambda: settings)
    prefs = {'permission': 'workspace-write', 'members': ['receiver']}
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict', lambda *_: prefs)
    spec = runtime.snapshot_child(child, 'task', owner_id='owner', session_id='s', kind='delegate',
                                  source_agent_id='owner', target_agent_id='receiver')
    runtime._attenuate(spec)
    settings['chat_fallback']['chain'][0]['model'] = 'different'
    with pytest.raises(ValueError, match='model configuration'):
        runtime._attenuate(spec)
    settings['chat_fallback']['chain'][0]['model'] = 'backup'
    prefs['members'] = []
    with pytest.raises(ValueError, match='delegation'):
        runtime._attenuate(spec)


def test_two_consumers_wait_for_one_attempt(tmp_path, setup_worker):
    import threading

    child, spec, _ = setup_worker
    store = TaskStore(tmp_path / 'journal' / 'tasks.db')
    task_id = store.submit('owner', 's', 'subagent', spec)['task_id']
    started, release = threading.Event(), threading.Event()
    calls = []

    def run(*args, **kwargs):
        calls.append(1)
        effect = child.recovery_attempt.before_tool('write', True, 'single-call')
        started.set()
        assert release.wait(3)
        child.recovery_attempt.after_tool(effect, {'ok': True})
        return 'one result'

    child.run_stream = run
    results = []
    owner = threading.Thread(target=lambda: results.append(runtime.execute_task(store, task_id, lambda: child)))
    owner.start()
    assert started.wait(3)
    waiter = threading.Thread(target=lambda: results.append(runtime.execute_task(store, task_id, lambda: child)))
    waiter.start()
    assert runtime.execute_task(store, task_id, wait_for_existing=False)['status'] == 'running'
    release.set()
    owner.join(3)
    waiter.join(3)
    assert not owner.is_alive() and not waiter.is_alive()
    assert len(results) == 2 and results[0] == results[1]
    assert results[0]['summary'] == 'one result' and calls == [1]
    assert len(store.get(task_id)['attempts'][0]['effects']) == 1


def test_receipt_failure_stops_further_effects(tmp_path, setup_worker, monkeypatch):
    child, spec, _ = setup_worker
    store = TaskStore(tmp_path / 'journal/tasks.db')
    task_id = store.submit('owner', 's', 'subagent', spec)['task_id']
    original = store.after_tool
    calls = []
    def fail_receipt(*args):
        calls.append(1)
        raise OSError('fixture unavailable')
    monkeypatch.setattr(store, 'after_tool', fail_receipt)
    def run(*args, **kwargs):
        writer = child.tools[0]
        writer.context = child
        first = writer.execute_tool({'path': 'first.txt', 'content': 'one effect'})
        assert first.status == 'error'
        monkeypatch.setattr(store, 'after_tool', original)
        second = writer.execute_tool({'path': 'second.txt', 'content': 'must not happen'})
        assert second.status == 'error'
        return 'must not report completed'
    child.run_stream = run
    result = runtime.execute_task(store, task_id, lambda: child)
    assert result['status'] == 'needs_review'
    assert (tmp_path / 'first.txt').read_text() == 'one effect'
    assert not (tmp_path / 'second.txt').exists()
    assert calls == [1]


def test_default_profile_and_group_follow_normal_model_routing(setup_worker, monkeypatch):
    import config
    child, _, _ = setup_worker
    monkeypatch.setattr(config, 'config', config.Config({'bot_type': 'global-provider',
                        'model': 'global-model', 'agent_workspace': child.workspace_dir}))
    monkeypatch.setattr(runtime, '_current_registry', lambda: SimpleNamespace(default_agent_id='owner'))
    prefs = {'permission': 'workspace-write', 'provider': 'session-provider', 'model': 'session-model'}
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict', lambda *_: prefs)
    for is_group in (False, True):
        prefs['members'] = ['teammate'] if is_group else []
        spec = runtime.snapshot_child(child, 'task', owner_id='owner', session_id='s',
                                      kind='subagent', source_agent_id='owner', target_agent_id='owner')
        restored = runtime.restore_child(spec, object())
        expected = ('global-provider', 'global-model') if is_group else ('session-provider', 'session-model')
        assert (spec['model_ref']['provider'], spec['model_ref']['model']) == expected
        assert (restored.model._resolve_bot_type(restored.model.model), restored.model.model) == expected
        assert restored.model._agent_provider is None and restored.model._agent_model is None


def test_disabled_subagents_do_not_start_queued_task(tmp_path, setup_worker, monkeypatch):
    child, spec, _ = setup_worker
    store = TaskStore(tmp_path / 'journal/tasks.db')
    task_id = store.submit('owner', 's', 'subagent', spec)['task_id']
    monkeypatch.setattr('config.conf', lambda: {'subagent': {'enabled': False}})
    child.run_stream = lambda *a, **k: pytest.fail('disabled worker started')
    assert runtime.execute_task(store, task_id, lambda: child)['status'] == 'failed'


def test_waiting_delegate_claims_after_session_owner_exits(tmp_path, setup_worker, monkeypatch):
    import threading
    child, _, profiles = setup_worker
    profiles.append(SimpleNamespace(id='receiver', enabled=True, workspace=str(tmp_path),
                                    bot_type='fixture', model='receiver-model'))
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict',
                        lambda *_: {'permission': 'workspace-write', 'members': ['receiver']})
    spec = runtime.snapshot_child(child, 'task', owner_id='owner', session_id='s', kind='delegate',
                                  source_agent_id='owner', target_agent_id='receiver')
    store = TaskStore(tmp_path / 'journal/tasks.db')
    first = store.submit('owner', 's', 'delegate', spec)['task_id']
    second = store.submit('owner', 's', 'delegate', spec)['task_id']
    claim = store.claim(first)
    store.request_stop(first, 'timed_out')
    started = threading.Event()
    child.run_stream = lambda *a, **k: started.set() or 'follower'
    results = []
    waiter = threading.Thread(target=lambda: results.append(runtime.execute_task(store, second, lambda: child)))
    waiter.start()
    try:
        assert not started.wait(.1)
        assert store.get(second)['attempt_count'] == 0
        claim.close()
        waiter.join(3)
        assert not waiter.is_alive() and started.is_set()
        assert results[0]['status'] == 'completed'
        assert store.get(first)['state'] == 'timed_out'
    finally:
        claim.close()
        store.request_stop(second)
        waiter.join(3)


@pytest.mark.parametrize('journal_available', [True, False])
def test_public_subagent_tool_requires_durable_admission(tmp_path, setup_worker, monkeypatch, journal_available):
    import json
    from pathlib import Path
    from agent.protocol import LLMModel
    from agent.tools.subagent import SubagentTool
    parent, _, _ = setup_worker
    parent.authority = Authority('workspace-write', frozenset({'fs.write', 'fs.read', 'subagent.spawn'}),
                                 (str(tmp_path),), (str(tmp_path),))
    parent._current_session_id = 's'

    class Model(LLMModel):
        def __init__(self):
            super().__init__('fixture-model')
            self.calls = 0

        def call_stream(self, request):
            self.calls += 1
            if self.calls == 1:
                yield {'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'native-write',
                    'function': {'name': 'write', 'arguments': json.dumps({'path': 'result.txt',
                    'content': 'public tool result'})}}]}, 'finish_reason': 'tool_calls'}]}
            else:
                yield {'choices': [{'delta': {'content': 'done'}, 'finish_reason': 'stop'}]}

    parent.model = Model()
    store = TaskStore(tmp_path / 'journal/tasks.db')
    monkeypatch.setattr(runtime, 'get_task_store', lambda: store)
    monkeypatch.setattr('agent.subagent.runner._open_run', lambda *a: None)
    if not journal_available:
        def unavailable(*a, **k):
            raise OSError('fixture journal unavailable')
        monkeypatch.setattr(store, 'submit', unavailable)
    tool = SubagentTool({'cwd': str(tmp_path)})
    tool.context = parent
    result = tool.execute_tool({'goal': 'Write result.txt in the task workspace'})
    if not journal_available:
        assert result.status == 'error' and parent.model.calls == 0
        assert store.list_tasks() == []
        return
    assert result.status == 'success', result.result
    item = json.loads(result.result)['results'][0]
    assert item['status'] == 'completed' and parent.model.calls == 2
    row = store.get(item['task_id'])
    assert row['state'] == 'completed' and row['attempt_count'] == 1
    effect, = row['attempts'][0]['effects']
    assert effect['name'] == 'write' and effect['mutating'] and effect['completed_at']
    assert (Path(item['task_workspace']) / 'result.txt').read_text() == 'public tool result'


def test_delayed_runtime_timeout_cannot_stop_explicit_retry(tmp_path, setup_worker, monkeypatch):
    child, spec, _ = setup_worker
    callbacks = []

    class DelayedTimer:
        def __init__(self, interval, callback):
            callbacks.append(callback)
        def start(self):
            pass
        def cancel(self):
            pass  # Model a callback already dispatched before cancel().

    monkeypatch.setattr('threading.Timer', DelayedTimer)
    store = TaskStore(tmp_path / 'journal/tasks.db')
    task_id = store.submit('owner', 's', 'subagent', spec)['task_id']
    def fail(*a, **k):
        raise RuntimeError('fixture attempt failure')
    child.run_stream = fail
    assert runtime.execute_task(store, task_id, lambda: child)['status'] == 'failed'
    store.retry(task_id)
    callbacks[0]()
    assert store.get(task_id)['state'] == 'queued'
    with store.claim(task_id):
        callbacks[0]()
        assert store.get(task_id)['state'] == 'running'
