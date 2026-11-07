"""Combined real-process isolation, recovery and verification boundaries."""
import json
import os
import signal
import time

import pytest

from agent.recovery.store import TaskStore
from agent.recovery.verification import outcome_summary
from tests.test_recovery_process import launch, wait_file

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='POSIX process ownership backend')


def configure(root, **options):
    (root / 'release-case.json').write_text(json.dumps(options))


def kill_at(root, mode):
    process = launch(root, mode)
    try:
        wait_file(process, root / 'ready')
        os.kill(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    task_id = (root / 'task-id').read_text()
    return TaskStore(root / 'private-journal/tasks.db'), task_id


def run_service(root, mode):
    process = launch(root, mode)
    try:
        assert process.wait(timeout=10) == 0, (root / (mode + '.log')).read_text()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def writes(root):
    path = root / 'effect-count'
    return path.read_text().splitlines() if path.exists() else []


@pytest.mark.parametrize('boundary', ['before_dispatch', 'before_effect', 'after_intent', 'after_effect', 'after_completion'])
def test_crash_boundaries_preserve_spec_and_verify_real_output(tmp_path, boundary):
    configure(tmp_path, verification=True)
    store, task_id = kill_at(tmp_path, boundary)
    initial = store.get(task_id)
    frozen = initial['spec']
    assert frozen['verification'] and frozen['owner_id'] == 'owner'
    assert initial['attempt_count'] == (0 if boundary == 'before_dispatch' else 1)
    run_service(tmp_path, 'service-first')
    row = store.get(task_id)
    if boundary in ('after_intent', 'after_effect'):
        assert row['state'] == 'needs_review'
        assert len(row['attempts'][0]['effects']) == 1
        assert row['attempts'][0]['effects'][0]['completed_at'] is None
        with pytest.raises(ValueError, match='acknowledgement'):
            store.retry(task_id)
        store.retry(task_id, acknowledge_effects=True)
        run_service(tmp_path, 'service-retry')
    row = store.get(task_id)
    assert row['state'] == 'completed' and row['spec'] == frozen
    assert row['attempt_count'] == (1 if boundary in ('before_dispatch', 'after_completion') else 2)
    assert outcome_summary(row)['verified']
    assert (tmp_path / 'workspace/result.txt').read_text() == 'durable fixture result'
    assert len(writes(tmp_path)) == (2 if boundary == 'after_effect' else 1)
    assert sum(len(a['effects']) for a in row['attempts']) == (2 if boundary in ('after_intent', 'after_effect') else 1)
    run_service(tmp_path, 'service-final')
    final = store.get(task_id)
    assert final['attempt_count'] == row['attempt_count']
    assert sum(len(a['verifications']) for a in final['attempts']) == 1
    assert writes(tmp_path) == (['write', 'write'] if boundary == 'after_effect' else ['write'])


@pytest.mark.parametrize('stop', ['cancelled', 'timed_out'])
def test_active_stop_retains_provenance_and_live_lock(tmp_path, stop):
    configure(tmp_path, verification=True, timeout=.3 if stop == 'timed_out' else 30)
    process = launch(tmp_path, 'before_effect')
    try:
        wait_file(process, tmp_path / 'ready')
        task_id = (tmp_path / 'task-id').read_text()
        store = TaskStore(tmp_path / 'private-journal/tasks.db')
        if stop == 'cancelled':
            assert store.request_stop(task_id, stop)
        else:
            deadline = time.monotonic() + 4
            while store.get(task_id)['state'] != stop and time.monotonic() < deadline:
                time.sleep(.02)
        row = store.get(task_id)
        assert row['state'] == stop and row['attempts'][0]['state'] == stop
        assert row['reason'] == stop and row['attempts'][0]['reason'] == stop
        with pytest.raises(RuntimeError, match='live execution'):
            store.retry(task_id)
        run_service(tmp_path, 'service-scan')
        assert store.get(task_id)['attempt_count'] == 1
    finally:
        process.kill()
        process.wait(timeout=5)
    run_service(tmp_path, 'service-scan')
    assert store.get(task_id)['state'] == stop
    assert not writes(tmp_path) and not (tmp_path / 'workspace/result.txt').exists()


def test_revoked_write_after_intent_blocks_acknowledged_retry(tmp_path):
    configure(tmp_path, verification=True)
    store, task_id = kill_at(tmp_path, 'after_intent')
    run_service(tmp_path, 'service-first')
    assert store.get(task_id)['state'] == 'needs_review'
    store.retry(task_id, acknowledge_effects=True)
    configure(tmp_path, verification=True, permission='read-only')
    run_service(tmp_path, 'service-retry')
    row = store.get(task_id)
    assert row['state'] == 'completed' and row['attempt_count'] == 2
    assert not outcome_summary(row)['verified']
    assert row['verification']['acceptance']['status'] != 'passed'
    assert not writes(tmp_path) and not (tmp_path / 'workspace/result.txt').exists()
    assert any(e['result'] and e['result'].get('permission_denied') for e in row['attempts'][1]['effects'])


@pytest.mark.parametrize('options', [{'content': 'wrong'}, {'skip_output': True}])
def test_bad_completed_output_is_never_verified_or_replayed(tmp_path, options):
    configure(tmp_path, verification=True, **options)
    store, task_id = kill_at(tmp_path, 'after_completion')
    for mode in ('service-first', 'service-final'):
        run_service(tmp_path, mode)
        row = store.get(task_id)
        assert row['state'] == 'completed' and row['attempt_count'] == 1
        assert not outcome_summary(row)['verified']
        assert row['verification']['acceptance']['status'] != 'passed'
        assert row['verification']['external_state']['status'] != 'confirmed'
    artifact = tmp_path / 'workspace/result.txt'
    if options.get('skip_output'):
        assert not artifact.exists() and not writes(tmp_path)
    else:
        assert artifact.read_text() == 'wrong' and writes(tmp_path) == ['write']


def test_sibling_read_denied_while_concurrent_service_respects_live_owner(tmp_path):
    configure(tmp_path, verification=True, sibling_probe=True, capture_requests=True)
    sibling = tmp_path / 'sibling'
    sibling.mkdir()
    (sibling / 'secret.txt').write_text('private sibling secret')
    process = launch(tmp_path, 'before_effect')
    try:
        wait_file(process, tmp_path / 'ready')
        task_id = (tmp_path / 'task-id').read_text()
        store = TaskStore(tmp_path / 'private-journal/tasks.db')
        run_service(tmp_path, 'service-scan')
        row = store.get(task_id)
        assert row['state'] == 'running' and row['attempt_count'] == 1
        assert row['attempts'][0]['effects'][0]['result']['permission_denied']
        assert 'private sibling secret' not in json.dumps(row)
    finally:
        process.kill()
        process.wait(timeout=5)
    run_service(tmp_path, 'service-first')
    row = store.get(task_id)
    assert row['state'] == 'completed' and row['attempt_count'] == 2
    assert row['verification']['acceptance']['status'] == 'failed'
    assert row['verification']['external_state']['status'] == 'confirmed'
    assert not outcome_summary(row)['verified']
    assert (tmp_path / 'workspace/result.txt').read_text() == 'durable fixture result'
    assert (sibling / 'secret.txt').read_text() == 'private sibling secret'
    assert 'private sibling secret' not in json.dumps(row)
    requests = (tmp_path / 'model-requests.jsonl').read_text()
    assert 'Write the fixture result once' in requests
    assert 'private sibling secret' not in requests
