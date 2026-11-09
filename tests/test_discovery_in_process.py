"""Acceptance tests for trusted observations of an initialized native runtime.

These tests use a disposable, normally initialized AgentBridge and a real
AgentDelegateTool. The model and I/O are never executed. No test constructs an
initialization anchor or caller scope directly.
"""
import json
from types import SimpleNamespace
import uuid

import pytest

from agent.discovery import (
    ExistingRuntimeBinding,
    TaskRequirements,
    TrustedDiscoveryHost,
    task_spec_fingerprint,
)
from agent.external import contract
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.operator_control import OperatorControl
from agent.external.operator_review import build_enrollment_review, build_task_review
from agent.external.supervisor import ExternalSupervisor
from agent.protocol.agent import Agent
from agent.registry import AgentProfile, AgentRegistry
from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool
from agent.tools.current_time.current_time import TimeTool
from agent.tools.read.read import Read
from bridge.context import Context, ContextType
from common.runtime_identity import identity_scope


NOW = 100.0
OWNER_ID = "owner"
TARGET_ID = "testpilot"
SESSION_ID = "in-process-discovery-session"


def _task(**changes):
    value = dict(
        task_id=str(uuid.uuid4()),
        policy_id="safe-default",
        category="analysis",
        input_contract="fictional_records.v1",
        output_contract="analysis_report.v1",
        persistent_memory="prohibited",
        persistent_context="prohibited",
        required_tools=(),
        max_authority=("fs.read", "time", "analyze_records"),
        approval="prohibited",
        verification="none",
        recovery="frozen_authority",
        cancellation="cooperative",
        deadline=NOW + 120,
        timeout_seconds=20.0,
        concurrency=1,
        permitted_mechanisms=("native_isolated",),
        prohibited_mechanisms=(),
        task_spec_hash=contract.digest({"fixture": "no execution"}),
        requested_agent_id=TARGET_ID,
    )
    value.update(changes)
    return TaskRequirements(**value)


def _approved_external_binding(tmp_path, registry):
    """Build real disposable operator records; the host must not read its files."""
    runtime_id = "cowagent." + TARGET_ID
    supervisor_id = "fixture-supervisor"
    scope = {
        "supervisor_id": supervisor_id,
        "owner_id": OWNER_ID,
        "source_id": OWNER_ID,
        "conversation_id": SESSION_ID,
        "runtime_id": runtime_id,
    }
    probe_path = tmp_path / "probe.json"
    probe_bytes = b'{"status":"synthetic-pass"}'
    probe_path.write_bytes(probe_bytes)
    probe_path.chmod(0o600)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"model": "target-fixture-model"}))
    config_path.chmod(0o600)
    current = {
        "runtime_kind": "cowagent-registered/1",
        "agent_id": TARGET_ID,
        "model": "target-fixture-model",
        "provider": "openai",
        "config_sha256": contract.digest({"config": "fixture"}),
        "profile_sha256": contract.digest(registry.get(TARGET_ID).to_dict()),
        "source_sha256": contract.digest({"source": "fixture"}),
    }
    enrollment = dict(current, probe_sha256=__import__("hashlib").sha256(probe_bytes).hexdigest())
    enrollment_review = build_enrollment_review(
        enrollment, current=current, observed_probe_sha256=enrollment["probe_sha256"])
    control = OperatorControl(tmp_path / "operator", initialize=True)

    def command(action, payload, revision):
        return {
            "protocol": "cow.external.operator-command/1",
            "request_id": str(uuid.uuid4()),
            "action": action,
            "scope": dict(scope),
            "expected_revision": revision,
            "payload": payload,
        }

    control.apply(command("enroll", {"review": enrollment_review, "expires_at": NOW + 80}, 0), now=NOW)
    task_id = str(uuid.uuid4())
    spec = {
        "task_id": task_id,
        "idempotency_key": "discovery-in-process-fixture",
        "owner_id": OWNER_ID,
        "source_id": OWNER_ID,
        "conversation_id": SESSION_ID,
        "runtime_id": runtime_id,
        "task": {"operation": "analyze_records", "artifact": "report.json",
                 "content": json.dumps({"schema_version": 1, "currency": "USD",
                                         "records": [{"id": "fake-1", "amount_cents": 25,
                                                      "status": "paid"}]})},
        "authority": {"operations": ["analyze_records"], "resource": task_id,
                      "expires_at": NOW + 75},
        "verification": {"acceptance": [], "external_state": []},
    }
    journal = ApprovalJournal(control)
    journal.create(supervisor_id, spec)
    task_review = build_task_review(spec, enrollment_review, now=NOW)
    control.apply(command("approve_task", {
        "spec": spec,
        "enrollment_revision": 1,
        "task_review_id": task_review["review_id"],
        "reviewed_at": NOW,
        "expires_at": NOW + 70,
    }, 0), now=NOW)
    credential = contract.Credential(
        supervisor_id, runtime_id, "fixture-key", b"x" * 32, NOW + 80,
        ("analyze_records",),
    )
    transport = SimpleNamespace(credential=credential)
    supervisor = ExternalSupervisor(journal, transport, owner_id=OWNER_ID,
                                    source_id=OWNER_ID, conversation_id=SESSION_ID)
    data = {
        "protocol": contract.VERSION,
        "runtime_id": runtime_id,
        "name": "Synthetic named runtime",
        "model": current["model"],
        "native_capabilities": current,
        "operations": ["analyze_records"],
        "approval_operations": ["analyze_records"],
        "session_ownership": "runtime",
        "cancellation": "cooperative",
        "epoch": uuid.uuid4().hex,
    }
    envelope = contract.envelope(credential, "discover", {"ok": True, "data": data},
                                 kind="response", now=NOW)
    binding = ExistingRuntimeBinding(
        supervisor=supervisor,
        spec=spec,
        probe_receipt_path=probe_path,
        config_path=config_path,
    )
    return SimpleNamespace(binding=binding, spec=spec, credential=credential,
                           envelope=envelope, control=control, operator_path=control.path,
                           config_path=config_path, probe_path=probe_path)


