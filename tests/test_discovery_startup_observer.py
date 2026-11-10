"""Security and startup-order tests for the launch-only discovery observer."""

import json
import os
import subprocess
import sys
import time
import types
import uuid
from pathlib import Path

import pytest

from agent.discovery import startup_observer as observer
from agent.external import contract
from agent.registry import AgentProfile, AgentRegistry


@pytest.fixture(autouse=True)
def clear_launch_state(monkeypatch):
    from common import runtime_drain
    monkeypatch.setattr(runtime_drain, "_installed", None)
    monkeypatch.setattr(observer, "_pending", None)
    monkeypatch.delenv("COW_DESKTOP", raising=False)


def _requirements(deadline=None):
    return {
        "task_id": str(uuid.uuid4()),
        "policy_id": "safe-default",
        "category": "analysis",
        "input_contract": "fictional_records.v1",
        "output_contract": "analysis_report.v1",
        "persistent_memory": "prohibited",
        "required_tools": [],
        "max_authority": ["fs.read"],
        "approval": "prohibited",
        "verification": "none",
        "recovery": "none",
        "cancellation": "cooperative",
        "deadline": deadline or time.time() + 120,
        "timeout_seconds": 20.0,
        "concurrency": 1,
        "permitted_mechanisms": ["native_isolated"],
        "prohibited_mechanisms": [],
        "task_spec_hash": contract.digest({"fixture": "no execution"}),
        "persistent_context": "prohibited",
    }


def _write_request(directory, *, changes=None, raw=None, name="request.json"):
    directory = Path(directory).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    path = directory / name
    request = {
        "protocol": observer.PROTOCOL,
        "request_id": uuid.uuid4().hex,
        "request_path": str(path),
        "issued_at": time.time() - 1,
        "expires_at": time.time() + 120,
        "uid": os.getuid(),
        "manifest": observer.source_manifest(),
        "interpreter": {"executable": os.path.abspath(__import__("sys").executable),
                        "prefix": os.path.abspath(__import__("sys").prefix)},
        "data_root": str(directory),
        "contact_authorized": False,
        "bindings": [],
        "requirements": [_requirements()],
    }
    if changes:
        request.update({
            key: value(request) if callable(value) else value
            for key, value in changes.items()
        })
    payload = raw if raw is not None else json.dumps(request, separators=(",", ":")).encode()
    path.write_bytes(payload)
    path.chmod(0o600)
    return path, request


def test_default_app_start_has_no_observer_activation(monkeypatch):
    assert observer.begin_startup(str(observer.ROOT / "app.py")) is None
    monkeypatch.setenv("COW_DISCOVERY_REQUEST", "/tmp/ignored.json")
    assert observer.begin_startup(str(observer.ROOT / "app.py")) is None


def test_valid_request_is_bound_consumed_and_begins_once(tmp_path, monkeypatch):
    path, request = _write_request(tmp_path / "private")
    monkeypatch.setenv("COW_DATA_DIR", str((tmp_path / "private").resolve()))

    launch = observer.prepare_launch(path)

    assert not path.exists()
    assert launch.consumed_path.name == f".cow-discovery-{request['request_id']}.consumed"
    assert launch.consumed_path.stat().st_mode & 0o777 == 0o600
    assert launch.receipt_path == path.with_name("request.json.receipt.json")
    assert observer.begin_startup(str(observer.ROOT / "app.py")) is launch
    with pytest.raises(observer.StartupObservationError, match="startup_launch_unavailable"):
        observer.begin_startup(str(observer.ROOT / "app.py"))


@pytest.mark.parametrize("changes,reason", [
    ({"uid": -1}, "startup_request_invalid"),
    ({"contact_authorized": True}, "startup_request_invalid"),
    ({"expires_at": lambda request: request["issued_at"] - 1}, "startup_request_invalid"),
    ({"expires_at": lambda request: request["issued_at"] + 301}, "startup_request_invalid"),
    ({"request_id": "not-a-nonce"}, "startup_request_invalid"),
    ({"manifest": {"app.py": "0" * 64}}, "startup_manifest_mismatch"),
    ({"interpreter": {"executable": "/wrong", "prefix": "/wrong"}}, "startup_launch_binding_mismatch"),
    ({"data_root": "/wrong"}, "startup_launch_binding_mismatch"),
])
def test_invalid_binding_and_expiry_fail_before_consumption(tmp_path, monkeypatch, changes, reason):
    path, _ = _write_request(tmp_path / "private", changes=changes)
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))

    with pytest.raises(observer.StartupObservationError, match=reason):
        observer.prepare_launch(path)

    assert path.exists()
    assert not list(path.parent.glob("*.consumed"))


