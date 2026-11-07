"""Native worker outcomes use independent checks, not worker claims."""

import json
from types import SimpleNamespace

import pytest

from agent.permission.authority import Authority
from agent.protocol import Agent, LLMModel
from agent.registry import AgentProfile, AgentRegistry, set_agent_registry
from agent.recovery import runtime
from agent.recovery.store import TaskStore
from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool, attach_agent_delegate_to_tool
from agent.tools.read.read import Read
from agent.tools.subagent import SubagentTool
from agent.tools.write.write import Write
from agent.workspace import project_store, session_prefs
from bridge.context import Context, ContextType


class WritingModel(LLMModel):
    """Fixture provider that streams a native write, then an untrusted claim."""

    def __init__(self, content, arguments=None):
        super().__init__("fixture-model")
        self.content = content
        self.arguments = arguments
        self.calls = 0
        self.requests = []

    def set_agent_default(self, provider, model):
        self.agent_default = (provider, model)

    def set_session_override(self, provider, model):
        self.session_override = (provider, model)

    def call_stream(self, request):
        self.calls += 1
        self.requests.append(request)
        if self.calls == 1:
            arguments = self.arguments or json.dumps({
                "path": "artifact.json", "content": self.content})
            yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "write-1",
                "function": {"name": "write", "arguments": arguments}}]},
                "finish_reason": "tool_calls"}]}
        else:
            yield {"choices": [{"delta": {"content":
                "Verified: the requested artifact is correct."}, "finish_reason": "stop"}]}


@pytest.fixture
def private_runtime(tmp_path, monkeypatch):
    """Use real private files and stores while keeping all state under tmp_path."""
    import config
    from agent.permission import authority

    source = tmp_path / "source"
    target = tmp_path / "target"
    project = tmp_path / "project"
    for path in (source, target, project):
        path.mkdir()
    registry = AgentRegistry([
        AgentProfile("src", "Source", str(source), model="src-model", bot_type="fixture"),
        AgentProfile("dst", "Target", str(target), model="dst-model", bot_type="fixture"),
    ], "src")
    set_agent_registry(registry)
    monkeypatch.setattr(runtime, "_registry_profiles", lambda: registry.list(include_disabled=True))
    monkeypatch.setattr(authority, "_registry_profiles", lambda: registry.list(include_disabled=True))
    monkeypatch.setattr(authority, "_current_registry", lambda: registry)
    settings = config.Config({"bot_type": "fixture", "model": "global-model",
                              "agent_workspace": str(project),
                              "subagent": {"enabled": True, "max_depth": 1, "max_concurrent": 1,
                                           "timeout_seconds": 10},
                              "agent_delegation": {"enabled": True, "allowed_targets": {"src": ["dst"]},
                                                   "max_depth": 3, "timeout_seconds": 5}})
    monkeypatch.setattr(config, "config", settings)
    monkeypatch.setattr(session_prefs, "_store_file", lambda: str(tmp_path / "session_prefs.json"))
    monkeypatch.setattr(project_store, "_store_file", lambda: str(tmp_path / "projects.json"))
    monkeypatch.setattr(runtime, "get_task_store", lambda: TaskStore(tmp_path / "journal" / "tasks.db"))
    monkeypatch.setattr("agent.subagent.runner._open_run", lambda *args: None)
    session_prefs.set_prefs("root-session", "src", permission="workspace-write", members=["src", "dst"])
    project_store.set_project_dir("root-session", str(project), "src")
    # The local delegate gets a stable per-target session. Its own current
    # read-only grant and selected project are independently loaded by runtime.
    target_session = AgentDelegateTool._session_id("src", "dst", "root-session")
    session_prefs.set_prefs(target_session, "dst", permission="read-only")
    project_store.set_project_dir(target_session, str(project), "dst")
    store = runtime.get_task_store()
    yield SimpleNamespace(source=source, target=target, project=project, registry=registry,
                          store=store, target_session=target_session)
    set_agent_registry(None)


def _parent(env, model):
    parent = Agent("private fixture parent", model=model, workspace_dir=str(env.source),
                   tools=[Read({"cwd": str(env.project)}), Write({"cwd": str(env.project)})],
                   enable_skills=False, skip_context_files=True, max_steps=8)
    parent._current_agent_id = "src"
    parent._current_session_id = "root-session"
    parent.apply_project_dir(str(env.project))
    parent.permission_mode = "workspace-write"
    parent.authority = Authority("workspace-write",
        frozenset({"fs.read", "fs.write", "subagent.spawn", "delegate.local"}),
        (str(env.project),), (str(env.project),))
    return parent


def _contract(expected_text):
    expected_json = json.loads(expected_text)
    return {
        "acceptance": [{"id": "artifact-content", "type": "json_equals",
                        "path": "artifact.json", "expected": expected_json}],
        "external_state": [{"id": "filesystem-content", "type": "text_equals",
                             "path": "artifact.json", "expected": expected_text}],
    }


