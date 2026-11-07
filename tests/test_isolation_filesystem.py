"""Real file effects through the restricted gateway, all under tmp_path."""
import json
import os
import threading
from types import SimpleNamespace

import pytest

from agent.permission import Authority
from agent.permission.filesystem import FileBroker, execute_file
from agent.protocol import Agent, LLMModel
from agent.tools.read.read import Read
from agent.tools.write.write import Write
from agent.tools.edit.edit import Edit
from agent.tools.ls.ls import Ls
from agent.tools.search_files.search_files import SearchFiles
from agent.tools.bash.bash import Bash


@pytest.fixture(autouse=True)
def private_config(tmp_path, monkeypatch):
    import config
    monkeypatch.setenv("COW_DATA_DIR", str(tmp_path / "host-state"))
    monkeypatch.setattr(config, "config", config.Config({
        "agent_workspace": str(tmp_path / "host-state"), "knowledge": False,
        "agent_permission_mode": "workspace-write", "self_evolution_enabled": False,
    }))
    monkeypatch.setattr("agent.permission.authority._registry_profiles", lambda: [])
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("network call"))


def binding(root, mode="workspace-write", denied=()):
    root = str(root.resolve())
    authority = Authority(mode, frozenset({"fs.read", "fs.write"}), (root,),
                          () if mode == "read-only" else (root,), tuple(map(str, denied)))
    return SimpleNamespace(authority=authority, effective_cwd=lambda: root,
                           effective_permission_mode=lambda: mode)


def call(cls, context, arguments):
    tool = cls({"cwd": context.effective_cwd()})
    tool.context = context
    return tool.execute_tool(arguments)


def test_authorized_write_edit_read_and_native_search(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("process created"))
    ws = tmp_path / "workspace"
    ws.mkdir()
    agent = binding(ws)
    assert call(Write, agent, {"path": "nested/a.txt", "content": "Shipment 42"}).status == "success"
    assert call(Edit, agent, {"path": "nested/a.txt", "oldText": "42", "newText": "43"}).status == "success"
    assert (ws / "nested/a.txt").read_text() == "Shipment 43"
    assert "Shipment 43" in str(call(Read, agent, {"path": "nested/a.txt"}).result)
    assert "nested/" in str(call(Ls, agent, {}).result)
    result = call(SearchFiles, agent, {"pattern": "Shipment", "file_glob": "*.txt"})
    assert result.status == "success" and "Shipment 43" in str(result.result)
    assert result.result["backend"] == "restricted-native"
    assert call(SearchFiles, agent, {"pattern": "shipment"}).result["match_count"] == 0
    assert call(SearchFiles, agent, {"pattern": "shipment", "ignore_case": True}).result["match_count"] == 1
    assert call(SearchFiles, agent, {"pattern": "a.txt", "target": "files"}).result["match_count"] == 1


@pytest.mark.parametrize("kind", ["outside", "symlink", "directory_symlink", "hardlink", "private"])
def test_private_files_cannot_be_read_edited_or_overwritten(tmp_path, kind):
    ws = tmp_path / "worker"
    sibling = tmp_path / "sibling"
    ws.mkdir(); sibling.mkdir()
    secret = sibling / "credential.txt"
    secret.write_text("FICTIONAL_PRIVATE_CREDENTIAL")
    agent = binding(ws)
    target = secret
    if kind == "symlink":
        target = ws / "alias.txt"; target.symlink_to(secret)
    elif kind == "directory_symlink":
        (ws / "alias").symlink_to(sibling, target_is_directory=True)
        target = ws / "alias/credential.txt"
    elif kind == "hardlink":
        target = ws / "alias.txt"; os.link(secret, target)
    elif kind == "private":
        target = ws / ".env"
        target.write_text("FICTIONAL_PRIVATE_CREDENTIAL")
    for cls, extra in [(Read, {}), (Write, {"content": "changed"}),
                       (Edit, {"oldText": "FICTIONAL_PRIVATE_CREDENTIAL", "newText": "changed"})]:
        result = call(cls, agent, {"path": str(target), **extra})
        assert result.status == "error"
        assert "FICTIONAL_PRIVATE_CREDENTIAL" not in str(result.result)
    assert secret.read_text() == "FICTIONAL_PRIVATE_CREDENTIAL"
    result = call(SearchFiles, agent, {"pattern": "FICTIONAL"})
    assert result.status == "success" and result.result["match_count"] == 0


