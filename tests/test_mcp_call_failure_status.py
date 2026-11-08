"""MCP transport results and authorized executor result handling are separate."""
import os
import sys
from contextlib import contextmanager

import pytest

from agent.permission.policy import READ_ONLY
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.tools.base_tool import ToolResult
from agent.tools.mcp.mcp_client import McpClient
from agent.tools.mcp.mcp_tool import McpTool
from agent.tools.subagent.subagent import SubagentTool


_SERVER = """
import json, sys, time
mode = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    if 'id' not in request:
        continue
    if request['method'] == 'initialize':
        response = {'result': {'protocolVersion': '2024-11-05', 'capabilities': {},
                              'serverInfo': {'name': 'fixture', 'version': '1'}}}
    elif mode == 'disconnect':
        sys.exit(0)
    elif mode == 'timeout':
        time.sleep(5)
        continue
    elif mode == 'rpc-error':
        response = {'error': {'code': -32603, 'message': 'fixture backend unavailable'}}
    else:
        text = 'Error: is ordinary document text' if mode == 'error-text' else 'fixture success'
        response = {'result': {'content': [{'type': 'text', 'text': text}]}}
    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], **response}), flush=True)
"""


class _ReadOnlySession:
    """Valid session authority for the registered executor stub."""

    def effective_permission_mode(self):
        return READ_ONLY

    def effective_cwd(self):
        return os.getcwd()

    def protected_paths(self):
        return []


@contextmanager
def native_tool_for(mode):
    client = McpClient({
        "name": "failure-fixture", "type": "stdio", "command": sys.executable,
        "args": ["-u", "-c", _SERVER, mode], "timeout": 1,
    })
    assert client.initialize()
    child = client._proc
    tool = McpTool(client, {"name": "fixture", "inputSchema": {"type": "object"}}, "failure-fixture")
    try:
        yield tool
    finally:
        client.shutdown()
        assert child.poll() is not None


def executor_for(result_factory, monkeypatch):
    """Pass a controlled ToolResult through a registered, authorized tool."""
    calls = []

    def execute(self, params):
        calls.append(params)
        return result_factory()

    monkeypatch.setattr(SubagentTool, "execute", execute)
    events = []
    executor = AgentStreamExecutor(
        agent=_ReadOnlySession(), model=None, system_prompt="",
        tools=[SubagentTool()], on_event=events.append,
    )
    return executor, events, calls


def _call(call_id="call"):
    return {"id": call_id, "name": "subagent", "arguments": {"goal": "fixture"}}


@pytest.mark.parametrize("mode, detail", [
    ("rpc-error", "fixture backend unavailable"),
    ("disconnect", "closed unexpectedly"),
    ("timeout", "timed out"),
])
def test_native_call_failure_reaches_mcp_tool_status(mode, detail):
    with native_tool_for(mode) as tool:
        result = tool.execute({})
        assert result.status == "error", result.result
        assert detail in result.result


@pytest.mark.parametrize("detail", [
    "fixture backend unavailable",
    "closed unexpectedly",
    "timed out",
])
def test_authorized_failure_result_reaches_executor_status(detail, monkeypatch):
    executor, events, calls = executor_for(lambda: ToolResult.fail(detail), monkeypatch)
    result = executor._execute_tool(_call())
    assert calls == [{"goal": "fixture"}]
    assert result["status"] == "error", result
    assert detail in result["result"]
    assert executor.tool_failure_history[-1][2] is False
    end = [event["data"] for event in events if event["type"] == "tool_execution_end"]
    assert len(end) == 1
    assert end[0]["status"] == "error"
    assert detail in end[0]["result"]


@pytest.mark.parametrize("mode, text", [
    ("success", "fixture success"),
    ("error-text", "Error: is ordinary document text"),
])
def test_native_success_text_is_not_classified_by_prefix(mode, text):
    with native_tool_for(mode) as tool:
        result = tool.execute({})
        assert result.status == "success"
        assert result.result == text


@pytest.mark.parametrize("text", ["fixture success", "Error: is ordinary document text"])
def test_authorized_success_text_is_not_classified_by_prefix(text, monkeypatch):
    executor, events, calls = executor_for(lambda: ToolResult.success(text), monkeypatch)
    result = executor._execute_tool(_call())
    assert calls == [{"goal": "fixture"}]
    assert result["status"] == "success"
    assert result["result"] == text
    assert executor.tool_failure_history[-1][2] is True
    assert events[-1]["data"]["status"] == "success"


def test_authorized_failures_activate_retry_guard_before_a_fourth_call(monkeypatch):
    executor, events, calls = executor_for(
        lambda: ToolResult.fail("fixture backend unavailable"), monkeypatch
    )
    for index in range(3):
        executor._execute_tool(_call(str(index)))
    result = executor._execute_tool(_call("fourth"))
    assert result["status"] == "error", result
    assert len(calls) == 3
    assert len([event for event in events if event["type"] == "tool_execution_start"]) == 3
