"""Fresh restricted workers must not inherit private runtime state."""
from pathlib import Path

from types import SimpleNamespace

from agent.protocol import Agent, LLMModel
from agent.registry import AgentProfile, AgentRegistry
from agent.subagent.runner import _build_child, SubagentTask
from agent.subagent.templates import GENERAL_PURPOSE
from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool, attach_agent_delegate_to_tool
from agent.tools.read.read import Read
from agent.tools.write.write import Write
from agent.tools.current_time.current_time import TimeTool
from bridge.context import Context, ContextType


def configure_recovery(tmp_path, monkeypatch, registry):
    from agent.recovery.store import TaskStore
    store = TaskStore(tmp_path / "journal" / "tasks.db")
    monkeypatch.setattr("agent.recovery.runtime.get_task_store", lambda: store)
    monkeypatch.setattr("agent.recovery.runtime._registry_profiles", lambda: registry.list(include_disabled=True))
    monkeypatch.setattr("agent.permission.authority._registry_profiles", lambda: registry.list(include_disabled=True))


class Backend(LLMModel):
    def __init__(self):
        super().__init__("local-fixture")
        self.requests = []

    def set_agent_default(self, provider, model):
        self.agent_default = (provider, model)

    def call_stream(self, request):
        self.requests.append(request)
        yield {"choices": [{"delta": {"content": "fixture done"}, "finish_reason": "stop"}]}


def make_parent(root):
    model = Backend()
    agent = Agent("parent private prompt", model=model,
                  tools=[Read({"cwd": str(root)}), Write({"cwd": str(root)}), TimeTool()],
                  workspace_dir=str(root), enable_skills=False, max_steps=2, output_mode="logger")
    agent.permission_mode = "workspace-write"
    agent.runtime_info = {"secret": "PRIVATE_RUNTIME"}
    agent.messages = [{"role": "user", "content": "PRIVATE_HISTORY"}]
    return agent