@pytest.fixture
def initialized(tmp_path, monkeypatch):
    """Create the owner through the real Bridge -> AgentBridge constructor."""
    import config
    import agent.registry as registry_module
    import agent.routing as routing_module
    from bridge.agent_bridge import AgentBridge, AgentLLMModel
    from bridge.bridge import Bridge

    root = tmp_path.resolve()
    owner_workspace = root / "owner"
    target_workspace = root / TARGET_ID
    owner_workspace.mkdir()
    target_workspace.mkdir()
    settings = {
        "agent_workspace": str(root),
        "model": "global-fixture-model",
        "bot_type": "openai",
        "agent_permission_mode": "read-only",
        "chat_fallback": {"enabled": False},
        "agent_delegation": {
            "enabled": True,
            "allowed_targets": {OWNER_ID: [TARGET_ID]},
            "max_depth": 3,
            "timeout_seconds": 20.0,
        },
    }
    monkeypatch.setattr(config, "config", config.Config(settings))
    registry = AgentRegistry(
        [
            AgentProfile(OWNER_ID, "Owner", str(owner_workspace), bot_type="openai"),
            AgentProfile(TARGET_ID, "TestPilot", str(target_workspace),
                         bot_type="openai", model="target-fixture-model"),
        ],
        default_agent_id=OWNER_ID,
    )
    monkeypatch.setattr(registry_module, "get_agent_registry", lambda: registry)
    # Preserve the normal AgentRouter construction and its registry binding.

    monkeypatch.setattr("agent.recovery.service.start_recovery_service",
                        lambda owner: setattr(owner, "recovery_service", None))
    monkeypatch.setattr("agent.tools.scheduler.integration.init_scheduler",
                        lambda *args, **kwargs: False)
    monkeypatch.setattr("agent.evolution.trigger.start_evolution_trigger", lambda *args: None)

    outer = Bridge.__wrapped__()
    owner = outer.get_agent_bridge()
    assert type(owner) is AgentBridge
    assert owner.bridge is outer

    host = TrustedDiscoveryHost.from_initialized_runtime(
        owner, external_bindings_source=lambda: (), clock=lambda: NOW,
    )

    # Use real runtime model and tools, but no model call. The agent is placed
    # in the existing owner cache so reply-scoped discovery cannot initialize it.
    model = AgentLLMModel(outer)
    model.set_agent_default("openai", "owner-fixture-model")
    delegate = AgentDelegateTool({"enabled": True, "timeout_seconds": 20.0})
    agent = Agent(
        "fixture owner",
        model=model,
        tools=[Read({"cwd": str(owner_workspace)}), TimeTool(), delegate],
        workspace_dir=str(owner_workspace),
        enable_skills=False,
        memory_manager=None,
        skip_context_files=True,
    )
    agent.agent_id = OWNER_ID
    agent.agent_profile = registry.get(OWNER_ID)
    agent.project_dir = str(owner_workspace)
    agent.permission_mode = "read-only"
    owner._agent_instances[(OWNER_ID, SESSION_ID)] = agent
    owner.agents[SESSION_ID] = agent

    from agent.workspace import project_store, session_prefs
    monkeypatch.setattr(project_store, "get_project_dir_strict", lambda *args: None)
    prefs = {"members": [TARGET_ID], "permission": "read-only"}
    monkeypatch.setattr(session_prefs, "get_prefs_strict", lambda *args: dict(prefs))

    # Keep the actual reply lifecycle and active-scope hook. Stub only storage,
    # event-side effects, and hot reload; discovery still sees real cached state.
    run_id = uuid.uuid4().hex
    context = Context(ContextType.TEXT, "synthetic fixture", kwargs={
        "agent_id": OWNER_ID,
        "session_id": SESSION_ID,
        "channel_type": "test",
    })
    owner._apply_session_project = lambda *args: None

    def begin_run(*_args):
        from common.utils import set_agent_run_id
        return run_id, set_agent_run_id(run_id), None

    def end_run(_store, _run_id, token, *_args):
        from common.utils import clear_agent_run_id
        clear_agent_run_id(token)

    owner._begin_run = begin_run
    owner._end_run = end_run
    owner._pre_persist_user_message = lambda *args: True
    owner._persist_messages = lambda *args, **kwargs: True
    owner.remember_context_usage = lambda *args: None
    owner._schedule_mcp_hot_reload = lambda *args: None
    monkeypatch.setattr("agent.evolution.trigger.mark_run_active", lambda *args: None)

    class _Steer:
        def register(self, *_args):
            return object()

        def unregister(self, *_args):
            return None

    monkeypatch.setattr("bridge.agent_bridge.get_steer_registry", lambda: _Steer())

    return SimpleNamespace(
        root=root, settings=settings, registry=registry, outer=outer, owner=owner,
        host=host, agent=agent, model=model, delegate=delegate, context=context,
        run_id=run_id, prefs=prefs, Agent=Agent, AgentBridge=AgentBridge,
        AgentLLMModel=AgentLLMModel, routing_module=routing_module,
    )


