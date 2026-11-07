import multiprocessing
import os
import sqlite3

import pytest

from agent.recovery.store import LeaseLost, TaskStore


def _owned(path, task_id, conn, effect):
    store = TaskStore(path)
    claim = store.claim(task_id)
    if effect:
        store.before_tool(claim, 'write', mutating=True)
    conn.send(bool(claim))
    conn.recv()
    os._exit(0)


def test_submission_and_fenced_stop(tmp_path):
    store = TaskStore(tmp_path / 'tasks.db')
    task = store.submit('agent', 'session', 'subagent', {'input': 'test'}, idempotency_key='one')
    assert store.submit('agent', 'session', 'subagent', {'input': 'test'}, idempotency_key='one')['task_id'] == task['task_id']
    with pytest.raises(ValueError):
        store.submit('agent', 'session', 'subagent', {'input': 'other'}, idempotency_key='one')
    claim = store.claim(task['task_id'])
    assert store.request_stop(task['task_id'], 'timed_out')
    assert not store.finish(claim, 'completed', result='late')
    with pytest.raises(LeaseLost):
        store.before_tool(claim, 'late', mutating=True)
    with pytest.raises(RuntimeError):
        store.retry(task['task_id'])
    claim.close()
    stopped = store.get(task['task_id'])
    assert stopped['state'] == stopped['attempts'][0]['state'] == 'timed_out'
    assert store.retry(task['task_id'])['state'] == 'queued'
    newer = store.claim(task['task_id'])
    assert not store.finish(claim, 'failed')
    assert store.finish(newer, 'completed', result={'ok': True})
    newer.close()
    assert store.get(task['task_id'])['result'] == {'ok': True}
    with pytest.raises(ValueError):
        store.retry(task['task_id'])


@pytest.mark.parametrize('effect', [False, True])
def test_process_ownership_and_reconcile(tmp_path, effect):
    path = str(tmp_path / 'tasks.db')
    store = TaskStore(path)
    task_id = store.submit('a', 's', 'delegation', {})['task_id']
    parent, child = multiprocessing.Pipe()
    process = multiprocessing.Process(target=_owned, args=(path, task_id, child, effect))
    process.start()
    assert parent.recv()
    assert store.claim(task_id) is None
    assert store.reconcile() == []
    parent.send('exit')
    process.join(10)
    assert process.exitcode == 0
    assert store.reconcile() == [task_id]
    task = store.get(task_id)
    assert task['state'] == ('needs_review' if effect else 'queued')
    assert task['attempts'][0]['state'] == 'interrupted'
    if effect:
        assert task['attempts'][0]['effects'][0]['completed_at'] is None
        with pytest.raises(ValueError):
            store.retry(task_id)
        assert store.retry(task_id, acknowledge_effects=True)['state'] == 'queued'
    claim = store.claim(task_id)
    assert claim.task['attempt_count'] == 2
    claim.close()


def test_wal_integrity_and_other_tables(tmp_path):
    path = tmp_path / 'tasks.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE unrelated (value TEXT)')
        db.execute("INSERT INTO unrelated VALUES ('intact')")
    store = TaskStore(path)
    task = store.submit('a', 's', 'task', {})
    with store.claim(task['task_id']) as claim:
        eid = store.before_tool(claim, 'read', mutating=False, call_id='call')
        assert store.after_tool(claim, eid, {'value': 1})
        assert store.finish(claim, 'completed', 'done')
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT value FROM unrelated').fetchone()[0] == 'intact'
    assert store.get(task['task_id'])['attempts'][0]['effects'][0]['result'] == {'value': 1}


def _try_claim(path, task_id, conn):
    store = TaskStore(path)
    claim = store.claim(task_id)
    conn.send(bool(claim))
    if claim:
        claim.close()
    conn.close()


def test_delegate_target_is_locked_until_timed_out_process_exits(tmp_path):
    path = str(tmp_path / 'tasks.db')
    store = TaskStore(path)
    def submit(target, session):
        return store.submit('a', 's', 'delegate', {
            'target_agent_id': target, 'target_session_id': session,
        })['task_id']
    first = submit('target', 'session')
    second = submit('target', 'session')
    other_agent = submit('other', 'session')
    other_session = submit('target', 'other')
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_owned, args=(path, first, child, False))
    process.start()
    try:
        assert parent.poll(10) and parent.recv()
        assert store.request_stop(first, 'timed_out')
        probe, probe_child = ctx.Pipe()
        contender = ctx.Process(target=_try_claim, args=(path, second, probe_child))
        contender.start()
        assert probe.poll(10) and not probe.recv()
        contender.join(10)
        assert contender.exitcode == 0
        assert store.get(second)['state'] == 'queued'
        assert store.get(second)['attempt_count'] == 0
        for task_id in (other_agent, other_session):
            claim = store.claim(task_id)
            assert claim is not None
            claim.close()
    finally:
        parent.send('exit')
        process.join(10)
    assert process.exitcode == 0
    claim = store.claim(second)
    assert claim is not None
    claim.close()


def test_delegate_requires_resource_identity(tmp_path):
    store = TaskStore(tmp_path / 'tasks.db')
    with pytest.raises(ValueError):
        store.submit('a', 's', 'delegate', {'target_agent_id': 'a'})
    with pytest.raises(ValueError):
        store.submit('a', 's', 'delegate', {'target_agent_id': 'a', 'target_session_id': 1})


def test_old_attempt_stop_cannot_stop_retry(tmp_path):
    store = TaskStore(tmp_path / 'tasks.db')
    task_id = store.submit('a', 's', 'task', {})['task_id']
    old = store.claim(task_id)
    old_attempt = old.attempt_id
    assert store.request_stop(task_id, 'timed_out', attempt_id=old_attempt)
    old.close()
    assert store.retry(task_id)['state'] == 'queued'
    assert not store.request_stop(task_id, 'timed_out', attempt_id=old_attempt)
    assert store.get(task_id)['state'] == 'queued'
    new = store.claim(task_id)
    assert new.attempt_id != old_attempt
    assert not store.request_stop(task_id, 'timed_out', attempt_id=old_attempt)
    assert store.get(task_id)['state'] == 'running'
    assert store.request_stop(task_id, 'cancelled')
    assert store.get(task_id)['state'] == 'cancelled'
    new.close()
