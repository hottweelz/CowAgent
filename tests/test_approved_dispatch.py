"""Shared SQLite admission and operator revocation tests."""
import copy
import threading

import pytest

from agent.external.approved_dispatch import ApprovalJournal
from agent.external.contract import Credential, ProtocolError
from agent.external.operator_control import OperatorControl
from tests.test_external_operator_control import SCOPE, approve_task, command, enroll, enrollment_review, make_spec


@pytest.fixture
def setup_gate(tmp_path, monkeypatch):
    monkeypatch.setattr('agent.external.approved_dispatch.time.time', lambda: 115.0)
    control = OperatorControl((tmp_path / 'state').resolve(), initialize=True)
    journal = ApprovalJournal(control)
    spec = make_spec()
    enroll(control)
    approve_task(control, spec)
    credential = Credential(SCOPE['supervisor_id'], SCOPE['runtime_id'], 'key', b'x' * 32,
                            expires_at=500, operations=('analyze_records',))
    journal.create(credential.supervisor_id, spec)
    return control, journal, spec, credential, enrollment_review()['enrollment']


def test_binding_intents_and_forged_receipts(setup_gate):
    _, journal, spec, cred, enrollment = setup_gate
    receipt = journal.begin_submit(spec['task_id'], cred)['approval']
    journal.validate_submission(spec, receipt, cred, enrollment=enrollment)
    for bad in (None, {'approved_by': 'operator'}, dict(receipt, task_revision=99)):
        with pytest.raises(ProtocolError):
            journal.validate_submission(spec, bad, cred, enrollment=enrollment)
    with pytest.raises(ProtocolError):
        journal.validate_submission(spec, receipt, cred, enrollment=None)
    with pytest.raises(ProtocolError):
        journal.authorize_publication(spec, receipt, cred, enrollment=enrollment)
    journal.authorize_native(spec, receipt, cred, enrollment=enrollment, native_thread='thread', native_session='session')
    with pytest.raises(ProtocolError):
        journal.authorize_native(spec, receipt, cred, enrollment=enrollment, native_thread='thread', native_session='session')
    journal.authorize_publication(spec, receipt, cred, enrollment=enrollment)
    with pytest.raises(ProtocolError):
        journal.authorize_publication(spec, receipt, cred, enrollment=enrollment)
    with pytest.raises(ProtocolError):
        journal.begin_submit(spec['task_id'], cred)


def test_revocation_fences_native_and_publication_in_same_commit(setup_gate):
    control, journal, spec, cred, enrollment = setup_gate
    receipt = journal.begin_submit(spec['task_id'], cred)['approval']
    journal.authorize_native(spec, receipt, cred, enrollment=enrollment, native_thread='thread', native_session='session')
    control.apply(command('revoke_task', payload={'task_id': spec['task_id']}, expected_revision=1), now=120)
    with control._connect() as db:
        assert db.execute('SELECT cancel_requested FROM external_tasks').fetchone()[0] == 1
        assert db.execute('SELECT cancel_status FROM external_approval_bindings').fetchone()[0] == 'pending'
        assert db.execute('SELECT count(*) FROM operator_decisions').fetchone()[0] == 3
    with pytest.raises(ProtocolError):
        journal.authorize_publication(spec, receipt, cred, enrollment=enrollment)
    assert journal.should_cancel(spec, receipt, cred, enrollment=enrollment)
    assert journal.claim_cancel(spec['task_id'])
    assert not journal.claim_cancel(spec['task_id'])
    assert journal.get(spec['task_id'])['observation'] is None


def test_revocation_first_blocks_native_and_reenrollment_fences(setup_gate):
    control, journal, spec, cred, enrollment = setup_gate
    receipt = journal.begin_submit(spec['task_id'], cred)['approval']
    enroll(control, now=120, expected_revision=1)
    with pytest.raises(ProtocolError):
        journal.authorize_native(spec, receipt, cred, enrollment=enrollment, native_thread='thread', native_session='session')
    assert journal.get(spec['task_id'])['cancel_requested']


def test_concurrent_submit_has_one_intent(setup_gate):
    _, journal, spec, cred, _ = setup_gate
    barrier = threading.Barrier(3)
    results = []
    def submit():
        barrier.wait()
        try:
            journal.begin_submit(spec['task_id'], cred)
            results.append('accepted')
        except ProtocolError:
            results.append('rejected')
    threads = [threading.Thread(target=submit) for _ in range(2)]
    for thread in threads: thread.start()
    barrier.wait()
    for thread in threads: thread.join()
    assert sorted(results) == ['accepted', 'rejected']
    with journal.control._connect() as db:
        assert db.execute("SELECT count(*) FROM external_events WHERE kind='submit_intent'").fetchone()[0] == 1


