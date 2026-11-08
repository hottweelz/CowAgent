"""Focused contract tests for the registered CowAgent native entry point.

All workspaces and config state in this file are disposable. The native Bridge
is a stub, so these tests cannot initialize a provider or contact a model.
"""

import json
from pathlib import Path
import uuid
from types import SimpleNamespace

import pytest

from agent.external import analysis, contract
from agent.external.cowagent_native import CowAgentNative, TARGET, _Prepared
from agent.registry import AgentProfile


def _spec():
    task_id = str(uuid.uuid4())
    return {
        "task_id": task_id,
        "task": {
            "content": json.dumps({
                "schema_version": 1,
                "currency": "USD",
                "records": [
                    {"id": "fictional-1", "amount_cents": 1234, "status": "paid"},
                    {"id": "fictional-2", "amount_cents": -100, "status": "refund"},
                ],
            }),
        },
    }


def _agent(profile, model="fixture-model", messages=None):
    from common import state_dir
    workspace = Path(profile.workspace)
    db_path = state_dir.memory_index_db(base=str(workspace), ensure=False)
    memory = SimpleNamespace(config=SimpleNamespace(get_workspace=lambda: workspace,
                                                      get_db_path=lambda: db_path),
                             storage=SimpleNamespace(db_path=db_path))

    class FixtureModel:
        def __init__(self):
            self.model = model

        @staticmethod
        def _primary_provider_id(_model):
            return "fixture-provider"

    class FixtureAgent:
        def __init__(self):
            self.agent_profile = profile
            self.messages = [] if messages is None else messages
            self.memory_manager = memory
            self.skip_context_files = False
            self.authority = None
            self.model = FixtureModel()
            self.system_prompt = "registered profile instructions"
            self.run_calls = []

        def effective_permission_mode(self):
            return "read-only"

        def run_stream(self, prompt, **kwargs):
            from common.runtime_identity import current_identity

            self.run_calls.append((prompt, kwargs, current_identity()))
            return self.response

    return FixtureAgent(), memory


def _native_fixture(monkeypatch, profile, agent, enrollment):
    from common.runtime_identity import current_identity

    class BridgeStub:
        def __init__(self):
            self.cached_queries = []
            self.agent_queries = []

        def get_cached_agent(self, session_id, agent_id):
            self.cached_queries.append((session_id, agent_id, current_identity()))
            return None

        def get_agent(self, **kwargs):
            self.agent_queries.append((kwargs, current_identity()))
            return agent

    bridge_stub = BridgeStub()
    import bridge.bridge

    monkeypatch.setattr(bridge.bridge, "Bridge", lambda: SimpleNamespace(
        get_agent_bridge=lambda: bridge_stub
    ))

    native = object.__new__(CowAgentNative)
    native._target = profile.id
    enrollment.setdefault('agent_id', profile.id)
    enrollment.setdefault('profile_sha256', 'b' * 64)
    native.config_path = None
    native.enrollment = enrollment
    native.bridge = None
    monkeypatch.setattr(native, "_profile", lambda: profile)
    monkeypatch.setattr(native, "discover", lambda: {
        key: value for key, value in enrollment.items() if key != "probe_sha256"
    })
    monkeypatch.setattr(native, "_preflight", lambda: None)
    return native, bridge_stub


def test_prepare_uses_registered_identity_fresh_read_only_session_and_preserves_profile(monkeypatch):
    profile = AgentProfile(
        id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot",
        model="fixture-model", bot_type="fixture-provider",
    )
    agent, memory = _agent(profile)
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, bridge = _native_fixture(monkeypatch, profile, agent, enrollment)

    prepared = native.prepare("fresh-session-1")

    assert isinstance(prepared, _Prepared)
    assert prepared.agent is agent
    assert prepared.session_id == "fresh-session-1"
    assert bridge.cached_queries[0][:2] == ("fresh-session-1", "testpilot")
    assert bridge.agent_queries[0][0] == {
        "session_id": "fresh-session-1", "agent_id": "testpilot",
        "permission_mode": "read-only",
    }
    for _sid, agent_id, identity in bridge.cached_queries:
        assert agent_id == "testpilot"
        assert identity.agent_id == "testpilot"
        assert identity.session_id == "fresh-session-1"
    for (kwargs, identity) in bridge.agent_queries:
        assert kwargs["agent_id"] == "testpilot"
        assert identity.agent_id == "testpilot"
        assert identity.session_id == "fresh-session-1"
    assert agent.agent_profile is profile
    assert agent.system_prompt == "registered profile instructions"
    assert agent.memory_manager is memory
    assert agent.authority is None
    assert agent.effective_permission_mode() == "read-only"
    assert agent.messages == []


