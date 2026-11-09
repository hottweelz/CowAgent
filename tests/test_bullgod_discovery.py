"""Acceptance tests for read-only BullGod capability discovery and selection."""
from dataclasses import replace
import json
from types import SimpleNamespace
import uuid

import pytest

from agent.external import contract as external_contract
from agent.external import operator_control as operator_control_module
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.operator_control import OperatorControl
from agent.external.operator_review import build_enrollment_review, build_task_review
from agent.external.supervisor import ExternalSupervisor
from agent.discovery import (
    AdmissionObservation,
    CapabilityContract,
    CapabilityProof,
    DiscoveryService,
    ExternalBinding,
    ExternalSource,
    NativeSource,
    SelectionPolicy,
    task_spec_fingerprint,
)
from agent.registry import AgentProfile, AgentRegistry
from agent.protocol.agent import Agent
from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool
from agent.tools.read.read import Read
from agent.tools.current_time.current_time import TimeTool


NOW = 110.0
PROBE_TIME = 100.0
TASK_ID = "cb4a1ff8-6401-4ce7-8f81-c1fcbd4cf9c6"
OWNER = "owner-1"
SOURCE = "owner-1"
CONVERSATION = "session-cow-discovery"


def _hash(label):
    return external_contract.digest({"fixture": label})


def _profiles(tmp_path, *, second_model="model-b", first_model="model-a"):
    for name in ("owner", "testpilot", "testpilot2"):
        (tmp_path / name).mkdir(exist_ok=True)
    return AgentRegistry([
        AgentProfile("owner-1", "Owner", str(tmp_path / "owner")),
        AgentProfile("testpilot", "TestPilot", str(tmp_path / "testpilot"),
                     description="Registered analysis agent", bot_type="openai", model=first_model),
        AgentProfile("testpilot2", "TestPilot2", str(tmp_path / "testpilot2"),
                     description="Registered analysis agent", bot_type="openai", model=second_model),
    ], "owner-1")


def _spec(runtime_id, *, task_id=TASK_ID, content=None, operation="analyze_records"):
    records = {"schema_version": 1, "currency": "USD",
               "records": [{"id": "fictional-1", "amount_cents": 125, "status": "paid"}]}
    return {
        "task_id": task_id,
        "idempotency_key": "idem-analysis-1",
        "owner_id": OWNER,
        "source_id": SOURCE,
        "conversation_id": CONVERSATION,
        "runtime_id": runtime_id,
        "task": {"operation": operation, "artifact": "report.json",
                 "content": content if content is not None else json.dumps(records)},
        "authority": {"operations": [operation], "resource": task_id, "expires_at": 300.0},
        "verification": {"acceptance": [], "external_state": []},
    }


def _task(spec, **changes):
    value = {
        "task_id": spec["task_id"],
        "policy_id": "safe-default",
        "category": "analyze_records",
        "input_contract": "fictional_records.v1",
        "output_contract": "analysis_report.v1",
        "persistent_memory": "required",
        "persistent_context": "required",
        "required_tools": (),
        "max_authority": ("analyze_records",),
        "approval": "required",
        "verification": "independent_analysis",
        "recovery": "intent_fenced",
        "cancellation": "cooperative",
        "deadline": 400.0,
        "timeout_seconds": 200.0,
        "concurrency": 1,
        "permitted_mechanisms": ("persistent_named", "external_runtime"),
        "prohibited_mechanisms": (),
        "task_spec_hash": task_spec_fingerprint(spec),
    }
    value.update(changes)
    return value


def _scope(runtime_id):
    return {
        "supervisor_id": "supervisor-" + runtime_id.replace(".", "-"),
        "owner_id": OWNER,
        "source_id": SOURCE,
        "conversation_id": CONVERSATION,
        "runtime_id": runtime_id,
    }


def _command(action, scope, payload, expected_revision):
    return {"protocol": operator_control_module.VERSION,
            "request_id": str(uuid.uuid4()), "action": action,
            "scope": dict(scope), "expected_revision": expected_revision,
            "payload": payload}