def test_duplicate_json_keys_rejected(tmp_path, monkeypatch):
    path, request = _write_request(tmp_path / "private")
    payload = json.dumps(request, separators=(",", ":"))[:-1] + ',"uid":0}'
    path.write_text(payload)
    path.chmod(0o600)
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))

    with pytest.raises(observer.StartupObservationError, match="startup_request_invalid"):
        observer.prepare_launch(path)
    assert path.exists()


def test_unknown_schema_field_and_expired_task_are_rejected(tmp_path, monkeypatch):
    directory = tmp_path / "private"
    path, request = _write_request(directory, changes={"extra": "forbidden"})
    monkeypatch.setenv("COW_DATA_DIR", str(directory.resolve()))
    with pytest.raises(observer.StartupObservationError, match="startup_request_invalid"):
        observer.prepare_launch(path)

    path2, _ = _write_request(
        directory,
        changes={"requirements": [_requirements(time.time() - 1)]},
        name="expired.json",
    )
    with pytest.raises(observer.StartupObservationError, match="startup_request_invalid"):
        observer.prepare_launch(path2)


@pytest.mark.parametrize("mode", [0o644, 0o666])
def test_request_mode_must_be_exact_private_mode(tmp_path, monkeypatch, mode):
    path, _ = _write_request(tmp_path / "private")
    path.chmod(mode)
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    with pytest.raises(Exception, match="untrusted_record_file"):
        observer.prepare_launch(path)
    assert path.exists()


def test_oversized_request_is_rejected_without_consuming(tmp_path, monkeypatch):
    path, _ = _write_request(tmp_path / "private", raw=b"{" + b" " * observer.MAX_BYTES + b"}")
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    with pytest.raises(Exception, match="untrusted_record_file"):
        observer.prepare_launch(path)
    assert path.exists()


def test_unsafe_ancestor_fails_closed(tmp_path, monkeypatch):
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o700)
    directory = unsafe / "private"
    path, _ = _write_request(directory, name="request.json")
    unsafe.chmod(0o777)
    monkeypatch.setenv("COW_DATA_DIR", str(directory))
    with pytest.raises(observer.StartupObservationError, match="startup_private_path_unavailable"):
        observer.prepare_launch(path)
    unsafe.chmod(0o700)


def test_filesystem_ownership_guard_failure_rejects_request(tmp_path, monkeypatch):
    path, _ = _write_request(tmp_path / "private")
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    import agent.external.filesystem_trust as trust
    real = trust.require_filesystem_ownership

    def denied(*args, **kwargs):
        target = kwargs.get("path") or (args[0] if args else None)
        if target is not None and Path(target).resolve() == path.parent:
            raise contract.ProtocolError("Filesystem ignores ownership")
        return real(*args, **kwargs)

    monkeypatch.setattr(trust, "require_filesystem_ownership", denied)
    with pytest.raises(contract.ProtocolError, match="Filesystem ignores ownership"):
        observer.prepare_launch(path)


def test_request_path_binding_prevents_copy_and_consumed_replay(tmp_path, monkeypatch):
    path, request = _write_request(tmp_path / "private")
    original = path.read_bytes()
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    copied = path.parent / "copy.json"
    copied.write_bytes(path.read_bytes())
    copied.chmod(0o600)
    with pytest.raises(observer.StartupObservationError, match="startup_launch_binding_mismatch"):
        observer.prepare_launch(copied)
    assert path.exists() and copied.exists()

    launch = observer.prepare_launch(path)
    monkeypatch.setattr(observer, "_pending", None)
    with pytest.raises(observer.StartupObservationError, match="startup_request_consumed"):
        observer.prepare_launch(launch.consumed_path)

    # Recreating the original request must not bypass the permanent request-id
    # claim in the same private directory.
    path.write_bytes(original)
    path.chmod(0o600)
    with pytest.raises(FileExistsError):
        observer.prepare_launch(path)
    assert path.exists()