def test_subagent_fresh_runtime_and_no_copied_managers(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("agent.tools.ToolManager.sync_mcp_into_agent", lambda *a: calls.append("MCP sync"))
    (tmp_path / "AGENT.md").write_text("PRIVATE_CONTEXT")
    parent = make_parent(tmp_path)
    parent.tools[1].memory_manager = object()
    child = _build_child(parent, GENERAL_PURPOSE, SubagentTask("do task"))
    assert child.authority.restricted
    assert child.memory_manager is None and child.skill_manager is None
    assert child.runtime_info is None and child.messages == []
    assert child.tools[1] is not parent.tools[1] and child.tools[1].memory_manager is None
    assert "PRIVATE_CONTEXT" not in child.get_full_system_prompt()
    assert child.run_stream("do task") == "fixture done"
    assert calls == []
    assert "PRIVATE_HISTORY" not in str([request.__dict__ for request in parent.model.requests])
    assert "PRIVATE_RUNTIME" not in str([request.__dict__ for request in parent.model.requests])


def test_local_delegate_runs_fresh_without_receiver_initializer(tmp_path, monkeypatch):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir(); dst.mkdir()
    (dst / "AGENT.md").write_text("RECEIVER_PRIVATE")
    parent = make_parent(src)
    registry = AgentRegistry([AgentProfile("src", "Source", str(src)),
                              AgentProfile("dst", "Target", str(dst), model="target-model", bot_type="target-provider")], "src")
    bridge = SimpleNamespace(agent_registry=registry, bridge=object(),
                             _cancel_key=lambda a, token, default: f"{a}:{token}")
    bridge.agent_reply = lambda *a, **k: (_ for _ in ()).throw(AssertionError("initializer reached"))
    configure_recovery(tmp_path, monkeypatch, registry)
    monkeypatch.setattr("agent.workspace.project_store.get_project_dir_strict", lambda *a: None)
    monkeypatch.setattr("agent.workspace.session_prefs.get_prefs_strict", lambda *a: {"members": ["dst"], "permission": "workspace-write"})
    monkeypatch.setattr("agent.subagent.runner._open_run", lambda *a: None)
    receiver_model = Backend()
    monkeypatch.setattr("bridge.agent_bridge.AgentLLMModel", lambda bridge: receiver_model)
    ctx = Context(ContextType.TEXT, "task", kwargs={"agent_id": "src", "session_id": "s",
                  "delegation_members": ["dst"], "is_delegated_task": True})
    tool = AgentDelegateTool({"timeout_seconds": 5})
    attach_agent_delegate_to_tool(tool, bridge, ctx)
    denied = tool.execute({"agent_id": "dst", "task": "do task"})
    assert denied.status == "error" and not receiver_model.requests
    tool.context = parent
    result = tool.execute({"agent_id": "dst", "task": "do task"})
    assert result.status == "success", result.result
    assert result.result["content"] == "fixture done"
    assert receiver_model.agent_default == ("target-provider", "target-model")
    assert receiver_model.requests
    assert "RECEIVER_PRIVATE" not in str([request.__dict__ for request in receiver_model.requests])
    assert "PRIVATE_HISTORY" not in str([request.__dict__ for request in receiver_model.requests])


def test_inbound_delegation_rejected_before_runtime():
    from agent.multiagent.inbound import serve_invoke
    chunks = []
    for mode in ("delegate", "speak", "clear"):
        serve_invoke({"mode": mode, "task": "x", "target_agent_id": "x"},
                     object(), chunks.append)
    assert all(c["status"] == "failed" and "authority protocol" in c["error"] for c in chunks)


def test_delegated_write_uses_shared_root_and_readonly_denies(tmp_path, monkeypatch):
    import json

    class WriteBackend(Backend):
        def __init__(self):
            super().__init__()
            self.turn = 0

        def call_stream(self, request):
            self.requests.append(request)
            self.turn += 1
            if self.turn == 1:
                yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call-1",
                    "function": {"name": "write", "arguments": json.dumps(
                        {"path": "result.txt", "content": "allowed"})}}]},
                    "finish_reason": "tool_calls"}]}
            else:
                yield {"choices": [{"delta": {"content": "done"}, "finish_reason": "stop"}]}

    shared = tmp_path / "shared"
    shared.mkdir()
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir(); target.mkdir()
    parent = make_parent(source)
    parent.apply_project_dir(str(shared))
    parent.max_steps = 8
    registry = AgentRegistry([AgentProfile("src", "Source", str(source)),
                              AgentProfile("dst", "Target", str(target))], "src")
    bridge = SimpleNamespace(agent_registry=registry, bridge=object(),
                             _cancel_key=lambda a, token, default: f"{a}:{token}")
    configure_recovery(tmp_path, monkeypatch, registry)
    monkeypatch.setattr("agent.workspace.project_store.get_project_dir_strict", lambda *a: str(shared))
    monkeypatch.setattr("agent.workspace.session_prefs.get_prefs_strict", lambda *a: {"permission": "workspace-write", "members": ["dst"]})
    monkeypatch.setattr("agent.subagent.runner._open_run", lambda *a: None)
    models = []
    def model_factory(_bridge):
        model = WriteBackend()
        models.append(model)
        return model
    monkeypatch.setattr("bridge.agent_bridge.AgentLLMModel", model_factory)
    ctx = Context(ContextType.TEXT, "task", kwargs={"agent_id": "src", "session_id": "s",
                  "delegation_members": ["dst"], "is_delegated_task": True})
    tool = AgentDelegateTool({"timeout_seconds": 5})
    attach_agent_delegate_to_tool(tool, bridge, ctx)
    tool.context = parent
    assert tool.execute({"agent_id": "dst", "task": "write"}).status == "success"
    assert (shared / "result.txt").read_text() == "allowed"
    (shared / "result.txt").unlink()
    parent.permission_mode = "read-only"
    denied = tool.execute({"agent_id": "dst", "task": "write"})
    assert denied.status == "error"
    assert denied.result['execution_status'] == 'completed'
    assert denied.result['acceptance_status'] == 'failed'
    assert denied.result['external_state_status'] == 'unverified'
    assert not (shared / "result.txt").exists()
    assert "denied" in str(models[-1].requests[-1].messages).lower()


