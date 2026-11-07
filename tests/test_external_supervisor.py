"""Actual isolated transport, host journal and independent external observations."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid

import pytest

from agent.external import contract
from agent.external.journal import ExternalJournal
from agent.external.supervisor import ExternalSupervisor
from agent.external.transport import ExternalTransport
from agent.external.verification import ExternalVerifier
from agent.recovery.store import TaskStore
from tests.test_external_runtime import fixture as runtime_fixture, wait_for

fixture = runtime_fixture


def host(fixture, verifier=True):
    root, _, _, _, transport = fixture
    journal = ExternalJournal(TaskStore(root.parent / 'host-journal/tasks.db'))
    observer = ExternalVerifier(root / 'exports', synthetic_effect_db=root / 'effects.db') if verifier else None
    return ExternalSupervisor(journal, transport, owner_id='owner', source_id='source',
                              conversation_id='conversation', verifier=observer)


def checked_spec(fixture, operation='record_effect'):
    spec = fixture[3](operation)
    spec['verification'] = {
        'acceptance': [{'id': 'output', 'type': 'text_equals', 'path': 'output.txt', 'expected': 'fictional'}],
        'external_state': ([{'id': 'effect', 'type': 'synthetic_effect', 'expected': 'fictional'}]
                           if operation == 'record_effect' else
                           [{'id': 'saved', 'type': 'text_equals', 'path': 'output.txt', 'expected': 'fictional'}]),
    }
    return spec


def completed(supervisor, spec):
    return wait_for(lambda: (value if value['execution_status'] == 'completed' else None)
                    if (value := supervisor.status(spec['task_id'])) else None)


def count_effects(root):
    with sqlite3.connect(root / 'effects.db') as db:
        return db.execute('SELECT count(*) FROM effects').fetchone()[0]


def test_delegation_preserves_ownership_and_requires_independent_evidence(fixture):
    root, start, _, _, _ = fixture
    process = start()
    private = root / 'private-memory.txt'; private.write_text('PRIVATE_RUNTIME_MEMORY')
    configuration = (root.parent / 'config.json').read_bytes()
    supervisor = host(fixture)
    discovery = supervisor.discover()
    assert discovery['model'] == 'fake-model' and discovery['session_ownership'] == 'runtime'
    spec = checked_spec(fixture)
    supervisor.prepare(spec)
    with pytest.raises(contract.ProtocolError, match='approval'):
        supervisor.submit(spec['task_id'])
    supervisor.approve(spec['task_id'], approved_by='operator', expires_at=time.time() + 120)
    supervisor.submit(spec['task_id'])
    done = completed(supervisor, spec)
    assert done['transport_status'] == 'acknowledged' and not done['verified']
    assert done['acceptance_status'] == done['external_state_status'] == 'unverified'
    session = done['session_id']; assert session != 'conversation'
    retrieved = supervisor.result(spec['task_id'])
    assert retrieved['execution_status'] == 'completed'
    assert retrieved['runtime_result']['artifact'] == 'output.txt'
    assert retrieved['result_provenance'] == 'authenticated_runtime_claim'
    assert supervisor.verify(spec['task_id'])['verified']
    process.kill(); process.wait(timeout=5); start()
    restored = host(fixture)
    rows = restored.reconcile()
    assert rows[0]['session_id'] == session and rows[0]['verified']
    assert count_effects(root) == 1
    assert private.read_text() == 'PRIVATE_RUNTIME_MEMORY'
    assert (root.parent / 'config.json').read_bytes() == configuration
    with restored.journal.store._connect() as db:
        assert db.execute('SELECT count(*) FROM recovery_tasks').fetchone()[0] == 0
        persisted = str([tuple(r) for r in db.execute('SELECT spec,observation FROM external_tasks')])
        assert 'PRIVATE_RUNTIME_MEMORY' not in persisted and 'ab' * 32 not in persisted
        assert db.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        assert db.execute('PRAGMA synchronous').fetchone()[0] == 2
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    from agent.recovery.service import RecoveryService
    native_service = RecoveryService(object(), restored.journal.store)
    try:
        native_service.scan_once()
        assert native_service._futures == {}
    finally:
        native_service.close(wait=True)


def test_prepare_queries_do_not_poison_submission_and_unsent_cancel_prevents_it(fixture):
    root, start, _, _, _ = fixture; start()
    supervisor = host(fixture)
    spec = checked_spec(fixture, 'write_artifact')
    supervisor.prepare(spec)
    assert supervisor.status(spec['task_id'])['transport_status'] == 'not_sent'
    assert supervisor.result(spec['task_id'])['execution_status'] == 'unknown'
    supervisor.submit(spec['task_id']); completed(supervisor, spec)
    other = checked_spec(fixture, 'write_artifact'); supervisor.prepare(other)
    stopped = supervisor.cancel(other['task_id'])
    assert stopped['execution_status'] == 'cancelled_before_submission' and stopped['termination_confirmed']
    assert supervisor.submit(other['task_id']) == stopped
    assert not (root / 'exports' / other['task_id']).exists()


def test_concurrent_host_requests_and_conflicting_duplicate(fixture):
    root, start, _, _, _ = fixture; start()
    supervisor = host(fixture)
    specs = [checked_spec(fixture, 'write_artifact') for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(supervisor.delegate, specs + [specs[0]] * 4))
    for spec in specs:
        completed(supervisor, spec)
        assert supervisor.verify(spec['task_id'])['verified']
    assert len(list((root / 'exports').iterdir())) == 4
    changed = json.loads(json.dumps(specs[0])); changed['task']['content'] = 'changed'
    with pytest.raises(contract.ProtocolError, match='conflicts'):
        supervisor.delegate(changed)
    with supervisor.journal.store._connect() as db:
        assert db.execute("SELECT count(*) FROM external_events WHERE kind='submit_intent'").fetchone()[0] == 4


def test_cancel_request_is_not_termination_and_disconnect_is_not_death(fixture):
    root, start, _, _, _ = fixture; process = start('before_intent')
    supervisor = host(fixture); spec = checked_spec(fixture, 'write_artifact')
    supervisor.delegate(spec); wait_for(lambda: (root / 'reached').exists())
    requested = supervisor.cancel(spec['task_id'])
    assert requested['cancel_requested'] and not requested['termination_confirmed']
    assert requested['execution_status'] == 'running'
    (root / 'release').touch()
    stopped = wait_for(lambda: (v if v['termination_confirmed'] else None)
                       if (v := supervisor.status(spec['task_id'])) else None)
    assert stopped['execution_status'] == 'cancelled'
    assert not (root / 'exports' / spec['task_id']).exists()
    process.kill(); process.wait(timeout=5)
    unreachable = supervisor.status(spec['task_id'])
    assert unreachable['transport_status'] == 'unreachable' and not unreachable['observation_current']
    assert unreachable['execution_status'] == 'cancelled'  # retained prior confirmed observation


@pytest.mark.parametrize('boundary', ['before_intent', 'after_intent', 'after_effect', 'after_completion'])
def test_runtime_process_restarts_preserve_effect_boundaries(fixture, boundary):
    root, start, _, _, _ = fixture; process = start(boundary)
    supervisor = host(fixture); spec = checked_spec(fixture)
    supervisor.prepare(spec); supervisor.approve(spec['task_id'], approved_by='operator', expires_at=time.time() + 120)
    supervisor.submit(spec['task_id']); wait_for(lambda: (root / 'reached').exists())
    process.kill(); process.wait(timeout=5)
    offline = supervisor.status(spec['task_id'])
    assert offline['transport_status'] == 'unreachable'
    start(); supervisor.reconcile()
    expected = 'completed' if boundary in ('before_intent', 'after_completion') else 'needs_review'
    result = wait_for(lambda: (v if v['execution_status'] == expected else None)
                      if (v := supervisor.status(spec['task_id'])) else None)
    assert result['termination_confirmed']
    assert count_effects(root) == (0 if boundary == 'after_intent' else 1)
    if expected == 'completed': assert supervisor.verify(spec['task_id'])['verified']
    else:
        with pytest.raises(contract.ProtocolError): supervisor.verify(spec['task_id'])
    supervisor.submit(spec['task_id']); supervisor.reconcile()
    assert count_effects(root) == (0 if boundary == 'after_intent' else 1)


@pytest.mark.parametrize('boundary', ['before_send', 'after_send'])
def test_supervisor_process_death_never_resubmits_uncertain_request(fixture, boundary):
    root, start, _, _, transport = fixture; start()
    spec = checked_spec(fixture)
    (root.parent / 'host-spec.json').write_text(json.dumps(spec))
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR')}
    command = [sys.executable, str(Path(__file__).with_name('external_supervisor_fixture.py')),
               str(root.parent), str(transport.socket_path), boundary]
    child = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        wait_for(lambda: (root.parent / 'host-reached').exists())
        child.kill(); child.wait(timeout=5)
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=5)
        child.stderr.close()
    supervisor = host(fixture)
    assert supervisor.journal.get(spec['task_id'])['submission_started']
    supervisor.reconcile(); supervisor.submit(spec['task_id'])
    if boundary == 'after_send':
        completed(supervisor, spec)
        assert supervisor.verify(spec['task_id'])['verified'] and count_effects(root) == 1
    else:
        assert supervisor.status(spec['task_id'])['execution_status'] == 'unknown'
        assert count_effects(root) == 0
    with supervisor.journal.store._connect() as db:
        assert db.execute("SELECT count(*) FROM external_events WHERE kind='submit_intent'").fetchone()[0] == 1


def test_stale_identity_and_verification_failure_never_trigger_execution(fixture):
    root, start, _, _, _ = fixture; start()
    supervisor = host(fixture); spec = checked_spec(fixture, 'write_artifact')
    supervisor.delegate(spec); completed(supervisor, spec)
    row = supervisor.journal.get(spec['task_id']); original = row['observation']
    for field, value in [('revision', original['revision'] - 1), ('session_id', str(uuid.uuid4())),
                         ('task_id', str(uuid.uuid4())), ('runtime_id', 'wrong')]:
        with pytest.raises(contract.ProtocolError):
            supervisor.journal.observe(spec['task_id'], dict(original, **{field: value}))
    assert supervisor.verify(spec['task_id'])['verified']
    artifact = root / 'exports' / spec['task_id'] / 'output.txt'; artifact.write_text('incorrect')
    failed = supervisor.verify(spec['task_id'])
    assert failed['execution_status'] == 'completed' and failed['acceptance_status'] == 'failed' and not failed['verified']
    artifact.unlink()
    assert supervisor.verify(spec['task_id'])['external_state_status'] == 'failed'
    supervisor.reconcile(); supervisor.submit(spec['task_id'])
    assert not artifact.exists()


def test_enrollment_scope_expiry_and_unsupported_verification(fixture):
    root, start, call, _, transport = fixture; start()
    supervisor = host(fixture); spec = checked_spec(fixture)
    supervisor.prepare(spec)
    assert call('submit', {'spec': spec, 'approval': None})['error'] == 'unauthorized'
    with pytest.raises(contract.ProtocolError): supervisor.approve(spec['task_id'], approved_by='operator', expires_at=time.time() - 1)
    supervisor.transport = ExternalTransport(transport.socket_path, replace(transport.credential, expires_at=time.time() - 1))
    with pytest.raises(contract.ProtocolError): supervisor.submit(spec['task_id'])
    assert not supervisor.journal.get(spec['task_id'])['submission_started']
    supervisor.transport = transport
    foreign = ExternalSupervisor(supervisor.journal, transport, owner_id='different', source_id='source', conversation_id='conversation')
    with pytest.raises(contract.ProtocolError): foreign.status(spec['task_id'])
    spec = checked_spec(fixture, 'write_artifact')
    spec['verification']['external_state'] = [{'id': 'remote', 'type': 'delivery_confirmation'}]
    supervisor.delegate(spec); completed(supervisor, spec)
    result = supervisor.verify(spec['task_id'])
    assert result['acceptance_status'] == 'passed' and result['external_state_status'] == 'unverified' and not result['verified']
    assert count_effects(root) == 0


@pytest.mark.parametrize('expiry_kind', ['grant', 'approval'])
def test_permission_expiry_while_queued_prevents_effect(fixture, expiry_kind):
    root, start, _, _, _ = fixture; start('before_intent')
    supervisor = host(fixture); spec = checked_spec(fixture)
    expiry = time.time() + .3
    if expiry_kind == 'grant': spec['authority']['expires_at'] = expiry
    supervisor.prepare(spec)
    supervisor.approve(spec['task_id'], approved_by='operator', expires_at=expiry)
    supervisor.submit(spec['task_id']); wait_for(lambda: (root / 'reached').exists())
    wait_for(lambda: time.time() > expiry)
    (root / 'release').touch()
    failed = wait_for(lambda: (v if v['execution_status'] == 'failed' else None)
                      if (v := supervisor.status(spec['task_id'])) else None)
    assert failed['termination_confirmed'] and not failed['verified']
    assert count_effects(root) == 0 and not (root / 'exports' / spec['task_id']).exists()
