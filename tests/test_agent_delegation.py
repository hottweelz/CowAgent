import threading
import time
from pathlib import Path

import pytest

from agent.registry import AgentProfile, AgentRegistry
from agent.protocol import Agent, LLMModel
from agent.tools.agent_delegate.agent_delegate import delegated_result_text, _DelegateView
from agent.tools.agent_delegate.agent_delegate import (
    AgentDelegateTool,
    DelegationPolicy,
    attach_agent_delegate_to_tool,
)
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType


def _registry(disable_research=False):
    return AgentRegistry(
        [
            AgentProfile("primary", "Primary", str(Path(FakeBridge.fixture_root) / "primary")),
            AgentProfile(
                "research",
                "Research",
                str(Path(FakeBridge.fixture_root) / "research"),
                enabled=not disable_research,
            ),
        ],
        "primary",
    )


def _context(agent_id="primary", session_id="user-session", **values):
    context = Context(ContextType.TEXT, "source turn", kwargs={})
    context["agent_id"] = agent_id
    context["session_id"] = session_id
    for key, value in values.items():
        context[key] = value
    return context


@pytest.fixture(autouse=True)
def _team_members(monkeypatch):
    """Make every conversation a team of primary + research by default.

    Targets are bounded to the conversation's members, read from session_prefs.
    Rather than touch the real store, stub the read so tests declare the roster
    inline; individual tests override ``roster`` to model a solo conversation.
    """
    roster = {"members": ["primary", "research"]}

    def fake_get_prefs(session_id, agent_id=None):
        return dict(roster)

    from agent.workspace import session_prefs

    monkeypatch.setattr(session_prefs, "get_prefs", fake_get_prefs)
    monkeypatch.setattr(session_prefs, "get_prefs_strict", fake_get_prefs)
    return roster


class FixtureBackend(LLMModel):
    def __init__(self):
        super().__init__("fixture-model")
        self.requests = []
        self.default = None
        self.entered = None
        self.release = None
        self.order = []

    def set_agent_default(self, provider, model):
        self.default = (provider, model)

    def call_stream(self, request):
        self.requests.append(request)
        query = str(request.messages)
        self.order.append(("start", query))
        if self.entered:
            self.entered.set()
        if self.release:
            self.release.wait(2)
        self.order.append(("end", query))
        yield {"choices": [{"delta": {"content": "delegated result"}, "finish_reason": "stop"}]}


@pytest.fixture(autouse=True)
def _isolated_runtime(monkeypatch, tmp_path):
    from agent.workspace import project_store
    monkeypatch.setattr(project_store, "get_project_dir_strict", lambda *args: str(tmp_path))
    from agent.recovery.store import TaskStore
    journal = TaskStore(tmp_path / "journal" / "tasks.db")
    monkeypatch.setattr("agent.recovery.runtime.get_task_store", lambda: journal)
    monkeypatch.setattr("agent.recovery.runtime._registry_profiles", lambda: FakeBridge.current_registry.list(include_disabled=True))
    monkeypatch.setattr("agent.subagent.runner._open_run", lambda *args: None)
    monkeypatch.setattr("bridge.agent_bridge.AgentLLMModel", lambda bridge: bridge.backend)
    monkeypatch.setattr("agent.permission.authority._registry_profiles", lambda: FakeBridge.current_registry.list(include_disabled=True))
    FakeBridge.fixture_root = str(tmp_path)
    for name in ("primary", "research", "designer"):
        (tmp_path / name).mkdir()


class FakeBridge:
    def __init__(self, registry=None):
        self.agent_registry = registry or _registry()
        FakeBridge.current_registry = self.agent_registry
        self.calls = []
        self.bridge = self
        self.backend = FixtureBackend()

    @staticmethod
    def _cancel_key(agent_id, token, default_agent_id):
        return token if agent_id == default_agent_id else f"{agent_id}::{token}"

    def agent_reply(self, query, context=None, on_event=None):
        self.calls.append((query, context, on_event))
        return Reply(ReplyType.TEXT, "delegated result")


