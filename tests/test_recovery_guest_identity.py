
import pytest

from agent.protocol import Agent, LLMModel
from agent.registry import AgentProfile, AgentRegistry
from agent.recovery import runtime
from agent.recovery.store import TaskStore
from agent.subagent.runner import SubagentTask, _prepare_task
from agent.subagent.templates import GENERAL_PURPOSE


class FixtureModel(LLMModel):
    def __init__(self, *_):
        super().__init__('guest-model')
        self.agent_id = 'guest'
        self.default = None
        self.session = None

    def set_agent_default(self, provider, model):
        self.default = (provider, model)

    def set_session_override(self, provider, model):
        self.session = (provider, model)

    def call_stream(self, request):
        yield {'choices': [{'delta': {'content': 'guest complete'}, 'finish_reason': 'stop'}]}


@pytest.fixture
def guest(tmp_path, monkeypatch):
    import config
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('COW_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('socket.socket.connect', lambda *a, **k: (_ for _ in ()).throw(AssertionError('network denied')))
    host = tmp_path / 'host'; host.mkdir()
    guest_root = tmp_path / 'guest'; guest_root.mkdir()
    project = tmp_path / 'project'; project.mkdir()
    settings = {'agent_permission_mode': 'workspace-write', 'model': 'global-model', 'bot_type': 'global',
                'default_agent_id': 'host'}
    monkeypatch.setattr(config, 'config', config.Config(settings))
    profiles = [AgentProfile('host', 'Host', str(host)),
                AgentProfile('guest', 'Guest', str(guest_root), bot_type='guest-provider', model='guest-model')]
    registry = AgentRegistry(profiles, 'host')
    monkeypatch.setattr(runtime, '_registry_profiles', lambda: profiles)
    monkeypatch.setattr('agent.permission.authority._registry_profiles', lambda: profiles)
    monkeypatch.setattr(runtime, '_current_registry', lambda: registry)
    prefs = {'permission': 'workspace-write', 'members': ['guest'], 'model': 'host-pinned'}
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict', lambda *_: dict(prefs))
    monkeypatch.setattr(runtime.project_store, 'get_project_dir_strict', lambda *_: str(project))
    store = TaskStore(tmp_path / 'journal/tasks.db')
    monkeypatch.setattr(runtime, 'get_task_store', lambda: store)
    monkeypatch.setattr('bridge.agent_bridge.AgentLLMModel', FixtureModel)
    parent = Agent('guest', model=FixtureModel(), workspace_dir=str(guest_root), enable_skills=False)
    parent.project_dir = str(project)
    parent.permission_mode = 'workspace-write'
    parent._current_agent_id = 'host'
    parent._current_session_id = 'group'
    return parent, prefs, profiles, store


def test_guest_recovery_keeps_guest_model_and_host_journal(guest):
    parent, _, _, store = guest
    _, task_id, child = _prepare_task(parent, GENERAL_PURPOSE, SubagentTask('work'), 20)
    row = store.get(task_id)
    assert row['owner_id'] == 'host'
    assert row['spec']['source_agent_id'] == row['spec']['target_agent_id'] == 'guest'
    assert row['spec']['model_ref']['model'] == 'guest-model'
    claim = store.claim(task_id)
    claim.close()
    assert store.reconcile() == [task_id]
    restored = runtime.restore_child(store.get(task_id)['spec'], object())
    assert restored.model.default == ('guest-provider', 'guest-model')
    assert restored.model.session == (None, None)
    result = runtime.execute_task(store, task_id, bridge=object())
    assert result['status'] == 'completed' and result['summary'] == 'guest complete'


def test_guest_recovery_current_host_permission_and_revocations(guest):
    parent, prefs, profiles, store = guest
    _, task_id, _ = _prepare_task(parent, GENERAL_PURPOSE, SubagentTask('work'), 20)
    spec = store.get(task_id)['spec']
    prefs['permission'] = 'read-only'
    auth, _, _ = runtime._attenuate(spec)
    assert auth.mode == 'read-only' and 'fs.write' not in auth.capabilities
    prefs['members'] = []
    with pytest.raises(ValueError, match='guest'):
        runtime._attenuate(spec)
    prefs['members'] = ['guest']
    profiles[1] = AgentProfile('guest', 'Guest', profiles[1].workspace, enabled=False)
    with pytest.raises(ValueError, match='principal'):
        runtime._attenuate(spec)


def test_guest_without_host_project_keeps_guest_workspace(guest, monkeypatch):
    parent, _, profiles, store = guest
    parent.project_dir = None
    monkeypatch.setattr(runtime.project_store, 'get_project_dir_strict', lambda *_: None)
    _, task_id, child = _prepare_task(parent, GENERAL_PURPOSE, SubagentTask('work'), 20)
    spec = store.get(task_id)['spec']
    assert child.task_workspace.startswith(profiles[1].workspace + '/')
    auth, _, _ = runtime._attenuate(spec)
    assert child.task_workspace in auth.write_roots