def test_subagents_get_separate_scratch_and_explicit_roots(tmp_path):
    from agent.permission import invoke
    from agent.tools.base_tool import ToolResult

    parent = make_parent(tmp_path)
    one = _build_child(parent, GENERAL_PURPOSE, SubagentTask("one"))
    two = _build_child(parent, GENERAL_PURPOSE, SubagentTask("two"))
    assert one.task_workspace and two.task_workspace and one.task_workspace != two.task_workspace
    assert one.authority.write_roots == (one.task_workspace,)
    first_write = next(t for t in one.tools if t.name == "write")
    first_read = next(t for t in one.tools if t.name == "read")
    assert invoke(first_write, {"path": "a.txt", "content": "one"}, one).status == "success"
    denied = invoke(first_read, {"path": str(Path(two.task_workspace) / "a.txt")}, one)
    assert isinstance(denied, ToolResult) and denied.status == "error"
    shared = _build_child(parent, GENERAL_PURPOSE,
                          SubagentTask("shared", read_roots=(str(tmp_path),)))
    read = next(t for t in shared.tools if t.name == "read")
    assert invoke(read, {"path": str(Path(one.task_workspace) / "a.txt")}, shared).status == "success"


def test_readonly_subagent_has_no_implicit_scratch(tmp_path):
    parent = make_parent(tmp_path)
    parent.permission_mode = "read-only"
    child = _build_child(parent, GENERAL_PURPOSE, SubagentTask("read-only"))
    assert child.task_workspace is None
    assert not child.authority.read_roots and not child.authority.write_roots
    assert not list(tmp_path.iterdir())


def test_cached_agent_refuses_corrupt_authority_settings(tmp_path, monkeypatch):
    import json
    import threading
    import pytest
    from bridge.agent_bridge import AgentBridge, SessionAuthorityError
    from bridge.reply import ReplyType
    from agent.workspace import project_store, session_prefs

    project_file = tmp_path / "projects.json"
    prefs_file = tmp_path / "prefs.json"
    monkeypatch.setattr(project_store, "_store_file", lambda: str(project_file))
    monkeypatch.setattr(session_prefs, "_store_file", lambda: str(prefs_file))
    monkeypatch.setattr("agent.permission.authority._registry_profiles", lambda: [])
    agent = make_parent(tmp_path)
    bridge = AgentBridge.__new__(AgentBridge)
    bridge.agent_registry = AgentRegistry([AgentProfile("src", "Source", str(tmp_path))], "src")
    bridge._agents_lock = threading.RLock()
    bridge._agent_instances = {("src", "session"): agent}
    bridge.agents = {}
    stale = tmp_path / "stale-project"
    stale.mkdir()
    agent.apply_project_dir(str(stale))
    agent.permission_mode = "full-access"

    # A stale cached project must never be returned as an executable agent.
    project_file.write_text('{"sessions":')
    with pytest.raises(SessionAuthorityError, match="project authority unavailable") as err:
        bridge.get_agent("session", "src")
    assert str(tmp_path) not in str(err.value)
    assert agent.model.requests == []
    monkeypatch.setattr(bridge, "route_context", lambda context: "src")
    monkeypatch.setattr(bridge, "_seed_team_members", lambda *args: None)
    monkeypatch.setattr(bridge, "_peer_speaker", lambda *args: None)
    monkeypatch.setattr(bridge, "_resolve_speaker", lambda *args: "src")
    monkeypatch.setattr(bridge, "_end_run", lambda *args: None)
    context = Context(ContextType.TEXT, "task", kwargs={"agent_id": "src", "session_id": "session"})
    reply = bridge.agent_reply("task", context=context)
    assert reply.type == ReplyType.ERROR
    assert "project authority unavailable" in reply.content
    assert str(tmp_path) not in reply.content and agent.model.requests == []

    project_file.write_text(json.dumps({"sessions": {}}))
    prefs_file.write_text('{"sessions":')
    with pytest.raises(SessionAuthorityError, match="permission authority unavailable") as err:
        bridge.get_agent("session", "src")
    assert str(tmp_path) not in str(err.value)
    assert agent.model.requests == []

    prefs_file.write_text(json.dumps({"sessions": {"src::session": {"permission": "invalid"}}}))
    with pytest.raises(SessionAuthorityError, match="permission authority unavailable"):
        bridge.get_agent("session", "src")

    prefs_file.write_text(json.dumps({"sessions": {"src::session": {"permission": "read-only"}}}))
    restored = bridge.get_agent("session", "src")
    assert restored is agent and restored.project_dir is None
    assert restored.effective_permission_mode() == "read-only"