def test_reserved_state_and_explicit_sibling_subtree_remain_private(tmp_path):
    ws = tmp_path / "workspace"; ws.mkdir()
    sibling = ws / "custom-peer"; sibling.mkdir()
    (sibling / "private.txt").write_text("FICTIONAL_PRIVATE")
    for name in ["memory", "skills", "knowledge", "agents", ".git", "scheduler",
                 "runs", "subagents", "system", "users", "backups", "logs"]:
        (ws / name).mkdir(); (ws / name / "private.txt").write_text("FICTIONAL_PRIVATE")
    agent = binding(ws, denied=(sibling,))
    assert call(Read, agent, {"path": str(sibling / "private.txt")}).status == "error"
    assert "FICTIONAL_PRIVATE" not in str(call(SearchFiles, agent, {"pattern": "FICTIONAL"}).result)
    for name in ["AGENT.md", "MEMORY.md", "mcp.json", "config.json", "foo.db"]:
        assert call(Write, agent, {"path": name, "content": "{}"}).status == "error"
        assert not (ws / name).exists()


def test_private_path_case_and_unicode_aliases_fail_closed(tmp_path):
    import unicodedata
    private = tmp_path / "PrivatéSibling"
    private.mkdir()
    target = private / "secret.txt"
    target.write_text("FICTIONAL_PRIVATE")
    context = binding(tmp_path, denied=(private,))
    for directory in ("privatésibling", unicodedata.normalize("NFD", "PRIVATÉSIBLING")):
        alias = tmp_path / directory / "secret.txt"
        assert call(Read, context, {"path": str(alias)}).status == "error"
        assert call(Write, context, {"path": str(alias), "content": "changed"}).status == "error"
    assert target.read_text() == "FICTIONAL_PRIVATE"


def test_child_cannot_plant_scheduled_work_or_grant_private_state(tmp_path):
    from agent.subagent.runner import _build_child, SubagentTask
    from agent.subagent.templates import GENERAL_PURPOSE
    from agent.permission.filesystem import FileDenied
    from agent.tools.scheduler.task_store import TaskStore
    parent = Agent("fixture", tools=[Write({"cwd": str(tmp_path)})],
                   workspace_dir=str(tmp_path), enable_skills=False, skip_context_files=True)
    parent.permission_mode = "workspace-write"
    parent._current_agent_id = "owner"
    child = _build_child(parent, GENERAL_PURPOSE, SubagentTask(
        "write only permitted artifacts", read_roots=(str(tmp_path),), write_roots=(str(tmp_path),)))
    child.tools[0].context = child
    scheduled = tmp_path / "scheduler/tasks.json"
    payload = json.dumps({"version": 1, "tasks": {"fictional": {
        "id": "fictional", "agent_id": "owner", "action": {"type": "agent_task",
        "channel_type": "web", "receiver": "fictional", "task_description": "fixture",
        "permission_mode": "full-access", "silent": True}}}})
    result = child.tools[0].execute_tool({"path": str(scheduled), "content": payload})
    assert result.status == "error" and not scheduled.exists()
    assert "fictional" not in TaskStore(str(scheduled)).load_tasks()
    with pytest.raises(FileDenied):
        _build_child(parent, GENERAL_PURPOSE, SubagentTask(
            "request private directory", read_roots=(str(scheduled.parent),)))


@pytest.mark.parametrize("mode", ["read-only", "workspace-write"])
def test_shell_python_background_and_cancel_never_create_process(tmp_path, monkeypatch, mode):
    marker = tmp_path / "escape"
    context = binding(tmp_path, mode)
    monkeypatch.setenv("FICTIONAL_PROVIDER_KEY", "NEVER_INHERIT")
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("untrusted process created"))
    monkeypatch.setattr("agent.tools.bash.bash.expand_path", lambda *a: pytest.fail("credential path read"))
    tool = Bash({"cwd": str(tmp_path)})
    tool.context = context
    for args in [{"command": f"printf bad > {marker}"},
                 {"command": f"python -c 'open({str(marker)!r},\"w\").write(\"bad\")'"},
                 {"command": "sleep 90", "run_in_background": True}, {"bash_id": "foreign-job", "kill": True}]:
        assert tool.execute_tool(args).status == "error"
    tool.cancel_event = threading.Event(); tool.cancel_event.set()
    assert tool.execute_tool({"command": "sleep 90"}).status == "error"
    assert not marker.exists()
    result = call(Write, context, {"path": "readonly.txt", "content": "bad"})
    if mode == "read-only":
        assert result.status == "error" and not (tmp_path / "readonly.txt").exists()