def test_desktop_mode_and_wrong_app_path_reject_launch(tmp_path, monkeypatch):
    path, _ = _write_request(tmp_path / "private")
    wrong_app = tmp_path / "other-app.py"
    wrong_app.write_text("# not the app\n")
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    observer.prepare_launch(path)
    with pytest.raises(observer.StartupObservationError, match="startup_launch_binding_mismatch"):
        observer.begin_startup(str(wrong_app))
    monkeypatch.setenv("COW_DESKTOP", "1")
    with pytest.raises(observer.StartupObservationError, match="startup_launch_unavailable"):
        observer.begin_startup(str(observer.ROOT / "app.py"))


def test_receipt_collision_prevents_observer_initialization(tmp_path, monkeypatch):
    path, _ = _write_request(tmp_path / "private")
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    path.with_name(path.name + ".receipt.json").write_text("sentinel")
    path.with_name(path.name + ".receipt.json").chmod(0o600)
    with pytest.raises(observer.StartupObservationError, match="startup_receipt_exists"):
        observer.prepare_launch(path)
    assert path.exists()


@pytest.fixture
def initialized_owner(tmp_path, monkeypatch):
    """Build the owner through the normal Bridge -> AgentBridge path."""
    import config
    import agent.registry as registry_module

    from bridge.bridge import Bridge
    from bridge.agent_bridge import AgentBridge

    root = tmp_path.resolve()
    data_root = root / "data"
    data_root.mkdir()
    monkeypatch.setenv("COW_DATA_DIR", str(data_root))
    settings = {
        "agent_workspace": str(root / "workspace"),
        "model": "fixture-model",
        "bot_type": "openai",
        "agent_permission_mode": "read-only",
        "self_evolution_enabled": False,
        "agent_delegation": {"enabled": True, "allowed_targets": {"owner": ["testpilot"]}},
        "chat_fallback": {"enabled": False},
    }
    (root / "workspace" / "owner").mkdir(parents=True)
    (root / "workspace" / "testpilot").mkdir(parents=True)
    monkeypatch.setattr(config, "config", config.Config(settings))
    registry = AgentRegistry([
        AgentProfile("owner", "Owner", str(root / "workspace" / "owner"), bot_type="openai"),
        AgentProfile("testpilot", "TestPilot", str(root / "workspace" / "testpilot"),
                     bot_type="openai", model="fixture-model"),
    ], default_agent_id="owner")
    monkeypatch.setattr(registry_module, "get_agent_registry", lambda: registry)
    monkeypatch.setattr("agent.recovery.service.start_recovery_service", lambda owner: None)
    scheduler_package = types.ModuleType("agent.tools.scheduler")
    scheduler_package.__path__ = []
    scheduler_integration = types.ModuleType("agent.tools.scheduler.integration")
    scheduler_integration.init_scheduler = lambda *a, **k: False
    monkeypatch.setitem(sys.modules, "agent.tools.scheduler", scheduler_package)
    monkeypatch.setitem(sys.modules, "agent.tools.scheduler.integration", scheduler_integration)
    monkeypatch.setattr("agent.evolution.trigger.start_evolution_trigger", lambda *a: None)
    bridge = Bridge.__wrapped__()
    owner = bridge.get_agent_bridge()
    assert type(owner) is AgentBridge
    return owner


