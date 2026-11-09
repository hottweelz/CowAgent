import threading
from types import SimpleNamespace

import pytest

from common import runtime_drain as drain
from common.runtime_identity import RuntimeIdentity, current_agent_id, use_identity


class FakeRuntime:
    def validate(self):
        pass


@pytest.fixture
def coordinator(monkeypatch):
    monkeypatch.setattr(drain, "_installed", None)
    monkeypatch.setattr(drain, "_validate_owner", lambda owner: FakeRuntime())
    coordinator = drain.RuntimeDrain()
    coordinator.bind_owner(object())
    drain.install(coordinator)
    return coordinator


def test_direct_agent_boundaries_reject_after_close_before_side_effects(coordinator):
    from agent.protocol.agent import Agent
    from agent.chat.service import ChatService
    from bridge.agent_bridge import AgentBridge

    coordinator.close_admission()

    with pytest.raises(drain.AdmissionClosed):
        Agent.run_stream(object(), "query")
    with pytest.raises(drain.AdmissionClosed):
        ChatService.run(object(), "query", "session", lambda _chunk: None)
    with pytest.raises(drain.AdmissionClosed):
        AgentBridge.agent_reply(object(), "query")


def test_parallel_tool_lease_outlives_cancelled_parent_and_carries_identity(coordinator, monkeypatch):
    from agent.protocol.agent_stream import AgentStreamExecutor
    from concurrent.futures import ThreadPoolExecutor

    entered = threading.Event()
    submitted_all = threading.Event()
    release = threading.Event()
    child_state = {}
    submit_count = 0

    class TrackingPool(ThreadPoolExecutor):
        def submit(self, *args, **kwargs):
            nonlocal submit_count
            future = super().submit(*args, **kwargs)
            submit_count += 1
            if submit_count == 2:
                submitted_all.set()
            return future

    monkeypatch.setattr("agent.protocol.agent_stream.ThreadPoolExecutor", TrackingPool)
    executor = AgentStreamExecutor.__new__(AgentStreamExecutor)
    executor.tools = {"held": SimpleNamespace(parallel_safe=True)}
    executor.cancel_event = threading.Event()

    def held_tool(_call, _tool):
        child_state["identity"] = current_agent_id()
        child_state["lease"] = drain._active.get()
        entered.set()
        assert release.wait(2)
        return {"status": "success", "result": "done"}

    executor._execute_tool = held_tool
    outcomes = []

    def run_parent():
        with use_identity(RuntimeIdentity(agent_id="agent-held", session_id="s")):
            outcomes.append(executor._run_parallel_calls([
                {"id": "call-1", "name": "held"},
                {"id": "call-2", "name": "held"},
            ]))

    # Use two distinct call IDs, but only one held invocation is needed to keep
    # the lease live while the parent observes cancellation and returns.
    executor.tools = {"held": SimpleNamespace(parallel_safe=True)}
    thread = threading.Thread(target=run_parent)
    thread.start()
    assert entered.wait(1)
    assert submitted_all.wait(1)
    coordinator.close_admission()
    executor.cancel_event.set()
    thread.join(1)
    assert not thread.is_alive()
    assert set(outcomes[0]) == {"call-1", "call-2"}
    assert all(item["status"] == "error" for item in outcomes[0].values())
    receipt = coordinator.snapshot()
    assert not receipt["drained"]
    assert receipt["active"].get("parallel_tool", 0) >= 1
    assert child_state["identity"] == "agent-held"
    assert child_state["lease"] is not None

    release.set()
    assert coordinator.wait(1)["drained"]


def test_subagent_lease_outlives_cancelled_parent_and_carries_identity(coordinator, monkeypatch):
    from agent.subagent import runner

    entered = threading.Event()
    release = threading.Event()
    child_state = {}

    class Journal:
        def request_stop(self, *_args):
            pass

    def held_run(_parent, _template, _task, _index, _cancel, *_args, **_kwargs):
        from common.runtime_identity import current_agent_id

        child_state["identity"] = current_agent_id()
        child_state["lease"] = drain._active.get()
        entered.set()
        assert release.wait(2)
        return {"status": "done"}

    monkeypatch.setattr(runner, "_prepare_task", lambda *_args: (Journal(), "task", object()))
    monkeypatch.setattr(runner, "_run_one", held_run)
    cancellation = threading.Event()
    results = []

    def run_parent():
        with use_identity(RuntimeIdentity(agent_id="agent-parent", session_id="s")):
            results.extend(runner.run_tasks(
                object(), [runner.SubagentTask("goal")],
                {"default": SimpleNamespace(name="default")},
                runner.SubagentSettings(timeout_seconds=5),
                cancel_event=cancellation,
            ))

    thread = threading.Thread(target=run_parent)
    thread.start()
    assert entered.wait(1)
    coordinator.close_admission()
    cancellation.set()
    thread.join(1)
    assert not thread.is_alive()
    assert results[0]["status"] == "cancelled"
    receipt = coordinator.snapshot()
    assert not receipt["drained"]
    assert receipt["active"].get("subagent", 0) == 1
    assert child_state["identity"] == "agent-parent"
    assert child_state["lease"] is not None

    release.set()
    assert coordinator.wait(1)["drained"]


def test_guest_close_rejects_sweep_before_filesystem_work(coordinator, monkeypatch):
    from agent.guest.runtime import GuestService

    service = GuestService()
    removed = []
    monkeypatch.setattr(service, "_sweep_work_dirs", lambda _now: removed.append(True))
    coordinator.close_admission()

    with pytest.raises(drain.AdmissionClosed):
        service.sweep()
    assert removed == []


