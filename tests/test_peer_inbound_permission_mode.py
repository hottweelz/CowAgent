"""Mode-only peer requests fail before a receiver can run."""

import pytest


def _serve(payload, local_mode="full-access"):
    """Run an inbound request and assert the receiver was not called."""
    from agent.registry import AgentProfile, AgentRegistry
    from bridge.reply import Reply, ReplyType
    from agent.multiagent.inbound import serve_invoke
    import config as config_module

    registry = AgentRegistry(
        [
            AgentProfile("local", "Local", "/tmp/perm-local"),
            AgentProfile("peer", "Peer", "/tmp/perm-peer"),
        ],
        "local",
    )
    seen = {}

    class Bridge:
        agent_registry = registry

        def agent_reply(self, query, context=None, on_event=None):
            seen["context"] = context
            return Reply(ReplyType.TEXT, "ok")

    chunks = []
    original = config_module.conf
    config_module.conf = lambda: {
        "agent_delegation": {"allowed_targets": {"peer": ["local"]}},
        "agent_permission_mode": local_mode,
    }
    try:
        serve_invoke(payload, Bridge(), chunks.append)
    finally:
        config_module.conf = original
    assert "context" not in seen
    assert chunks and chunks[-1].get("status") == "failed"
    return chunks[-1]


def _payload(**overrides):
    payload = {
        "request_id": "req-1",
        "mode": "delegate",
        "source_agent_id": "peer",
        "source_name": "Peer",
        "target_agent_id": "local",
        "task": "read the config",
        "root_session_id": "root-1",
    }
    payload.update(overrides)
    return payload


def test_the_request_field_defaults_to_empty():
    from agent.multiagent import InvokeRequest

    request = InvokeRequest(
        request_id="r", target_id="peer", task="t", source_id="local", source_name="Local",
        root_session_id="root", trace=("local", "peer"), depth=1,
    )
    assert request.permission_mode == ""


@pytest.mark.parametrize("remote, local, expected", [
    ("read-only", "full-access", "read-only"),
    ("full-access", "read-only", "read-only"),
    ("full-access", "workspace-write", "workspace-write"),
    ("bogus", "workspace-write", "workspace-write"),
])
def test_a_remote_mode_is_rejected_without_authority(remote, local, expected):
    result = _serve(_payload(permission_mode=remote), local_mode=local)
    assert "authority protocol" in result["error"]


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_a_blank_mode_is_rejected_without_authority(blank):
    result = _serve(_payload(permission_mode=blank))
    assert "authority protocol" in result["error"]
