"""Legacy remote invocation stays denied, independent of alias or trace shape."""

import pytest


def _registry(default_id, profiles=(("main-agent", "Main"), ("helper", "Helper"))):
    from agent.registry import AgentProfile, AgentRegistry

    return AgentRegistry(
        [AgentProfile(pid, name, f"/tmp/alias-{pid}") for pid, name in profiles], default_id
    )


def _serve(trace, addressed, registry, monkeypatch, **overrides):
    from agent.multiagent.inbound import serve_invoke
    from bridge.reply import Reply, ReplyType
    import config as config_module

    seen = {}

    class Bridge:
        agent_registry = registry

        def agent_reply(self, query, context=None, on_event=None):
            seen["called"] = True
            seen["context"] = context
            return Reply(ReplyType.TEXT, "ok")

    payload = dict(
        request_id="req-1", mode="delegate", source_agent_id="helper", source_name="Helper",
        target_agent_id=addressed, task="read the config", root_session_id="root-1", trace=trace,
        **overrides,
    )
    chunks = []
    monkeypatch.setattr(config_module, "conf", lambda: {"agent_delegation": {}})
    serve_invoke(payload, Bridge(), chunks.append)
    return seen, (chunks[-1] if chunks else {})


def _assert_remote_invocation_denied(seen, result):
    assert seen == {}
    assert result.get("chunk_type") == "result"
    assert result.get("request_id") == "req-1"
    assert result.get("status") == "failed"
    assert result.get("error") == "Remote invocation denied: unsupported authority protocol"


@pytest.mark.parametrize(
    "default_id, trace",
    [
        ("main-agent", ["helper", "main-agent", "default"]),
        ("main-agent", ["main-agent", "helper", "main-agent"]),
        ("main-agent", ["default", "helper"]),
        # With helper as the default, "default" means helper and must not fold onto main-agent.
        ("helper", ["main-agent", "helper"]),
    ],
)
def test_legacy_remote_invocation_is_denied_for_alias_and_cycle_traces(
    monkeypatch, default_id, trace
):
    seen, result = _serve(trace, "main-agent", _registry(default_id), monkeypatch)
    _assert_remote_invocation_denied(seen, result)


@pytest.mark.parametrize("trace, addressed", [(["helper"], "main-agent"), (["helper", "default"], "default")])
def test_legacy_remote_invocation_is_denied_for_fresh_alias_chains(
    monkeypatch, trace, addressed
):
    seen, result = _serve(
        trace, addressed, _registry("main-agent"), monkeypatch, members=["default", "helper"]
    )
    _assert_remote_invocation_denied(seen, result)


def test_legacy_remote_invocation_is_denied_on_a_single_agent_install(monkeypatch):
    roster = _registry("default", profiles=(("default", "Solo"),))
    seen, result = _serve(["helper"], "default", roster, monkeypatch)
    _assert_remote_invocation_denied(seen, result)