def test_selected_missing_project_fails_closed(tmp_path, monkeypatch):
    import json
    import pytest
    from agent.workspace import project_store
    file = tmp_path / "projects.json"
    file.write_text(json.dumps({"sessions": {"src::s": {"path": str(tmp_path / "missing")}}}))
    monkeypatch.setattr(project_store, "_store_file", lambda: str(file))
    with pytest.raises(ValueError):
        project_store.get_project_dir_strict("s", "src")


def test_receiver_keeps_its_exclusion_for_source_private_workspace(tmp_path, monkeypatch):
    import json
    src = tmp_path / "source"; src.mkdir()
    dst = tmp_path / "target"; dst.mkdir()
    secret = src / "private.txt"; secret.write_text("FICTIONAL_SOURCE_PRIVATE")
    parent = make_parent(src)
    parent._current_agent_id = "src"
    parent.project_dir = str(tmp_path)
    registry = AgentRegistry([AgentProfile("src", "Source", str(src)),
                              AgentProfile("dst", "Target", str(dst))], "src")
    monkeypatch.setattr("agent.permission.authority._registry_profiles",
                        lambda: registry.list(include_disabled=True))
    bridge = SimpleNamespace(agent_registry=registry, bridge=object(),
                             _cancel_key=lambda a, token, default: f"{a}:{token}")
    configure_recovery(tmp_path, monkeypatch, registry)
    monkeypatch.setattr("agent.workspace.project_store.get_project_dir_strict", lambda *a: str(tmp_path))
    monkeypatch.setattr("agent.workspace.session_prefs.get_prefs_strict", lambda *a: {"permission": "workspace-write", "members": ["dst"]})
    monkeypatch.setattr("agent.subagent.runner._open_run", lambda *a: None)
    class Receiver(Backend):
        def call_stream(self, request):
            from common.runtime_identity import current_agent_id
            assert current_agent_id() == "dst"
            self.requests.append(request)
            if len(self.requests) == 1:
                yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "fixture",
                    "function": {"name": "read", "arguments": json.dumps({"path": str(secret)})}}]},
                    "finish_reason": "tool_calls"}]}
            else:
                yield {"choices": [{"delta": {"content": "denial observed"}, "finish_reason": "stop"}]}
    model = Receiver()
    monkeypatch.setattr("bridge.agent_bridge.AgentLLMModel", lambda *a: model)
    ctx = Context(ContextType.TEXT, "task", kwargs={"agent_id": "src", "session_id": "s",
                  "delegation_members": ["dst"], "is_delegated_task": True})
    tool = AgentDelegateTool({"timeout_seconds": 5})
    attach_agent_delegate_to_tool(tool, bridge, ctx)
    tool.context = parent
    result = tool.execute_tool({"agent_id": "dst", "task": "inspect requested file"})
    assert result.status == "error", result.result
    assert result.result['execution_status'] == 'completed'
    assert result.result['acceptance_status'] == 'failed'
    assert result.result['external_state_status'] == 'unverified'
    assert len(model.requests) == 2
    captured = str([r.__dict__ for r in model.requests])
    assert "FICTIONAL_SOURCE_PRIVATE" not in captured
    assert "private_state" in captured