def _tool(bridge=None, config=None, context=None):
    tool = AgentDelegateTool(config=config)
    actual_bridge = bridge or FakeBridge()
    actual_context = context or _context()
    attach_agent_delegate_to_tool(tool, actual_bridge, actual_context)
    tool.context = Agent("private", model=actual_bridge.backend, tools=[],
                         workspace_dir=actual_bridge.fixture_root, enable_skills=False,
                         max_steps=4, output_mode="logger")
    tool.context.permission_mode = "workspace-write"
    return tool


def test_policy_defaults_to_other_agents_and_honors_allowlist():
    default = DelegationPolicy.from_config({})
    assert default.allows("primary", "research") is True
    assert default.allows("primary", "primary") is False

    restricted = DelegationPolicy.from_config(
        {"allowed_targets": {"primary": ["research"], "research": []}}
    )
    assert restricted.allows("primary", "research") is True
    assert restricted.allows("research", "primary") is False


def test_policy_timeout_defaults_to_ten_minutes():
    assert DelegationPolicy.from_config({}).timeout_seconds == 600.0


def test_delegate_runs_target_with_source_attribution_and_private_relay_session():
    bridge = FakeBridge()
    tool = _tool(bridge=bridge)
    result = tool.execute({"agent_id": "research", "task": "Check the evidence"})
    assert result.status == "success" and result.result["agent_id"] == "research"
    assert result.result["delegated_by"] == "primary"
    assert result.result["session_id"].startswith("delegate_primary_research_")
    assert result.result["content"] == "delegated result"
    assert "Delegated by Agent 'Primary' (primary)" in str(bridge.backend.requests[0].messages)
    assert not bridge.calls
    assert "Primary → Research" in result.display


def test_delegate_keeps_the_answer_when_the_teammate_sent_a_file():
    reply = Reply(ReplyType.IMAGE_URL, "https://example.com/chart.png")
    reply.text_content = "Refund rate doubled to 2.63%."
    content = delegated_result_text(reply)
    assert content.startswith("Refund rate doubled to 2.63%.")
    assert "![](https://example.com/chart.png)" in content


def test_delegate_leaves_an_unpublished_file_as_a_plain_path():
    reply = Reply(ReplyType.IMAGE_URL, "file:///tmp/chart.png")
    assert delegated_result_text(reply) == "file:///tmp/chart.png"


def test_delegate_rejects_targets_outside_the_conversation_and_lists_the_real_ones(
    _team_members,
):
    _team_members["members"] = ["primary"]  # research is not a teammate here
    tool = _tool()

    result = tool.execute({"agent_id": "research", "task": "Do work"})

    assert result.status == "error"
    assert "is not a teammate you can delegate to" in result.result
    # The error names the actual options so the model can correct itself. Here
    # only the source is a member, so there is no one to delegate to.
    assert "no teammates you can delegate to" in result.result


def test_delegate_error_names_the_available_teammates(_team_members):
    _team_members["members"] = ["research"]
    tool = _tool()

    result = tool.execute({"agent_id": "missing", "task": "Do work"})

    assert result.status == "error"
    assert "is not a teammate you can delegate to" in result.result
    # The hint names ids plainly, without the "@" the roster shows.
    assert "Research (research)" in result.result
    assert "@research" not in result.result


def test_delegate_accepts_an_agent_id_with_a_leading_at_sign():
    """The roster shows ids as "@id", so a model often passes the "@" too."""
    bridge = FakeBridge()
    tool = _tool(bridge=bridge)

    result = tool.execute({"agent_id": "@research", "task": "Check it"})

    assert result.status == "success"
    assert result.result["agent_id"] == "research"


def test_restricted_delegate_does_not_inherit_nested_delegation_tools():
    bridge = FakeBridge()
    tool = _tool(bridge=bridge)
    result = tool.execute({"agent_id": "research", "task": "Look into it"})
    assert result.status == "success"
    assert all(t.get("name") != "agent_delegate" for t in bridge.backend.requests[0].tools or [])


