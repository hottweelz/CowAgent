"""Pin the current split between context, run, and title-call accounting.

These are audit tests. They describe the current behavior and do not propose
an accounting change.
"""

import ast
import inspect
import json
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

from agent.protocol.agent import Agent
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.chat import session_service


def test_usage_log_estimate_excludes_tool_schema_counted_by_context_chart():
    """The live chart includes tools, while the [Usage] estimate omits them."""
    agent = Agent.__new__(Agent)
    agent.system_prompt = "system-prompt"
    agent.tools = [object()]
    agent.messages = [{"role": "user", "content": "history"}]
    agent.max_context_tokens = 10_000
    agent.model = SimpleNamespace(model="synthetic-model")
    agent.last_usage = None
    agent.get_skills_prompt = lambda: ""
    agent._get_model_context_window = lambda: 10_000
    agent._estimate_text_tokens = lambda text: len(text)
    agent._estimate_message_tokens = lambda message: len(str(message.get("content", "")))

    schema = [{"name": "synthetic_tool", "description": "synthetic schema"}]
    with patch("agent.protocol.agent.is_tool_available", return_value=True), patch(
        "agent.protocol.agent_stream.build_tools_schema", return_value=schema
    ):
        chart = agent.get_context_usage()

    # Keep this as a source-backed characterization of the diagnostic line.
    # If the production estimate changes to include tools, this test must be
    # updated with the accounting contract.
    tree = ast.parse(textwrap.dedent(inspect.getsource(AgentStreamExecutor._call_llm_stream)))
    estimate_assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "est_in" for target in node.targets)
    ]
    assert len(estimate_assignments) == 1
    assert ast.unparse(estimate_assignments[0].value) == "est_sys + est_hist"

    system_estimate = len(agent.system_prompt)
    history_estimate = len("history")
    diagnostic_estimate = system_estimate + history_estimate
    tool_estimate = len(json.dumps(schema, ensure_ascii=False))
    assert chart["estimated"] is True
    assert chart["breakdown"]["tools"] == tool_estimate
    assert chart["used"] == diagnostic_estimate + tool_estimate
    assert chart["used"] > diagnostic_estimate

    first_call = AgentStreamExecutor._normalize_stream_usage({
        "prompt_tokens": 9_967,
        "completion_tokens": 80,
        "total_tokens": 10_047,
        "prompt_cache_hit_tokens": 0,
    })
    last_call = AgentStreamExecutor._normalize_stream_usage({
        "prompt_tokens": 10_241,
        "completion_tokens": 80,
        "total_tokens": 10_321,
        "prompt_cache_hit_tokens": 0,
    })
    run_usage = AgentStreamExecutor._merge_usage(first_call, last_call)
    agent.last_usage = {
        **last_call,
        "_est_history": history_estimate,
    }
    latest_chart = agent.get_context_usage()

    assert run_usage["prompt_tokens"] == 20_208
    assert run_usage["completion_tokens"] == 160
    assert run_usage["calls"] == 2
    assert latest_chart["used"] == 10_241
    assert latest_chart["estimated"] is False


def test_context_chart_uses_cached_prompt_after_full_prompt_rebuild():
    """Rebuilding a prompt does not replace the prompt held by the Agent."""
    agent = Agent.__new__(Agent)
    agent.system_prompt = "cached synthetic prompt"
    agent.tools = []
    agent.messages = []
    agent.max_context_tokens = 10_000
    agent.model = SimpleNamespace(model="synthetic-model")
    agent.last_usage = None
    agent.skill_manager = None
    agent.workspace_dir = ""
    agent.skip_context_files = False
    agent.memory_manager = None
    agent.runtime_info = None
    agent.project_dir = None
    agent.extra_system_suffix = ""
    agent.get_skills_prompt = lambda: ""
    agent.effective_permission_mode = lambda: "workspace-write"
    agent._get_model_context_window = lambda: 10_000
    agent._estimate_text_tokens = lambda text: len(text)
    agent._estimate_message_tokens = lambda message: len(str(message.get("content", "")))

    with patch("common.i18n.get_language", return_value="en"), patch(
        "agent.prompt.PromptBuilder"
    ) as prompt_builder:
        prompt_builder.return_value.build.return_value = "rebuilt current prompt"
        rebuilt = agent.get_full_system_prompt()
        chart = agent.get_context_usage()

    assert rebuilt == "rebuilt current prompt"
    assert agent.system_prompt == "cached synthetic prompt"
    assert chart["used"] == len("cached synthetic prompt")
    assert chart["breakdown"]["system"] == len("cached synthetic prompt")
    prompt_builder.assert_called_once()
    assert prompt_builder.call_args.kwargs["language"] == "en"


def test_session_title_uses_a_separate_mocked_chat_request():
    """Title generation calls the global chat bot and returns no usage record."""
    calls = []

    class FakeBot:
        def reply_text(self, session):
            calls.append(session)
            return {
                "content": "Synthetic title",
                "prompt_tokens": 73,
                "completion_tokens": 3,
                "total_tokens": 76,
            }

    class FakeBridge:
        def get_bot(self, bot_type):
            assert bot_type == "chat"
            return FakeBot()

    with patch("bridge.bridge.Bridge", FakeBridge):
        result = session_service.generate_session_title(
            "Synthetic user question", "", "synthetic-session"
        )

    assert result == "Synthetic title"
    assert len(calls) == 1
    assert calls[0].session_id == "synthetic-session"
    assert calls[0].system_prompt == ""
    assert len(calls[0].messages) == 1
    assert calls[0].messages[0]["role"] == "user"
    assert "Synthetic user question" in calls[0].messages[0]["content"]