def test_guest_direct_run_rejects_before_begin_and_janitor_exits_on_close(coordinator, monkeypatch):
    from agent.guest.runtime import GuestService

    service = GuestService()
    began = []
    monkeypatch.setattr(service, "begin", lambda *_args, **_kwargs: began.append(True))
    coordinator.close_admission()

    with pytest.raises(drain.AdmissionClosed):
        service.run_turn(None, "visitor", "session", "hello")
    assert began == []

    monkeypatch.setattr("agent.guest.runtime.time.sleep", lambda _seconds: None)
    service._janitor()
    assert began == []


def test_external_supervisor_is_sticky_unknown_and_mutations_are_gated(coordinator):
    from agent.external.supervisor import ExternalSupervisor

    transport = SimpleNamespace(credential=SimpleNamespace(supervisor_id="sup"))
    supervisor = ExternalSupervisor(
        object(), transport, owner_id="owner", source_id="source",
        conversation_id="conversation",
    )
    coordinator.close_admission()

    with pytest.raises(drain.AdmissionClosed):
        supervisor.discover()
    receipt = coordinator.wait(0)
    assert "external_runtime_unattested" in receipt["blockers"]
    assert not receipt["drained"]


def test_legacy_bridge_dispatch_marks_unknown_before_provider_invocation(coordinator):
    from bridge.bridge import Bridge
    from bridge.reply import Reply, ReplyType

    calls = []
    bot = SimpleNamespace(reply=lambda query, context: calls.append((query, context)) or Reply(ReplyType.TEXT, "ok"))
    bridge = SimpleNamespace(get_bot=lambda kind: bot)

    result = Bridge.__wrapped__.fetch_reply_content(bridge, "query", object())

    assert result.content == "ok"
    assert calls == [("query", calls[0][1])]
    coordinator.close_admission()
    receipt = coordinator.wait(0)
    assert "legacy_provider_untracked" in receipt["blockers"]
    assert not receipt["drained"]


def test_legacy_bridge_closed_admission_prevents_provider_invocation(coordinator):
    from bridge.bridge import Bridge

    calls = []
    bridge = SimpleNamespace(get_bot=lambda _kind: calls.append(True))
    coordinator.close_admission()

    with pytest.raises(drain.AdmissionClosed):
        Bridge.__wrapped__.fetch_reply_content(bridge, "query", object())
    assert calls == []


def test_direct_xunfei_entrypoint_marks_unknown_and_closed_gate_prevents_work(coordinator, monkeypatch):
    from bridge.context import Context, ContextType
    from models.xunfei import xunfei_spark_bot as xunfei

    bot = xunfei.XunFeiBot.__new__(xunfei.XunFeiBot)
    bot.sessions = SimpleNamespace(
        session_query=lambda *_args: SimpleNamespace(messages=[]),
        session_reply=lambda *_args: None,
    )
    monkeypatch.setattr(bot, "gen_request_id", lambda _session: "fake-request")

    def fake_socket(_self, _messages, request_id):
        import queue
        from types import SimpleNamespace

        xunfei.queue_map[request_id] = queue.Queue()
        xunfei.queue_map[request_id].put(
            SimpleNamespace(is_end=True, reply="ok", usage={})
        )

    monkeypatch.setattr(xunfei.XunFeiBot, "create_web_socket", fake_socket)
    context = Context(ContextType.TEXT, "query")
    context["session_id"] = "session"
    reply = bot.reply("query", context)
    assert reply.content == "ok"
    coordinator.close_admission()
    assert "legacy_provider_untracked" in coordinator.wait(0)["blockers"]

    with pytest.raises(drain.AdmissionClosed):
        bot.reply("query", None)


def test_direct_linkai_detached_image_marks_unknown_and_closed_gate_prevents_work(coordinator, monkeypatch):
    import sys
    from bridge.context import Context, ContextType
    from models.linkai import link_ai_bot as linkai

    sent = threading.Event()
    bot = linkai.LinkAIBot.__new__(linkai.LinkAIBot)
    bot.sessions = SimpleNamespace(
        session_msg_query=lambda query, _session: [{"role": "user", "content": query}],
        session_reply=lambda *_args, **_kwargs: None,
    )
    bot._find_group_mapping_code = lambda _context: None
    bot._fetch_agent_suffix = lambda _response: ""
    bot._fetch_knowledge_search_suffix = lambda _response: ""
    bot._send_image = lambda *_args: sent.set()
    bot._process_url = lambda content: content

    monkeypatch.setattr(linkai, "conf", lambda: {
        "linkai_api_key": "test-key", "model": "test-model",
        "temperature": 0, "top_p": 1, "frequency_penalty": 0,
        "presence_penalty": 0, "channel_type": "web",
        "request_timeout": 1,
    })
    monkeypatch.setattr(linkai.utils, "apply_client_source", lambda _headers: None)
    monkeypatch.setitem(sys.modules, "linkai", SimpleNamespace(
        LinkAIClient=SimpleNamespace(fetch_client_id=lambda: None)
    ))

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [{
                    "message": {"content": "answer"},
                    "img_urls": ["https://example.invalid/fake.png"],
                    "text_content": "answer",
                }],
                "usage": {"total_tokens": 1},
            }

    requests = []
    monkeypatch.setattr(linkai.requests, "post", lambda **_kwargs: requests.append(True) or Response())
    context = Context(ContextType.TEXT, "query")
    context["session_id"] = "session"

    reply = bot._chat("query", context)
    assert reply.content == "answer"
    assert sent.wait(1)
    assert requests == [True]
    assert "legacy_provider_untracked" in coordinator.snapshot()["blockers"]

    coordinator.close_admission()
    with pytest.raises(drain.AdmissionClosed):
        bot._chat("query", None)
    assert requests == [True]
