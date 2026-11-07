import hashlib

import pytest

from agent.recovery.store import TaskStore


def _hash(store, contract):
    return hashlib.sha256(store._json(contract).encode('utf-8')).hexdigest()


def _report(status='passed'):
    return {'verifier': 'native-file-verifier-v1', 'checked_at': '2026-11-07T00:00:00Z',
            'acceptance': {'status': status, 'checks': []},
            'external_state': {'status': 'unverified', 'checks': []}}


def test_report_history_and_preserves_execution(tmp_path):
    path = tmp_path / 'tasks.db'
    store = TaskStore(path)
    contract = {'acceptance': [{'id': 'check'}], 'external_state': []}
    task_id = store.submit('a', 's', 'task', {'verification': contract})['task_id']
    claim = store.claim(task_id)
    assert store.finish(claim, 'completed', result={'summary': 'worker result'})
    assert store.get(task_id)['verification'] is None
    assert store.record_verification(task_id, claim.attempt_id, _hash(store, contract), _report())
    assert store.record_verification(task_id, claim.attempt_id, _hash(store, contract), _report('failed'))
    claim.close()
    reopened = TaskStore(path).get(task_id)
    assert reopened['state'] == 'completed'
    assert reopened['result'] == {'summary': 'worker result'}
    assert reopened['attempt_count'] == 1
    assert reopened['verification']['acceptance']['status'] == 'failed'
    records = reopened['attempts'][0]['verifications']
    assert [r['acceptance']['status'] for r in records] == ['passed', 'failed']
    assert records[0]['verification_id'] != records[1]['verification_id']
    assert records[0]['observed_at'] == '2026-11-07T00:00:00Z'
    assert records[0]['recorded_at']


def test_fences_and_report_validation(tmp_path):
    store = TaskStore(tmp_path / 'tasks.db')
    task_id = store.submit('a', 's', 'task', {})['task_id']
    old = store.claim(task_id)
    assert not store.record_verification(task_id, old.attempt_id, _hash(store, {}), _report())
    assert store.finish(old, 'failed')
    old.close()
    store.retry(task_id)
    current = store.claim(task_id)
    assert store.finish(current, 'completed', result='done')
    assert not store.record_verification(task_id, old.attempt_id, _hash(store, {}), _report())
    assert not store.record_verification(task_id, current.attempt_id, 'wrong', _report())
    with pytest.raises(ValueError):
        store.record_verification(task_id, current.attempt_id, _hash(store, {}), _report('confirmed'))
    with pytest.raises(ValueError):
        store.record_verification(task_id, current.attempt_id, _hash(store, {}), {'acceptance': {}})
    assert store.record_verification(task_id, current.attempt_id, _hash(store, {}), _report())
    current.close()
    task = store.get(task_id)
    assert task['attempts'][0]['verifications'] == []
    assert task['verification']['attempt_id'] == current.attempt_id


def test_verification_lock_and_unverified_query(tmp_path):
    store = TaskStore(tmp_path / 'tasks.db')
    task_id = store.submit('a', 's', 'task', {})['task_id']
    with pytest.raises(ValueError):
        with store.verification_lock(task_id):
            pass
    claim = store.claim(task_id)
    assert store.finish(claim, 'completed', result='done')
    with store.verification_lock(task_id) as locked:
        assert locked is None
    assert [t['task_id'] for t in store.list_unverified_completed()] == [task_id]
    claim.close()
    with store.verification_lock(task_id) as locked:
        assert locked['task_id'] == task_id
        with store.verification_lock(task_id) as busy:
            assert busy is None
        assert store.record_verification(task_id, locked['attempt_id'], _hash(store, {}), _report())
    assert store.list_unverified_completed() == []
