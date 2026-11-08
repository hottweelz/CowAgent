"""BaseTool execution keeps authorization and returns safe ToolResult failures."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.permission.policy import READ_ONLY  # noqa: E402
from agent.tools.base_tool import ToolResult  # noqa: E402
from agent.tools.subagent.subagent import SubagentTool  # noqa: E402


class _ReadOnlySession:
    """Valid session authority for the real tool gateway."""

    def effective_permission_mode(self):
        return READ_ONLY

    def effective_cwd(self):
        return os.getcwd()

    def protected_paths(self):
        return []


def _registered_tool(execute):
    """Keep the exact registered implementation; stub only its body."""
    tool = SubagentTool()
    tool.context = _ReadOnlySession()
    tool.execute = execute
    return tool


class TestExecuteToolReturnsAResult:
    def test_a_raising_tool_yields_a_failed_result_not_none(self):
        calls = []

        def execute(params):
            calls.append(params)
            raise RuntimeError("upstream refused the connection")

        result = _registered_tool(execute).execute_tool({"goal": "fixture"})
        assert result is not None, "execute_tool returned None; the caller would raise AttributeError"
        assert result.status == "error"
        assert calls == [{"goal": "fixture"}]

    def test_execution_failure_is_sanitized_after_authorized_execution(self):
        calls = []

        def execute(params):
            calls.append(params)
            raise RuntimeError("upstream refused the connection")

        result = _registered_tool(execute).execute_tool({"goal": "fixture"})
        assert calls == [{"goal": "fixture"}]
        assert result.status == "error"
        assert result.result == "Authorization or execution failed."
        assert "upstream refused the connection" not in str(result.result)
        assert "RuntimeError" not in str(result.result)
        assert "NoneType" not in str(result.result)

    def test_the_caller_can_read_status_without_raising(self):
        result = _registered_tool(
            lambda params: (_ for _ in ()).throw(RuntimeError("fixture failure"))
        ).execute_tool({"goal": "fixture"})
        payload = {"status": result.status, "result": result.result,
                   "execution_time": 0}
        assert payload["status"] == "error"

    def test_a_succeeding_tool_is_untouched(self):
        calls = []
        result = _registered_tool(
            lambda params: (calls.append(params), ToolResult.success("done"))[1]
        ).execute_tool({"goal": "fixture"})
        assert calls == [{"goal": "fixture"}]
        assert result.status == "success"
        assert result.result == "done"