def test_run_uses_only_caller_records_and_codex_source_with_registered_identity(monkeypatch):
    from common.runtime_identity import current_identity

    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot")
    agent, _memory = _agent(profile)
    spec = _spec()
    expected = analysis.expected_report(spec)
    agent.response = json.dumps(expected)
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, _bridge = _native_fixture(monkeypatch, profile, agent, enrollment)
    prepared = native.prepare("fresh-session-2")

    result = prepared.run(spec, cancel_event=object())

    prompt, _kwargs, identity = agent.run_calls[0]
    assert "External caller: Codex" in prompt
    assert "fictional-1" in prompt and "fictional-2" in prompt
    assert "registered profile instructions" not in prompt
    assert identity.agent_id == "testpilot"
    assert identity.session_id == "fresh-session-2"
    assert identity.run_id
    assert current_identity().agent_id is None
    assert result["report"] == expected
    assert result["receipt"]["source"] == "codex"
    assert result["receipt"]["prompt_source"] == "native"
    assert result["receipt"]["memory_owner"] == "runtime"
    assert result["receipt"]["agent_id"] == "testpilot"


@pytest.mark.parametrize("bad_response", [
    "private native response text",
    '{"task_id":"wrong","unexpected":"invalid"}',
])
def test_invalid_or_private_response_is_not_returned_or_included_in_error(monkeypatch, bad_response):
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot")
    agent, _memory = _agent(profile)
    agent.response = bad_response
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, _bridge = _native_fixture(monkeypatch, profile, agent, enrollment)
    prepared = native.prepare("fresh-session-3")

    with pytest.raises(ValueError) as raised:
        prepared.run(_spec(), cancel_event=object())

    assert "private native response text" not in str(raised.value)
    assert len(agent.run_calls) == 1


def test_prepare_rejects_existing_session_and_never_reuses_history(monkeypatch):
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot")
    agent, _memory = _agent(profile, messages=["synthetic historical turn"])
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, bridge = _native_fixture(monkeypatch, profile, agent, enrollment)

    def existing(session_id, agent_id):
        assert (session_id, agent_id) == ("old-session", "testpilot")
        return agent

    bridge.get_cached_agent = existing
    with pytest.raises(contract.ProtocolError, match="session already exists"):
        native.prepare("old-session")
    assert bridge.agent_queries == []
    assert agent.messages == ["synthetic historical turn"]
    assert agent.run_calls == []


def test_prepare_rejects_model_drift_before_running(monkeypatch):
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot")
    agent, _memory = _agent(profile, model="drifted-model")
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, _bridge = _native_fixture(monkeypatch, profile, agent, enrollment)

    with pytest.raises(contract.ProtocolError, match="identity, model or session differs"):
        native.prepare("fresh-session-4")
    assert agent.run_calls == []


def test_run_rejects_model_drift_after_native_execution(monkeypatch):
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot")
    agent, _memory = _agent(profile)
    spec = _spec()
    agent.response = json.dumps(analysis.expected_report(spec))
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, _bridge = _native_fixture(monkeypatch, profile, agent, enrollment)
    prepared = native.prepare("fresh-session-5")
    agent.run_stream = lambda *args, **kwargs: setattr(agent.model, "model", "drifted-model") or "{}"

    with pytest.raises(contract.ProtocolError, match="model changed during execution"):
        prepared.run(spec, cancel_event=object())


def test_run_rejects_provider_fallback_even_when_model_name_is_unchanged(monkeypatch):
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace="/synthetic/testpilot")
    agent, _memory = _agent(profile)
    spec = _spec()
    agent.response = json.dumps(analysis.expected_report(spec))
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native, _bridge = _native_fixture(monkeypatch, profile, agent, enrollment)
    prepared = native.prepare("fresh-session-7")

    def fallback_same_model(*_args, **_kwargs):
        agent.model._fallback_provider = "other-provider"
        return agent.response

    agent.run_stream = fallback_same_model
    with pytest.raises(contract.ProtocolError, match="model changed during execution"):
        prepared.run(spec, cancel_event=object())