def test_cancellation_before_atomic_replace_preserves_previous_file(tmp_path, monkeypatch):
    agent = binding(tmp_path)
    target = tmp_path / "out.txt"; target.write_text("before")
    cancel = threading.Event()
    original = os.fsync
    def cancel_after_flush(fd):
        original(fd)
        cancel.set()
    monkeypatch.setattr(os, "fsync", cancel_after_flush)
    result = execute_file("write", {"path": "out.txt", "content": "after"},
                          agent.authority, str(tmp_path), cancel)
    assert result.status == "error" and result.ext_data["code"] == "cancelled"
    assert target.read_text() == "before"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out.txt"]


def test_host_source_write_denied_without_touching_checkout():
    from agent.permission.filesystem import _SOURCE_ROOT, FileDenied
    context = binding(__import__("pathlib").Path(_SOURCE_ROOT))
    with pytest.raises(FileDenied, match="host_source_protected"):
        FileBroker(context.authority, _SOURCE_ROOT).locate("agent/fictional.py", write=True)


def test_real_agent_stream_denial_has_no_file_effect(tmp_path):
    class Script(LLMModel):
        def __init__(self):
            super().__init__("local-fictional"); self.calls = 0
        def call_stream(self, request):
            self.calls += 1
            if self.calls == 1:
                yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "fixture",
                    "function": {"name": "write", "arguments": json.dumps({
                        "path": str(tmp_path / "sibling.txt"), "content": "bad"})}}]},
                    "finish_reason": "tool_calls"}]}
            else:
                yield {"choices": [{"delta": {"content": "denial observed"}, "finish_reason": "stop"}]}
    ws = tmp_path / "task"; ws.mkdir()
    agent = Agent("synthetic task", model=Script(), tools=[Write({"cwd": str(ws)})],
                  workspace_dir=str(ws), enable_skills=False, skip_context_files=True,
                  max_steps=3, output_mode="logger")
    agent.permission_mode = "workspace-write"
    events = []
    assert agent.run_stream("try assigned operation", on_event=events.append) == "denial observed"
    assert not (tmp_path / "sibling.txt").exists()
    ends = [e["data"] for e in events if e["type"] == "tool_execution_end"]
    assert ends and ends[0]["status"] == "error"


def test_owner_indexed_memory_survives_reopen_through_gateway(tmp_path):
    from agent.memory.config import MemoryConfig
    from agent.memory.manager import MemoryManager
    from agent.tools.memory.memory_search import MemorySearchTool
    workspace = tmp_path / "owner"
    (workspace / "memory").mkdir(parents=True)
    (workspace / "memory/fixture.md").write_text("# Fixture\nQUARTZISOLATION7381 indexed fact\n")
    for _ in range(3):
        manager = MemoryManager(MemoryConfig(workspace_root=str(workspace)), embedding_provider=None)
        try:
            import asyncio
            asyncio.run(manager.sync())
            assert manager.storage.fts5_available
            assert manager.storage.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            statements = []
            manager.storage.conn.set_trace_callback(statements.append)
            owner = Agent("fictional owner", tools=[], workspace_dir=str(workspace),
                          enable_skills=False, skip_context_files=True)
            owner.permission_mode = "full-access"
            tool = MemorySearchTool(manager)
            tool.context = owner
            result = tool.execute_tool({"query": "QUARTZISOLATION7381", "min_score": 0})
            assert result.status == "success" and "indexed fact" in str(result.result)
            assert any(" MATCH " in sql.upper() for sql in statements)
            assert not any(" LIKE " in sql.upper() for sql in statements)
            assert manager.storage.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            manager.close()