def test_delegate_reads_the_inherited_roster_when_the_session_has_none(_team_members, monkeypatch):
    registry = AgentRegistry([AgentProfile("primary", "Primary", str(Path(FakeBridge.fixture_root) / "primary")),
        AgentProfile("research", "Research", str(Path(FakeBridge.fixture_root) / "research")),
        AgentProfile("designer", "Designer", str(Path(FakeBridge.fixture_root) / "designer"))], "primary")
    bridge = FakeBridge(registry=registry)
    context = _context(agent_id="primary", speaker_agent_id="research",
        session_id="delegate_primary_research_abc", delegation_root_session="user-session",
        delegation_members=["primary", "designer"], delegation_trace=["primary", "research"],
        delegation_host_id="primary")
    _team_members["members"] = ["research", "designer"]
    monkeypatch.setattr("agent.workspace.session_prefs.get_prefs", lambda *args: {})
    tool = _tool(bridge=bridge, context=context)
    ok = tool.execute({"agent_id": "designer", "task": "Make a banner"})
    assert ok.status == "success" and ok.result["agent_id"] == "designer"
    assert tool.execute({"agent_id": "primary", "task": "Loop back"}).status == "error"


def test_guest_speaker_delegates_under_its_own_identity_and_can_reach_the_host(_team_members):
    bridge = FakeBridge()
    _team_members["members"] = ["research"]
    tool = _tool(bridge=bridge, context=_context(agent_id="primary", speaker_agent_id="research"))
    result = tool.execute({"agent_id": "primary", "task": "Please cover the intro"})
    assert result.status == "success" and result.result["delegated_by"] == "research"
    assert "Delegated by Agent 'Research' (research)" in str(bridge.backend.requests[0].messages)


def test_guest_speaker_cannot_delegate_to_itself(_team_members):
    """The guest may reach the host and other members, but never itself."""
    _team_members["members"] = ["research"]
    context = _context(agent_id="primary", speaker_agent_id="research")
    tool = _tool(context=context)

    result = tool.execute({"agent_id": "research", "task": "Do it yourself"})

    assert result.status == "error"
    assert "is not a teammate you can delegate to" in result.result
    # The host is offered as a real option; the guest itself is not.
    assert "Primary (primary)" in result.result


def test_delegate_rejects_unknown_targets_as_non_teammates():
    tool = _tool()
    result = tool.execute({"agent_id": "missing", "task": "Do work"})
    assert result.status == "error"
    # Unknown ids are simply not teammates; the roster is offered instead.
    assert "is not a teammate you can delegate to" in result.result


def test_delegate_honors_the_allowlist_by_hiding_disallowed_teammates():
    # research is a member, but the ACL forbids primary -> research, so it is
    # not offered and delegating to it is refused as a non-teammate.
    denied = _tool(config={"allowed_targets": {"primary": []}})
    result = denied.execute({"agent_id": "research", "task": "Do work"})
    assert result.status == "error"
    assert "is not a teammate you can delegate to" in result.result


def test_delegate_rejects_cycles_and_depth_overflow():
    cycle = _tool(
        context=_context(
            agent_id="research",
            delegation_trace=["primary", "research"],
            delegation_depth=1,
        )
    )
    result = cycle.execute({"agent_id": "primary", "task": "Send it back"})
    assert result.status == "error"
    assert "cycle rejected" in result.result

    too_deep = _tool(
        config={"max_depth": 1},
        context=_context(delegation_trace=["primary"], delegation_depth=1),
    )
    result = too_deep.execute({"agent_id": "research", "task": "Go deeper"})
    assert result.status == "error"
    assert "exceeds the maximum" in result.result


def test_delegate_enforces_message_limit():
    tool = _tool(config={"max_message_chars": 4})
    result = tool.execute({"agent_id": "research", "task": "12345"})
    assert result.status == "error"
    assert "exceeds 4 characters" in result.result


