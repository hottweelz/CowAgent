"""Pin current OpenAI-compatible adapter behavior without provider calls.

The request and response fixtures below use synthetic content. They document
what the custom adapter sends and what the existing usage pipeline retains.
"""

import json

from agent.protocol.agent_stream import AgentStreamExecutor
from models.openai_compatible_bot import OpenAICompatibleBot


MODEL = "nvidia/nemotron-3.5-super-vl:free"
API_BASE = "https://openrouter.ai/api/v1"
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "synthetic_lookup",
        "description": "Synthetic test tool",
        "parameters": {"type": "object", "properties": {}},
    },
}


class _CustomAdapter(OpenAICompatibleBot):
    def get_api_config(self):
        return {
            "api_key": "synthetic-key",
            "api_base": API_BASE,
            "model": MODEL,
            "default_temperature": 0.7,
            "default_top_p": 1.0,
        }


class _Response:
    def __init__(self, body=None, stream_bytes=None):
        self.status_code = 200
        self.headers = {"X-OpenRouter-Cache-Status": "HIT"}
        self._body = body
        self._stream_bytes = stream_bytes
        self.closed = False

    def json(self):
        return self._body

    def iter_content(self, chunk_size=None, decode_unicode=False):
        yield self._stream_bytes

    def close(self):
        self.closed = True


def _messages():
    return [{"role": "user", "content": "Synthetic request"}]


def _cache_kwargs():
    return {
        "session_id": "synthetic-session",
        "prompt_cache_key": "synthetic-prefix",
        "cache_control": {"type": "ephemeral"},
        "provider": {"sort": "throughput"},
        "reasoning_effort": "high",
    }


def test_stream_request_sends_usage_option_and_keeps_system_and_tool_schema(monkeypatch):
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 5,
        "total_tokens": 105,
        "prompt_tokens_details": {"cached_tokens": 60, "cache_write_tokens": 4},
    }
    event = {"choices": [], "usage": usage}
    response = _Response(stream_bytes=(f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n").encode())
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return response

    monkeypatch.setattr("models.openai.openai_http_client.requests.post", fake_post)
    bot = _CustomAdapter()
    chunks = list(bot.call_with_tools(
        _messages(),
        tools=[TOOL_SCHEMA],
        stream=True,
        system="Synthetic stable system prefix",
        **_cache_kwargs(),
    ))

    payload = captured["json"]
    assert captured["url"] == f"{API_BASE}/chat/completions"
    assert payload["stream"] is True
    assert payload["stream_options"] == {"include_usage": True}
    assert payload["messages"][0] == {
        "role": "system",
        "content": "Synthetic stable system prefix",
    }
    assert payload["tools"] == [TOOL_SCHEMA]
    for omitted in (
        "session_id",
        "prompt_cache_key",
        "cache_control",
        "provider",
        "reasoning_effort",
    ):
        assert omitted not in payload
    assert all(key not in payload["messages"][0] for key in _cache_kwargs())

    # The HTTP client returns SSE JSON only. Response headers are not attached
    # to chunks, while the raw usage object remains available to the caller.
    assert chunks == [{"choices": [], "usage": usage}]
    assert "X-OpenRouter-Cache-Status" not in chunks[0]
    assert response.closed

    normalized = AgentStreamExecutor._normalize_stream_usage(chunks[0]["usage"])
    assert normalized == {
        "prompt_tokens": 100,
        "completion_tokens": 5,
        "total_tokens": 105,
        "prompt_cache_hit_tokens": 60,
        "prompt_cache_miss_tokens": 40,
        "calls": 1,
    }
    assert "cache_write_tokens" not in normalized


def test_sync_request_omits_cache_routing_fields_but_returns_raw_usage(monkeypatch):
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 5,
        "total_tokens": 105,
        "prompt_tokens_details": {"cached_tokens": 60, "cache_write_tokens": 4},
        "cost": 0.0,
    }
    body = {"choices": [{"message": {"content": "synthetic"}}], "usage": usage}
    response = _Response(body=body)
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return response

    monkeypatch.setattr("models.openai.openai_http_client.requests.post", fake_post)
    result = _CustomAdapter().call_with_tools(
        _messages(),
        tools=[TOOL_SCHEMA],
        stream=False,
        system="Synthetic stable system prefix",
        **_cache_kwargs(),
    )

    payload = captured["json"]
    assert payload["stream"] is False
    assert "stream_options" not in payload
    assert payload["messages"][0]["content"] == "Synthetic stable system prefix"
    assert payload["tools"] == [TOOL_SCHEMA]
    for omitted in (
        "session_id",
        "prompt_cache_key",
        "cache_control",
        "provider",
        "reasoning_effort",
    ):
        assert omitted not in payload
    assert result == body
    assert result["usage"]["prompt_tokens_details"] == {
        "cached_tokens": 60,
        "cache_write_tokens": 4,
    }
    # The parsed HTTP response body is returned; response headers are not.
    assert "X-OpenRouter-Cache-Status" not in result
