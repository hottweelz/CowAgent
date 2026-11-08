"""Read-only enrollment and task review packet tests."""
import copy
import builtins
import json
from pathlib import Path
import socket
import subprocess
import uuid
from unittest.mock import patch

import pytest

from agent.external import contract
from agent.external.operator_review import (
    build_enrollment_review,
    build_task_review,
)


def enrollment():
    return {
        "cli_version": "0.165.0",
        "model": "codex-test",
        "modelProvider": "openai",
        "policy_revision": "native-readonly-artifact-v1",
        "probe_sha256": "1" * 64,
        "provider_config_sha256": "2" * 64,
        "config_sha256": "3" * 64,
    }


def current_enrollment():
    return {key: value for key, value in enrollment().items() if key != "probe_sha256"}


def task_spec(*, operation="analyze_records", operations=None, expires_at=2000.0):
    return {
        "task_id": str(uuid.uuid4()),
        "idempotency_key": "idem-1",
        "owner_id": "owner-1",
        "source_id": "source-1",
        "conversation_id": "conversation-1",
        "runtime_id": "runtime-1",
        "task": {
            "operation": operation,
            "artifact": "report.json",
            "content": json.dumps({
                "schema_version": 1,
                "currency": "USD",
                "records": [{"id": "row-1", "amount_cents": 100, "status": "paid"}],
            }),
        },
        "authority": {
            "operations": [operation] if operations is None else operations,
            "resource": "PLACEHOLDER",
            "expires_at": expires_at,
        },
        "verification": {
            "acceptance": [{"id": "report-check", "type": "schema_v9", "details": "retain"}],
            "external_state": [],
        },
    }


def make_spec(**kwargs):
    value = task_spec(**kwargs)
    value["authority"]["resource"] = value["task_id"]
    return value


def enrollment_packet(**kwargs):
    return build_enrollment_review(
        enrollment(), current=current_enrollment(), observed_probe_sha256="1" * 64, **kwargs
    )


def test_matching_enrollment_snapshot_is_review_only_and_binds_observation():
    packet = enrollment_packet()

    assert packet["protocol"] == "cow.external.operator-review/1"
    assert packet["kind"] == "enrollment"
    assert packet["enrollment"] == enrollment()
    assert packet["current"] == current_enrollment()
    assert packet["observed_probe_sha256"] == "1" * 64
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
        ("config_sha256", "4" * 64),
        ("provider_config_sha256", "5" * 64),
        ("probe_sha256", "6" * 64),
    ],
)
def test_enrollment_drift_blocks_review(field, changed):
    observed = enrollment()
    observed[field] = changed
    packet = build_enrollment_review(
        observed, current=current_enrollment(), observed_probe_sha256="1" * 64
    )

    assert packet["status"] == "blocked"
    assert packet["approval_status"] == "not_granted"
    assert packet["execution_enabled"] is False
    assert packet["external_actions_enabled"] is False
    assert packet["reasons"]


def test_unsupported_cli_or_policy_revision_blocks_enrollment():
    unsupported = enrollment()
    unsupported["cli_version"] = "999.0"
    unsupported["policy_revision"] = "unknown-policy"

    packet = build_enrollment_review(
        unsupported, current={**current_enrollment(), "cli_version": "999.0",
                             "policy_revision": "unknown-policy"},
        observed_probe_sha256="1" * 64,
    )

    assert packet["status"] == "blocked"
    assert {"unsupported_cli_version", "unsupported_policy_revision"} <= set(packet["reasons"])


@pytest.mark.parametrize("extra", ["api_key", "access_token", "credential"])
def test_enrollment_rejects_unknown_or_credential_fields(extra):
    observed = enrollment()
    observed[extra] = "secret-like"

    with pytest.raises(contract.ProtocolError):
        build_enrollment_review(
            observed, current=current_enrollment(), observed_probe_sha256="1" * 64
        )


