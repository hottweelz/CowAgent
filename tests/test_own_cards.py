"""A tool that draws its own cards should not also get the generic one.

The loop puts up a card for every tool call. A tool running several units of
work at once puts up a card per unit, and the generic card then repeats all of
them at once: every unit's arguments run together in its input, every unit's
output run together in its result. `renders_own_cards` lets such a call opt out
of the generic card - but only for as long as it actually draws its own, since
a refusal that draws nothing has to be visible somewhere.
"""

import os

from agent.protocol.agent_stream import AgentStreamExecutor
from agent.permission.policy import READ_ONLY
from agent.tools.base_tool import ToolResult
from agent.tools.current_time.current_time import TimeTool
from agent.tools.subagent.subagent import SubagentTool


class _ReadOnlySession:
    def effective_permission_mode(self):
        return READ_ONLY

    def effective_cwd(self):
        return os.getcwd()

    def protected_paths(self):
        return []


def _run(tool, arguments=None):
    events = []
    executor = object.__new__(AgentStreamExecutor)
    executor.tools = {tool.name: tool}
    executor.model = None
    executor.agent = _ReadOnlySession()
    executor.cancel_event = None
    executor._record_tool_result = lambda *a, **kw: None
    executor._check_consecutive_failures = lambda *a, **kw: (False, None, False)
    executor._emit_event = lambda kind, data: events.append((kind, data))
    executor._execute_tool({"id": "call_1", "name": tool.name, "arguments": arguments or {}})
    return events


def _cards_for(events, call_id):
    return [kind for kind, data in events if data.get("tool_call_id") == call_id]


def test_the_generic_card_gives_way_to_the_tool_s_own():
    tool = SubagentTool()

    def execute(params):
        tool.emit_event("tool_execution_start", {"tool_call_id": "unit_1", "tool_name": "unit"})
        tool.emit_event("tool_execution_end", {"tool_call_id": "unit_1", "tool_name": "unit"})
        return ToolResult.success("done")

    tool.execute = execute
    events = _run(tool, {"tasks": [{"goal": "one"}, {"goal": "two"}]})

    assert _cards_for(events, "call_1") == []
    assert _cards_for(events, "unit_1") == ["tool_execution_start", "tool_execution_end"]


def test_a_refusal_that_draws_nothing_is_still_seen():
    """Nothing was on screen to carry the message, so the generic card comes
    back rather than the call disappearing."""
    tool = SubagentTool()
    tool.execute = lambda params: ToolResult.fail("that setting is off")
    events = _run(tool, {"tasks": [{"goal": "one"}, {"goal": "two"}]})

    assert _cards_for(events, "call_1") == ["tool_execution_start", "tool_execution_end"]
    assert events[-1][1]["result"] == "that setting is off"


def test_a_tool_that_throws_says_so():
    """Whatever it had drawn is stranded mid-spin, so the generic card comes
    back to close the call out. The tool gateway returns a safe error."""
    tool = SubagentTool()
    tool.execute = lambda params: (_ for _ in ()).throw(RuntimeError("fixture failure"))
    events = _run(tool, {"tasks": [{"goal": "one"}, {"goal": "two"}]})

    assert _cards_for(events, "call_1") == ["tool_execution_start", "tool_execution_end"]
    assert events[-1][1]["status"] == "error"
    assert events[-1][1]["result"] == "Authorization or execution failed."


def test_every_other_tool_is_unaffected():
    events = _run(TimeTool(), {})

    assert _cards_for(events, "call_1") == ["tool_execution_start", "tool_execution_end"]


def test_one_sub_agent_keeps_the_spawn_call_s_card():
    """It reports under that card, so taking it away leaves nothing at all."""
    from agent.tools.subagent import SubagentTool

    tool = SubagentTool()

    assert tool.renders_own_cards({"goal": "find out"}) is False


def test_several_sub_agents_get_cards_of_their_own_instead():
    from agent.tools.subagent import SubagentTool

    tool = SubagentTool()

    assert tool.renders_own_cards({"tasks": [{"goal": "one"}, {"goal": "two"}]}) is True