def _enrollment(runtime_id, profile=None, *, model=None, provider="openai"):
    model = model or (profile.model if profile else "fixture-model")
    if runtime_id.startswith("cowagent."):
        target_id = runtime_id.removeprefix("cowagent.")
        return {
            "runtime_kind": "cowagent-registered/1",
            "agent_id": target_id,
            "model": model,
            "provider": provider,
            "config_sha256": _hash(runtime_id + "-config"),
            "profile_sha256": external_contract.digest(profile.to_dict()) if profile else _hash(target_id + "-profile"),
            "source_sha256": _hash(runtime_id + "-source"),
        }
    from agent.external.codex_policy import ANALYSIS_POLICY_REVISION, VERSION as CODEX_VERSION
    return {
        "cli_version": CODEX_VERSION,
        "model": model,
        "modelProvider": provider,
        "policy_revision": ANALYSIS_POLICY_REVISION,
        "provider_config_sha256": _hash(runtime_id + "-provider"),
        "config_sha256": _hash(runtime_id + "-config"),
    }


def _setup_external(tmp_path, runtime_id, registry, *, approve_task=True,
                    model=None, provider="openai", task_id=TASK_ID,
                    operation="analyze_records", admission_health="healthy",
                    available_slots=1, active_load=0):
    """Build a real temporary operator journal, approval journal and signed probe."""
    profile = registry.get(runtime_id.removeprefix("cowagent.")) if runtime_id.startswith("cowagent.") else None
    model = model or (profile.model if profile else "fixture-model")
    current = _enrollment(runtime_id, profile, model=model, provider=provider)
    enrollment = dict(current, probe_sha256=_hash(runtime_id + "-probe"))
    review = build_enrollment_review(enrollment, current=current,
                                     observed_probe_sha256=enrollment["probe_sha256"])
    scope = _scope(runtime_id)
    control = OperatorControl((tmp_path / ("operator-" + runtime_id.replace(".", "-"))).resolve(), initialize=True)
    control.apply(_command("enroll", scope, {"review": review, "expires_at": 500.0}, 0), now=NOW)
    spec = _spec(runtime_id, task_id=task_id, operation=operation)
    journal = ApprovalJournal(control)
    journal.create(scope["supervisor_id"], spec)
    if approve_task:
        task_review = build_task_review(spec, review, now=105.0)
        control.apply(_command("approve_task", scope, {
            "spec": spec,
            "enrollment_revision": 1,
            "task_review_id": task_review["review_id"],
            "reviewed_at": 105.0,
            "expires_at": 250.0,
        }, 0), now=NOW)

    credential = external_contract.Credential(
        scope["supervisor_id"], runtime_id, "key-" + runtime_id.replace(".", "-"),
        b"x" * 32, expires_at=500.0, operations=("analyze_records",),
    )
    # No method on this transport is called by discovery. The real envelope below
    # authenticates the retained synthetic response with this credential.
    transport = SimpleNamespace(credential=credential)
    supervisor = ExternalSupervisor(journal, transport, owner_id=OWNER, source_id=SOURCE,
                                    conversation_id=CONVERSATION)
    data = {
        "protocol": external_contract.VERSION,
        "runtime_id": runtime_id,
        "name": "Codex fixture" if profile is None else "CowAgent registered agent",
        "model": model,
        "native_capabilities": current,
        "operations": ["analyze_records"],
        "approval_operations": ["analyze_records"],
        "session_ownership": "runtime",
        "cancellation": "cooperative",
        "epoch": str(uuid.uuid4()),
    }
    probe_time = [PROBE_TIME]
    admission_time = [None]
    load_value = [active_load]
    tamper_envelope = [False]

    def envelope_source():
        value = external_contract.envelope(
            credential, "discover", {"ok": True, "data": data},
            kind="response", now=probe_time[0],
        )
        if tamper_envelope[0]:
            value["mac"] = "0" * 64
        return value

    def admission_source(requested_runtime, boundary, now):
        assert requested_runtime == runtime_id
        issued_at = now if admission_time[0] is None else admission_time[0]
        return AdmissionObservation(boundary, _hash(runtime_id + "-admission"),
                                    issued_at, issued_at + 20.0, admission_health,
                                    available_slots, load_value[0])

    binding = ExternalBinding(
        supervisor=supervisor,
        discovery_envelope_source=envelope_source,
        admission_source=admission_source,
        spec_source=lambda requested_task_id: spec if requested_task_id == task_id else None,
    )
    return {"binding": binding, "control": control, "journal": journal,
            "credential": credential, "scope": scope, "spec": spec,
            "enrollment": enrollment, "review": review, "current": current,
            "discovery_data": data,
            "tamper_envelope": tamper_envelope,
            "probe_time": probe_time, "admission_time": admission_time,
            "load_value": load_value,
            "envelope_source": envelope_source, "admission_source": admission_source}


