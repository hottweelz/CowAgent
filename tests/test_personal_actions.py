"""Single-use owner action integration through the native file broker."""
from concurrent.futures import ThreadPoolExecutor
import time
from types import SimpleNamespace

import pytest

from agent.memory.conversation_store import ConversationStore
from agent.personal import service
from agent.registry import AgentProfile


@pytest.fixture
def owner(tmp_path, monkeypatch):
    workspace = tmp_path / 'work'
    workspace.mkdir()
    profile = AgentProfile('owner', 'Owner', str(workspace))
    registry = SimpleNamespace(get_addressed=lambda aid: profile if aid == 'owner' else (_ for _ in ()).throw(KeyError(aid)))
    store = ConversationStore(tmp_path / 'conversation.db')
    store.append_messages('session', [{'role': 'user', 'content': 'Create a checklist'}], channel_type='web')
    monkeypatch.setattr(service, 'get_agent_registry', lambda: registry)
    monkeypatch.setattr(service, 'get_conversation_store', lambda root: store)
    monkeypatch.setattr('agent.permission.authority._registry_profiles', lambda: [profile])
    return service.PersonalService('owner', 'session'), workspace


def proposal(owner, path='projects/cedar/checklist.md', content='Exact content\n'):
    svc, _ = owner
    return svc.store.propose_action('session', path, content, 0, int(time.time()) + 600, str(svc.profile.workspace))


def test_approval_exact_content_and_no_replay(owner):
    svc, workspace = owner
    action = proposal(owner)
    with pytest.raises(ValueError):
        svc.execute(action['action_id'])
    assert not (workspace / action['path']).exists()
    svc.store.decide_action('session', action['action_id'], 'approve')
    svc.execute(action['action_id'])
    assert (workspace / action['path']).read_bytes() == b'Exact content\n'
    assert svc.store.snapshot('session')['actions'][0]['status'] == 'completed'
    with pytest.raises(ValueError):
        svc.execute(action['action_id'])


def test_invalid_paths_and_symlink_denied(owner, tmp_path):
    svc, workspace = owner
    for path in ('../escape.txt', str(tmp_path / 'escape.txt'), 'memory/MEMORY.md'):
        with pytest.raises(ValueError):
            svc._validate_target(path, 'content')
    (workspace / 'linked').symlink_to(tmp_path, target_is_directory=True)
    action = proposal(owner, 'linked/out.txt')
    svc.store.decide_action('session', action['action_id'], 'approve')
    svc.execute(action['action_id'])
    assert not (tmp_path / 'out.txt').exists()
    assert svc.store.snapshot('session')['actions'][0]['status'] == 'failed'


def test_atomic_claim_and_restart_nonreplay(owner):
    svc, workspace = owner
    action = proposal(owner)
    aid = action['action_id']
    svc.store.decide_action('session', aid, 'approve')
    def run():
        try:
            svc.execute(aid)
            return 'claimed'
        except ValueError:
            return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: run(), range(2))) == ['claimed', 'rejected']
    assert (workspace / action['path']).read_text() == action['content']
    again = service.PersonalService('owner', 'session')
    with pytest.raises(ValueError):
        again.execute(aid)


def test_readback_failure_is_visible_and_not_replayed(owner, monkeypatch):
    svc, _ = owner
    action = proposal(owner)
    svc.store.decide_action('session', action['action_id'], 'approve')
    native = service.invoke
    def invoke(tool, args, context):
        if tool.name == 'read':
            from agent.tools.base_tool import ToolResult
            return ToolResult.fail('test')
        return native(tool, args, context)
    monkeypatch.setattr(service, 'invoke', invoke)
    svc.execute(action['action_id'])
    assert svc.store.snapshot('session')['actions'][0]['status'] == 'failed'
    with pytest.raises(ValueError):
        service.PersonalService('owner', 'session').execute(action['action_id'])


def test_changed_workspace_does_not_redirect_approved_action(owner, tmp_path):
    svc, original = owner
    action = proposal(owner)
    svc.store.decide_action('session', action['action_id'], 'approve')
    changed = tmp_path / 'changed'
    changed.mkdir()
    svc.profile = AgentProfile('owner', 'Owner', str(changed))
    svc.execute(action['action_id'])
    assert not (original / action['path']).exists()
    assert not (changed / action['path']).exists()
    assert svc.store.snapshot('session')['actions'][0]['status'] == 'failed'


def test_cached_capabilities_show_native_permissions_and_clean_skills(owner, monkeypatch):
    from agent.tools.read.read import Read
    from agent.tools.write.write import Write
    svc, workspace = owner
    runtime = service._OwnerAction(svc.profile)
    runtime.effective_permission_mode = lambda: 'read-only'
    runtime.tools = [Read({'cwd': str(workspace)}), Write({'cwd': str(workspace)})]
    runtime.skill_manager = SimpleNamespace(list_skills=lambda: [
        {'name': 'notes', 'description': 'Maintain notes'},
        SimpleNamespace(skill=SimpleNamespace(name='review', description='Review changes')),
    ])
    bridge = SimpleNamespace(_agent_bridge=SimpleNamespace(get_cached_agent=lambda *args: runtime))
    monkeypatch.setattr('bridge.bridge.Bridge', lambda: bridge)
    caps = svc.snapshot()['capabilities']
    assert caps['permission_mode'] == 'read-only'
    assert {item['name']: item['allowed'] for item in caps['tools']} == {'read': True, 'write': False}
    assert caps['skills'] == [{'name': 'notes', 'description': 'Maintain notes'},
                              {'name': 'review', 'description': 'Review changes'}]
