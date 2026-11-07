import json
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from agent.recovery.__main__ import main
from agent.recovery.service import RecoveryService, start_recovery_service
from agent.recovery.store import TaskStore


def test_operator_retry_acknowledgement_and_ownership(tmp_path, capsys):
    store = TaskStore(tmp_path / 'journal/tasks.db')
    task = store.submit('owner', 'session', 'subagent', {'prompt': 'private fixture'})
    task_id = task['task_id']
    claim = store.claim(task_id)
    store.before_tool(claim, 'write', mutating=True)
    store.request_stop(task_id, 'timed_out')
    assert main(['retry', task_id, '--owner', 'owner', '--acknowledge-effects'], store=store) == 1
    assert 'live execution' in capsys.readouterr().out
    claim.close()
    assert main(['show', task_id, '--owner', 'other'], store=store) == 1
    assert 'private fixture' not in capsys.readouterr().out
    assert main(['retry', task_id, '--owner', 'owner'], store=store) == 1
    assert 'acknowledgement' in capsys.readouterr().out
    assert main(['retry', task_id, '--owner', 'owner', '--acknowledge-effects'], store=store) == 0
    assert json.loads(capsys.readouterr().out)['state'] == 'queued'
    assert main(['cancel', task_id, '--owner', 'owner'], store=store) == 0
    assert json.loads(capsys.readouterr().out)['state'] == 'cancelled'
    assert main(['list', '--owner', 'owner'], store=store) == 0
    assert 'prompt' not in capsys.readouterr().out


def test_service_bootstrap_once_and_failed_future_does_not_poison_queue(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'journal/tasks.db')
    bridge = SimpleNamespace(bridge=object())
    monkeypatch.setattr('agent.recovery.runtime.get_task_store', lambda: store)
    monkeypatch.setattr(RecoveryService, 'start', lambda self: self)
    service = start_recovery_service(bridge)
    try:
        assert start_recovery_service(bridge) is service
        failed = Future(); failed.set_exception(RuntimeError('fixture'))
        service._futures['failed'] = failed
        with pytest.raises(RuntimeError):
            service.scan_once()
        assert service._futures == {}
        service.scan_once()
        assert service.last_error is None
    finally:
        service.close(wait=True)


def test_bridge_constructor_starts_recovery(monkeypatch):
    from bridge.agent_bridge import AgentBridge
    calls = []
    monkeypatch.setattr('agent.recovery.service.start_recovery_service', lambda b: calls.append(b))
    monkeypatch.setattr('agent.tools.scheduler.integration.init_scheduler', lambda *a: None)
    monkeypatch.setattr('agent.evolution.trigger.start_evolution_trigger', lambda *a: None)
    bridge = AgentBridge(object())
    assert calls == [bridge]


def test_journal_private_permissions_and_fair_queue(tmp_path):
    import os
    store = TaskStore(tmp_path / 'private/tasks.db')
    first = store.submit('owner', 's', 'subagent', {})
    store.submit('owner', 's', 'subagent', {'second': True})
    assert store.list_tasks(states=['queued'], limit=1, oldest_first=True)[0]['task_id'] == first['task_id']
    assert os.stat(store.path).st_mode & 0o077 == 0
