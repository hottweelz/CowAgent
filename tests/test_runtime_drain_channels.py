import threading
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from bridge.context import Context, ContextType
from channel.chat_channel import ChatChannel
from channel.web.web_channel import drain_wsgi
from common import runtime_drain


@pytest.fixture
def coordinator(monkeypatch):
    drain = runtime_drain.RuntimeDrain()
    monkeypatch.setattr(runtime_drain, "_installed", drain)
    return drain


def test_wsgi_holds_until_iterable_close_and_rejects_all_except_health(coordinator):
    effects = []
    def app(env, start):
        effects.append(env["PATH_INFO"])
        start("200 OK", [])
        def body():
            yield b"first"
            yield b"last"
        return body()
    wrapped = drain_wsgi(app)
    statuses = []
    def start(status, headers):
        statuses.append(status)
    response = wrapped({"REQUEST_METHOD": "POST", "PATH_INFO": "/message"}, start)
    assert next(response) == b"first"
    coordinator.close_admission()
    assert coordinator.snapshot()["active"] == {"http": 1}
    assert list(wrapped({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/health"}, start)) == [b"first", b"last"]
    denied = wrapped({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/scheduler/run"}, start)
    assert list(denied) == [b"Service unavailable\n"]
    assert statuses[-1].startswith("503")
    assert effects == ["/message", "/api/health"]
    response.close()
    assert coordinator.snapshot()["active"] == {}


def test_queued_chat_leases_survive_close_until_callback_and_cancel(monkeypatch, coordinator):
    import importlib
    bridge_module = importlib.import_module("bridge.bridge")
    import channel.chat_channel as module
    bridge = SimpleNamespace(route_context=lambda ctx: ctx["agent_id"],
                             _cancel_key=lambda agent, session, default: agent + session,
                             agent_registry=SimpleNamespace(default_agent_id="default"),
                             scoped_session_key=lambda session, agent: agent + session)
    monkeypatch.setattr(bridge_module, "Bridge", lambda: SimpleNamespace(get_agent_bridge=lambda: bridge))
    monkeypatch.setattr(module, "conf", lambda: {})
    channel = ChatChannel.__new__(ChatChannel)
    channel.sessions, channel.futures, channel.lock = {}, {}, threading.Lock()
    contexts = [Context(ContextType.TEXT, "hello", {"session_id": "s", "agent_id": a}) for a in ("a", "b")]
    for context in contexts:
        channel.produce(context)
    coordinator.close_admission()
    assert coordinator.snapshot()["active"] == {"chat": 2}
    with pytest.raises(runtime_drain.AdmissionClosed):
        channel.produce(contexts[0])
    future = Future()
    monkeypatch.setattr(module.handler_pool, "submit", lambda *args: future)
    channel._consume_session("as")
    assert coordinator.snapshot()["active"] == {"chat": 2}
    channel.cancel_session("s", "b")
    # Route lookup for cancellation is independent from admission.
    assert coordinator.snapshot()["active"] == {"chat": 1}
    future.cancel()
    assert coordinator.snapshot()["active"] == {}


def test_chat_callback_remains_admitted_through_publication(monkeypatch, coordinator):
    import importlib
    from concurrent.futures import ThreadPoolExecutor
    module = importlib.import_module("channel.chat_channel")
    bridge_module = importlib.import_module("bridge.bridge")
    bridge = SimpleNamespace(route_context=lambda ctx: "a", _cancel_key=lambda *args: "key",
                             agent_registry=SimpleNamespace(default_agent_id="default"))
    monkeypatch.setattr(bridge_module, "Bridge", lambda: SimpleNamespace(get_agent_bridge=lambda: bridge))
    monkeypatch.setattr(module, "conf", lambda: {})
    channel = ChatChannel.__new__(ChatChannel)
    channel.sessions, channel.futures, channel.lock = {}, {}, threading.Lock()
    entered, finish = threading.Event(), threading.Event()
    channel._handle = lambda context: None
    def publish(*args, **kwargs):
        entered.set()
        assert finish.wait(5)
    channel._success_callback = publish
    with ThreadPoolExecutor(max_workers=1) as pool:
        monkeypatch.setattr(module, "handler_pool", pool)
        context = Context(ContextType.TEXT, "hello", {"session_id": "s"})
        channel.produce(context)
        # Ensure the callback does not run inline during registration.
        original = channel._handle
        allow_handle = threading.Event()
        channel._handle = lambda context: (allow_handle.wait(5), original(context))
        channel._consume_session("key")
        allow_handle.set()
        assert entered.wait(5)
        coordinator.close_admission()
        assert coordinator.snapshot()["active"] == {"chat": 1}
        finish.set()
    assert coordinator.snapshot()["active"] == {}


def test_wsgi_admitted_generator_can_start_child_after_close(coordinator):
    entered, finish = threading.Event(), threading.Event()
    worker = []
    def app(env, start):
        def response():
            yield b"headers"
            worker.append(runtime_drain.start_thread("descendant", lambda: (entered.set(), finish.wait(5))))
            yield b"done"
        return response()
    response = drain_wsgi(app)({"REQUEST_METHOD": "GET", "PATH_INFO": "/stream"}, lambda *args: None)
    assert next(response) == b"headers"
    coordinator.close_admission()
    assert next(response) == b"done"
    assert entered.wait(5)
    response.close()
    assert coordinator.snapshot()["active"] == {"descendant": 1}
    finish.set()
    worker[0].join(5)
    assert coordinator.snapshot()["active"] == {}


@pytest.mark.parametrize("method,path,blocker", [
    ("POST", "/api/file/reveal", "web_external_work"),
    ("POST", "/api/update/start", "web_external_work"),
    ("POST", "/api/mcp/servers/test", "web_external_work"),
    ("GET", "/mcp/oauth/callback", "web_mcp_oauth"),
    ("PUT", "/api/mcp/servers", "web_mcp_reconfigure"),
])
def test_external_http_effect_blocks_drain_after_response(monkeypatch, coordinator, method, path, blocker):
    monkeypatch.setattr(runtime_drain, "_validate_owner", lambda owner: owner)
    coordinator.bind_owner(SimpleNamespace(validate=lambda: None))
    response = drain_wsgi(lambda env, start: [b"ok"])(
        {"REQUEST_METHOD": method, "PATH_INFO": path}, lambda *args: None
    )
    assert list(response) == [b"ok"]
    coordinator.close_admission()
    receipt = coordinator.wait(0)
    assert receipt["active"] == {}
    assert not receipt["drained"]
    assert receipt["blockers"] == [blocker]


def test_external_marker_is_noop_without_coordinator(monkeypatch):
    monkeypatch.setattr(runtime_drain, "_installed", None)
    response = drain_wsgi(lambda env, start: [b"ok"])(
        {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/file/reveal"}, lambda *args: None
    )
    assert list(response) == [b"ok"]


def test_web_startup_tracks_preparation_but_not_serve(monkeypatch, coordinator):
    from channel.web.core.channel import WebChannel
    cls = WebChannel.__wrapped__
    entered, finish, serving = threading.Event(), threading.Event(), threading.Event()
    def prepare():
        entered.set()
        assert finish.wait(5)
        return SimpleNamespace(serve=lambda: serving.set()), None, "127.0.0.1", 1234, "http"
    channel = SimpleNamespace(_prepare_startup=prepare, _stop_loopback=lambda: None,
                              _rebind_to=None, _http_server=None)
    thread = threading.Thread(target=cls.startup, args=(channel,))
    thread.start()
    assert entered.wait(5)
    coordinator.close_admission()
    assert coordinator.snapshot()["active"] == {"web_startup": 1}
    finish.set()
    thread.join(5)
    assert serving.is_set()
    assert coordinator.snapshot()["active"] == {}


def test_sse_janitor_holds_each_sweep_and_stops_after_close(monkeypatch, coordinator):
    from channel.web.core.channel import WebChannel
    import channel.web.core.channel as module
    cls = WebChannel.__wrapped__
    entered, finish = threading.Event(), threading.Event()
    calls = []
    def sweep():
        calls.append(1)
        entered.set()
        assert finish.wait(5)
        return 0
    channel = SimpleNamespace(_sse_janitor_started=False, _sweep_sse_streams=sweep)
    threads = []
    real_thread = threading.Thread
    def spawn(*args, **kwargs):
        thread = real_thread(*args, **kwargs)
        threads.append(thread)
        return thread
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(module.threading, "Thread", spawn)
    cls._start_sse_janitor(channel)
    assert entered.wait(5)
    coordinator.close_admission()
    assert coordinator.snapshot()["active"] == {"sse_sweep": 1}
    finish.set()
    threads[0].join(5)
    assert not threads[0].is_alive()
    assert calls == [1]
    assert coordinator.snapshot()["active"] == {}