def test_actual_initialized_owner_observes_once_without_dispatch_or_private_construction(
    tmp_path, monkeypatch, initialized_owner,
):
    from agent.discovery.runtime_readers import TrustedDiscoveryHost
    from agent.memory.manager import MemoryManager
    from agent.protocol.agent import Agent
    from bridge.agent_bridge import AgentBridge, AgentLLMModel

    path, _ = _write_request(tmp_path / "private")
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    launch = observer.prepare_launch(path)
    observer.begin_startup(str(observer.ROOT / "app.py"))
    calls = {"host": 0, "select": 0, "revalidate": 0}
    original_factory = TrustedDiscoveryHost.from_initialized_runtime

    def make_host(owner, **kwargs):
        calls["host"] += 1
        host = original_factory(owner, **kwargs)
        select, revalidate = host.select, host.revalidate
        host.select = lambda task: (calls.__setitem__("select", calls["select"] + 1) or select(task))
        host.revalidate = lambda decision, task: (
            calls.__setitem__("revalidate", calls["revalidate"] + 1) or revalidate(decision, task)
        )
        return host

    monkeypatch.setattr(TrustedDiscoveryHost, "from_initialized_runtime", make_host)
    monkeypatch.setattr(Agent, "__init__", lambda *a, **k: pytest.fail("Agent constructed"))
    monkeypatch.setattr(AgentBridge, "__init__", lambda *a, **k: pytest.fail("AgentBridge constructed"))
    monkeypatch.setattr(AgentLLMModel, "__init__", lambda *a, **k: pytest.fail("model constructed"))
    monkeypatch.setattr(MemoryManager, "__init__", lambda *a, **k: pytest.fail("memory constructed"))

    receipt = observer.observe_and_publish(launch, initialized_owner)

    assert calls == {"host": 1, "select": 1, "revalidate": 1}
    assert receipt["adapter_contact"] is False
    assert receipt["dispatch_permitted"] is False
    assert receipt["execution_revalidation_required"] is True
    assert len(receipt["inventory"]) == 2
    assert len(receipt["decisions"]) == 1
    assert receipt["decisions"][0]["selection"]["dispatch_permitted"] is False
    assert launch.receipt_path.exists()
    assert launch.receipt_path.stat().st_mode & 0o777 == 0o600


def test_invalid_owner_is_rejected_before_private_binding_reader(tmp_path, monkeypatch):
    from agent.discovery.runtime_readers import TrustedDiscoveryHost

    binding = {"operator_dir": str(tmp_path), "credential_path": str(tmp_path / "credential.json"),
               "spec_path": str(tmp_path / "spec.json"), "probe_receipt_path": None, "config_path": None}
    path, _ = _write_request(tmp_path / "private", changes={"bindings": [binding]})
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    launch = observer.prepare_launch(path)
    observer.begin_startup(str(observer.ROOT / "app.py"))
    monkeypatch.setattr(TrustedDiscoveryHost, "from_initialized_runtime",
                        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("owner rejected")))
    from agent.discovery.runtime_readers import ExistingRuntimeBinding
    monkeypatch.setattr(ExistingRuntimeBinding, "from_private_files",
                        lambda **_k: pytest.fail("private authority opened before owner validation"))

    with pytest.raises(ValueError, match="owner rejected"):
        observer.observe_and_publish(launch, object())


@pytest.mark.parametrize('with_control', [False, True])
def test_source_startup_runs_observer_after_owner_before_channels(monkeypatch, with_control):
    import app
    from common import maintenance_control, service_lifecycle

    order = []
    prepared = types.SimpleNamespace(close=lambda: order.append('prepared_closed'))
    launch = types.SimpleNamespace(maintenance_control=prepared if with_control else None)
    owner = object()
    # This test isolates orchestration order. Genuine-owner validation is
    # exercised separately below and in the disposable service rehearsal.
    monkeypatch.setattr(service_lifecycle, "bind_initialized",
                        lambda coordinator, got_owner, channels: order.append("lifecycle"))
    def bind_control(got_prepared, coordinator, got_owner):
        assert got_prepared is prepared and got_owner is owner
        order.append('control')
        return types.SimpleNamespace(close=lambda: order.append('control_closed'))
    monkeypatch.setattr(maintenance_control, 'bind_initialized', bind_control)
    monkeypatch.setattr(observer, "begin_startup", lambda _path: launch)
    monkeypatch.setattr(observer, "observe_and_publish", lambda got_launch, got_owner: (
        order.append("observe") if got_launch is launch and got_owner is owner else None
    ))
    monkeypatch.setattr(app, "ensure_ca_bundle", lambda: None)
    monkeypatch.setattr(app, "load_config", lambda: order.append("config"))
    monkeypatch.setattr(app, "_register_pid_file", lambda: None)
    monkeypatch.setattr(app, "_migrate_team_roster", lambda: None)
    monkeypatch.setattr(app, "_migrate_conversations", lambda: None)
    monkeypatch.setattr(app, "_warn_if_legacy_workspace_data_exists", lambda: None)
    monkeypatch.setattr(app, "sigterm_handler_wrap", lambda *_a: None)
    monkeypatch.setattr(app, "conf", lambda: {"web_console": False, "channel_type": "web"})
    monkeypatch.setattr(app, "_resolve_startup_channels", lambda _raw: [])
    monkeypatch.setattr(app, "_has_web_entry", lambda _names: True)
    monkeypatch.setattr(app, "_sync_builtin_skills", lambda: None)
    monkeypatch.setattr(app, "_scaffold_subagent_assets", lambda: None)
    monkeypatch.setattr(app, "_warmup_mcp_tools", lambda: None)
    monkeypatch.setattr(app, "_warmup_scheduler", lambda: (order.append("owner") or owner))
    monkeypatch.setattr(app, "DESKTOP_MODE", False)

    class Channels:
        def start(self, *_args, **_kwargs):
            order.append("channels")
            raise KeyboardInterrupt

    monkeypatch.setattr(app, "ChannelManager", Channels)
    monkeypatch.setattr(app, "set_channel_manager", lambda _manager: None)
    app.run()

    assert order.index("owner") < order.index("lifecycle") < order.index("observe") < order.index("channels")
    if with_control:
        assert order.index('lifecycle') < order.index('control') < order.index('observe')
        assert order[-2:] == ['control_closed', 'prepared_closed']
    else:
        assert 'control' not in order