def test_delegate_reports_a_target_failure_through_the_result(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("secret target exception")
    monkeypatch.setattr(Agent, "run_stream", fail)
    result = _tool().execute({"agent_id": "research", "task": "Do work"})
    assert result.status == "error" and "failed" in result.result
    assert "secret target exception" not in result.result


def test_delegate_relays_the_teammates_turn_bracketed_by_who_is_speaking():
    emitted = []
    tool = _tool()
    tool.tool_call_id = "card-123"
    tool.event_callback = lambda etype, data: emitted.append((etype, data))
    result = tool.execute({"agent_id": "research", "task": "Look it up"})
    assert result.status == "success"
    types = [t for t, _ in emitted]
    assert types[0] == "peer_message_start" and types[-1] == "peer_message_end"
    assert "message_update" in types
    assert emitted[0][1]["agent_id"] == "research"
    assert emitted[0][1]["source_id"] == "primary"
    assert emitted[0][1]["card_id"] == "card-123"


def test_delegate_closes_the_teammates_turn_when_the_hand_off_fails(monkeypatch):
    def fail(self, query, on_event=None, **kwargs):
        on_event({"type": "message_update", "data": {"delta": "starting"}})
        raise RuntimeError("private failure")
    monkeypatch.setattr(Agent, "run_stream", fail)
    emitted = []
    tool = _tool()
    tool.event_callback = lambda etype, data: emitted.append((etype, data))
    result = tool.execute({"agent_id": "research", "task": "Look it up"})
    assert result.status == "error" and "private failure" not in result.result
    assert emitted[0][0] == "peer_message_start" and emitted[-1][0] == "peer_message_end"


def test_delegate_passes_a_nested_hand_off_straight_through():
    emitted = []
    tool = _tool()
    tool.event_callback = lambda etype, data: emitted.append((etype, data))
    view = _DelegateView(tool, "card", AgentProfile("primary", "Primary", "/tmp/p"), "research", "Research")
    view.relay({"type": "message_update", "data": {"delta": "asking"}})
    view.relay({"type": "peer_message_start", "data": {"agent_id": "writer"}})
    view.relay({"type": "peer_message_end", "data": {"agent_id": "writer"}})
    view.close()
    assert [t for t, _ in emitted] == ["peer_message_start", "message_update", "peer_message_start", "peer_message_end", "peer_message_end"]


def test_delegate_says_nothing_when_the_teammate_never_speaks():
    emitted = []
    tool = _tool()
    tool.event_callback = lambda etype, data: emitted.append((etype, data))
    view = _DelegateView(tool, "card", AgentProfile("primary", "Primary", "/tmp/p"), "research", "Research")
    view.relay({"type": "turn_start", "data": {}})
    view.close()
    assert emitted == []


def test_delegate_serializes_hands_off_to_the_same_target_session():
    bridge = FakeBridge()
    bridge.backend.entered, bridge.backend.release = threading.Event(), threading.Event()
    first = threading.Thread(target=lambda: _tool(bridge=bridge).execute({"agent_id": "research", "task": "first"}))
    second = threading.Thread(target=lambda: _tool(bridge=bridge).execute({"agent_id": "research", "task": "second"}))
    first.start()
    try:
        assert bridge.backend.entered.wait(2)
        second.start()
        time.sleep(0.1)
        assert len(bridge.backend.order) == 1
    finally:
        bridge.backend.release.set()
        first.join(3)
        if second.ident:
            second.join(3)
    assert [kind for kind, _ in bridge.backend.order] == ["start", "end", "start", "end"]


def test_a_delegated_run_inherits_the_delegating_permission_mode(monkeypatch):
    captured = []
    original = Agent.run_stream
    def observe(self, *args, **kwargs):
        captured.append(self.authority)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Agent, "run_stream", observe)
    tool = _tool()
    tool.context.permission_mode = "read-only"
    assert tool.execute({"agent_id": "research", "task": "Check"}).status == "success"
    assert captured[0].mode == "read-only" and "fs.write" not in captured[0].capabilities


def test_no_live_source_denies_delegation():
    tool = _tool()
    tool.context = None
    result = tool.execute({"agent_id": "research", "task": "Check"})
    assert result.status == "error" and "authority" in result.result


def test_a_failing_authority_lookup_denies_delegation(monkeypatch):
    def fail(*args):
        raise RuntimeError("secret lookup failure")
    monkeypatch.setattr("agent.permission.authority.restricted_authority", fail)
    result = _tool().execute({"agent_id": "research", "task": "Check"})
    assert result.status == "error" and "authority" in result.result
    assert "secret lookup failure" not in result.result


def test_ordinary_turns_still_read_their_prefs():
    class _Target:
        def __init__(self):
            self.applied = []
            self.model = None

        def apply_permission_mode(self, mode):
            self.applied.append(mode)

    from bridge.agent_bridge import AgentBridge

    bridge = AgentBridge.__new__(AgentBridge)

    target = _Target()
    bridge.apply_session_prefs(target, "ordinary-session", "primary")
    assert target.applied == [None]

    target = _Target()
    bridge.apply_session_prefs(
        target, "ordinary-session", "primary", permission_mode="read-only"
    )
    assert target.applied == ["read-only"]
