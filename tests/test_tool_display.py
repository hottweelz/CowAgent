"""A tool result written for a person, alongside the one written for a model.

Some tools produce something a person is waiting to read - a report, a summary
- but must hand the model a machine-readable form of it. `ToolResult.display`
carries the readable one out to whoever is watching without spending any of the
model's context on a second copy.
"""

from pathlib import Path

from agent.protocol.agent_stream import AgentStreamExecutor
from agent.tools.base_tool import ToolResult
from agent.tools.read.read import Read


class _AgentContext:
    """Small full-access session for exercising the real tool gateway."""

    def __init__(self, root):
        self.root = str(root)

    def effective_permission_mode(self):
        return "full-access"

    def effective_cwd(self):
        return self.root


def _read_tool(result):
    """Use a registered native tool and stub only its raw implementation."""
    tool = Read()
    tool.execute = lambda params: result
    return tool


def _executor(tool, tmp_path):
    events = []
    executor = object.__new__(AgentStreamExecutor)
    executor.tools = {tool.name: tool}
    executor.model = None
    executor.agent = _AgentContext(tmp_path)
    executor.cancel_event = None
    executor._record_tool_result = lambda *a, **kw: None
    executor._check_consecutive_failures = lambda *a, **kw: (False, None, False)
    executor._emit_event = lambda kind, data: events.append((kind, data))
    return executor, events


def _run(tool, tmp_path):
    executor, events = _executor(tool, tmp_path)
    result = executor._execute_tool({"id": "call_1", "name": tool.name,
                                     "arguments": {"path": "fixture.txt"}})
    ends = [data for kind, data in events if kind == "tool_execution_end"]
    return result, ends[0]


def test_the_readable_form_travels_with_the_event(tmp_path):
    result, end = _run(_read_tool(ToolResult.success(
        '{"ok": true}', display="## Findings\n\nAll clear.")), tmp_path)

    assert end["display"] == "## Findings\n\nAll clear."
    assert end["result"] == '{"ok": true}'


def test_the_readable_form_stays_out_of_the_model_s_context(tmp_path):
    """The returned dict becomes the tool_result the model reads. A second
    rendering of the same outcome there would just cost context."""
    result, _ = _run(_read_tool(ToolResult.success(
        '{"ok": true}', display="## Findings\n\nAll clear.")), tmp_path)

    assert "display" not in result
    assert result["result"] == '{"ok": true}'


def test_a_tool_whose_result_already_reads_well_sends_nothing_extra(tmp_path):
    _, end = _run(_read_tool(ToolResult.success("just text")), tmp_path)

    assert "display" not in end


def test_a_tool_can_tell_which_call_it_is_running(tmp_path):
    """A tool that reports work of its own needs to say which entry in the
    client's view that work belongs under."""
    tool = Read()
    tool.seen = "unset"
    tool.execute = lambda params: (setattr(tool, "seen", tool.tool_call_id)
                                   or ToolResult.success("ok"))

    _run(tool, tmp_path)

    assert tool.seen == "call_1"
    # Cleared afterwards, like every other per-call slot the loop assigns.
    assert tool.tool_call_id is None


def test_both_consoles_render_what_the_backend_sends():
    """The web console and the desktop app read the same stream. A field only
    one of them understands is a feature that exists on one client."""
    root = Path(__file__).parents[1]
    from conftest import console_js
    web = console_js()
    desktop_store = (root / "desktop/src/renderer/src/store/chatStore.ts").read_text(encoding="utf-8")
    desktop_steps = (root / "desktop/src/renderer/src/components/MessageSteps.tsx").read_text(encoding="utf-8")

    # The readable form is rendered as markdown rather than dumped as text.
    assert "renderMarkdown(String(item.display))" in web
    assert "<Markdown content={step.display} />" in desktop_steps

    # A sub agent's own tool calls are filed under its card on both.
    assert "item.type === 'subagent_step'" in web
    assert "case 'subagent_step':" in desktop_store
    assert "substeps" in desktop_steps