def test_real_runtime_owner_tracks_two_agents_until_last_completion(initialized_owner):
    from common import runtime_drain

    coordinator = runtime_drain.install(runtime_drain.RuntimeDrain())
    coordinator.bind_owner(initialized_owner)
    first = coordinator.reserve("agent", "owner")
    second = coordinator.reserve("agent", "testpilot")
    coordinator.close_admission()
    assert coordinator.wait(0)["agents"] == {"owner": 1, "testpilot": 1}
    first.release()
    assert coordinator.wait(0)["drained"] is False
    second.release()
    assert coordinator.wait(1)["drained"] is True


def test_real_owner_cannot_substitute_for_missing_component_coverage(initialized_owner):
    from common import service_lifecycle

    coordinator = service_lifecycle.prepare()
    service_lifecycle.bind_initialized(coordinator, initialized_owner, ["web", "telegram"])
    receipt = service_lifecycle.drain(initialized_owner, 0.2)
    assert receipt["drained"] is False
    assert "missing_component:recovery" in receipt["blockers"]
    assert "http_not_ready" in receipt["blockers"]
    assert "non_web_ingress" in receipt["blockers"]
    assert receipt["registered_agents"] == ["owner", "testpilot"]


def test_ordinary_source_start_has_no_observer_and_keeps_startup_order(monkeypatch):
    import app

    order = []
    monkeypatch.setattr(observer, "_pending", None)
    monkeypatch.setattr(observer, "observe_and_publish", lambda *_a: pytest.fail("observer activated"))
    monkeypatch.setattr(app, "ensure_ca_bundle", lambda: None)
    monkeypatch.setattr(app, "load_config", lambda: order.append("config"))
    monkeypatch.setattr(app, "_register_pid_file", lambda: None)
    monkeypatch.setattr(app, "_migrate_team_roster", lambda: order.append("team_migration"))
    monkeypatch.setattr(app, "_migrate_conversations", lambda: order.append("conversation_migration"))
    monkeypatch.setattr(app, "_warn_if_legacy_workspace_data_exists", lambda: None)
    monkeypatch.setattr(app, "sigterm_handler_wrap", lambda *_a: None)
    monkeypatch.setattr(app, "conf", lambda: {"web_console": False, "channel_type": "web"})
    monkeypatch.setattr(app, "_resolve_startup_channels", lambda _raw: [])
    monkeypatch.setattr(app, "_has_web_entry", lambda _names: True)
    monkeypatch.setattr(app, "_sync_builtin_skills", lambda: order.append("skills"))
    monkeypatch.setattr(app, "_scaffold_subagent_assets", lambda: order.append("assets"))
    monkeypatch.setattr(app, "_warmup_mcp_tools", lambda: order.append("mcp"))
    monkeypatch.setattr(app, "_warmup_scheduler", lambda: (order.append("owner") or None))
    monkeypatch.setattr(app, "DESKTOP_MODE", False)

    class Channels:
        def start(self, *_args, **_kwargs):
            order.append("channels")
            raise KeyboardInterrupt

    monkeypatch.setattr(app, "ChannelManager", Channels)
    monkeypatch.setattr(app, "set_channel_manager", lambda _manager: None)
    app.run()

    assert order.index("config") < order.index("team_migration") < order.index("conversation_migration")
    assert order.index("skills") < order.index("assets") < order.index("mcp")
    assert order.index("mcp") < order.index("owner") < order.index("channels")


