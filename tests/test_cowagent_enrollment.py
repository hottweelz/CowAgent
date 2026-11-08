"""Fixture-only tests for a registered CowAgent enrollment review branch."""
import copy
import json
import uuid

import pytest

from agent.external import contract
from agent.external.codex_policy import (
    ANALYSIS_POLICY_REVISION,
    VERSION as CODEX_VERSION,
)
from agent.external.operator_control import OperatorControl, VERSION as OPERATOR_VERSION
from agent.external.operator_review import (
    _enrollment_packet,
    build_enrollment_review,
    build_task_review,
)


SCOPE = {
    "supervisor_id": "supervisor-fixture",
    "owner_id": "owner-fixture",
    "source_id": "source-fixture",
    "conversation_id": "conversation-fixture",
    "runtime_id": "runtime-fixture",
}
PROBE = "a" * 64


def cowagent_enrollment():
    return {
        "runtime_kind": "cowagent-registered/1",
        "agent_id": "testpilot",
        "model": "fixture-model",
        "provider": "fixture-provider",
        "config_sha256": "1" * 64,
        "profile_sha256": "2" * 64,
        "source_sha256": "3" * 64,
        "probe_sha256": PROBE,
    }


def cowagent_current():
    return {key: value for key, value in cowagent_enrollment().items()
            if key != "probe_sha256"}


def cowagent_review(*, enrollment=None, current=None, observed_probe_sha256=PROBE):
    return build_enrollment_review(
        cowagent_enrollment() if enrollment is None else enrollment,
        current=cowagent_current() if current is None else current,
        observed_probe_sha256=observed_probe_sha256,
    )


def test_existing_codex_enrollment_review_shape_remains_supported():
    enrollment = {
        "cli_version": CODEX_VERSION,
        "model": "fixture-codex-model",
        "modelProvider": "openai",
        "policy_revision": ANALYSIS_POLICY_REVISION,
        "probe_sha256": PROBE,
        "provider_config_sha256": "4" * 64,
        "config_sha256": "5" * 64,
    }
    current = {key: value for key, value in enrollment.items()
               if key != "probe_sha256"}

    packet = build_enrollment_review(
        enrollment, current=current, observed_probe_sha256=PROBE
    )

    assert packet["status"] == "review_required"
    assert packet["enrollment"] == enrollment
    assert packet["current"] == current
    assert set(packet["enrollment"]) == {
        "cli_version", "model", "modelProvider", "policy_revision",
        "probe_sha256", "provider_config_sha256", "config_sha256",
    }
    assert "runtime_kind" not in packet["enrollment"]


def make_spec(*, operation="analyze_records", operations=None):
    task_id = str(uuid.uuid4())
    return {
        "task_id": task_id,
        "idempotency_key": "idempotency-fixture",
        "owner_id": SCOPE["owner_id"],
        "source_id": SCOPE["source_id"],
        "conversation_id": SCOPE["conversation_id"],
        "runtime_id": SCOPE["runtime_id"],
        "task": {
            "operation": operation,
            "artifact": "report.json",
            "content": json.dumps({
                "schema_version": 1,
                "currency": "USD",
                "records": [{"id": "fixture-1", "amount_cents": 250,
                             "status": "paid"}],
            }),
        },
        "authority": {
            "operations": [operation] if operations is None else operations,
            "resource": task_id,
            "expires_at": 500.0,
        },
        "verification": {"acceptance": [], "external_state": []},
    }


def operator_command(action, payload, expected_revision, request_id=None):
    return {
        "protocol": OPERATOR_VERSION,
        "request_id": request_id or str(uuid.uuid4()),
        "action": action,
        "scope": copy.deepcopy(SCOPE),
        "expected_revision": expected_revision,
        "payload": copy.deepcopy(payload),
    }


def test_registered_cowagent_enrollment_review_is_read_only_and_binds_snapshot():
    packet = cowagent_review()

    assert packet["protocol"] == "cow.external.operator-review/1"
    assert packet["kind"] == "enrollment"
    assert packet["enrollment"] == cowagent_enrollment()
    assert packet["current"] == cowagent_current()
    assert packet["observed_probe_sha256"] == PROBE
    assert packet["observation_source"] == "caller_supplied"
    assert packet["status"] == "review_required"
    assert packet["approval_status"] == "not_granted"
    assert packet["execution_enabled"] is False
    assert packet["external_actions_enabled"] is False
    body = {key: value for key, value in packet.items() if key != "review_id"}
    assert packet["review_id"] == contract.digest(body)


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("model", "other-model"),
        ("provider", "other-provider"),
        ("config_sha256", "4" * 64),
        ("profile_sha256", "5" * 64),
        ("source_sha256", "6" * 64),
    ],
)
def test_registered_cowagent_snapshot_drift_blocks_review(field, changed):
    current = cowagent_current()
    current[field] = changed

    packet = cowagent_review(current=current)

    assert packet["status"] == "blocked"
    assert f"{field}_mismatch" in packet["reasons"]
    assert packet["approval_status"] == "not_granted"
    assert packet["execution_enabled"] is False
    assert packet["external_actions_enabled"] is False