def test_preflight_checks_only_disposable_metadata_and_blocks_active_scheduler(tmp_path, monkeypatch):
    import config
    import agent.permission.authority as authority

    workspace = tmp_path / "testpilot"
    workspace.mkdir()
    schedule = workspace / "scheduler" / "tasks.json"
    schedule.parent.mkdir()
    schedule.write_text(json.dumps({"tasks": {"synthetic-job": {"enabled": True}}}))
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace=str(workspace))

    class RegistryStub:
        def list(self, include_disabled=False):
            return [profile]

        def get(self, agent_id=None):
            assert agent_id is None
            return profile

    monkeypatch.setattr(config, "conf", lambda: {"self_evolution_enabled": False})
    monkeypatch.setattr(authority, "_current_registry", lambda: RegistryStub())
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home" / ".cow").mkdir(parents=True)
    monkeypatch.setattr("agent.external.cowagent_native.time.localtime", lambda: SimpleNamespace(tm_hour=12, tm_min=0))

    native = object.__new__(CowAgentNative)
    native._target = TARGET
    with pytest.raises(contract.ProtocolError, match="Existing scheduler work requires review"):
        native._preflight()
    assert schedule.read_text() == json.dumps({"tasks": {"synthetic-job": {"enabled": True}}})
    assert sorted(p.name for p in workspace.iterdir()) == ["scheduler"]


@pytest.mark.parametrize("blocker", ["configured_mcp", "scheduler_backup"])
def test_prepare_preflight_blockers_do_not_start_native_bridge(tmp_path, monkeypatch, blocker):
    import config
    import agent.permission.authority as authority

    workspace = tmp_path / "testpilot"
    workspace.mkdir()
    profile = AgentProfile(id=TARGET, name="Test Pilot", workspace=str(workspace))

    class RegistryStub:
        def list(self, include_disabled=False):
            return [profile]

        def get(self, agent_id=None):
            assert agent_id is None
            return profile

    settings = {"self_evolution_enabled": False}
    if blocker == "configured_mcp":
        settings["mcp_servers"] = {"fixture": {"command": "must-not-run"}}
    else:
        schedule = workspace / "scheduler" / "tasks.json.bak"
        schedule.parent.mkdir()
        schedule.write_text(json.dumps({"tasks": {"synthetic-job": {"enabled": True}}}))

    monkeypatch.setattr(config, "conf", lambda: settings)
    monkeypatch.setattr(authority, "_current_registry", lambda: RegistryStub())
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home" / ".cow").mkdir(parents=True)
    monkeypatch.setattr(
        "agent.external.cowagent_native.time.localtime",
        lambda: SimpleNamespace(tm_hour=12, tm_min=0),
    )
    bridge_starts = []

    import bridge.bridge
    monkeypatch.setattr(bridge.bridge, "Bridge", lambda: bridge_starts.append(True))
    enrollment = {"model": "fixture-model", "provider": "fixture-provider"}
    native = object.__new__(CowAgentNative)
    native.enrollment = enrollment
    native._target = TARGET
    native.bridge = None
    monkeypatch.setattr(native, "discover", lambda: enrollment)

    expected = (
        "Configured MCP startup requires review"
        if blocker == "configured_mcp"
        else "Existing scheduler work requires review"
    )
    with pytest.raises(contract.ProtocolError, match=expected):
        native.prepare("fresh-session-6")

    assert bridge_starts == []
    assert native.bridge is None

@pytest.mark.parametrize('target,model', [('testpilot', 'fixture-model'), ('testpilot2', 'other-model')])
def test_target_scoped_memory_and_metadata(tmp_path, monkeypatch, target, model):
    workspace = tmp_path / target
    workspace.mkdir()
    profile = AgentProfile(id=target, name=target, workspace=str(workspace))
    agent, memory = _agent(profile, model=model)
    enrollment = {'model': model, 'provider': 'fixture-provider'}
    native, _ = _native_fixture(monkeypatch, profile, agent, enrollment)
    prepared = native.prepare('session-' + target)
    metadata = native.context_metadata()
    assert prepared.receipt_binding['agent_id'] == target
    assert prepared.receipt_binding['model'] == model
    assert metadata['memory_scope_sha256'] == prepared.receipt_binding['memory_scope_sha256']
    assert metadata['entries']['MEMORY.md'] == {'exists': False, 'size': None, 'mtime_ns': None}
    memory.storage.db_path = tmp_path / 'wrong.db'
    with pytest.raises(contract.ProtocolError, match='memory scope'):
        native.prepare('another-' + target)


