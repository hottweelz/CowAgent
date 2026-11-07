"""Real process death and restart of the shipped recovery consumer."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from agent.recovery.store import TaskStore

FIXTURE = Path(__file__).with_name('recovery_process_fixture.py')


def launch(root, mode):
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR')}
    output = (root / (mode + '.log')).open('w')
    proc = subprocess.Popen([sys.executable, str(FIXTURE), str(root), mode],
                            stdout=output, stderr=subprocess.STDOUT, env=env)
    output.close()
    return proc


def wait_file(proc, path):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not path.exists() and proc.poll() is None:
        time.sleep(.02)
    assert path.exists(), f'fixture did not reach boundary: {proc.poll()}'


@pytest.mark.skipif(os.name != 'posix', reason='POSIX process ownership backend')
@pytest.mark.parametrize('boundary', ['before_effect', 'after_intent', 'after_effect'])
def test_process_interruption_and_service_recovery(tmp_path, boundary):
    proc = launch(tmp_path, boundary)
    try:
        wait_file(proc, tmp_path / 'ready')
        assert proc.poll() is None
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill(); proc.wait(timeout=5)
    task_id = (tmp_path / 'task-id').read_text()
    store = TaskStore(tmp_path / 'private-journal/tasks.db')
    assert store.get(task_id)['state'] == 'running'
    service = launch(tmp_path, 'service')
    try:
        assert service.wait(timeout=10) == 0, (tmp_path / 'service.log').read_text()
    finally:
        if service.poll() is None:
            service.kill(); service.wait(timeout=5)
    row = store.get(task_id)
    if boundary == 'before_effect':
        assert row['state'] == 'completed'
        assert row['attempt_count'] == 2
        assert (tmp_path / 'workspace/result.txt').read_text() == 'durable fixture result'
        assert (tmp_path / 'effect-count').read_text().splitlines() == ['write']
    else:
        assert row['state'] == 'needs_review' and row['attempt_count'] == 1
        expected = 1 if boundary == 'after_effect' else 0
        count = (tmp_path / 'effect-count').read_text().splitlines() if (tmp_path / 'effect-count').exists() else []
        assert len(count) == expected
        with pytest.raises(ValueError, match='acknowledgement'):
            store.retry(task_id)
        store.retry(task_id, acknowledge_effects=True)
        retry = launch(tmp_path, 'service-retry')
        try:
            assert retry.wait(timeout=10) == 0, (tmp_path / 'service-retry.log').read_text()
        finally:
            if retry.poll() is None:
                retry.kill(); retry.wait(timeout=5)
        assert store.get(task_id)['state'] == 'completed'
        assert store.get(task_id)['attempt_count'] == 2
        assert len((tmp_path / 'effect-count').read_text().splitlines()) == expected + 1
    # Another restart cannot re-execute a completed task.
    final = launch(tmp_path, 'service-final')
    try:
        assert final.wait(timeout=10) == 0
    finally:
        if final.poll() is None:
            final.kill(); final.wait(timeout=5)
    assert store.get(task_id)['attempt_count'] == 2
    assert json.loads((tmp_path / 'service-result.json').read_text())['state'] == 'completed'