def test_registered_cowagent_probe_drift_blocks_review():
    packet = cowagent_review(observed_probe_sha256="b" * 64)

    assert packet["status"] == "blocked"
    assert "probe_sha256_mismatch" in packet["reasons"]
    assert packet["execution_enabled"] is False


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("enrollment", "runtime_kind", "other-runtime/1"),
        ("current", "runtime_kind", "other-runtime/1"),
        ("enrollment", "agent_id", "other-agent"),
        ("current", "agent_id", "other-agent"),
        ("enrollment", "model", ""),
        ("current", "provider", ""),
        ("enrollment", "model", "m" * 129),
        ("current", "provider", "p" * 129),
        ("enrollment", "config_sha256", "A" * 64),
        ("current", "profile_sha256", "short"),
        ("enrollment", "source_sha256", "g" * 64),
    ],
)
def test_registered_cowagent_rejects_invalid_identity_and_snapshot_fields(
    target, field, value
):
    enrollment = cowagent_enrollment()
    current = cowagent_current()
    (enrollment if target == "enrollment" else current)[field] = value

    with pytest.raises(contract.ProtocolError):
        cowagent_review(enrollment=enrollment, current=current)


@pytest.mark.parametrize("target", ["enrollment", "current"])
@pytest.mark.parametrize(
    "extra",
    [
        {"model_override": "attacker-model"},
        {"session_id": "borrowed-session"},
        {"credentials": {"token": "fixture-secret"}},
        {"memory": "private-memory"},
        {"tools": ["write_file"]},
    ],
)
def test_registered_cowagent_rejects_overrides_and_private_fields(target, extra):
    enrollment = cowagent_enrollment()
    current = cowagent_current()
    (enrollment if target == "enrollment" else current).update(extra)

    with pytest.raises(contract.ProtocolError):
        cowagent_review(enrollment=enrollment, current=current)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda packet: packet.update(status="blocked"),
        lambda packet: packet.update(review_id="0" * 64),
        lambda packet: packet["enrollment"].update(model="tampered-model"),
        lambda packet: packet.update(memory="private-memory"),
    ],
)
def test_registered_cowagent_enrollment_packet_rejects_tampering(tamper):
    packet = cowagent_review()
    tamper(packet)

    with pytest.raises(contract.ProtocolError):
        _enrollment_packet(packet)


def test_registered_cowagent_enrollment_keeps_bounded_analysis_review_behavior():
    enrollment_review = cowagent_review()
    packet = build_task_review(make_spec(), enrollment_review, now=100.0)

    assert packet["kind"] == "task"
    assert packet["enrollment_review_id"] == enrollment_review["review_id"]
    assert packet["task"]["operation"] == "analyze_records"
    assert packet["status"] == "review_required"
    assert packet["execution_enabled"] is False
    assert packet["external_actions_enabled"] is False
    assert packet["verified"] is False

    with pytest.raises(contract.ProtocolError):
        build_task_review(
            make_spec(operation="record_effect", operations=["record_effect"]),
            enrollment_review,
            now=100.0,
        )


def test_local_operator_can_enroll_and_approve_task_from_registered_review(tmp_path):
    control = OperatorControl((tmp_path / "operator-state").resolve(), initialize=True)
    review = cowagent_review()
    enrollment_result = control.apply(operator_command(
        "enroll", {"review": review, "expires_at": 450.0}, expected_revision=0
    ), now=100.0)

    assert enrollment_result["current"]["approval_current"] is True
    assert enrollment_result["current"]["review_id"] == review["review_id"]
    assert enrollment_result["current"]["execution_enabled"] is False

    spec = make_spec()
    task_review = build_task_review(spec, review, now=105.0)
    approved = control.apply(operator_command(
        "approve_task",
        {
            "spec": spec,
            "enrollment_revision": 1,
            "task_review_id": task_review["review_id"],
            "reviewed_at": 105.0,
            "expires_at": 300.0,
        },
        expected_revision=0,
    ), now=110.0)

    assert approved["current"]["approval_current"] is True
    assert approved["current"]["enrollment_review_id"] == review["review_id"]
    assert approved["current"]["execution_enabled"] is False
    assert approved["current"]["external_actions_enabled"] is False