def _external_service(registry, setups, *, policy=None, now=NOW):
    return DiscoveryService(
        registry_source=lambda: registry,
        external_source=ExternalSource(lambda: tuple(item["binding"] for item in setups)),
        policy=policy,
        clock=lambda: now,
    )


def _candidate(result, target_id, mechanism):
    return next(row for row in result["candidates"]
                if row["target_id"] == target_id and row["mechanism"] == mechanism)


def _outcome(value):
    return json.dumps(value, sort_keys=True)


def _native_source(tmp_path, registry, monkeypatch):
    """Use the real native source/authority resolver with trusted fixture proofs."""
    from agent.permission import authority as authority_module
    from agent.workspace import project_store, session_prefs
    import config

    project = tmp_path / "shared-project"
    project.mkdir(exist_ok=True)
    monkeypatch.setattr(config, "conf", lambda: {
        "agent_workspace": str(tmp_path), "model": "gpt-fixture", "bot_type": "openai",
        "agent_permission_mode": "read-only", "chat_fallback": {"enabled": False},
    })
    monkeypatch.setattr(authority_module, "_registry_profiles",
                        lambda: registry.list(include_disabled=True))
    monkeypatch.setattr(project_store, "get_project_dir_strict", lambda *args: str(project))

    def prefs(session_id, agent_id=None):
        if agent_id == "owner-1":
            return {"members": ["testpilot", "testpilot2"], "permission": "read-only"}
        return {"permission": "read-only"}

    monkeypatch.setattr(session_prefs, "get_prefs_strict", prefs)
    source_agent = Agent("fixture source", workspace_dir=str(tmp_path / "owner"),
                         tools=[Read({"cwd": str(project)}), TimeTool()], enable_skills=False,
                         skip_context_files=True)
    source_agent._current_agent_id = "owner-1"
    source_agent.project_dir = str(project)
    source_agent.permission_mode = "read-only"
    tool = AgentDelegateTool(config={"enabled": True,
                                     "allowed_targets": {"owner-1": ["testpilot", "testpilot2"]},
                                     "max_depth": 3, "timeout_seconds": 30.0})
    tool.current_context = SimpleNamespace(kwargs={
        "agent_id": "owner-1", "session_id": CONVERSATION,
        "delegation_host_id": "owner-1", "delegation_root_session": CONVERSATION,
    })
    tool.context = source_agent

    contract = CapabilityContract(
        ("analyze_records",), ("fictional_records.v1",), ("analysis_report.v1",),
        tools=("fs.read", "time"), verification="native_checks",
        recovery="frozen_authority", cancellation="cooperative", timeout_ceiling=600.0,
    )

    def proof_source(_target_id, configuration_fingerprint, now):
        return CapabilityProof(configuration_fingerprint, contract, _hash("native-proof"),
                               now - 1.0, now + 60.0, "trusted_test")

    def admission_source(_target_id, boundary_fingerprint, now):
        return AdmissionObservation(boundary_fingerprint, _hash("native-admission"),
                                    now, now + 20.0, "healthy", 1, 0)

    return NativeSource(tool, proof_source=proof_source, admission_source=admission_source,
                        source_fingerprint_source=lambda: _hash("native-source"))