def _run_with_observation(initialized, callback, *, context=None):
    f = initialized
    active_context = context or f.context
    f.agent.run_stream = lambda **_kwargs: callback(_select_in_run(f, _task()))
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        return f.owner.agent_reply("no model call", context=active_context)


def _candidate(result, target=TARGET_ID):
    return next(row for row in result["candidates"]
                if row["target_id"] == target and row["mechanism"] == "native_isolated")


def _select_in_run(f, task):
    # Use Agent's real non-dispatch tool lookup to bind the owner Agent.
    assert f.agent._find_tool("agent_delegate") is f.delegate
    return f.host.select(task)


def test_normal_owner_and_active_reply_are_observed_without_dispatch(initialized, monkeypatch):
    f = initialized
    from agent.memory.manager import MemoryManager
    calls = []
    original_select = f.host.select

    def observe(task):
        result = original_select(task)
        calls.append(result)
        return result

    def run_without_dispatch(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        observe(_task())
        return "fixture reply"

    f.agent.run_stream = run_without_dispatch

    # No construction or execution is allowed after the normal fixture exists.
    monkeypatch.setattr(
        f.Agent, "__init__", lambda *a, **kw: pytest.fail("Agent constructed during observation"))
    monkeypatch.setattr(
        f.AgentBridge, "__init__", lambda *a, **kw: pytest.fail("AgentBridge constructed during observation"))
    monkeypatch.setattr(
        f.AgentLLMModel, "__init__", lambda *a, **kw: pytest.fail("model constructed during observation"))
    monkeypatch.setattr(
        MemoryManager, "__init__", lambda *a, **kw: pytest.fail("memory constructed during observation"))
    monkeypatch.setattr(f.delegate, "execute", lambda *_a, **_kw: pytest.fail("delegate dispatched"))

    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        reply = f.owner.agent_reply("no model call", context=f.context)

    assert reply.content == "fixture reply"
    assert len(calls) == 1
    result = calls[0]
    assert result["status"] == "denied", result["reasons"]
    row = _candidate(result)
    policy = row["native_policy"]
    assert policy["runtime_source"] == "initialized_in_process"
    assert policy["context"] == "active"
    assert policy["caller_scope"] == "root"
    assert policy["source_agent_id"] == OWNER_ID
    assert policy["owner_agent_id"] == OWNER_ID
    assert policy["delegation_depth"] == 0
    assert policy["team"] == "applied_session_state"
    assert TARGET_ID in policy["team_members"]
    assert policy["receiver_allowed"] is True
    assert policy["team_allowed"] is True
    assert policy["receiver_authority"] == "unknown"
    assert policy["contract_proof"] == "unavailable"
    assert "native_capability_proof_unavailable" in row["reasons"]
    assert row["eligible_for_admission"] is False
    assert result["dispatch_permitted"] is False


def test_forged_or_unowned_bridge_cannot_create_host(initialized):
    from agent.discovery.runtime_readers import TrustedDiscoveryHost
    from agent.discovery.contracts import DiscoveryError

    with pytest.raises(DiscoveryError, match="initialized_runtime_unavailable"):
        TrustedDiscoveryHost.from_initialized_runtime(SimpleNamespace())

    # A separately initialized bridge is not owned by the attached server Bridge.
    unowned = initialized.AgentBridge(initialized.outer)
    with pytest.raises(DiscoveryError, match="initialized_runtime_unavailable"):
        TrustedDiscoveryHost.from_initialized_runtime(unowned)


def test_stale_process_binding_and_configuration_disable_fail_closed(initialized, monkeypatch):
    import agent.discovery.initialized_runtime as initialized_runtime

    pid = initialized_runtime.os.getpid()
    monkeypatch.setattr(initialized_runtime.os, "getpid", lambda: pid + 1)
    result = initialized.host.select(_task())
    assert result["status"] == "denied"
    assert result["reasons"] == ["authoritative_state_unavailable"]


def test_replaced_initialization_epoch_is_rejected(initialized):
    from dataclasses import replace

    f = initialized
    original = f.owner._discovery_runtime_anchor
    f.owner._discovery_runtime_anchor = replace(original, epoch=uuid.uuid4().hex)
    result = f.host.select(_task())
    assert result["status"] == "denied"
    assert result["reasons"] == ["authoritative_state_unavailable"]


def test_stale_pid_blocks_external_inspection_before_bindings_or_transport(initialized, monkeypatch):
    import agent.discovery.initialized_runtime as initialized_runtime

    f = initialized
    calls = []
    f.host.bindings_source = lambda: calls.append("bindings") or ()
    pid = initialized_runtime.os.getpid()
    monkeypatch.setattr(initialized_runtime.os, "getpid", lambda: pid + 1)
    with pytest.raises(ValueError, match="initialized_runtime_unavailable"):
        f.host.observe_external(["any-runtime"], contact_authorized=True)
    assert calls == []


def test_registry_replacement_invalidates_initialized_owner(initialized):
    f = initialized
    replacement = AgentRegistry(
        [AgentProfile(OWNER_ID, "Replacement", str(f.root / "owner")),
         AgentProfile(TARGET_ID, "TestPilot", str(f.root / TARGET_ID), model="target-fixture-model")],
        default_agent_id=OWNER_ID,
    )
    f.owner.agent_registry = replacement
    result = f.host.select(_task())
    assert result["status"] == "denied"
    assert result["reasons"] == ["authoritative_state_unavailable"]


def test_failed_session_preferences_clear_prior_receipt(initialized, monkeypatch):
    f = initialized
    from agent.workspace import session_prefs
    from bridge.agent_bridge import SessionAuthorityError
    f.owner.apply_session_prefs(f.agent, SESSION_ID, OWNER_ID)
    assert f.agent._discovery_applied_session is not None
    monkeypatch.setattr(session_prefs, "get_prefs_strict", lambda *_args: (_ for _ in ()).throw(
        OSError("fixture read failure")))
    with pytest.raises(SessionAuthorityError):
        f.owner.apply_session_prefs(f.agent, SESSION_ID, OWNER_ID)
    assert f.agent._discovery_applied_session is None


def test_current_config_disable_invalidates_revalidation(initialized):
    import config

    f = initialized
    observations = []

    def select_then_disable(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        task = _task()
        observations.append(f.host.select(task))
        config.conf()["agent_delegation"] = False
        observations.append(f.host.select(task))
        config.conf()["agent_delegation"] = f.settings["agent_delegation"]
        return "fixture reply"

    f.agent.run_stream = select_then_disable
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)

    assert observations[0]["dispatch_permitted"] is False
    before = _candidate(observations[0])["native_policy"]
    after = _candidate(observations[1])["native_policy"]
    assert before["enabled"] is True
    assert after["enabled"] is False
    assert (_candidate(observations[0])["configuration_fingerprint"]
            != _candidate(observations[1])["configuration_fingerprint"])
    assert "native_team_policy_or_cycle_denied" in _candidate(observations[1])["reasons"]


def test_cached_session_model_route_is_reported_separately(initialized):
    f = initialized
    f.prefs.update({"members": [], "permission": "read-only",
                    "provider": "openai", "model": "session-fixture-model"})
    captured = []
    f.agent.run_stream = lambda **_kwargs: captured.append(_select_in_run(f, _task())) or "fixture reply"
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)

    row = _candidate(captured[0])
    policy = row["native_policy"]
    assert policy["effective_route"] == "cached_session"
    assert policy["caller_model"] == "session-fixture-model"
    assert row["model"] == "target-fixture-model"
    assert policy["team"] == "applied_session_state"
    assert policy["team_allowed"] is False


