import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.personal import interpretation as subject
from agent.protocol.models import LLMRequest
from agent.registry import AgentProfile
from bridge.agent_bridge import AgentLLMModel


PROFILE = AgentProfile(id="owner", name="Owner", workspace="/tmp", bot_type="openai", model="gpt-6-luna")
RECORD = {"objective": "Monitor finance", "preferences": ["tokenization"], "followups": [{"text": "Track funds"}]}
SELECTION = {"selected": [{"article_id": "a", "headline": "New fund", "description": "A report", "source_url": "https://example.test/story"}]}


def response(result):
    return {"choices": [{"message": {"content": json.dumps(result)}, "finish_reason": "stop"}], "usage": {"total_tokens": 42, "secret": "no"}}


class FakeModel:
    def __init__(self, bridge):
        self.model = None
        self._session_provider = self._agent_provider = None
        self.calls = []
    def set_agent_default(self, provider, model):
        self._agent_provider, self.model = provider, model
    def set_session_override(self, provider, model):
        self._session_provider = provider
        self.model = model or self.model
    def call_stream(self, request):
        self.calls.append(request)
        content = json.dumps({"selected_ids": ["a"], "reasons": {"a": "Relevant fund"}, "proposals": [{"action": "track_story", "reason": "Watch progress", "source_ids": ["a"]}]})
        return iter([{"choices": [{"delta": {"content": content}, "finish_reason": None}]}, {"choices": [{"delta": {}, "finish_reason": "stop"}]}, {"choices": [], "usage": {"total_tokens": 42, "secret": "no"}}])


def test_native_route_and_bounded_input_without_mutation():
    captured = []
    def factory(bridge):
        model = FakeModel(bridge)
        captured.append(model)
        return model
    original = copy.deepcopy((RECORD, SELECTION))
    with patch.object(subject, "Bridge", return_value=object()), patch.object(subject, "AgentLLMModel", side_effect=factory), patch.object(subject.session_prefs, "get_prefs_strict", return_value={"provider": "openai", "model": "gpt-5.6-luna"}) as prefs:
        result = subject.interpret(PROFILE, "session", RECORD, SELECTION)
    prefs.assert_called_once_with("session", "owner")
    model = captured[0]
    req = model.calls[0]
    assert req.tools == [] and req.request_timeout == 35 and req.max_tokens is None
    assert result["provenance"] == {"model": "gpt-5.6-luna", "requested_provider": "openai", "usage": {"total_tokens": 42}}
    assert json.loads(req.messages[1]["content"])["followups"] == ["Track funds"]
    assert "https://example.test" not in req.messages[1]["content"]
    assert (RECORD, SELECTION) == original


@pytest.mark.parametrize("result", [
    {"selected_ids": ["other"], "reasons": {"other": "reason"}, "proposals": []},
    {"selected_ids": ["a"], "reasons": {}, "proposals": []},
    {"selected_ids": ["a"], "reasons": {"a": "reason"}, "proposals": [{"action": "draft_post", "reason": "reason", "source_ids": ["other"]}]},
    {"selected_ids": [], "reasons": {}, "proposals": [], "url": "bad"},
])
def test_invalid_result_fails_closed(result):
    with pytest.raises(ValueError):
        subject._decode(response(result), {"a"})


def test_empty_and_tool_calls():
    assert subject._decode(response({"selected_ids": [], "reasons": {}, "proposals": []}), {"a"})["selected_ids"] == []
    bad = response({"selected_ids": [], "reasons": {}, "proposals": []})
    bad["choices"][0]["message"]["tool_calls"] = [{"name": "publish"}]
    with pytest.raises(ValueError):
        subject._decode(bad, {"a"})


@pytest.mark.parametrize("failure,code", [(TimeoutError("secret"), "model_timeout"), (RuntimeError("secret"), "model_unavailable")])
def test_errors_are_sanitized(failure, code):
    with patch.object(subject, "Bridge", side_effect=failure), pytest.raises(subject.InterpretationError) as error:
        subject.interpret(PROFILE, "s", RECORD, SELECTION)
    assert error.value.code == code and str(error.value) == code


def test_invalid_response_and_timeout_return():
    with pytest.raises(subject.InterpretationError, match="model_timeout"):
        subject._decode({"error": True, "message": "request timed out"}, {"a"})
    with patch.object(subject, "Bridge", return_value=object()), patch.object(subject, "AgentLLMModel", return_value=FakeModel(None)) as factory, patch.object(subject.session_prefs, "get_prefs_strict", return_value={}):
        factory.return_value.call_stream = lambda req: iter([{"choices": [{"delta": {"content": "not json"}, "finish_reason": None}]}, {"choices": [{"delta": {}, "finish_reason": "stop"}]}])
        with pytest.raises(subject.InterpretationError, match="model_invalid_response"):
            subject.interpret(PROFILE, "s", RECORD, SELECTION)