def test_observer_failure_exits_nonzero_before_channels(monkeypatch):
    import app

    order = []
    monkeypatch.setattr(observer, "begin_startup", lambda _path: object())
    monkeypatch.setattr(observer, "observe_and_publish", lambda *_a: (_ for _ in ()).throw(
        observer.StartupObservationError("startup_observation_invalid")))
    monkeypatch.setattr(app, "ensure_ca_bundle", lambda: None)
    monkeypatch.setattr(app, "load_config", lambda: None)
    monkeypatch.setattr(app, "_register_pid_file", lambda: None)
    monkeypatch.setattr(app, "_migrate_team_roster", lambda: None)
    monkeypatch.setattr(app, "_migrate_conversations", lambda: None)
    monkeypatch.setattr(app, "_warn_if_legacy_workspace_data_exists", lambda: None)
    monkeypatch.setattr(app, "sigterm_handler_wrap", lambda *_a: None)
    monkeypatch.setattr(app, "conf", lambda: {"web_console": False, "channel_type": "web"})
    monkeypatch.setattr(app, "_resolve_startup_channels", lambda _raw: [])
    monkeypatch.setattr(app, "_has_web_entry", lambda _names: True)
    monkeypatch.setattr(app, "_sync_builtin_skills", lambda: None)
    monkeypatch.setattr(app, "_scaffold_subagent_assets", lambda: None)
    monkeypatch.setattr(app, "_warmup_mcp_tools", lambda: None)
    monkeypatch.setattr(app, "_warmup_scheduler", lambda: object())
    monkeypatch.setattr(app, "DESKTOP_MODE", False)

    class Channels:
        def start(self, *_args, **_kwargs):
            order.append("channels")

    monkeypatch.setattr(app, "ChannelManager", Channels)
    monkeypatch.setattr(app, "set_channel_manager", lambda _manager: None)
    with pytest.raises(SystemExit) as exc:
        app.run()
    assert exc.value.code
    assert "channels" not in order


def test_ordinary_desktop_start_keeps_deferred_warmup_order(monkeypatch):
    import app

    order = []
    monkeypatch.setattr(observer, "_pending", None)
    monkeypatch.setattr(app, "ensure_ca_bundle", lambda: None)
    monkeypatch.setattr(app, "load_config", lambda: order.append("config"))
    monkeypatch.setattr(app, "_register_pid_file", lambda: None)
    monkeypatch.setattr(app, "_migrate_team_roster", lambda: None)
    monkeypatch.setattr(app, "_migrate_conversations", lambda: None)
    monkeypatch.setattr(app, "_warn_if_legacy_workspace_data_exists", lambda: None)
    monkeypatch.setattr(app, "sigterm_handler_wrap", lambda *_a: None)
    monkeypatch.setattr(app, "conf", lambda: {"web_console": False, "channel_type": "web"})
    monkeypatch.setattr(app, "_resolve_startup_channels", lambda _raw: [])
    monkeypatch.setattr(app, "_has_web_entry", lambda _names: True)
    monkeypatch.setattr(app, "_sync_builtin_skills", lambda: None)
    monkeypatch.setattr(app, "_scaffold_subagent_assets", lambda: None)
    monkeypatch.setattr(app, "_preload_heavy_imports", lambda: order.append("preload"))
    monkeypatch.setattr(app, "_start_web_watchdog", lambda: order.append("watchdog"))
    monkeypatch.setattr(app, "_warmup_scheduler", lambda: order.append("sync_warmup"))
    monkeypatch.setattr(app, "_warmup_mcp_tools", lambda: pytest.fail("desktop MCP warmup"))
    monkeypatch.setattr(app, "DESKTOP_MODE", True)

    class Thread:
        def __init__(self, *, target, daemon):
            assert target is app._warmup_scheduler and daemon is True
            order.append("thread_constructed")

        def start(self):
            order.append("thread_started")

    class Channels:
        def start(self, *_args, **_kwargs):
            order.append("channels")
            raise KeyboardInterrupt

    monkeypatch.setattr(app.threading, "Thread", Thread)
    monkeypatch.setattr(app, "ChannelManager", Channels)
    monkeypatch.setattr(app, "set_channel_manager", lambda _manager: None)
    app.run()

    assert order.index("preload") < order.index("watchdog")
    assert order.index("thread_started") < order.index("channels")
    assert "sync_warmup" not in order


