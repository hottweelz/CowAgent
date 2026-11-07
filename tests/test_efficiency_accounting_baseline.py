"""Pin the current split between context, run, and title-call accounting.

The historical audit expectations are updated for the Phase 1 accounting contract.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from agent.protocol.agent import Agent
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.chat import session_service


def test_request_estimate_includes_schemas_and_run_total_remains_separate():
    from agent.protocol.accounting import request_snapshot
    agent = Agent.__new__(Agent)
    agent._estimate_message_tokens = lambda message: len(message.get('content', ''))
    agent._estimate_text_tokens = len
    schema = [{'name': 'synthetic_tool', 'description': 'synthetic schema'}]
    snapshot = request_snapshot(agent, 'system', [{'role': 'user', 'content': 'history'}], schema, 'model')
    assert snapshot['estimated_input_tokens'] == len('system') + len('history') + len(json.dumps(schema, ensure_ascii=False))
    first = AgentStreamExecutor._normalize_stream_usage({'prompt_tokens': 9967, 'completion_tokens': 80})
    last = AgentStreamExecutor._normalize_stream_usage({'prompt_tokens': 10241, 'completion_tokens': 80})
    total = AgentStreamExecutor._merge_usage(first, last)
    assert (total['prompt_tokens'], total['completion_tokens'], total['calls']) == (20208, 160, 2)
    assert last['prompt_tokens'] == 10241


def test_context_chart_counts_rebuilt_prompt_without_rebuilding_on_hover():
    """A count-only rebuilt snapshot supersedes the cached initialization prompt."""
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
    assert chart["used"] == len("rebuilt current prompt")
    assert chart["breakdown"]["system"] == len("rebuilt current prompt")
    assert chart["breakdown_estimated"] is True
    prompt_builder.return_value.build.assert_called_once()
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