def test_scenario_a_requires_persistent_context_and_never_dispatches(tmp_path, monkeypatch):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry)
    native = _native_source(tmp_path, registry, monkeypatch)
    monkeypatch.setattr(Agent, "__init__", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("discovery must not construct an Agent")))
    service = DiscoveryService(registry_source=lambda: registry, native_source=native,
                              external_source=ExternalSource(lambda: (setup["binding"],)),
                              clock=lambda: NOW)
    before = setup["control"].status(setup["scope"], task_id=TASK_ID, now=NOW)

    result = service.select(_task(
        setup["spec"], approval="optional", verification="none", recovery="none",
        max_authority=("fs.read", "time", "analyze_records"),
        permitted_mechanisms=("persistent_named", "native_isolated"),
    ))

    assert result["status"] == "selected", _outcome(result)
    assert result["selected"]["mechanism"] == "persistent_named"
    assert result["selected"]["persistent_context"] is True
    assert result["selected"]["persistent_memory"] is True
    assert result["selected"]["prior_manual_transcript_restored"] is False
    assert result["dispatch_permitted"] is False
    assert result["selected"]["dispatch_permitted"] is False
    assert result["execution_revalidation_required"] is True
    assert "persistent_context_required" in _candidate(
        result, "testpilot", "native_isolated")["reasons"]
    assert _candidate(result, "testpilot", "native_isolated")["reasons"] == [
        "persistent_context_required"]
    assert setup["control"].status(setup["scope"], task_id=TASK_ID, now=NOW) == before
    with setup["control"]._connect() as db:
        count = db.execute(
            "SELECT count(*) FROM external_events "
            "WHERE kind IN ('submit_intent','native_intent','publication_intent')"
        ).fetchone()[0]
        assert count == 0


def test_scenario_b_prohibits_persistent_context_and_memory_conflicts_are_invalid(tmp_path, monkeypatch):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry)
    native = _native_source(tmp_path, registry, monkeypatch)
    task = _task(setup["spec"], persistent_memory="prohibited",
                 persistent_context="prohibited", required_tools=("fs.read",),
                 max_authority=("fs.read", "time", "analyze_records"),
                 verification="native_checks", recovery="frozen_authority",
                 approval="optional",
                 deadline=400.0, timeout_seconds=200.0,
                 permitted_mechanisms=("persistent_named", "native_isolated"))

    service = DiscoveryService(registry_source=lambda: registry, native_source=native,
                               external_source=ExternalSource(lambda: (setup["binding"],)),
                               clock=lambda: NOW)
    result = service.select(task)

    assert result["status"] == "selected", _outcome(result)
    assert result["selected"]["mechanism"] == "native_isolated"
    assert "persistent_context_prohibited" in _candidate(result, "testpilot", "persistent_named")["reasons"]
    conflict = _task(setup["spec"], persistent_memory="required",
                     persistent_context="prohibited")
    assert _external_service(registry, [setup]).select(conflict)["status"] == "invalid_request"


