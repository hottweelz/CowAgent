"""Deterministic composition proof for bounded analysis under operator control.

This uses a fixture transport only. The enrollment review fields retain the
legacy Codex-shaped fixture schema used by the existing operator-control tests;
this file does not invoke a Codex adapter, CLI, or real model.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import threading
import time
import uuid

import pytest

from agent.external import contract
from agent.external.analysis import AnalysisVerifier, expected_report
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.codex_policy import ANALYSIS_POLICY_REVISION, VERSION as LEGACY_FIXTURE_VERSION
from agent.external.operator_control import OperatorControl, VERSION as OPERATOR_VERSION
from agent.external.operator_review import build_enrollment_review, build_task_review
from agent.external.supervisor import ExternalSupervisor
from agent.external.transport import RemoteRejected, TransportUnavailable


SCOPE = {
    "supervisor_id": "fixture-supervisor",
    "owner_id": "fixture-owner",
    "source_id": "fixture-source",
    "conversation_id": "fixture-conversation",
    "runtime_id": "fixture-runtime",
}
ENROLLMENT = {
    # Legacy fixture metadata only; this is not a current Codex runtime claim.
    "cli_version": LEGACY_FIXTURE_VERSION,
    "model": "fixture-only-model",
    "modelProvider": "fixture-only-provider",
    "policy_revision": ANALYSIS_POLICY_REVISION,
    "probe_sha256": "1" * 64,
    "provider_config_sha256": "2" * 64,
    "config_sha256": "3" * 64,
}
CURRENT_ENROLLMENT = {key: value for key, value in ENROLLMENT.items() if key != "probe_sha256"}


def _request(action, payload, revision):
    return {"protocol": OPERATOR_VERSION, "request_id": str(uuid.uuid4()),
            "action": action, "scope": dict(SCOPE), "expected_revision": revision,
            "payload": payload}


def _spec(task_id=None):
    task_id = task_id or str(uuid.uuid4())
    content = {"schema_version": 1, "currency": "USD", "records": [
        {"id": "fictional-paid", "amount_cents": 1250, "status": "paid"},
        {"id": "fictional-refund", "amount_cents": -250, "status": "refund"},
    ]}
    return contract.normalize_spec({
        "task_id": task_id,
        "idempotency_key": "fixture-analysis-" + task_id,
        "owner_id": SCOPE["owner_id"], "source_id": SCOPE["source_id"],
        "conversation_id": SCOPE["conversation_id"], "runtime_id": SCOPE["runtime_id"],
        "task": {"operation": "analyze_records", "artifact": "report.json",
                 "content": json.dumps(content, sort_keys=True)},
        "authority": {"operations": ["analyze_records"], "resource": task_id,
                      "expires_at": time.time() + 120},
        "verification": {},
    })


def _observation(spec, *, state, revision, result=None, cancel_requested=False):
    return {"task_id": spec["task_id"], "task_hash": contract.digest(spec),
            "runtime_id": spec["runtime_id"], "session_id": "fixture-session-stable",
            "revision": revision, "state": state,
            "cancel_requested": cancel_requested,
            "termination_confirmed": state in {"completed", "failed", "cancelled"},
            "result": result, "reason": "fixture_observation"}


class FixtureAnalysisTransport:
    """Test adapter for the supervisor/runtime boundary; no provider calls."""

    def __init__(self, adapter_id, credential, journal, exports, *, mode="complete"):
        if adapter_id != "fixture-analysis-v1":
            raise contract.ProtocolError("Unsupported fixture adapter")
        if not isinstance(credential, contract.Credential):
            raise contract.ProtocolError("Fixture credential required")
        self.adapter_id = adapter_id
        self.credential = credential
        self.journal = journal
        self.exports = exports
        self.mode = mode
        self.submit_calls = 0
        self._state = {}
        self.entered = threading.Event()
        self.release = threading.Event()
        self.cancel_count = 0

    def submit(self, spec, approval=None):
        self.submit_calls += 1
        if self.mode == "invalid_credential":
            raise RemoteRejected("fixture_authentication_rejected")
        if self.mode == "reject":
            raise RemoteRejected("fixture_submission_rejected")
        self.journal.validate_submission(spec, approval, self.credential,
                                         enrollment=ENROLLMENT)
        self.journal.authorize_native(spec, approval, self.credential,
                                      enrollment=ENROLLMENT,
                                      native_thread="fixture-thread",
                                      native_session="fixture-session-stable")
        self.entered.set()
        if self.mode == "block":
            assert self.release.wait(2)
        if self.mode in {"lost_ack", "unknown"}:
            self._state[spec["task_id"]] = {"spec": spec, "approval": approval,
                                            "revision": 1, "state": "running"}
            raise TransportUnavailable("fixture acknowledgement lost")
        self._state[spec["task_id"]] = {"spec": spec, "approval": approval,
                                        "revision": 1, "state": "running"}
        return _observation(spec, state="running", revision=1)

    def status(self, spec):
        current = self._state.get(spec["task_id"])
        if current is None:
            raise TransportUnavailable("fixture outcome unavailable")
        if current["state"] == "running" and self.mode == "unknown":
            raise TransportUnavailable("fixture outcome unknown")
        if current["state"] == "running" and self.mode == "complete":
            if self.journal.should_cancel(spec, current["approval"], self.credential,
                                          enrollment=ENROLLMENT):
                current.update(state="cancelled", revision=2, cancel_requested=True)
                return _observation(spec, state="cancelled", revision=2,
                                    cancel_requested=True)
            self._publish(spec, current["approval"])
            current.update(state="completed", revision=2)
        if current["state"] == "running" and self.mode == "cancel_pending":
            return _observation(spec, state="running", revision=current["revision"],
                                cancel_requested=True)
        return _observation(spec, state=current["state"], revision=current["revision"],
                            result=current.get("result"),
                            cancel_requested=current.get("cancel_requested", False))

    def cancel(self, spec):
        self.cancel_count += 1
        current = self._state[spec["task_id"]]
        current.update(revision=current["revision"] + 1, cancel_requested=True)
        if self.cancel_count == 1:
            self.mode = "cancel_pending"
            return _observation(spec, state="running", revision=current["revision"],
                                cancel_requested=True)
        current.update(state="cancelled")
        return _observation(spec, state="cancelled", revision=current["revision"],
                            cancel_requested=True)

    def result(self, spec):
        return self.status(spec)

    def _publish(self, spec, approval):
        self.journal.authorize_publication(spec, approval, self.credential,
                                           enrollment=ENROLLMENT)
        report = expected_report(spec)
        raw = json.dumps(report, sort_keys=True, separators=(",", ":"))
        target = self.exports / spec["task_id"]
        target.mkdir(parents=True, exist_ok=True)
        (target / spec["task"]["artifact"]).write_text(raw, encoding="utf-8")
        self._state[spec["task_id"]]["result"] = {
            "artifact": spec["task"]["artifact"],
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        }


@pytest.fixture
def setup(tmp_path):
    credential = contract.Credential("fixture-supervisor", "fixture-runtime",
                                     "fixture-key", b"f" * 32,
                                     time.time() + 300, ("analyze_records",))
    state = (tmp_path / "operator-state").resolve()
    control = OperatorControl(state, initialize=True)
    review = build_enrollment_review(ENROLLMENT, current=CURRENT_ENROLLMENT,
                                     observed_probe_sha256=ENROLLMENT["probe_sha256"])
    control.apply(_request("enroll", {"review": review, "expires_at": time.time() + 240}, 0))
    journal = ApprovalJournal(control)
    exports = tmp_path / "exports"
    exports.mkdir()

    def supervisor(transport=None):
        transport = transport or FixtureAnalysisTransport(
            "fixture-analysis-v1", credential, journal, exports)
        return ExternalSupervisor(journal, transport, owner_id=SCOPE["owner_id"],
                                  source_id=SCOPE["source_id"],
                                  conversation_id=SCOPE["conversation_id"],
                                  verifier=AnalysisVerifier(exports))

    def approve(spec, *, apply=True):
        reviewed_at = time.time()
        task_review = build_task_review(spec, review, now=reviewed_at)
        if not apply:
            return task_review
        control.apply(_request("approve_task", {
            "spec": spec, "enrollment_revision": 1,
            "task_review_id": task_review["review_id"],
            "reviewed_at": reviewed_at,
            "expires_at": min(spec["authority"]["expires_at"], time.time() + 180),
        }, 0))

    def revoke(spec):
        current = control.status(SCOPE, task_id=spec["task_id"])
        return control.apply(_request("revoke_task", {"task_id": spec["task_id"]},
                                       current["revision"]))

    return control, journal, credential, exports, supervisor, approve, revoke, state


def test_fictional_analysis_has_separate_submit_ack_completion_and_verification(setup):
    control, journal, credential, exports, make_supervisor, approve, _, state = setup
    spec = _spec()
    review = approve(spec, apply=False)
    assert review["status"] == "review_required"  # Proposed review packet.
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal, exports)
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    awaiting = journal.preview_admission(spec, credential)
    # The proposed review is Awaiting until current task approval is recorded.
    assert awaiting["task_approval_status"] == "missing"
    assert awaiting["task_approval_current"] is False
    approve(spec)
    admitted = journal.preview_admission(spec, credential)
    assert admitted["task_approval_status"] == "approved"
    assert admitted["task_approval_current"] is True

    acknowledged = supervisor.submit(spec["task_id"])
    assert acknowledged["transport_status"] == "acknowledged"
    assert acknowledged["execution_status"] == "running"
    assert acknowledged["session_id"] == "fixture-session-stable"
    assert acknowledged["verified"] is False

    completed = supervisor.status(spec["task_id"])
    assert completed["execution_status"] == "completed"
    assert completed["verified"] is False
    assert (exports / spec["task_id"] / "report.json").exists()
    verified = supervisor.verify(spec["task_id"])
    assert verified["acceptance_status"] == "passed"
    assert verified["external_state_status"] == "confirmed"
    assert verified["verified"] is True

    # Reopen the host journal and supervisor. Keep the fixture transport alive;
    # adapter-process recovery is covered by the existing native fixture tests.
    restarted_control = OperatorControl(state)
    restarted_journal = ApprovalJournal(restarted_control)
    reconstructed = ExternalSupervisor(
        restarted_journal, transport, owner_id=SCOPE["owner_id"],
        source_id=SCOPE["source_id"], conversation_id=SCOPE["conversation_id"],
        verifier=AnalysisVerifier(exports))
    persisted = reconstructed.result(spec["task_id"])
    assert persisted["session_id"] == "fixture-session-stable"
    assert persisted["execution_status"] == "completed"
    assert reconstructed.verify(spec["task_id"])["verified"] is True
    assert transport.submit_calls == 1
    assert control.status(SCOPE, task_id=spec["task_id"])["approval_status"] == "approved"


@pytest.mark.parametrize("decision", ["missing", "revoked"])
def test_missing_or_revoked_decision_blocks_native_submission(setup, decision):
    control, journal, credential, exports, make_supervisor, approve, revoke, _ = setup
    spec = _spec()
    if decision == "revoked":
        approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal, exports)
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    if decision == "revoked":
        revoke(spec)
    with pytest.raises(contract.ProtocolError, match="approval"):
        supervisor.submit(spec["task_id"])
    assert transport.submit_calls == 0
    assert not journal.get(spec["task_id"])["submission_started"]


def test_revocation_after_submit_fences_local_export(setup):
    control, journal, credential, exports, make_supervisor, approve, revoke, _ = setup
    spec = _spec()
    approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal, exports)
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    assert supervisor.submit(spec["task_id"])["execution_status"] == "running"

    revoke(spec)
    fenced = supervisor.status(spec["task_id"])
    assert fenced["execution_status"] == "cancelled"
    assert fenced["termination_confirmed"]
    assert not (exports / spec["task_id"] / "report.json").exists()


@pytest.mark.parametrize("mode,status", [("reject", "rejected"),
                                          ("invalid_credential", "rejected"),
                                          ("lost_ack", "uncertain")])
def test_submission_failure_and_lost_ack_never_retry(setup, mode, status):
    _, journal, credential, exports, make_supervisor, approve, _, _ = setup
    spec = _spec()
    approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal,
                                         exports, mode=mode)
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    first = supervisor.submit(spec["task_id"])
    assert first["transport_status"] == status
    assert supervisor.submit(spec["task_id"]) == first
    assert transport.submit_calls == 1
    assert journal.get(spec["task_id"])["submission_started"]


@pytest.mark.parametrize("adapter_id", ["muse", "grok", ""])
def test_unselected_adapters_and_missing_credentials_fail_closed(setup, adapter_id):
    _, journal, credential, exports, _, _, _, _ = setup
    with pytest.raises(contract.ProtocolError, match="Unsupported fixture adapter"):
        FixtureAnalysisTransport(adapter_id, credential, journal, exports)
    with pytest.raises(contract.ProtocolError, match="credential required"):
        FixtureAnalysisTransport("fixture-analysis-v1", None, journal, exports)


def test_unknown_result_reconcile_and_reconstructed_supervisor_do_not_resubmit(setup):
    _, journal, credential, exports, make_supervisor, approve, _, _ = setup
    spec = _spec()
    approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal,
                                         exports, mode="unknown")
    first = make_supervisor(transport)
    first.prepare(spec)
    assert first.submit(spec["task_id"])["execution_status"] == "unknown"
    assert first.result(spec["task_id"])["execution_status"] == "unknown"

    resumed = make_supervisor(transport)
    resumed.reconcile()
    assert resumed.submit(spec["task_id"])["execution_status"] == "unknown"
    assert transport.submit_calls == 1
    assert not (exports / spec["task_id"] / "report.json").exists()


def test_concurrent_duplicate_submit_is_one_shot(setup):
    _, journal, credential, exports, make_supervisor, approve, _, _ = setup
    spec = _spec()
    approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal,
                                         exports, mode="block")
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(supervisor.submit, spec["task_id"])
        assert transport.entered.wait(2)
        duplicate = pool.submit(supervisor.submit, spec["task_id"])
        transport.release.set()
        first_result, duplicate_result = first.result(timeout=3), duplicate.result(timeout=3)
    assert transport.submit_calls == 1
    assert {first_result["session_id"], duplicate_result["session_id"]} <= {
        None, "fixture-session-stable"}
    observed = supervisor.status(spec["task_id"])
    assert observed["session_id"] == "fixture-session-stable"
    assert observed["transport_status"] == "acknowledged"
    assert observed["cancel_requested"] is False


def test_cancel_request_is_not_confirmed_until_runtime_confirms(setup):
    _, journal, credential, exports, make_supervisor, approve, _, _ = setup
    spec = _spec()
    approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal, exports)
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    supervisor.submit(spec["task_id"])

    requested = supervisor.cancel(spec["task_id"])
    assert requested["cancel_requested"] is True
    assert requested["transport_status"] == "acknowledged"
    assert requested["termination_confirmed"] is False
    assert requested["execution_status"] == "running"
    confirmed = supervisor.cancel(spec["task_id"])
    assert confirmed["execution_status"] == "cancelled"
    assert confirmed["termination_confirmed"] is True
    assert confirmed["transport_status"] == "acknowledged"
    assert supervisor.status(spec["task_id"])["transport_status"] == "acknowledged"


def test_independent_verifier_rejects_fabricated_completion(setup):
    _, journal, credential, exports, make_supervisor, approve, _, _ = setup
    spec = _spec()
    approve(spec)
    transport = FixtureAnalysisTransport("fixture-analysis-v1", credential, journal,
                                         exports, mode="unknown")
    supervisor = make_supervisor(transport)
    supervisor.prepare(spec)
    supervisor.submit(spec["task_id"])
    fabricated = _observation(spec, state="completed", revision=2, result={
        "artifact": "report.json", "sha256": "a" * 64,
    })
    target = exports / spec["task_id"]
    target.mkdir(parents=True, exist_ok=True)
    (target / "report.json").write_text('{"fabricated":true}', encoding="utf-8")
    fabricated["result"]["sha256"] = hashlib.sha256(
        (target / "report.json").read_bytes()).hexdigest()
    row = journal.get(spec["task_id"])
    report = AnalysisVerifier(exports).verify({"spec": spec, "observation": fabricated})
    assert report["acceptance"]["status"] == "failed"
    assert report["external_state"]["status"] == "failed"
    assert row["observation"] is None
