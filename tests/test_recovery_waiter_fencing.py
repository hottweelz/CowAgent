import sqlite3
import threading

from agent.recovery.runtime import execute_task
from agent.recovery.store import TaskStore


def test_cancelled_waiter_cannot_stop_replacement_attempt(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'tasks.db')
    task_id = store.submit('owner', 'session', 'subagent', {'timeout_seconds': 10})['task_id']
    original_claim = store.claim(task_id)
    cancel = threading.Event()
    cancel.set()
    original_stop = store.request_stop
    replacement = []

    def stop_then_retry(*args, **kwargs):
        result = original_stop(*args, **kwargs)
        original_claim.close()
        store.retry(task_id)
        replacement.append(store.claim(task_id))
        return result

    monkeypatch.setattr(store, 'request_stop', stop_then_retry)
    result = execute_task(store, task_id, cancel_event=cancel)
    assert result['status'] == result['execution_status'] == 'cancelled'
    assert result['acceptance_status'] == result['external_state_status'] == 'unverified'
    assert result['verified'] is False
    assert result['attempt_id'] == original_claim.attempt_id
    row = store.get(task_id)
    assert row['state'] == 'running' and row['attempt_id'] == replacement[0].attempt_id
    replacement[0].close()


def test_queued_retry_generation_fences_old_waiter(tmp_path):
    store = TaskStore(tmp_path / 'tasks.db')
    task_id = store.submit('owner', 'session', 'subagent', {})['task_id']
    generation = store.get(task_id)['generation']
    assert store.request_stop(task_id, expected_generation=generation, expected_state='queued')
    store.retry(task_id)
    assert store.claim(task_id, expected_generation=generation) is None
    assert not store.request_stop(task_id, expected_generation=generation, expected_state='queued')
    assert store.get(task_id)['state'] == 'queued'


def test_existing_journal_adds_generation(tmp_path):
    path = tmp_path / 'old.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE recovery_tasks (task_id TEXT PRIMARY KEY, owner_id TEXT, session_id TEXT, '
                   'kind TEXT, spec TEXT, idempotency_key TEXT, state TEXT, attempt_id TEXT, '
                   'attempt_count INTEGER, result TEXT, error TEXT, reason TEXT, created_at TEXT, updated_at TEXT)')
        db.execute("INSERT INTO recovery_tasks(task_id,owner_id,session_id,kind,spec,state,attempt_count,error,reason) "
                   "VALUES ('legacy','owner','session','subagent','{}','queued',0,'','')")
    store = TaskStore(path)
    with store._connect() as db:
        row = db.execute("SELECT task_id, state, generation FROM recovery_tasks WHERE task_id='legacy'").fetchone()
        assert tuple(row) == ('legacy', 'queued', 0)


def test_completion_wins_waiter_stop_cas(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'tasks.db')
    task_id = store.submit('owner', 'session', 'subagent', {'timeout_seconds': 10})['task_id']
    claim = store.claim(task_id)
    cancel = threading.Event()
    cancel.set()
    original_stop = store.request_stop

    def finish_before_stop(*args, **kwargs):
        assert store.finish(claim, 'completed', result={'summary': 'finished'})
        claim.close()
        return original_stop(*args, **kwargs)

    monkeypatch.setattr(store, 'request_stop', finish_before_stop)
    result = execute_task(store, task_id, cancel_event=cancel)
    assert result['status'] == result['execution_status'] == 'completed'
    assert result['summary'] == 'finished'
    assert result['acceptance_status'] == result['external_state_status'] == 'unverified'
    assert result['verified'] is False