def test_scenario_c_codex_name_does_not_grant_coding_capability(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task = _task(setup["spec"], category="software_development",
                 input_contract="repository_patch.v1", output_contract="git_diff.v1",
                 persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "denied"
    candidate = _candidate(result, "codex", "external_runtime")
    assert candidate["verified_capabilities"]["categories"] == ("analyze_records",)
    assert "capability_contract_mismatch" in candidate["reasons"]
    assert candidate["supported_tools"] == []


def test_scenario_d_revocation_and_reenrollment_invalidate_retained_selection(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry)
    service = _external_service(registry, [setup])
    original_task = _task(setup["spec"])
    selected = service.select(original_task)
    assert selected["status"] == "selected"

    setup["control"].apply(_command("revoke_task", setup["scope"], {"task_id": TASK_ID}, 1), now=110.0)
    revoked = service.revalidate(selected, original_task)
    assert revoked["valid"] is False
    assert revoked["current"]["dispatch_permitted"] is False


def test_scenario_d_reenrollment_fences_current_task_approval(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry)
    service = _external_service(registry, [setup])
    task = _task(setup["spec"])
    selected = service.select(task)
    setup["control"].apply(_command("revoke_enrollment", setup["scope"], {}, 1), now=110.0)
    review = build_enrollment_review(
        setup["enrollment"], current=setup["current"],
        observed_probe_sha256=setup["enrollment"]["probe_sha256"],
    )
    setup["control"].apply(_command("enroll", setup["scope"],
                                     {"review": review, "expires_at": 500.0}, 2), now=120.0)
    current = service.revalidate(selected, task)
    assert current["valid"] is False
    assert current["current"]["status"] in ("denied", "approval_required")


def test_missing_task_approval_is_approval_required_and_never_executes(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry, approve_task=False)

    result = _external_service(registry, [setup]).select(_task(setup["spec"]))

    assert result["status"] == "approval_required"
    assert result["dispatch_permitted"] is False
    assert result["approvals_required"] == [
        {"target_id": "testpilot", "mechanism": "persistent_named", "approval": "task"}
    ]


def test_persistent_approval_required_does_not_fall_back_to_same_target_native(tmp_path, monkeypatch):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry, approve_task=False)
    native = _native_source(tmp_path, registry, monkeypatch)
    task = _task(setup["spec"], requested_agent_id="testpilot",
                 persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 max_authority=("fs.read", "time", "analyze_records"),
                 permitted_mechanisms=("persistent_named", "native_isolated"))
    service = DiscoveryService(registry_source=lambda: registry, native_source=native,
                               external_source=ExternalSource(lambda: (setup["binding"],)),
                               clock=lambda: NOW)

    result = service.select(task)

    assert result["status"] in ("approval_required", "denied")
    assert result["selected"] is None
    assert result["dispatch_permitted"] is False
    native_candidate = _candidate(result, "testpilot", "native_isolated")
    assert "persistent_denial_no_fallback" in native_candidate["reasons"]


def test_tampered_signed_discovery_envelope_fails_closed(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    setup["tamper_envelope"][0] = True
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "denied"
    assert result["selected"] is None
    candidate = _candidate(result, "codex", "external_runtime")
    assert "external_binding_or_observation_unavailable" in candidate["reasons"]
    assert candidate["verification_status"] == "unverified"


def test_model_profile_and_configuration_drift_invalidates_selection(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry, model="model-a")
    service = _external_service(registry, [setup])
    task = _task(setup["spec"])
    selected = service.select(task)
    assert selected["selected"]["model"] == "model-a"
    assert registry.get("testpilot").model == "model-a"

    # The retained signed snapshot no longer matches the live enrolled profile
    # after the registry's profile model changes.
    registry.upsert(replace(registry.get("testpilot"), model="model-changed"))
    current = service.revalidate(selected, task)
    assert current["valid"] is False
    assert current["current"]["dispatch_permitted"] is False


def test_natural_language_claim_does_not_create_verified_capability(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task = _task(setup["spec"], category="cybersecurity_audit",
                 input_contract="repo_tree.v1", output_contract="security_report.v1",
                 persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "denied"
    candidate = _candidate(result, "codex", "external_runtime")
    assert candidate["verification_status"] == "verified"
    assert "cybersecurity_audit" not in candidate["verified_capabilities"]["categories"]
    assert "capability_contract_mismatch" in candidate["reasons"]


def test_profile_description_claim_is_not_a_verified_capability(tmp_path, monkeypatch):
    registry = _profiles(tmp_path)
    registry.upsert(replace(registry.get("testpilot"),
                            description="Expert cybersecurity auditor and incident responder"))
    native = _native_source(tmp_path, registry, monkeypatch)
    spec = _spec("native-test")
    task = _task(spec, category="cybersecurity_audit", input_contract="repo_tree.v1",
                 output_contract="security_report.v1", persistent_memory="prohibited",
                 persistent_context="prohibited", approval="optional", verification="none",
                 recovery="none", max_authority=("fs.read", "time"),
                 permitted_mechanisms=("native_isolated",))

    result = DiscoveryService(registry_source=lambda: registry, native_source=native,
                              clock=lambda: NOW).select(task)

    assert result["status"] == "denied"
    candidate = _candidate(result, "testpilot", "native_isolated")
    assert "cybersecurity_audit" not in candidate["declared_capabilities"]["categories"]
    assert "cybersecurity_audit" not in candidate["verified_capabilities"]["categories"]
    assert "capability_contract_mismatch" in candidate["reasons"]


def test_two_persistent_runtime_boundaries_and_provider_parallelism_unknown(tmp_path):
    registry = _profiles(tmp_path, first_model="shared-model", second_model="shared-model")
    first = _setup_external(tmp_path, "cowagent.testpilot", registry, model="shared-model")
    second = _setup_external(tmp_path, "cowagent.testpilot2", registry, model="shared-model")
    task = _task(first["spec"], concurrency=1)

    result = _external_service(registry, [second, first]).select(task)

    assert result["status"] == "selected"
    candidates = result["ranked_candidates"]
    assert {item["target_id"] for item in candidates} == {"testpilot", "testpilot2"}
    assert all(item["concurrency"]["max_concurrent"] == 1 for item in candidates)
    assert all(item["concurrency"]["provider_parallelism"] == "unknown" for item in candidates)
    assert candidates[0]["target_id"] == "testpilot"  # deterministic tie break
    assert candidates[0]["concurrency"]["boundary_fingerprint"] != candidates[1]["concurrency"]["boundary_fingerprint"]


def test_no_candidate_and_requested_identity_substitution_are_structured_denials(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry)
    task = _task(setup["spec"], requested_agent_id="testpilot2")

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "denied"
    assert result["selected"] is None
    assert result["reasons"] == ["no_eligible_candidate"]
    assert "requested_identity_mismatch" in _candidate(result, "testpilot", "persistent_named")["reasons"]
    assert result["dispatch_permitted"] is False


def test_runtime_health_and_admission_evidence_expiry_fail_closed(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "cowagent.testpilot", registry,
                            admission_health="healthy", available_slots=1)
    clock = [NOW]
    service = DiscoveryService(
        registry_source=lambda: registry,
        external_source=ExternalSource(lambda: (setup["binding"],)),
        clock=lambda: clock[0],
    )
    task = _task(setup["spec"])
    assert service.select(task)["status"] == "selected"

    # Keep the retained signed probe fresh while the admission observation ages
    # out. The observation stays bound to the existing runtime boundary.
    setup["probe_time"][0] = 120.0
    setup["admission_time"][0] = NOW
    clock[0] = NOW + 21.0
    expired = service.select(task)
    assert expired["status"] == "denied"
    assert "admission_evidence_stale" in _candidate(expired, "testpilot", "persistent_named")["reasons"]


def test_task_spec_and_enrollment_drift_are_not_trusted_from_requirements(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    service = _external_service(registry, [setup])
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    selected = service.select(task)
    assert selected["status"] == "selected"

    changed = dict(task, task_spec_hash=_hash("other-task"))
    drifted = service.select(changed)
    assert drifted["status"] == "denied"
    assert "external_binding_or_observation_unavailable" in _candidate(
        drifted, "codex", "external_runtime")["reasons"]
    assert service.revalidate(selected, changed)["valid"] is False


def test_exact_task_approval_does_not_cover_changed_spec_content(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    setup["spec"]["task"]["content"] = json.dumps({
        "schema_version": 1, "currency": "USD",
        "records": [{"id": "fictional-1", "amount_cents": 999999, "status": "paid"}],
    })
    changed = dict(task, task_spec_hash=task_spec_fingerprint(setup["spec"]))

    result = _external_service(registry, [setup]).select(changed)

    assert result["status"] == "denied"
    candidate = _candidate(result, "codex", "external_runtime")
    assert "task_binding_mismatch" in candidate["reasons"]
    assert result["dispatch_permitted"] is False


def test_task_caller_scope_substitution_cannot_reuse_registered_enrollment(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task_spec = dict(setup["spec"], owner_id="other-owner")
    task = _task(task_spec, persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    setup["spec"]["owner_id"] = "other-owner"

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "denied"
    candidate = _candidate(result, "codex", "external_runtime")
    assert "external_binding_or_observation_unavailable" in candidate["reasons"]
    assert result["dispatch_permitted"] is False


def test_candidate_order_and_selection_are_permutation_invariant(tmp_path):
    registry = _profiles(tmp_path)
    first = _setup_external(tmp_path, "cowagent.testpilot", registry, model="same-model")
    second = _setup_external(tmp_path, "cowagent.testpilot2", registry, model="same-model")
    task = _task(first["spec"])

    forward = _external_service(registry, [first, second]).select(task)
    reverse = _external_service(registry, [second, first]).select(task)

    assert forward["status"] == reverse["status"] == "selected"
    assert forward["selected"]["target_id"] == reverse["selected"]["target_id"] == "testpilot"
    assert _outcome(forward["ranked_candidates"]) == _outcome(reverse["ranked_candidates"])
    assert _outcome(forward["candidates"]) == _outcome(reverse["candidates"])


def test_target_model_preferences_and_known_load_precede_unknown(tmp_path):
    registry = _profiles(tmp_path)
    first = _setup_external(tmp_path, "cowagent.testpilot", registry,
                            model="model-a", active_load=None)
    second = _setup_external(tmp_path, "cowagent.testpilot2", registry,
                             model="model-b", active_load=5)
    task = _task(first["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("persistent_named",))
    bindings = [first, second]

    # A preferred model on an unknown-load target does not beat a measured load.
    load_policy = SelectionPolicy(preferred_models=("model-a",))
    load_result = _external_service(registry, bindings, policy=load_policy).select(task)
    assert load_result["selected"]["target_id"] == "testpilot2"
    assert _candidate(load_result, "testpilot", "persistent_named")["active_load"] is None

    # An explicit target preference is the first ranking key.
    target_policy = SelectionPolicy(preferred_targets=("testpilot",))
    target_result = _external_service(registry, bindings, policy=target_policy).select(task)
    assert target_result["selected"]["target_id"] == "testpilot"

    # When load is equally known, the configured model preference breaks the tie.
    first["load_value"][0] = 5
    model_policy = SelectionPolicy(preferred_models=("model-b",))
    model_result = _external_service(registry, bindings, policy=model_policy).select(task)
    assert model_result["selected"]["target_id"] == "testpilot2"


def test_selection_response_is_sanitized_and_task_cannot_supply_host_evidence(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    hostile = dict(task, capability_proof={"verified": True, "secret": "credential-marker"},
                   agent_prompt="private-instructions-marker", workspace="/private/raw-path-marker")
    result = _external_service(registry, [setup]).select(hostile)

    assert result["status"] == "invalid_request"
    serialized = _outcome(result)
    assert "credential-marker" not in serialized
    assert "private-instructions-marker" not in serialized
    assert "/private/raw-path-marker" not in serialized


def test_selection_does_not_call_transport_or_create_new_intents(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    calls = []
    setup["binding"].supervisor.transport.submit = lambda *args: calls.append("submit")
    setup["binding"].supervisor.transport.discover = lambda *args: calls.append("discover")
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "selected"
    assert calls == []
    with setup["control"]._connect() as db:
        count = db.execute(
            "SELECT count(*) FROM external_events "
            "WHERE kind IN ('submit_intent','native_intent','publication_intent')"
        ).fetchone()[0]
        assert count == 0


def test_policy_fingerprint_change_invalidates_retained_selection(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    first_policy = SelectionPolicy(policy_id="safe-default", revision=1)
    service = _external_service(registry, [setup], policy=first_policy)
    selected = service.select(task)
    other = DiscoveryService(registry_source=lambda: registry,
                             external_source=ExternalSource(lambda: (setup["binding"],)),
                             policy=SelectionPolicy(policy_id="safe-default", revision=2),
                             clock=lambda: NOW)

    assert other.revalidate(selected, task)["valid"] is False


def test_config_fingerprint_drift_invalidates_enrolled_capability(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    clock = [NOW]
    service = DiscoveryService(registry_source=lambda: registry,
                               external_source=ExternalSource(lambda: (setup["binding"],)),
                               clock=lambda: clock[0])
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    selected = service.select(task)
    assert selected["status"] == "selected"

    setup["discovery_data"]["native_capabilities"]["config_sha256"] = _hash("new-config")
    setup["probe_time"][0] = 120.0
    clock[0] = 120.0
    current = service.revalidate(selected, task)

    assert current["valid"] is False
    assert current["current"]["status"] == "denied"
    assert "capability_configuration_mismatch" in _candidate(
        current["current"], "codex", "external_runtime")["reasons"]


def test_revalidation_rejects_task_and_evidence_expiry(tmp_path):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry)
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))
    clock = [NOW]
    service = DiscoveryService(registry_source=lambda: registry,
                               external_source=ExternalSource(lambda: (setup["binding"],)),
                               clock=lambda: clock[0])
    selected = service.select(task)
    assert selected["status"] == "selected"
    clock[0] = 401.0

    assert service.revalidate(selected, task)["valid"] is False


@pytest.mark.parametrize("health", ["unknown", "unavailable"])
def test_unknown_or_unavailable_runtime_health_is_not_eligible(tmp_path, health):
    registry = _profiles(tmp_path)
    setup = _setup_external(tmp_path, "codex", registry, admission_health=health)
    task = _task(setup["spec"], persistent_memory="optional", persistent_context="optional",
                 approval="optional", verification="none", recovery="none",
                 permitted_mechanisms=("external_runtime",))

    result = _external_service(registry, [setup]).select(task)

    assert result["status"] == "denied"
    reasons = _candidate(result, "codex", "external_runtime")["reasons"]
    assert "runtime_health_unknown" in reasons or "runtime_unavailable" in reasons