def test_preflight_rejects_aliased_supported_workspaces(tmp_path, monkeypatch):
    import config
    import agent.permission.authority as authority
    root = tmp_path / 'workspace'
    root.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    profiles = [AgentProfile(id='testpilot', name='One', workspace=str(root)),
                AgentProfile(id='testpilot2', name='Two', workspace=str(alias))]
    registry = SimpleNamespace(list=lambda include_disabled=False: profiles, get=lambda: profiles[0])
    monkeypatch.setattr(config, 'conf', lambda: {'self_evolution_enabled': False})
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    monkeypatch.setattr('agent.external.cowagent_native.time.localtime', lambda: SimpleNamespace(tm_hour=12, tm_min=0))
    native = object.__new__(CowAgentNative)
    native._target = 'testpilot'
    with pytest.raises(contract.ProtocolError, match='workspaces overlap'):
        native._preflight()


@pytest.mark.parametrize('state,verification,blocked', [
    ('queued', False, True), ('running', False, True), ('completed', False, True),
    ('completed', True, False), ('failed', False, False),
])
def test_preflight_recovery_metadata(tmp_path, monkeypatch, state, verification, blocked):
    import sqlite3
    import config
    import agent.permission.authority as authority
    root = tmp_path / 'workspace'
    db_path = root / 'memory' / 'recovery' / 'tasks.db'
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as db:
        db.executescript('CREATE TABLE recovery_tasks(task_id TEXT, attempt_id TEXT, state TEXT);'
                         'CREATE TABLE recovery_verifications(task_id TEXT, attempt_id TEXT, report TEXT);')
        db.execute('INSERT INTO recovery_tasks VALUES (?, ?, ?)', ('task', 'attempt', state))
        if verification:
            db.execute('INSERT INTO recovery_verifications VALUES (?, ?, ?)', ('task', 'attempt', '{"status":"unverified"}'))
    profile = AgentProfile(id='testpilot', name='One', workspace=str(root))
    registry = SimpleNamespace(list=lambda include_disabled=False: [profile], get=lambda: profile)
    monkeypatch.setattr(config, 'conf', lambda: {'self_evolution_enabled': False})
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr('agent.external.cowagent_native.time.localtime', lambda: SimpleNamespace(tm_hour=12, tm_min=0))
    native = object.__new__(CowAgentNative)
    native._target = 'testpilot'
    if blocked:
        with pytest.raises(contract.ProtocolError, match='recovery work'):
            native._preflight()
    else:
        native._preflight()


@pytest.mark.parametrize('alias_kind', ['directory_symlink', 'file_symlink', 'hardlink'])
def test_preflight_blocks_memory_database_alias_before_bridge(tmp_path, monkeypatch, alias_kind):
    import os
    import config
    import agent.permission.authority as authority
    import bridge.bridge
    from common import state_dir

    roots = [tmp_path / 'one', tmp_path / 'two']
    for root in roots:
        root.mkdir()
    paths = [state_dir.memory_index_db(base=str(root), ensure=False) for root in roots]
    paths[1].parent.mkdir(parents=True)
    paths[1].touch()
    if alias_kind == 'directory_symlink':
        paths[0].parent.parent.mkdir(parents=True)
        paths[0].parent.symlink_to(paths[1].parent, target_is_directory=True)
    else:
        paths[0].parent.mkdir(parents=True)
        if alias_kind == 'file_symlink':
            paths[0].symlink_to(paths[1])
        else:
            os.link(paths[1], paths[0])
    profiles = [AgentProfile(id='testpilot', name='One', workspace=str(roots[0])),
                AgentProfile(id='testpilot2', name='Two', workspace=str(roots[1]))]
    registry = SimpleNamespace(list=lambda include_disabled=False: profiles, get=lambda: profiles[0])
    monkeypatch.setattr(config, 'conf', lambda: {'self_evolution_enabled': False})
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    monkeypatch.setattr('agent.external.cowagent_native.time.localtime', lambda: SimpleNamespace(tm_hour=12, tm_min=0))
    starts = []
    monkeypatch.setattr(bridge.bridge, 'Bridge', lambda: starts.append(True))
    native = object.__new__(CowAgentNative)
    native._target = 'testpilot'
    native.bridge = None
    native.enrollment = {'model': 'fixture'}
    monkeypatch.setattr(native, 'discover', lambda: native.enrollment)
    expected = 'share an inode' if alias_kind == 'hardlink' else 'escapes workspace'
    with pytest.raises(contract.ProtocolError, match=expected):
        native.prepare('fixture-session')
    assert starts == []
    assert native.bridge is None
