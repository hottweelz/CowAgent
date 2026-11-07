"""Focused tests for the route-scoped title request budget."""

import config as config_module
from config import Config
from models.session_manager import Session


MODEL = "nvidia/nemotron-3.5-super-vl:free"
OPENROUTER = "https://openrouter.ai/api/v1"


class _Response:
    status_code = 200

    def __init__(self, content="A concise title", finish_reason="stop"):
        self._body = {
            "model": MODEL,
            "choices": [{"message": {"role": "assistant", "content": content},
                         "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 91, "completion_tokens": 12,
                      "total_tokens": 103, "completion_tokens_details": {"reasoning_tokens": 0}},
        }

    def json(self):
        return self._body


def _make_bot(monkeypatch, *, api_base=OPENROUTER, model=MODEL, api_type="auto"):
    config = {
        "bot_type": "custom:title-test",
        "model": model,
        "custom_providers": [{"id": "title-test", "name": "title-test",
                              "api_key": "synthetic-key", "api_base": api_base,
                              "model": model}],
        "open_ai_api_type": api_type,
    }
    monkeypatch.setattr(config_module, "config", Config(config))
    from models.chatgpt.chat_gpt_bot import ChatGPTBot
    return ChatGPTBot("custom:title-test")


def _install_bridge_bot(monkeypatch, bot):
    from bridge import bridge

    class _Bridge:
        def get_bot(self, kind):
            assert kind == "chat"
            return bot

    monkeypatch.setattr(bridge, "Bridge", _Bridge)


def _http_response(content="A concise title", finish_reason="stop"):
    return _Response(content, finish_reason)


def test_title_budget_reaches_http_and_does_not_mutate_normal_chat_args(monkeypatch):
    from agent.chat import session_service

    bot = _make_bot(monkeypatch)
    _install_bridge_bot(monkeypatch, bot)
    original_args = dict(bot.args)
    captured = []

    def fake_post(url, **kwargs):
        captured.append((url, kwargs["json"].copy()))
        return _http_response()

    monkeypatch.setattr("models.openai.openai_http_client.requests.post", fake_post)

    # Capture the ordinary request shape on both sides of title generation.
    ordinary = Session("ordinary", system_prompt="")
    ordinary.messages = [{"role": "user", "content": "normal chat"}]
    bot.reply_text(ordinary)
    attempts = []
    title = session_service.generate_session_title("Explain a short topic", attempts=attempts)
    bot.reply_text(ordinary)

    assert title == "A concise title"
    assert attempts[0]["status"] == "success"
    assert attempts[0]["usage"]["prompt_tokens"] == 91
    assert [body for _, body in captured][0] == [body for _, body in captured][2]
    title_url, title_body = captured[1]
    assert title_url == f"{OPENROUTER}/chat/completions"
    assert title_body["model"] == MODEL
    assert title_body["reasoning"] == {"enabled": False}
    assert title_body["max_tokens"] == 128
    assert bot.args == original_args
    assert "reasoning" not in bot.args
    assert "max_tokens" not in bot.args


def test_title_budget_keeps_valid_english_and_chinese_titles(monkeypatch):
    from agent.chat import session_service

    bot = _make_bot(monkeypatch)
    _install_bridge_bot(monkeypatch, bot)
    responses = iter((_http_response("A short title"), _http_response("简短标题")))
    monkeypatch.setattr(
        "models.openai.openai_http_client.requests.post",
        lambda *args, **kwargs: next(responses),
    )

    assert session_service.generate_session_title("First request") == "A short title"
    assert session_service.generate_session_title("第二个请求") == "简短标题"


def test_budget_is_limited_to_the_verified_route(monkeypatch):
    from agent.chat.session_service import _title_request_args

    exact = _make_bot(monkeypatch)
    assert _title_request_args(exact) == {
        **exact.args, "reasoning": {"enabled": False}, "max_tokens": 128,
    }

    other_provider = _make_bot(monkeypatch, api_base="https://provider.example/v1")
    assert _title_request_args(other_provider) is None

    other_model = _make_bot(monkeypatch, model="nvidia/another-model")
    assert _title_request_args(other_model) is None

    responses_bot = _make_bot(monkeypatch)
    monkeypatch.setattr(responses_bot, "_use_responses_for_plain_calls", lambda: True)
    assert _title_request_args(responses_bot) is None

    class SessionOnlyBot:
        def reply_text(self, session):
            return {"completion_tokens": 1, "content": "Title"}

    assert _title_request_args(SessionOnlyBot()) is None


def test_truncated_primary_keeps_usage_and_uses_configured_fallback(monkeypatch):
    from agent.chat import session_service
    from bridge import agent_bridge
    from agent.memory.summarizer import MemoryFlushManager

    bot = _make_bot(monkeypatch)
    _install_bridge_bot(monkeypatch, bot)
    monkeypatch.setattr(
        "models.openai.openai_http_client.requests.post",
        lambda *args, **kwargs: _http_response("partial title", "length"),
    )

    class FallbackModel:
        def __init__(self, bridge):
            pass

        def fallback_config(self):
            return {"chain": [{"provider": "custom:test", "model": "fallback"}]}

        def use_fallback(self):
            return True

        def call(self, request):
            assert request.stream is False
            return {"text": "Fallback title",
                    "usage": {"prompt_tokens": 20, "completion_tokens": 3},
                    "model": "fallback", "provider": "custom:test"}

    monkeypatch.setattr(agent_bridge, "AgentLLMModel", FallbackModel)
    monkeypatch.setattr(MemoryFlushManager, "_extract_response_text",
                        staticmethod(lambda response: response["text"]))
    attempts = []

    assert session_service.generate_session_title("User question", attempts=attempts) == "Fallback title"
    assert [attempt["status"] for attempt in attempts] == ["failed", "success"]
    assert attempts[0]["usage"]["completion_tokens"] == 12
    assert attempts[1]["usage"]["prompt_tokens"] == 20


def test_primary_error_uses_configured_fallback_and_empty_primary_uses_local_title(monkeypatch):
    from agent.chat import session_service
    from bridge import bridge, agent_bridge
    from agent.memory.summarizer import MemoryFlushManager

    class PrimaryBot:
        def __init__(self, result=None, error=False):
            self.result = result
            self.error = error

        def reply_text(self, session):
            if self.error:
                raise RuntimeError("synthetic failure")
            return self.result

    class Bridge:
        def __init__(self, bot):
            self.bot = bot

        def get_bot(self, kind):
            assert kind == "chat"
            return self.bot

    class FallbackModel:
        response_text = "Recovered title"

        def __init__(self, bridge):
            pass

        def fallback_config(self):
            return {"chain": [{"provider": "custom:test", "model": "fallback"}]}

        def use_fallback(self):
            return True

        def call(self, request):
            return {"text": self.response_text,
                    "usage": {"prompt_tokens": 17, "completion_tokens": 4},
                    "model": "fallback", "provider": "custom:test"}

    monkeypatch.setattr(bridge, "Bridge", lambda: Bridge(current_bot))
    monkeypatch.setattr(agent_bridge, "AgentLLMModel", FallbackModel)
    monkeypatch.setattr(MemoryFlushManager, "_extract_response_text",
                        staticmethod(lambda response: response["text"]))

    for bot in (
        PrimaryBot(error=True),
        PrimaryBot(result={"content": "", "completion_tokens": 0,
                           "usage": {"prompt_tokens": 8, "completion_tokens": 0}}),
    ):
        current_bot = bot
        attempts = []
        assert session_service.generate_session_title("Question", attempts=attempts) == "Recovered title"
        assert [attempt["route"] for attempt in attempts] == ["primary", "fallback"]
        if not bot.error:
            assert attempts[0]["usage"]["prompt_tokens"] == 8
        assert attempts[1]["usage"]["prompt_tokens"] == 17

    current_bot = PrimaryBot(result={"content": "", "completion_tokens": 0,
                                     "usage": {"prompt_tokens": 8, "completion_tokens": 0}})
    FallbackModel.fallback_config = lambda self: {"chain": []}
    attempts = []
    assert session_service.generate_session_title("Question", attempts=attempts) == "Question"
    assert attempts[0]["usage"]["prompt_tokens"] == 8