def test_expiry_and_config_mismatch_fence(setup_gate, monkeypatch):
    _, journal, spec, cred, enrollment = setup_gate
    receipt = journal.begin_submit(spec['task_id'], cred)['approval']
    mismatch = copy.deepcopy(enrollment)
    mismatch['config_sha256'] = '9' * 64
    assert journal.should_cancel(spec, receipt, cred, enrollment=mismatch)
    assert journal.get(spec['task_id'])['cancel_requested']
    monkeypatch.setattr('agent.external.approved_dispatch.time.time', lambda: 301.0)
    with pytest.raises(ProtocolError):
        journal.authorize_native(spec, receipt, cred, enrollment=enrollment, native_thread='thread', native_session='session')


def test_expiry_sampled_after_actual_writer_lock_wait(setup_gate, monkeypatch):
    from contextlib import contextmanager
    control, journal, spec, cred, _ = setup_gate
    entered = threading.Event()
    clock = [115.0]
    monkeypatch.setattr('agent.external.approved_dispatch.time.time', lambda: clock[0])
    original = control._connect
    @contextmanager
    def traced_connect():
        with original() as db:
            db.set_trace_callback(lambda statement: entered.set() if statement == 'BEGIN IMMEDIATE' else None)
            yield db
    results = []
    def submit():
        try:
            journal.begin_submit(spec['task_id'], cred)
            results.append('accepted')
        except ProtocolError as exc:
            results.append(str(exc))
    with original() as blocker:
        blocker.execute('BEGIN IMMEDIATE')
        monkeypatch.setattr(control, '_connect', traced_connect)
        thread = threading.Thread(target=submit)
        thread.start()
        assert entered.wait(5), 'submission did not reach SQLite writer lock'
        clock[0] = 301.0
    thread.join(5)
    assert not thread.is_alive()
    assert results == ['Current task and enrollment approval required']
    with original() as db:
        assert db.execute('SELECT count(*) FROM external_approval_bindings').fetchone()[0] == 0
        assert db.execute('SELECT submission_started FROM external_tasks').fetchone()[0] == 0


def test_pending_cancel_is_sent_once_until_explicit_retry(setup_gate):
    from agent.external.supervisor import ExternalSupervisor
    from agent.external.transport import TransportUnavailable
    control, journal, spec, cred, _ = setup_gate
    journal.begin_submit(spec['task_id'], cred)
    control.apply(command('revoke_task', payload={'task_id': spec['task_id']}, expected_revision=1), now=120)
    class Transport:
        credential = cred
        calls = 0
        def cancel(self, spec):
            self.calls += 1
            raise TransportUnavailable('lost')
    transport = Transport()
    supervisor = ExternalSupervisor(journal, transport, owner_id=SCOPE['owner_id'], source_id=SCOPE['source_id'], conversation_id=SCOPE['conversation_id'])
    assert len(supervisor.flush_pending_cancellations()) == 1
    assert supervisor.flush_pending_cancellations() == []
    assert transport.calls == 1
    outcome = supervisor.cancel(spec['task_id'])
    assert transport.calls == 2 and not outcome['termination_confirmed']


def test_revoked_before_submit_never_records_intent(setup_gate):
    control, journal, spec, cred, _ = setup_gate
    control.apply(command('revoke_task', payload={'task_id': spec['task_id']}, expected_revision=1), now=120)
    with pytest.raises(ProtocolError):
        journal.begin_submit(spec['task_id'], cred)
    assert not journal.get(spec['task_id'])['submission_started']


def test_legacy_journal_and_label_cannot_authorize_analysis(setup_gate, tmp_path):
    from agent.external.journal import ExternalJournal
    from agent.external.supervisor import ExternalSupervisor
    from agent.recovery.store import TaskStore
    _, approved, spec, cred, _ = setup_gate

    class Transport:
        credential = cred
        def submit(self, *args):
            raise AssertionError('An unguarded submit reached transport')

    legacy = ExternalJournal(TaskStore(tmp_path / 'legacy/tasks.db'))
    host = ExternalSupervisor(legacy, Transport(), owner_id=SCOPE['owner_id'],
                              source_id=SCOPE['source_id'], conversation_id=SCOPE['conversation_id'])
    with pytest.raises(ProtocolError, match='approval journal'):
        host.prepare(spec)
    legacy.create(cred.supervisor_id, spec)  # Simulate an old persisted analysis row.
    with pytest.raises(ProtocolError, match='approval journal'):
        host.submit(spec['task_id'])
    assert not legacy.get(spec['task_id'])['submission_started']
    gated = ExternalSupervisor(approved, Transport(), owner_id=SCOPE['owner_id'],
                               source_id=SCOPE['source_id'], conversation_id=SCOPE['conversation_id'])
    with pytest.raises(ProtocolError, match='operator decision'):
        gated.approve(spec['task_id'], approved_by='claimed-operator', expires_at=250)