def test_analysis_task_packet_binds_identity_hash_and_verification_criteria():
    spec = make_spec()
    enrollment_review = enrollment_packet()
    packet = build_task_review(spec, enrollment_review, now=1000.0)
    normalized = contract.normalize_spec(spec)

    assert packet["protocol"] == "cow.external.operator-review/1"
    assert packet["kind"] == "task"
    assert packet["task_hash"] == contract.digest(normalized)
    assert packet["identity"] == {key: normalized[key] for key in (
        "task_id", "idempotency_key", "owner_id", "source_id", "conversation_id", "runtime_id"
    )}
    assert packet["enrollment_review_id"] == enrollment_review["review_id"]
    assert packet["authority"] == normalized["authority"]
    assert packet["task"]["operation"] == "analyze_records"
    assert packet["task"]["artifact"] == "report.json"
    assert packet["task"]["record_count"] == 1
    assert packet["task"]["dataset_sha256"] == contract.digest({
        "schema_version": 1, "currency": "USD",
        "records": [{"id": "row-1", "amount_cents": 100, "status": "paid"}],
    })
    assert packet["verification"]["required_checks"] == [
        "artifact_schema", "analysis_result", "published_artifact_sha256"
    ]
    assert packet["verification"]["caller_contract"] == normalized["verification"]
    assert packet["status"] == "review_required"
    assert packet["approval_status"] == "not_granted"
    assert packet["execution_enabled"] is False
    assert packet["external_actions_enabled"] is False
    assert packet["execution_status"] == "unobserved"
    assert packet["acceptance_status"] == "unverified"
    assert packet["external_state_status"] == "unverified"
    assert packet["verified"] is False
    assert packet["reviewed_at"] == 1000.0
    body = {key: value for key, value in packet.items() if key != "review_id"}
    assert packet["review_id"] == contract.digest(body)


def test_task_hash_changes_when_data_or_authority_changes():
    first = make_spec()
    second = copy.deepcopy(first)
    second["task"]["content"] = json.dumps({
        "schema_version": 1, "currency": "USD",
        "records": [{"id": "row-1", "amount_cents": 101, "status": "paid"}],
    })
    third = copy.deepcopy(first)
    third["authority"]["expires_at"] = 2100.0
    enrollment_review = enrollment_packet()

    first_packet = build_task_review(first, enrollment_review, now=1000.0)
    second_packet = build_task_review(second, enrollment_review, now=1000.0)
    third_packet = build_task_review(third, enrollment_review, now=1000.0)

    assert len({first_packet["task_hash"], second_packet["task_hash"], third_packet["task_hash"]}) == 3
    assert len({first_packet["review_id"], second_packet["review_id"], third_packet["review_id"]}) == 3


def test_review_packets_do_not_retain_mutable_input_references():
    observed = enrollment()
    current = current_enrollment()
    packet = build_enrollment_review(observed, current=current, observed_probe_sha256="1" * 64)
    observed["config_sha256"] = "4" * 64
    current["config_sha256"] = "5" * 64
    assert packet["enrollment"]["config_sha256"] == "3" * 64
    assert packet["current"]["config_sha256"] == "3" * 64

    spec = make_spec()
    task_packet = build_task_review(spec, enrollment_packet(), now=1000.0)
    spec["authority"]["operations"].append("write_artifact")
    assert task_packet["authority"]["operations"] == ["analyze_records"]


def test_authority_expiry_boundary_blocks_task_review():
    packet = build_task_review(
        make_spec(expires_at=1000.0), enrollment_packet(), now=1000.0
    )

    assert packet["status"] == "blocked"
    assert "expired_authority" in packet["reasons"]
    assert packet["approval_status"] == "not_granted"
    assert packet["execution_enabled"] is False


@pytest.mark.parametrize("tamper", [
    lambda packet: packet.update(execution_enabled=True),
    lambda packet: packet.update(approval_status="granted"),
    lambda packet: packet.update(review_id="0" * 64),
])
def test_task_review_rejects_tampered_enrollment_packet(tamper):
    packet = enrollment_packet()
    tamper(packet)

    with pytest.raises(contract.ProtocolError):
        build_task_review(make_spec(), packet, now=1000.0)


@pytest.mark.parametrize(
    ("operation", "operations"),
    [
        ("record_effect", ["record_effect"]),
        ("write_artifact", ["write_artifact"]),
        ("analyze_records", ["analyze_records", "write_artifact"]),
    ],
)
def test_task_review_blocks_unsupported_operation_or_broader_authority(operation, operations):
    with pytest.raises(contract.ProtocolError):
        build_task_review(
            make_spec(operation=operation, operations=operations), enrollment_packet(), now=1000.0
        )


@pytest.mark.parametrize("now", [float("nan"), float("inf"), -float("inf")])
def test_task_review_rejects_non_finite_review_time(now):
    with pytest.raises(contract.ProtocolError):
        build_task_review(make_spec(), enrollment_packet(), now=now)


def test_review_builders_do_not_open_files_start_processes_or_create_sockets():
    spec = make_spec()
    with patch.object(builtins, "open", side_effect=AssertionError("file opened")), \
            patch.object(Path, "write_text", side_effect=AssertionError("file written")), \
            patch.object(subprocess, "Popen", side_effect=AssertionError("process started")), \
            patch.object(socket, "socket", side_effect=AssertionError("socket created")):
        enrollment_review = build_enrollment_review(
            enrollment(), current=current_enrollment(), observed_probe_sha256="1" * 64
        )
        task_review = build_task_review(spec, enrollment_review, now=1000.0)

    assert enrollment_review["kind"] == "enrollment"
    assert task_review["kind"] == "task"
