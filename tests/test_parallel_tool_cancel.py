"""A cancel ends the parallel tool prefetch without waiting for the slow calls."""

import threading
import time
import os

import pytest

from agent.permission.policy import READ_ONLY
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.tools.base_tool import ToolResult
from agent.tools.subagent.subagent import SubagentTool


class _ReadOnlySession:
    def effective_permission_mode(self):
        return READ_ONLY

    def effective_cwd(self):
        return os.getcwd()

    def protected_paths(self):
        return []


def _executor(tool, cancel_event=None):
    executor = object.__new__(AgentStreamExecutor)
    executor.tools = {tool.name: tool}
    executor.model = None
    executor.agent = _ReadOnlySession()
    executor.cancel_event = cancel_event
    executor._record_tool_result = lambda *a, **kw: None
    executor._check_consecutive_failures = lambda *a, **kw: (False, None, False)
    executor._emit_event = lambda *a, **kw: None
    return executor


def _calls(tags):
    return [
        {"id": f"call_{i}", "name": "subagent", "arguments": {"goal": tag}}
        for i, tag in enumerate(tags)
    ]


def _install_gated_execute(monkeypatch, release, quick=()):
    finished = []
    quick = set(quick)

    def execute(self, params):
        tag = params["goal"]
        if tag == "boom":
            raise RuntimeError("boom")
        if tag not in quick:
            release.wait(timeout=30)
        finished.append(tag)
        return ToolResult.success(tag)

    monkeypatch.setattr(SubagentTool, "execute", execute)
    return finished


@pytest.fixture
def release():
    event = threading.Event()
    yield event
    event.set()


def test_cancel_returns_while_a_worker_is_still_running(release, monkeypatch):
    cancel = threading.Event()
    tool = SubagentTool()
    finished = _install_gated_execute(monkeypatch, release, quick={"quick"})
    threading.Timer(0.3, cancel.set).start()

    started = time.time()
    results = _executor(tool, cancel)._run_parallel_calls(_calls(["quick", "stuck"]))

    assert time.time() - started < 5
    assert finished == ["quick"]
    assert results["call_0"]["status"] == "success" and results["call_0"]["result"] == "quick"
    assert results["call_1"]["status"] == "error" and "discarded" in results["call_1"]["result"]


def test_without_a_cancel_every_call_is_waited_for(release, monkeypatch):
    tool = SubagentTool()
    finished = _install_gated_execute(monkeypatch, release)
    threading.Timer(0.1, release.set).start()
    results = _executor(tool, threading.Event())._run_parallel_calls(_calls(["t0", "t1"]))
    assert sorted(r["result"] for r in results.values()) == ["t0", "t1"]
    assert sorted(finished) == ["t0", "t1"]


def test_a_raising_call_keeps_its_error_to_its_own_id(release, monkeypatch):
    release.set()
    tool = SubagentTool()
    finished = _install_gated_execute(monkeypatch, release)
    results = _executor(tool)._run_parallel_calls(_calls(["boom", "t1"]))
    assert results["call_0"]["status"] == "error"
    assert results["call_0"]["result"] == "Authorization or execution failed."
    assert "boom" not in results["call_0"]["result"]
    assert results["call_1"]["result"] == "t1"
    assert finished == ["t1"]