def test_context_mutation_during_turn_invalidates_caller_binding(initialized):
    f = initialized
    captured = []

    def mutate_then_select(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        f.context.kwargs["speaker_agent_id"] = TARGET_ID
        captured.append(f.host.select(_task()))
        return "fixture reply"

    f.agent.run_stream = mutate_then_select
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)

    row = _candidate(captured[0])
    assert row["native_policy"]["context"] == "unavailable"
    assert "native_active_caller_unavailable" in row["reasons"]


def test_nested_context_does_not_claim_root_lineage(initialized):
    f = initialized
    nested = Context(ContextType.TEXT, "nested fixture", kwargs={
        "agent_id": OWNER_ID,
        "session_id": SESSION_ID,
        "delegation_trace": [OWNER_ID],
        "delegation_depth": 1,
        "parent_run_id": "parent-run",
    })
    captured = []
    f.agent.run_stream = lambda **_kwargs: captured.append(_select_in_run(f, _task())) or "fixture reply"
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=nested)

    row = _candidate(captured[0])
    policy = row["native_policy"]
    assert policy["context"] == "active"
    assert policy["caller_scope"] == "unknown"
    assert "native_delegation_lineage_unknown" in row["reasons"]
    assert "delegation_depth" not in policy


def test_inherited_ambient_parent_without_delegation_fields_is_not_root(initialized):
    f = initialized
    captured = []
    f.agent.run_stream = lambda **_kwargs: captured.append(_select_in_run(f, _task())) or "fixture reply"
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID, run_id="ambient-parent-run"):
        f.owner.agent_reply("no model call", context=f.context)

    row = _candidate(captured[0])
    policy = row["native_policy"]
    assert policy["context"] == "active"
    assert policy["caller_scope"] == "unknown"
    assert "native_delegation_lineage_unknown" in row["reasons"]
    assert "delegation_trace" not in policy


