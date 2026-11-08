"""CLI routing and bounded-input tests for the local operator controls."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import pytest

from agent.external import contract
from agent.external import operator_cli
from agent.external.codex_policy import ANALYSIS_POLICY_REVISION, VERSION as CODEX_VERSION
from agent.external.operator_control import VERSION as COMMAND_VERSION
from agent.external.operator_review import build_enrollment_review, build_task_review


SCOPE = {
    "supervisor_id": "supervisor-1",
    "owner_id": "owner-1",
    "source_id": "source-1",
    "conversation_id": "conversation-1",
    "runtime_id": "runtime-1",
}


def invoke(args, capsys):
    code = operator_cli.main(args)
    captured = capsys.readouterr()
    output = captured.out if code == 0 else captured.err
    return code, json.loads(output)


def test_state_directory_is_required(capsys):
    code, result = invoke(["init"], capsys)

    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}


def test_init_and_commands_route_to_operator_control(tmp_path, monkeypatch, capsys):
    calls = []

    class StubControl:
        def __init__(self, state_dir, *, initialize=False):
            calls.append(("construct", state_dir, initialize))

        def apply(self, request, *, now=None):
            calls.append(("apply", request, now))
            return {"operation": "applied"}

        def status(self, scope, *, task_id=None, now=None):
            calls.append(("status", scope, task_id, now))
            return {"operation": "status"}

        def audit(self, scope):
            calls.append(("audit", scope))
            return {"operation": "audit"}

    monkeypatch.setattr(operator_cli, "OperatorControl", StubControl)
    state_dir = tmp_path / "operator-state"

    code, result = invoke(["--state-dir", str(state_dir), "init"], capsys)
    assert code == 0
    assert result == {
        "status": "initialized",
        "execution_enabled": False,
        "external_actions_enabled": False,
    }
    state_dir.mkdir()

    request_file = tmp_path / "request.json"
    request_file.write_text('{"decision":"grant"}', encoding="utf-8")
    scope_file = tmp_path / "scope.json"
    scope_file.write_text(json.dumps(SCOPE), encoding="utf-8")

    code, result = invoke([
        "--state-dir", str(state_dir), "apply", "--request", str(request_file),
    ], capsys)
    assert code == 0 and result == {"operation": "applied"}
    code, result = invoke([
        "--state-dir", str(state_dir), "status", "--scope", str(scope_file),
        "--task-id", "task-1",
    ], capsys)
    assert code == 0 and result == {"operation": "status"}
    code, result = invoke([
        "--state-dir", str(state_dir), "audit", "--scope", str(scope_file),
    ], capsys)
    assert code == 0 and result == {"operation": "audit"}

    assert calls == [
        ("construct", state_dir, True),
        ("construct", state_dir, False), ("apply", {"decision": "grant"}, None),
        ("construct", state_dir, False), ("status", SCOPE, "task-1", None),
        ("construct", state_dir, False), ("audit", SCOPE),
    ]


def test_uninitialized_state_fails_without_constructing_control(tmp_path, monkeypatch, capsys):
    class MustNotConstruct:
        def __init__(self, *args, **kwargs):
            pytest.fail("operator control must not open an uninitialized state")

    monkeypatch.setattr(operator_cli, "OperatorControl", MustNotConstruct)
    code, result = invoke([
        "--state-dir", str(tmp_path / "missing"), "audit", "--scope", "-",
    ], capsys)

    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}


def test_json_input_is_bounded_and_invalid_json_is_rejected(tmp_path, monkeypatch, capsys):
    class StubControl:
        def __init__(self, *args, **kwargs):
            pass

        def apply(self, request, *, now=None):
            pytest.fail("invalid input must not reach operator control")

    monkeypatch.setattr(operator_cli, "OperatorControl", StubControl)
    large = tmp_path / "large.json"
    large.write_bytes(b" " * (contract.MAX_MESSAGE_BYTES + 1))
    code, result = invoke([
        "--state-dir", str(tmp_path), "apply", "--request", str(large),
    ], capsys)
    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    code, result = invoke([
        "--state-dir", str(tmp_path), "apply", "--request", str(invalid),
    ], capsys)
    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}


def test_scope_requires_exact_fields_and_json_stdin_is_supported(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(operator_cli.sys, "stdin", io.TextIOWrapper(io.BytesIO(
        json.dumps(SCOPE).encode("utf-8")
    )))
    (tmp_path / "existing").mkdir()

    class StubControl:
        def __init__(self, *args, **kwargs):
            pass

        def status(self, scope, *, task_id=None, now=None):
            return {"scope": scope}

    monkeypatch.setattr(operator_cli, "OperatorControl", StubControl)
    code, result = invoke([
        "--state-dir", str(tmp_path / "existing"), "status", "--scope", "-",
    ], capsys)
    assert code == 0 and result == {"scope": SCOPE}

    extra = tmp_path / "extra.json"
    extra.write_text(json.dumps({**SCOPE, "extra": "reject"}), encoding="utf-8")
    code, result = invoke([
        "--state-dir", str(tmp_path / "existing"), "audit", "--scope", str(extra),
    ], capsys)
    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}


@pytest.mark.parametrize("command", ["activate", "enable", "dispatch"])
def test_activation_commands_are_not_supported(tmp_path, command, capsys):
    code, result = invoke(["--state-dir", str(tmp_path), command], capsys)

    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}


def test_operator_identity_arguments_are_not_supported(tmp_path, capsys):
    code, result = invoke([
        "--state-dir", str(tmp_path), "apply", "--request", "-", "--approved-by", "name",
    ], capsys)

    assert code == 1
    assert result == {"status": "error", "error": "operator_control_failed"}


def _run_cli(repo, state_dir, command, *args, input_value=None):
    completed = subprocess.run(
        [sys.executable, "-m", "agent.external.operator_cli", "--state-dir",
         str(state_dir), command, *args],
        cwd=repo,
        input=None if input_value is None else json.dumps(input_value),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_real_cli_persists_decisions_across_processes_and_replays_history(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    state_dir = (tmp_path / "operator-state").resolve()
    os.chmod(tmp_path, 0o700)
    scope = dict(SCOPE)
    now = time.time()
    enrollment_expiry = now + 3600
    enrollment = {
        "cli_version": CODEX_VERSION,
        "model": "fictional-model",
        "modelProvider": "fictional-provider",
        "policy_revision": ANALYSIS_POLICY_REVISION,
        "probe_sha256": "1" * 64,
        "provider_config_sha256": "2" * 64,
        "config_sha256": "3" * 64,
    }
    enrollment_review = build_enrollment_review(
        enrollment,
        current={key: value for key, value in enrollment.items() if key != "probe_sha256"},
        observed_probe_sha256=enrollment["probe_sha256"],
    )
    task_id = str(uuid.uuid4())
    task_spec = {
        "task_id": task_id,
        "idempotency_key": "fictional-idem-1",
        "owner_id": scope["owner_id"],
        "source_id": scope["source_id"],
        "conversation_id": scope["conversation_id"],
        "runtime_id": scope["runtime_id"],
        "task": {
            "operation": "analyze_records",
            "artifact": "fictional-report.json",
            "content": json.dumps({
                "schema_version": 1,
                "currency": "USD",
                "records": [{"id": "fictional-row", "amount_cents": 125, "status": "paid"}],
            }),
        },
        "authority": {
            "operations": ["analyze_records"],
            "resource": task_id,
            "expires_at": enrollment_expiry,
        },
        "verification": {"acceptance": [], "external_state": []},
    }
    reviewed_at = time.time()
    task_review = build_task_review(task_spec, enrollment_review, now=reviewed_at)
    task_expiry = reviewed_at + 1800

    initialized = _run_cli(repo, state_dir, "init")
    assert initialized == {
        "status": "initialized",
        "execution_enabled": False,
        "external_actions_enabled": False,
    }
    assert state_dir.stat().st_mode & 0o777 == 0o700

    enrollment_request = {
        "protocol": COMMAND_VERSION,
        "request_id": str(uuid.uuid4()),
        "action": "enroll",
        "scope": scope,
        "expected_revision": 0,
        "payload": {"review": enrollment_review, "expires_at": enrollment_expiry},
    }
    enrollment_result = _run_cli(
        repo, state_dir, "apply", "--request", "-", input_value=enrollment_request,
    )
    assert enrollment_result["receipt"]["operator_uid"] == os.getuid()
    assert enrollment_result["receipt"]["execution_enabled"] is False
    assert enrollment_result["receipt"]["external_actions_enabled"] is False
    assert enrollment_result["current"]["approval_status"] == "approved"
    assert enrollment_result["current"]["execution_enabled"] is False
    assert enrollment_result["current"]["external_actions_enabled"] is False

    approval_request = {
        "protocol": COMMAND_VERSION,
        "request_id": str(uuid.uuid4()),
        "action": "approve_task",
        "scope": scope,
        "expected_revision": 0,
        "payload": {
            "spec": task_spec,
            "enrollment_revision": 1,
            "task_review_id": task_review["review_id"],
            "reviewed_at": reviewed_at,
            "expires_at": task_expiry,
        },
    }
    approved = _run_cli(
        repo, state_dir, "apply", "--request", "-", input_value=approval_request,
    )
    assert approved["receipt"]["operator_uid"] == os.getuid()
    assert approved["receipt"]["decision"] == "approved"
    assert approved["current"]["approval_status"] == "approved"
    assert approved["current"]["execution_enabled"] is False
    assert approved["current"]["external_actions_enabled"] is False

    revoke_request = {
        "protocol": COMMAND_VERSION,
        "request_id": str(uuid.uuid4()),
        "action": "revoke_task",
        "scope": scope,
        "expected_revision": 1,
        "payload": {"task_id": task_id},
    }
    revoked = _run_cli(
        repo, state_dir, "apply", "--request", "-", input_value=revoke_request,
    )
    assert revoked["receipt"]["operator_uid"] == os.getuid()
    assert revoked["current"]["approval_status"] == "revoked"
    assert revoked["current"]["approval_current"] is False
    assert revoked["current"]["execution_enabled"] is False
    assert revoked["current"]["external_actions_enabled"] is False

    status = _run_cli(
        repo, state_dir, "status", "--scope", "-", "--task-id", task_id,
        input_value=scope,
    )
    assert status["operator_uid"] == os.getuid()
    assert status["approval_status"] == "revoked"
    assert status["approval_current"] is False
    assert status["execution_enabled"] is False
    assert status["external_actions_enabled"] is False

    replay = _run_cli(
        repo, state_dir, "apply", "--request", "-", input_value=approval_request,
    )
    assert replay["duplicate"] is True
    assert replay["receipt"]["historical"] is True
    assert replay["receipt"]["snapshot"]["decision"] == "approved"
    assert replay["receipt"]["operator_uid"] == os.getuid()
    assert replay["current"]["approval_status"] == "revoked"
    assert replay["current"]["execution_enabled"] is False
    assert replay["current"]["external_actions_enabled"] is False