def test_real_bridge_passes_optional_timeout_to_bot():
    calls = []
    bot = SimpleNamespace(call_with_tools=lambda **kw: calls.append(kw) or {})
    model = AgentLLMModel.__new__(AgentLLMModel)
    model._bot = bot
    model._bot_model = "test"
    model._bot_type = "test"
    with patch.object(AgentLLMModel, "bot", new_callable=lambda: property(lambda self: bot)), patch.object(AgentLLMModel, "model", new_callable=lambda: property(lambda self: "test")), patch.object(AgentLLMModel, "_is_thinking_only_model", return_value=False):
        model.call(LLMRequest(messages=[], tools=[], request_timeout=35))
        model.call(LLMRequest(messages=[], tools=[]))
    assert calls[0]["request_timeout"] == 35 and calls[0]["tools"] == []
    assert "request_timeout" not in calls[1]
    for value in (0, -1, float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            LLMRequest(request_timeout=value)


def test_profile_model_applies_when_session_has_no_pin_or_is_group():
    for prefs in ({}, {"members": ["peer"], "provider": "other", "model": "other-model"}):
        instance = FakeModel(None)
        with patch.object(subject, "Bridge", return_value=object()), patch.object(subject, "AgentLLMModel", return_value=instance), patch.object(subject.session_prefs, "get_prefs_strict", return_value=prefs):
            result = subject.interpret(PROFILE, "session", RECORD, SELECTION)
        assert result["provenance"]["model"] == "gpt-6-luna"
        assert result["provenance"]["requested_provider"] == "openai"


@pytest.mark.parametrize("api_type,model_name", [("chat", "gpt-5.6-luna"), ("responses", "gpt-6-luna")])
def test_openai_compatible_transport_timeout_not_in_payload(api_type, model_name):
    from models.openai_compatible_bot import OpenAICompatibleBot

    calls = []
    class Client:
        def chat_completions(self, *, api_key, api_base, timeout, stream, **payload):
            calls.append((timeout, payload))
            return {"choices": [{"message": {"content": "ok"}}]}
        def responses(self, *, api_key, api_base, timeout, stream, **payload):
            calls.append((timeout, payload))
            return {"status": "completed", "output": []}
    class Bot(OpenAICompatibleBot):
        def get_api_config(self):
            return {"api_type": api_type, "model": model_name, "api_key": "fixture", "api_base": "https://example.invalid"}
        def _get_http_client(self):
            return Client()

    Bot().call_with_tools([{"role": "user", "content": "test"}], tools=[], model=model_name, request_timeout=35)
    assert len(calls) == 1
    timeout, payload = calls[0]
    assert timeout == 35
    assert "request_timeout" not in payload and "timeout" not in payload
    assert "api_key" not in payload and "api_base" not in payload


def stream_chunk(delta, finish=None):
    return {"choices": [{"delta": delta, "finish_reason": finish}]}


@pytest.mark.parametrize("chunks,code", [
    ([stream_chunk({"tool_calls": [{"index": 0}]})], "model_invalid_response"),
    ([stream_chunk({"function_call": {"name": "publish"}})], "model_invalid_response"),
    ([stream_chunk({}, "length")], "model_invalid_response"),
    ([stream_chunk({"content": "x" * 16001})], "model_invalid_response"),
    ([stream_chunk({"content": "{}"})], "model_invalid_response"),
    ([{"error": True, "message": "timed out"}], "model_timeout"),
    ([{"error": True, "message": "provider error"}], "model_unavailable"),
])
def test_stream_rejects_invalid_or_failed_output_and_closes(chunks, code):
    class Stream:
        closed = False
        def __iter__(self):
            return iter(chunks)
        def close(self):
            self.closed = True
    stream = Stream()
    with pytest.raises(subject.InterpretationError, match=code):
        subject._collect_stream(stream, float("inf"))
    assert stream.closed


def test_stream_rejects_late_result_without_mutation():
    before = copy.deepcopy((RECORD, SELECTION))
    stream = iter([stream_chunk({"content": "{}"}, "stop")])
    with patch.object(subject.time, "monotonic", return_value=36), pytest.raises(subject.InterpretationError, match="model_timeout"):
        subject._collect_stream(stream, 35)
    assert (RECORD, SELECTION) == before


def test_bridge_stream_passes_timeout_and_closes_underlying():
    calls = []
    class Stream:
        closed = False
        def __iter__(self):
            return iter([stream_chunk({"content": "data"})])
        def close(self):
            self.closed = True
    stream = Stream()
    bot = SimpleNamespace(call_with_tools=lambda **kw: calls.append(kw) or stream)
    model = AgentLLMModel.__new__(AgentLLMModel)
    with patch.object(AgentLLMModel, "bot", new_callable=lambda: property(lambda self: bot)), patch.object(AgentLLMModel, "model", new_callable=lambda: property(lambda self: "test")), patch.object(AgentLLMModel, "_is_thinking_only_model", return_value=False):
        iterator = model.call_stream(LLMRequest(tools=[], request_timeout=35, sensitive=True))
        next(iterator)
        iterator.close()
    assert calls[0]["request_timeout"] == 35 and calls[0]["stream"] is True
    assert calls[0]["tools"] == [] and "max_tokens" not in calls[0]
    assert stream.closed
