"""Integer tool arguments a model sends quoted ("offset": "2") are converted once,
in BaseTool.execute_tool, for every tool that declares them as integers."""

import pytest

from agent.tools.base_tool import ToolResult
from agent.tools.memory.memory_get import MemoryGetTool
from agent.tools.read.read import Read


class _AgentContext:
    """Small full-access session for exercising the real tool gateway."""

    def __init__(self, root):
        self.root = str(root)

    def effective_permission_mode(self):
        return "full-access"

    def effective_cwd(self):
        return self.root


def _memory_get(root):
    """Use the registered native descriptor while stubbing memory access."""
    tool = MemoryGetTool(None)
    tool.context = _AgentContext(root)
    tool.execute = lambda params: ToolResult.success(params)
    return tool


@pytest.mark.parametrize("raw, expected", [("2", 2), (" 2 ", 2), ("2.0", 2), (2.0, 2), (2, 2)])
def test_integer_arguments_are_converted(raw, expected, tmp_path):
    result = _memory_get(tmp_path).execute_tool({"path": "7", "start_line": raw})
    assert result.status == "success"
    assert result.result == {"path": "7", "start_line": expected}


@pytest.mark.parametrize("raw", ["two", "2.5", True])
def test_a_non_integer_is_refused_with_the_argument_name(raw, tmp_path):
    result = _memory_get(tmp_path).execute_tool({"path": "fixture", "start_line": raw})
    assert result.status == "error"
    assert "start_line must be an integer" in result.result


def test_read_accepts_quoted_offset_and_limit(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("\n".join(f"line{i}" for i in range(1, 13)) + "\n", encoding="utf-8")
    tool = Read({"cwd": str(tmp_path)})
    tool.context = _AgentContext(tmp_path)

    quoted = tool.execute_tool({"path": str(path), "offset": "4", "limit": "2"})
    plain = tool.execute_tool({"path": str(path), "offset": 4, "limit": 2})

    assert quoted.status == "success", quoted.result
    assert quoted.result["content"] == plain.result["content"]
    assert quoted.result["content"].startswith("4|line4\n5|line5")


def test_memory_get_refuses_a_non_positive_num_lines(tmp_path):
    tool = MemoryGetTool(None)
    tool.context = _AgentContext(tmp_path)
    result = tool.execute_tool({"path": "MEMORY.md", "num_lines": "0"})
    assert result.status == "error"
    assert "num_lines must be a positive" in result.result
