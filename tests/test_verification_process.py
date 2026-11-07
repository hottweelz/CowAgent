"""Restart verifies committed execution without executing its worker again."""
import os
import signal

import pytest

from agent.recovery.store import TaskStore
from agent.recovery.verification import outcome_summary
from tests.test_recovery_process import launch, wait_file


@pytest.mark.skipif(os.name != 'posix', reason='POSIX process ownership backend')
def test_death_after_execution_commit_recovers_only_verification(tmp_path):
    process = launch(tmp_path, 'after_completion')
    try:
        wait_file(process, tmp_path / 'ready')
        os.kill(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    task_id = (tmp_path / 'task-id').read_text()
    store = TaskStore(tmp_path / 'private-journal/tasks.db')
    before = store.get(task_id)
    assert before['state'] == 'completed' and before['verification'] is None
    assert (tmp_path / 'effect-count').read_text().splitlines() == ['write']
    for mode in ('service-verification', 'service-verification-again'):
        service = launch(tmp_path, mode)
        try:
            assert service.wait(timeout=10) == 0, (tmp_path / (mode + '.log')).read_text()
        finally:
            if service.poll() is None:
                service.kill()
                service.wait(timeout=5)
        row = store.get(task_id)
        assert row['state'] == 'completed' and row['attempt_count'] == 1
        assert outcome_summary(row)['verified']
        assert len(row['attempts'][0]['verifications']) == 1
        assert (tmp_path / 'effect-count').read_text().splitlines() == ['write']