@pytest.mark.parametrize(("written", "expected", "acceptance", "external"), [
    ('{"answer":42}', '{"answer":42}', "passed", "confirmed"),
    ('{"answer":0}', '{"answer":42}', "failed", "failed"),
])
def test_native_subagent_reports_execution_acceptance_and_external_state(
        private_runtime, written, expected, acceptance, external):
    env = private_runtime
    model = WritingModel(written)
    parent = _parent(env, model)
    tool = SubagentTool({"cwd": str(env.project)})
    tool.context = parent

    result = tool.execute_tool({"goal": "Write artifact.json, then report the result.",
                                "verification": _contract(expected)})
    assert result.status == ("success" if acceptance == "passed" else "error"), result.result
    payload = json.loads(result.result)
    item = payload["results"][0]
    assert item["execution_status"] == "completed"
    assert item["acceptance_status"] == acceptance
    assert item["external_state_status"] == external
    assert item["verified"] is (acceptance == "passed" and external == "confirmed")
    assert "Execution:" in result.display and "Acceptance:" in result.display
    assert "External state:" in result.display
    assert "verified" in result.display.lower()
    row = env.store.get(item["task_id"])
    assert row["state"] == "completed" and row["attempt_count"] == 1
    assert row["verification"]["acceptance"]["status"] == acceptance
    assert row["verification"]["external_state"]["status"] == external
    assert model.calls == 2


def test_local_delegate_denied_write_does_not_turn_worker_claim_into_acceptance(
        private_runtime, monkeypatch):
    import bridge.agent_bridge as bridge_module

    env = private_runtime
    expected = '{"answer":42}'
    artifact = env.project / "artifact.json"
    artifact.write_text(expected, encoding="utf-8")
    model = WritingModel(expected)
    monkeypatch.setattr(bridge_module, "AgentLLMModel", lambda _bridge: model)
    parent = _parent(env, WritingModel(expected))
    # Keep real session/project configuration. The target's selected session
    # is read-only, so the real tool gateway records the denied write.
    bridge = SimpleNamespace(agent_registry=env.registry, bridge=object(),
                             _cancel_key=lambda agent, token, default: f"{agent}:{token}")
    context = Context(ContextType.TEXT, "task", kwargs={
        "agent_id": "src", "session_id": "root-session", "delegation_members": ["dst"],
        "is_delegated_task": True,
    })
    tool = AgentDelegateTool({"timeout_seconds": 5})
    attach_agent_delegate_to_tool(tool, bridge, context)
    tool.context = parent

    result = tool.execute_tool({"agent_id": "dst", "task": "Write artifact.json and verify it.",
                                "verification": _contract(expected)})
    assert result.status == "error", result.result
    assert "Execution:" in result.display and "Acceptance:" in result.display
    assert "External state:" in result.display
    assert "verified" in result.display.lower()
    assert artifact.read_text(encoding="utf-8") == expected

    rows = env.store.list_tasks()
    assert len(rows) == 1
    row = env.store.get(rows[0]["task_id"])
    assert row["state"] == "completed" and row["attempt_count"] == 1
    effect, = row["attempts"][0]["effects"]
    assert effect["result"]["permission_denied"] is True
    assert row["verification"]["acceptance"]["status"] == "failed"
    assert row["verification"]["acceptance"]["reason"] == "failed_or_denied_tool"
    assert row["verification"]["external_state"]["status"] == "confirmed"
    assert model.calls == 2


@pytest.mark.parametrize("arguments", [
    "{}",
    "{",
    '{"path":"artifact.json","content":null}',
])
def test_rejected_native_write_cannot_use_preexisting_artifact_as_acceptance(
        private_runtime, monkeypatch, arguments):
    import bridge.agent_bridge as bridge_module

    env = private_runtime
    expected = '{"answer":42}'
    artifact = env.project / "artifact.json"
    artifact.write_text(expected, encoding="utf-8")
    # Exercise ordinary current write authority. The failure must come from
    # invalid/rejected tool input, not a permission denial.
    session_prefs.set_prefs(env.target_session, "dst", permission="workspace-write")
    model = WritingModel(expected, arguments=arguments)
    monkeypatch.setattr(bridge_module, "AgentLLMModel", lambda _bridge: model)
    parent = _parent(env, WritingModel(expected))
    bridge = SimpleNamespace(agent_registry=env.registry, bridge=object(),
                             _cancel_key=lambda agent, token, default: f"{agent}:{token}")
    context = Context(ContextType.TEXT, "task", kwargs={
        "agent_id": "src", "session_id": "root-session", "delegation_members": ["dst"],
        "is_delegated_task": True,
    })
    tool = AgentDelegateTool({"timeout_seconds": 5})
    attach_agent_delegate_to_tool(tool, bridge, context)
    tool.context = parent

    result = tool.execute_tool({"agent_id": "dst", "task": "Write artifact.json and verify it.",
                                "verification": _contract(expected)})
    assert result.status == "error", result.result
    assert "Execution: completed" in result.display
    assert "Acceptance: failed" in result.display
    assert "External state: confirmed" in result.display
    assert artifact.read_text(encoding="utf-8") == expected

    rows = env.store.list_tasks()
    assert len(rows) == 1
    row = env.store.get(rows[0]["task_id"])
    assert row["state"] == "completed" and row["attempt_count"] == 1
    effect, = row["attempts"][0]["effects"]
    assert effect["name"] == "write"
    assert effect["mutating"] is (arguments == '{"path":"artifact.json","content":null}')
    assert effect["result"]["status"] == "error"
    if not effect["mutating"]:
        assert effect["result"]["execution_rejected"] is True
    assert row["verification"]["acceptance"]["status"] == "failed"
    assert row["verification"]["acceptance"]["reason"] == "failed_or_denied_tool"
    assert row["verification"]["external_state"]["status"] == "confirmed"
    assert model.calls == 2