def test_task_json_cannot_supply_runtime_or_proof_fields():
    value = _task().to_dict()
    value["runtime_source"] = "initialized_in_process"
    from agent.discovery import DiscoveryService
    selection = DiscoveryService(
        registry_source=lambda: AgentRegistry([AgentProfile(OWNER_ID, "Owner", "/tmp/owner")], OWNER_ID),
        clock=lambda: NOW,
    ).select(value)
    assert selection["status"] == "invalid_request"
    assert selection["reasons"] == ["invalid_requirements"]


def test_active_observation_never_reads_private_agent_state(initialized):
    f = initialized

    class PrivateState:
        def __getattribute__(self, _name):
            pytest.fail("discovery accessed private Agent state")

    f.agent.memory_manager = PrivateState()
    f.agent.messages = PrivateState()
    captured = []
    f.agent.run_stream = lambda **_kwargs: captured.append(_select_in_run(f, _task())) or "fixture reply"
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)
    assert _candidate(captured[0])["native_policy"]["contract_proof"] == "unavailable"


def test_wrong_ambient_run_identity_does_not_create_caller_scope(initialized):
    f = initialized
    captured = []
    f.agent.run_stream = lambda **_kwargs: captured.append(_select_in_run(f, _task())) or "fixture reply"
    def wrong_run(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        with identity_scope(run_id="different-run"):
            captured.append(f.host.select(_task()))
        return "fixture reply"

    f.agent.run_stream = wrong_run
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)

    row = _candidate(captured[0])
    assert row["native_policy"]["context"] == "unavailable"
    assert "native_active_caller_unavailable" in row["reasons"]


