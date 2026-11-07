from agent.protocol.usage import merge_usage, normalize_usage
from models.openai.responses_adapter import _cc_usage


def test_usage_preserves_missing_and_reported_zero_and_aggregates():
    missing = normalize_usage({'prompt_tokens': 9967, 'completion_tokens': 4})
    zero = normalize_usage({'prompt_tokens': 10241, 'completion_tokens': 3,
                            'prompt_tokens_details': {'cached_tokens': 0},
                            'completion_tokens_details': {'reasoning_tokens': 2},
                            'cache_creation_input_tokens': 8, 'cost': 0.25},
                           model='returned', provider='gateway', purpose='chat')
    assert 'prompt_cache_hit_tokens' not in missing
    assert zero['prompt_cache_hit_tokens'] == 0
    assert zero['prompt_cache_miss_tokens'] == 10241
    assert zero['reasoning_tokens'] == 2
    assert (zero['model'], zero['provider'], zero['purpose']) == ('returned', 'gateway', 'chat')
    total = merge_usage(missing, zero)
    assert total['prompt_tokens'] == 20208
    assert total['calls'] == 2
    assert total['prompt_cache_hit_tokens_reported_calls'] == 1
    assert total['cache_creation_input_tokens'] == 8
    assert total['cost'] == 0.25
    assert 'model' not in total


def test_responses_translation_retains_metadata_and_explicit_zero():
    raw = {'input_tokens': 20, 'output_tokens': 4, 'total_tokens': 24,
           'input_tokens_details': {'cached_tokens': 0},
           'output_tokens_details': {'reasoning_tokens': 3}, 'cost': 0.01}
    usage = normalize_usage(_cc_usage(raw))
    assert usage['prompt_cache_hit_tokens'] == 0
    assert usage['reasoning_tokens'] == 3
    assert usage['cost'] == 0.01


def test_title_primary_and_fallback_attempts_are_separate(monkeypatch):
    from agent.chat import session_service
    from bridge import bridge, agent_bridge
    from agent.memory.summarizer import MemoryFlushManager

    class Bot:
        def reply_text(self, session):
            return {'completion_tokens': 0, 'content': '',
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 0}, 'model': 'primary'}

    class Bridge:
        def get_bot(self, kind):
            return Bot()

    class Model:
        model = 'fallback'
        def __init__(self, bridge): pass
        def fallback_config(self): return {'chain': [{}]}
        def use_fallback(self): return True
        def call(self, request):
            return {'usage': {'prompt_tokens': 12, 'completion_tokens': 3,
                              'prompt_cache_hit_tokens': 0},
                    'model': 'returned-fallback', 'provider': 'synthetic', 'text': 'Title'}

    monkeypatch.setattr(bridge, 'Bridge', Bridge)
    monkeypatch.setattr(agent_bridge, 'AgentLLMModel', Model)
    monkeypatch.setattr(MemoryFlushManager, '_extract_response_text', staticmethod(lambda x: x['text']))
    attempts = []
    assert session_service.generate_session_title('question', session_id='test', attempts=attempts) == 'Title'
    assert [a['status'] for a in attempts] == ['failed', 'success']
    assert [a['usage']['prompt_tokens'] for a in attempts] == [10, 12]
    assert attempts[1]['usage']['model'] == 'returned-fallback'
    assert attempts[1]['usage']['prompt_cache_hit_tokens'] == 0


def test_title_dispatch_exposes_attempts(monkeypatch):
    from agent.chat.session_service import SessionService
    service = SessionService.__new__(SessionService)
    service.agent_id = None
    def gen_title(*args, attempts=None, **kwargs):
        attempts.append({"route": "primary", "status": "success", "purpose": "title",
                         "usage": normalize_usage({"prompt_tokens": 9, "completion_tokens": 1}, purpose="title")})
        return "Title"
    monkeypatch.setattr(service, "gen_title", gen_title)
    result = service.dispatch("generate_title", {"session_id": "test", "user_message": "question"})
    assert result["payload"]["title"] == "Title"
    assert result["payload"]["title_attempts"][0]["usage"]["prompt_tokens"] == 9


def test_cache_write_aliases_and_zero_input_are_reported():
    for details in ("prompt_tokens_details", "input_tokens_details"):
        usage = normalize_usage({"prompt_tokens": 0, "completion_tokens": 0,
                                 details: {"cache_write_tokens": 0}})
        assert usage["calls"] == 1
        assert usage["prompt_tokens"] == 0
        assert usage["prompt_tokens_reported_calls"] == 1
        assert usage["cache_creation_input_tokens"] == 0
        assert usage["cache_creation_input_tokens_reported_calls"] == 1
        nonzero = normalize_usage({details: {"cache_write_tokens": 13}})
        assert nonzero["cache_creation_input_tokens"] == 13
        assert "prompt_tokens_reported_calls" not in nonzero


def test_merge_only_counts_supported_fields_and_preserves_request_routes():
    one = normalize_usage({"prompt_tokens": 0, "completion_tokens": 0},
                          model="first", provider="one", purpose="chat")
    one["unrelated_numeric"] = 400
    one["private"] = "not retained"
    two = normalize_usage({"prompt_tokens": 10, "completion_tokens": 2},
                          model="second", provider="two", purpose="chat")
    merged = merge_usage(merge_usage(None, one), two)
    assert merged["calls"] == 2
    assert merged["prompt_tokens_reported_calls"] == 2
    assert "unrelated_numeric" not in merged
    assert [x["model"] for x in merged["requests"]] == ["first", "second"]
    assert [x["provider"] for x in merged["requests"]] == ["one", "two"]
    assert "private" not in merged["requests"][0]
    assert "requests" not in merged["requests"][0]


def test_title_primary_flat_usage_preserves_unknown_input(monkeypatch):
    from agent.chat import session_service
    from bridge import bridge

    class Bot:
        def reply_text(self, session):
            return {"content": "Title", "total_tokens": 76, "completion_tokens": 6}

    class Bridge:
        def get_bot(self, kind):
            return Bot()

    monkeypatch.setattr(bridge, "Bridge", Bridge)
    attempts = []
    assert session_service.generate_session_title("question", attempts=attempts) == "Title"
    usage = attempts[0]["usage"]
    assert attempts[0]["status"] == "success"
    assert usage["total_tokens"] == 76
    assert usage["completion_tokens"] == 6
    assert usage["completion_tokens_reported_calls"] == 1
    assert "prompt_tokens_reported_calls" not in usage
    assert "model" not in usage
