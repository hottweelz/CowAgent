"""Several calls to one parallel-safe tool in a single turn.

Tools run in the order the model asked for them, which is what most of them
need. A model handed two independent jobs expresses that as two calls, though,
and for a tool whose whole point is that its calls are independent, running the
second only after the first finishes doubles the wait for nothing.
"""

import os
import threading
import time

from agent.permission.policy import READ_ONLY
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.tools.current_time.current_time import TimeTool
from agent.tools.subagent.subagent import SubagentTool
from agent.tools.base_tool import ToolResult


class _ReadOnlySession:
    """Minimal valid session for the real permission evaluator."""

    def effective_permission_mode(self):
        return READ_ONLY

    def effective_cwd(self):
        return os.getcwd()

    def protected_paths(self):
        return []


def _executor(tool):
    executor = object.__new__(AgentStreamExecutor)
    executor.tools = {tool.name: tool}
    executor.model = None
    executor.agent = _ReadOnlySession()
    executor.cancel_event = None
    executor._record_tool_result = lambda *a, **kw: None
    executor._check_consecutive_failures = lambda *a, **kw: (False, None, False)
    executor._emit_event = lambda *a, **kw: None
    return executor


def _calls(name, count):
    return [
        {"id": f"call_{i}", "name": name, "arguments": {"tag": f"t{i}"}}
        for i in range(count)
    ]


def test_parallel_safe_calls_run_at_the_same_time(monkeypatch):
    tool = SubagentTool()

    def execute(self, params):
        time.sleep(0.3)
        return ToolResult.success(params["tag"])

    monkeypatch.setattr(SubagentTool, "execute", execute)
    executor = _executor(tool)

    started = time.time()
    results = executor._run_parallel_calls(_calls(tool.name, 3))
    elapsed = time.time() - started

    assert sorted(results) == ["call_0", "call_1", "call_2"]
    assert [results[k]["result"] for k in sorted(results)] == ["t0", "t1", "t2"]
    # Serial would be 3 * delay; anything under two delays can only be overlap.
    assert elapsed < 0.6


def test_each_parallel_call_gets_its_own_tool_instance(monkeypatch):
    """Concurrent calls need distinct tool state for cancellation and progress."""
    tool = SubagentTool()
    instances = []

    def execute(self, params):
        instances.append(self)
        time.sleep(0.1)
        return ToolResult.success(params["tag"])

    monkeypatch.setattr(SubagentTool, "execute", execute)
    executor = _executor(tool)

    executor._run_parallel_calls(_calls(tool.name, 2))

    assert len(instances) == 2
    first, second = instances
    assert first is not second
    assert tool not in instances


def test_ordinary_tools_keep_running_in_order():
    tool = TimeTool()
    executor = _executor(tool)

    assert executor._run_parallel_calls(_calls(tool.name, 3)) == {}


def test_a_lone_call_is_left_to_the_caller(monkeypatch):
    """No overlap means no pool and no loss of the caller's cancel checkpoint."""
    tool = SubagentTool()
    calls = []
    monkeypatch.setattr(SubagentTool, "execute", lambda self, params: calls.append(params))
    executor = _executor(tool)

    assert executor._run_parallel_calls(_calls(tool.name, 1)) == {}
    assert calls == []


def test_a_failing_call_does_not_take_its_siblings_down(monkeypatch):
    tool = SubagentTool()

    def execute(self, params):
        if params["tag"] == "t0":
            raise RuntimeError("boom")
        return ToolResult.success(params["tag"])

    monkeypatch.setattr(SubagentTool, "execute", execute)
    executor = _executor(tool)

    results = executor._run_parallel_calls(_calls(tool.name, 2))

    assert len(results) == 2
    assert results["call_1"]["result"] == "t1"


def test_two_calls_are_in_flight_together(monkeypatch):
    """A barrier proves that both calls enter execute before either can leave."""
    barrier = threading.Barrier(2, timeout=3)
    threads = []
    tool = SubagentTool()

    def execute(self, params):
        threads.append(threading.current_thread())
        barrier.wait()
        return ToolResult.success(params["tag"])

    monkeypatch.setattr(SubagentTool, "execute", execute)
    executor = _executor(tool)
    results = executor._run_parallel_calls(_calls(tool.name, 2))

    assert [r["status"] for r in results.values()] == ["success", "success"]
    assert threading.current_thread() not in threads