def test_copied_context_cannot_reuse_finished_caller_scope(initialized):
    import contextvars

    f = initialized
    copied = []

    def capture_scope(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        copied.append(contextvars.copy_context())
        return "fixture reply"

    f.agent.run_stream = capture_scope
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)

    result = copied[0].run(f.host.select, _task())
    assert result["status"] == "denied"
    assert result["reasons"] == ["no_eligible_candidate"]
    row = _candidate(result)
    assert row["native_policy"]["context"] == "unavailable"
    assert "native_active_caller_unavailable" in row["reasons"]


def test_scope_closes_when_run_stream_raises(initialized):
    f = initialized

    def fail(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        raise RuntimeError("fixture failure")

    f.agent.run_stream = fail
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        reply = f.owner.agent_reply("no model call", context=f.context)
    assert reply.type.name == "ERROR"

    result = f.host.select(_task())
    row = _candidate(result)
    assert row["native_policy"]["context"] == "unavailable"
    assert "native_active_caller_unavailable" in row["reasons"]


def test_cached_route_change_during_enumeration_rejects_mixed_observation(initialized, monkeypatch):
    f = initialized
    from agent.discovery.sources import NativeSource
    original = NativeSource._route
    count = [0]

    def change_route(profile, registry, settings):
        route = original(profile, registry, settings)
        count[0] += 1
        if count[0] == 2:
            f.model._fallback_provider = "openai"
            f.model._fallback_model = "mid-observation-fallback"
        return route

    monkeypatch.setattr(NativeSource, "_route", staticmethod(change_route))
    captured = []
    f.agent.run_stream = lambda **_kwargs: captured.append(_select_in_run(f, _task())) or "fixture reply"
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)

    assert captured[0]["status"] == "denied"
    assert captured[0]["reasons"] == ["authoritative_state_unavailable"]


def test_observation_does_not_create_data_root(initialized, monkeypatch):
    import os

    f = initialized
    data_root = f.root / "missing-cow-data"
    monkeypatch.setenv("COW_DATA_DIR", str(data_root))
    assert not data_root.exists()

    def observe(**_kwargs):
        assert f.agent._find_tool("agent_delegate") is f.delegate
        original = os.makedirs

        def deny_mkdir(*args, **kwargs):
            pytest.fail("discovery attempted to create a data root")

        os.makedirs = deny_mkdir
        try:
            return f.host.select(_task())
        finally:
            os.makedirs = original

    f.agent.run_stream = observe
    with identity_scope(agent_id=OWNER_ID, session_id=SESSION_ID):
        f.owner.agent_reply("no model call", context=f.context)
    assert not data_root.exists()


def test_initialized_observation_does_not_read_private_native_snapshot(initialized, monkeypatch):
    import agent.discovery.runtime_readers as readers

    f = initialized
    setup = _approved_external_binding(f.root, f.registry)
    reads = []
    monkeypatch.setattr(readers, "native_snapshot", lambda *a, **kw: reads.append("native_snapshot"))
    monkeypatch.setattr(readers, "_owned_bytes", lambda *a, **kw: reads.append("private_file"))
    f.host.bindings_source = lambda: (setup.binding,)
    task = TaskRequirements(
        task_id=setup.spec["task_id"], policy_id="safe-default",
        category="analyze_records", input_contract="fictional_records.v1",
        output_contract="analysis_report.v1", persistent_memory="required",
        persistent_context="required", required_tools=(), max_authority=("analyze_records",),
        approval="required", verification="independent_analysis", recovery="intent_fenced",
        cancellation="cooperative", deadline=NOW + 100, timeout_seconds=100.0,
        concurrency=1, permitted_mechanisms=("persistent_named",), prohibited_mechanisms=(),
        task_spec_hash=task_spec_fingerprint(setup.spec), requested_agent_id=TARGET_ID,
    )
    result = f.host.select(task)
    row = next(row for row in result["candidates"]
               if row["target_id"] == TARGET_ID and row["mechanism"] == "persistent_named")
    assert row["runtime_state"]["exact_task_approval"] == "approved"
    assert row["proof_status"] != "verified"
    assert row["runtime_state"]["operator_provenance"] == "private_operator_account"
    assert row["runtime_state"]["enrolled"] == "approved"
    assert row["runtime_state"]["authorized"] is True
    assert row["eligible_for_admission"] is False
    assert reads == []
    public = json.dumps(result, sort_keys=True)
    assert str(setup.operator_path) not in public
    assert str(setup.config_path) not in public
    assert str(setup.probe_path) not in public
    assert setup.credential.secret.hex() not in public