def test_desktop_maintenance_launch_is_rejected_before_config_load(tmp_path, monkeypatch):
    import app

    path, _ = _write_request(tmp_path / "private")
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    observer.prepare_launch(path)
    monkeypatch.setenv("COW_DESKTOP", "1")
    calls = []
    monkeypatch.setattr(app, "load_config", lambda: calls.append("config"))

    with pytest.raises(SystemExit, match="Authenticated startup observation rejected"):
        app.run()
    assert calls == []


def test_helper_rejects_invalid_request_before_app_execution(tmp_path, monkeypatch):
    import scripts.discovery_startup as launcher

    path, _ = _write_request(tmp_path / "private", changes={"data_root": "/wrong"})
    monkeypatch.setenv("COW_DATA_DIR", str(path.parent))
    monkeypatch.setattr(launcher.runpy, "run_path", lambda *_a, **_k: pytest.fail("app executed"))

    with pytest.raises(SystemExit, match="Authenticated startup observation rejected") as exc:
        launcher.main(["--request", str(path)])
    assert exc.value.code
    assert path.exists()
    assert observer._pending is None


def test_helper_authenticates_before_preparing_control(tmp_path, monkeypatch):
    import scripts.discovery_startup as launcher
    from common import maintenance_control

    request, _ = _write_request(tmp_path / 'private')
    monkeypatch.setattr(launcher.sys, 'argv', list(sys.argv))
    monkeypatch.setattr(launcher.sys, 'path', list(sys.path))
    monkeypatch.setenv('COW_DATA_DIR', str(request.parent))
    prepared = object()
    calls = []
    def prepare(path):
        assert observer._pending is not None and not request.exists()
        calls.append(('prepare', path))
        return prepared
    def run_app(*_args, **_kwargs):
        assert observer._pending.maintenance_control is prepared
        calls.append(('app', None))
    monkeypatch.setattr(maintenance_control, 'prepare', prepare)
    monkeypatch.setattr(launcher.runpy, 'run_path', run_app)
    launcher.main(['--request', str(request), '--control-dir', str(tmp_path / 'control')])
    assert [item[0] for item in calls] == ['prepare', 'app']


def test_invalid_launch_cannot_prepare_control(tmp_path, monkeypatch):
    import scripts.discovery_startup as launcher
    from common import maintenance_control

    monkeypatch.setattr(maintenance_control, 'prepare',
                        lambda *_a: pytest.fail('control prepared before authentication'))
    monkeypatch.setattr(launcher.runpy, 'run_path', lambda *_a, **_k: pytest.fail('app executed'))
    with pytest.raises(SystemExit, match='Authenticated startup observation rejected'):
        launcher.main(['--request', str(tmp_path / 'missing'),
                       '--control-dir', str(tmp_path / 'control')])


@pytest.mark.parametrize("invalid_case", ["missing", "schema", "expiry"])
def test_cold_helper_rejects_before_runtime_setup_without_data_or_logs(tmp_path, invalid_case):
    """A fresh interpreter must reject before config, logging or app startup."""
    repo = observer.ROOT
    home = tmp_path / "isolated-home"
    data_root = tmp_path / "not-created-data"
    request = tmp_path / "missing-request.json"
    home.mkdir(mode=0o700)
    if invalid_case == "schema":
        request, _ = _write_request(
            tmp_path / "request-private",
            changes={"unsupported_field": "reject"},
        )
    elif invalid_case == "expiry":
        request, _ = _write_request(
            tmp_path / "request-private",
            changes={"expires_at": lambda value: value["issued_at"] - 1},
        )
    env = {
        "HOME": str(home),
        "COW_DATA_DIR": str(data_root),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
    }

    result = subprocess.run(
        [sys.executable, str(repo / "scripts/discovery_startup.py"), "--request", str(request)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode != 0
    assert result.stderr.strip() == "Authenticated startup observation rejected"
    assert not data_root.exists()
    assert not home.joinpath(".cow").exists()
    assert not list(tmp_path.rglob("run.log"))
    assert "Starting channels" not in result.stdout + result.stderr
