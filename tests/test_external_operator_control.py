"""Fixture-only tests for local operator enrollment and approval decisions."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
import sqlite3
import stat
import threading
import uuid

import pytest

from agent.external import contract
from agent.external import operator_control as operator_control_module
from agent.external.codex_policy import ANALYSIS_POLICY_REVISION, VERSION as CODEX_VERSION
from agent.external.operator_control import OperatorControl, VERSION
from agent.external.operator_review import build_enrollment_review, build_task_review


SCOPE = {
    "supervisor_id": "supervisor-1",
    "owner_id": "owner-1",
    "source_id": "source-1",
    "conversation_id": "conversation-1",
    "runtime_id": "runtime-1",
}


def enrollment_review():
    enrollment = {
        "cli_version": CODEX_VERSION,
        "model": "codex-fixture-model",
        "modelProvider": "openai",
        "policy_revision": ANALYSIS_POLICY_REVISION,
        "probe_sha256": "1" * 64,
        "provider_config_sha256": "2" * 64,
        "config_sha256": "3" * 64,
    }
    current = {key: value for key, value in enrollment.items() if key != "probe_sha256"}
    return build_enrollment_review(
        enrollment, current=current, observed_probe_sha256=enrollment["probe_sha256"]
    )


def make_spec(*, task_id=None, owner_id=None, amount=100):
    task_id = task_id or str(uuid.uuid4())
    return {
        "task_id": task_id,
        "idempotency_key": "idem-1",
        "owner_id": owner_id or SCOPE["owner_id"],
        "source_id": SCOPE["source_id"],
        "conversation_id": SCOPE["conversation_id"],
        "runtime_id": SCOPE["runtime_id"],
        "task": {
            "operation": "analyze_records",
            "artifact": "report.json",
            "content": json.dumps({
                "schema_version": 1,
                "currency": "USD",
                "records": [{"id": "fictional-1", "amount_cents": amount, "status": "paid"}],
            }),
        },
        "authority": {
            "operations": ["analyze_records"],
            "resource": task_id,
            "expires_at": 400.0,
        },
        "verification": {"acceptance": [], "external_state": []},
    }


def command(action, *, payload, expected_revision, scope=None, request_id=None):
    return {
        "protocol": VERSION,
        "request_id": request_id or str(uuid.uuid4()),
        "action": action,
        "scope": copy.deepcopy(SCOPE if scope is None else scope),
        "expected_revision": expected_revision,
        "payload": copy.deepcopy(payload),
    }


@pytest.fixture
def state_dir(tmp_path):
    return (tmp_path / "operator-state").resolve()


@pytest.fixture
def control(state_dir):
    return OperatorControl(state_dir, initialize=True)


def enroll(control, *, now=100.0, expires_at=500.0, review=None, expected_revision=0):
    return control.apply(command(
        "enroll", payload={"review": enrollment_review() if review is None else review,
                            "expires_at": expires_at},
        expected_revision=expected_revision,
    ), now=now)


def approve_task(control, spec=None, *, now=110.0, reviewed_at=105.0,
                 expires_at=300.0, enrollment_revision=1, task_review_id=None,
                 expected_revision=0, scope=None, request_id=None):
    spec = make_spec() if spec is None else copy.deepcopy(spec)
    reviewed = build_task_review(spec, enrollment_review(), now=reviewed_at)
    return control.apply(command(
        "approve_task",
        payload={"spec": spec, "enrollment_revision": enrollment_revision,
                 "task_review_id": reviewed["review_id"] if task_review_id is None else task_review_id,
                 "reviewed_at": reviewed_at, "expires_at": expires_at},
        expected_revision=expected_revision,
        scope=scope,
        request_id=request_id,
    ), now=now)


def test_initialization_is_explicit_private_and_owner_only(state_dir):
    with pytest.raises(contract.ProtocolError):
        OperatorControl(state_dir)
    assert not state_dir.exists()

    control = OperatorControl(state_dir, initialize=True)
    assert state_dir.is_dir()
    assert stat.S_IMODE(state_dir.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(control.path.stat().st_mode) & 0o077 == 0
    assert control.uid == os.getuid()


def test_enrollment_approval_uses_local_actor_and_keeps_execution_disabled(control):
    result = enroll(control)

    assert result["duplicate"] is False
    assert result["receipt"]["operator_uid"] == os.getuid()
    assert result["current"]["operator_uid"] == os.getuid()
    assert result["current"]["approval_status"] == "approved"
    assert result["current"]["approval_current"] is True
    assert result["receipt"]["execution_enabled"] is False
    assert result["receipt"]["external_actions_enabled"] is False
    assert result["current"]["execution_enabled"] is False
    assert result["current"]["external_actions_enabled"] is False
    assert "approved_by" not in result["current"]


def test_request_cannot_forge_operator_identity(control):
    request = command("enroll", payload={"review": enrollment_review(), "expires_at": 500.0},
                      expected_revision=0)
    request["approved_by"] = "forged-user"

    with pytest.raises(contract.ProtocolError):
        control.apply(request, now=100.0)


def test_changed_effective_account_is_rejected(control, state_dir, monkeypatch):
    monkeypatch.setattr(operator_control_module.os, "geteuid", lambda: control.uid + 1)
    with pytest.raises(contract.ProtocolError, match="account"):
        control.status(SCOPE, now=100.0)
    with pytest.raises(contract.ProtocolError, match="account"):
        OperatorControl(state_dir)


def test_task_approval_binds_exact_review_authority_scope_and_enrollment(control):
    enroll(control)
    spec = make_spec()
    result = approve_task(control, spec)

    assert result["current"]["kind"] == "task"
    assert result["current"]["decision"] == "approved"
    assert result["current"]["task_hash"] == contract.digest(contract.normalize_spec(spec))
    assert result["current"]["enrollment_revision"] == 1
    assert result["current"]["enrollment_review_id"] == enrollment_review()["review_id"]
    assert result["current"]["approval_current"] is True
    assert result["current"]["execution_enabled"] is False
    assert result["current"]["external_actions_enabled"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"task_review_id": "0" * 64},
        {"enrollment_revision": 0},
        {"expires_at": 401.0},  # Exceeds task authority expiry.
    ],
)
def test_task_approval_rejects_wrong_review_revision_or_expiry(control, changes):
    enroll(control)
    with pytest.raises(contract.ProtocolError):
        approve_task(control, **changes)


def test_task_approval_rejects_a_caller_scope_mismatch(control):
    enroll(control)
    wrong_scope = dict(SCOPE, owner_id="other-owner")
    with pytest.raises(contract.ProtocolError):
        approve_task(control, scope=wrong_scope, spec=make_spec(owner_id="other-owner"))


def test_task_approval_rejects_wider_operations(control):
    enroll(control)
    spec = make_spec()
    spec["authority"]["operations"] = ["analyze_records", "write_artifact"]
    request = command("approve_task", payload={
        "spec": spec,
        "enrollment_revision": 1,
        "task_review_id": "0" * 64,
        "reviewed_at": 105.0,
        "expires_at": 300.0,
    }, expected_revision=0)

    with pytest.raises(contract.ProtocolError):
        control.apply(request, now=110.0)


@pytest.mark.parametrize(
    ("action", "payload", "expires_at"),
    [
        ("enroll", {"review": enrollment_review(), "expires_at": 100.0}, None),
        ("approve_task", None, 110.0),
    ],
)
def test_expired_approval_is_rejected_at_commit(control, action, payload, expires_at):
    if action == "enroll":
        request = command(action, payload=payload, expected_revision=0)
    else:
        enroll(control)
        spec = make_spec()
        request = command("approve_task", payload={
            "spec": spec, "enrollment_revision": 1,
            "task_review_id": build_task_review(spec, enrollment_review(), now=105.0)["review_id"],
            "reviewed_at": 105.0, "expires_at": expires_at,
        }, expected_revision=0)

    with pytest.raises(contract.ProtocolError):
        control.apply(request, now=110.0 if action == "approve_task" else 100.0)


def test_unrepresentable_expiry_is_rejected_without_audit_write(control):
    request = command("enroll", payload={"review": enrollment_review(), "expires_at": 10 ** 400},
                      expected_revision=0)

    with pytest.raises(contract.ProtocolError):
        control.apply(request, now=100.0)

    assert control.audit(SCOPE) == []
    assert control.status(SCOPE, now=100.0)["approval_status"] == "missing"


def test_status_inspects_expired_enrollment_and_task_approvals(control):
    enroll(control, expires_at=120.0)
    spec = make_spec()
    approve_task(control, spec, expires_at=115.0)

    assert control.status(SCOPE, now=121.0)["approval_status"] == "expired"
    assert control.status(SCOPE, task_id=spec["task_id"], now=121.0)["approval_status"] == "expired"
    assert control.status(SCOPE, task_id=spec["task_id"], now=121.0)["execution_enabled"] is False


def test_wrong_caller_and_changed_immutable_task_are_rejected(control):
    enroll(control)
    original = make_spec()
    approve_task(control, original)

    with pytest.raises(contract.ProtocolError):
        control.status(dict(SCOPE, source_id="other-source"), task_id=original["task_id"], now=111.0)

    changed = make_spec(task_id=original["task_id"], amount=101)
    with pytest.raises(contract.ProtocolError):
        approve_task(control, changed, expected_revision=1)


def test_revoked_task_duplicate_command_returns_history_without_regrant(control):
    enroll(control)
    spec = make_spec()
    request_id = str(uuid.uuid4())
    approval_request = command("approve_task", payload={
        "spec": spec,
        "enrollment_revision": 1,
        "task_review_id": build_task_review(spec, enrollment_review(), now=105.0)["review_id"],
        "reviewed_at": 105.0,
        "expires_at": 300.0,
    }, expected_revision=0, request_id=request_id)
    first = control.apply(approval_request, now=110.0)
    control.apply(command("revoke_task", payload={"task_id": spec["task_id"]},
                          expected_revision=1), now=120.0)

    replay = control.apply(approval_request, now=121.0)

    assert replay["duplicate"] is True
    assert replay["receipt"] == first["receipt"]
    assert replay["current"]["approval_status"] == "revoked"
    assert replay["current"]["revision"] == 2
    assert replay["current"]["execution_enabled"] is False


def test_same_request_id_with_different_payload_is_a_conflict(control):
    request = command("enroll", payload={"review": enrollment_review(), "expires_at": 500.0},
                      expected_revision=0)
    control.apply(request, now=100.0)
    changed = copy.deepcopy(request)
    changed["payload"]["expires_at"] = 600.0

    with pytest.raises(contract.ProtocolError):
        control.apply(changed, now=101.0)


def test_restart_keeps_approval_audit_and_current_revoked_status(state_dir):
    first = OperatorControl(state_dir, initialize=True)
    enroll(first)
    spec = make_spec()
    approve_task(first, spec)
    first.apply(command("revoke_task", payload={"task_id": spec["task_id"]},
                        expected_revision=1), now=120.0)

    restarted = OperatorControl(state_dir)
    current = restarted.status(SCOPE, task_id=spec["task_id"], now=121.0)
    audit = restarted.audit(SCOPE)

    assert current["approval_status"] == "revoked"
    assert [item["action"] for item in audit] == ["enroll", "approve_task", "revoke_task"]
    assert [item["sequence"] for item in audit] == [1, 2, 3]
    assert [item["operator_uid"] for item in audit] == [os.getuid()] * 3
    assert [item["recorded_at"] for item in audit] == [100.0, 110.0, 120.0]
    assert audit[1]["target_id"] == "task-" + spec["task_id"]
    assert audit[1]["review_id"] == build_task_review(spec, enrollment_review(), now=105.0)["review_id"]
    assert audit[1]["historical"] is True
    assert audit[1]["snapshot"]["decision"] == "approved"
    assert audit[1]["snapshot"]["expires_at"] == 300.0
    assert audit[1]["snapshot"]["task_hash"] == current["task_hash"]
    assert audit[2]["snapshot"]["decision"] == "revoked"
    assert audit[1]["snapshot"]["revision"] == 1
    assert audit[2]["snapshot"]["revision"] == 2


def test_reenrollment_invalidates_prior_task_approval(control):
    enroll(control)
    spec = make_spec()
    approve_task(control, spec)
    control.apply(command("revoke_enrollment", payload={}, expected_revision=1), now=120.0)
    enroll(control, now=130.0, expected_revision=2)

    current = control.status(SCOPE, task_id=spec["task_id"], now=131.0)
    assert current["approval_status"] == "enrollment_changed"
    assert current["approval_current"] is False
    assert current["execution_enabled"] is False


def test_two_instances_competing_for_one_revision_commit_once(state_dir):
    first = OperatorControl(state_dir, initialize=True)
    enroll(first)
    spec = make_spec()
    approve_task(first, spec)
    second = OperatorControl(state_dir)
    barrier = threading.Barrier(2)

    def revoke(control):
        request = command("revoke_task", payload={"task_id": spec["task_id"]},
                          expected_revision=1)
        barrier.wait(timeout=5)
        try:
            return control.apply(request, now=120.0)
        except contract.ProtocolError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(revoke, (first, second)))

    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    errors = [outcome for outcome in outcomes if isinstance(outcome, contract.ProtocolError)]
    assert len(errors) == 1
    assert "revision" in str(errors[0]).lower()
    assert first.status(SCOPE, task_id=spec["task_id"], now=121.0)["revision"] == 2
    assert len(first.audit(SCOPE)) == 3


def test_clock_is_sampled_after_waiting_for_decision_lock(state_dir, monkeypatch):
    control = OperatorControl(state_dir, initialize=True)
    enroll(control)
    spec = make_spec()
    review = build_task_review(spec, enrollment_review(), now=205.0)
    request = command("approve_task", payload={
        "spec": spec,
        "enrollment_revision": 1,
        "task_review_id": review["review_id"],
        "reviewed_at": 205.0,
        "expires_at": 250.0,
    }, expected_revision=0)
    clock = {"now": 210.0}
    monkeypatch.setattr(operator_control_module.time, "time", lambda: clock["now"])
    lock = sqlite3.connect(control.path, timeout=30)
    lock.execute("BEGIN IMMEDIATE")
    attempting = threading.Event()
    connect = sqlite3.connect

    def observe_write_lock(*args, **kwargs):
        db = connect(*args, **kwargs)
        db.set_trace_callback(lambda sql: attempting.set() if sql == "BEGIN IMMEDIATE" else None)
        return db

    monkeypatch.setattr(operator_control_module.sqlite3, "connect", observe_write_lock)

    def apply_without_explicit_time():
        try:
            return control.apply(request)
        except contract.ProtocolError as exc:
            return exc

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(apply_without_explicit_time)
            assert attempting.wait(timeout=5)
            clock["now"] = 251.0
            lock.commit()
            result = pending.result(timeout=5)
    finally:
        lock.close()

    assert isinstance(result, contract.ProtocolError)
    assert str(result) == "Approval expiry must be in the future"
    assert control.status(SCOPE, task_id=spec["task_id"], now=252.0)["approval_status"] == "missing"
    assert [item["action"] for item in control.audit(SCOPE)] == ["enroll"]


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "group_writable"])
def test_unsafe_state_directory_or_journal_is_rejected(tmp_path, unsafe):
    state_dir = (tmp_path / "operator-state").resolve()
    control = OperatorControl(state_dir, initialize=True)
    if unsafe == "symlink":
        alias = tmp_path / "operator-alias"
        alias.symlink_to(state_dir, target_is_directory=True)
        with pytest.raises(contract.ProtocolError):
            OperatorControl(alias)
    elif unsafe == "hardlink":
        os.link(control.path, tmp_path / "journal-link")
        with pytest.raises(contract.ProtocolError):
            control.status(SCOPE, now=100.0)
    else:
        state_dir.chmod(0o770)
        with pytest.raises(contract.ProtocolError):
            OperatorControl(state_dir)


def test_unsafe_writable_ancestor_is_rejected_before_leaf_creation(tmp_path):
    unsafe_parent = tmp_path / "unsafe-parent"
    unsafe_parent.mkdir()
    unsafe_parent.chmod(0o777)
    state_dir = (unsafe_parent / "operator-state").resolve()

    with pytest.raises(contract.ProtocolError):
        OperatorControl(state_dir, initialize=True)

    assert not state_dir.exists()


def test_enrollment_rejects_blocked_review_and_extra_payload_authority(control):
    blocked = enrollment_review()
    blocked["status"] = "blocked"
    body = {key: value for key, value in blocked.items() if key != "review_id"}
    blocked["review_id"] = contract.digest(body)
    with pytest.raises(contract.ProtocolError):
        enroll(control, review=blocked)

    request = command("enroll", payload={"review": enrollment_review(), "expires_at": 500.0,
                                         "approved_by": "forged"}, expected_revision=0)
    with pytest.raises(contract.ProtocolError):
        control.apply(request, now=100.0)


@pytest.mark.parametrize('replacement', ['missing', 'private', 'hardlink', 'bad_mode', 'foreign_owner', 'symlink', 'zero'])
def test_sidecar_zero_link_is_rechecked_without_weakening_guard(control, monkeypatch, replacement):
    from pathlib import Path
    from types import SimpleNamespace
    sidecar = Path(str(control.path) + '-wal')
    sidecar.touch(mode=0o600)
    original = Path.lstat
    genuine = original(sidecar)
    calls = []
    def result(mode=genuine.st_mode, uid=genuine.st_uid, links=1):
        return SimpleNamespace(st_mode=mode, st_uid=uid, st_nlink=links)
    def lstat(path):
        if path != sidecar:
            return original(path)
        calls.append(True)
        if len(calls) == 1 or replacement == 'zero':
            return result(links=0)
        if replacement == 'missing':
            raise FileNotFoundError
        if replacement == 'private':
            return result()
        if replacement == 'hardlink':
            return result(links=2)
        if replacement == 'bad_mode':
            return result(mode=stat.S_IFREG | 0o644)
        if replacement == 'foreign_owner':
            return result(uid=control.uid + 1)
        return result(mode=stat.S_IFLNK | 0o777)
    monkeypatch.setattr(Path, 'lstat', lstat)
    if replacement in ('missing', 'private'):
        control._guard()
        assert len(calls) == 2
    else:
        with pytest.raises(contract.ProtocolError, match='not private and owned'):
            control._guard()
        assert len(calls) == (4 if replacement == 'zero' else 2)


def test_zero_link_primary_database_is_not_retried(control, monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    original = Path.lstat
    genuine = original(control.path)
    calls = []
    def lstat(path):
        if path == control.path:
            calls.append(True)
            return SimpleNamespace(st_mode=genuine.st_mode, st_uid=genuine.st_uid, st_nlink=0)
        return original(path)
    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(contract.ProtocolError, match='not private and owned'):
        control._guard()
    assert len(calls) == 1
