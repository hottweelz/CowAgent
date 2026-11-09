import threading
from types import SimpleNamespace

import pytest

from common import runtime_drain as drain
from agent.tools.scheduler.scheduler_service import SchedulerService
from agent.recovery.service import RecoveryService
from agent.recovery.verification import verify_task
from agent.evolution.executor import run_evolution_for_session


@pytest.fixture
def coordinator(monkeypatch):
    coordinator = drain.RuntimeDrain()
    monkeypatch.setattr(drain, "_validate_owner", lambda owner: SimpleNamespace(validate=lambda: None))
    coordinator.bind_owner(object())
    monkeypatch.setattr(drain, '_installed', coordinator)
    return coordinator


class SchedulerStore:
    def get_task(self, task_id):
        return {'id': task_id, 'name': 'test'}

    def update_task(self, *args):
        pass


def test_manual_callback_is_reserved_before_thread_runs(coordinator):
    entered, release = threading.Event(), threading.Event()
    service = SchedulerService(SchedulerStore(), lambda task: (entered.set(), release.wait(2), True)[2])
    service.run_task_now('test')
    assert entered.wait(1)
    coordinator.close_admission()
    receipt = coordinator.wait(.02)
    assert not receipt['drained'] and receipt['active']['scheduler_manual'] == 1
    with pytest.raises(drain.AdmissionClosed):
        service.run_task_now('other')
    release.set()
    assert coordinator.wait(1)['drained']


class RecoveryStore:
    def __init__(self):
        self.pending = True
        self.unverified = False

    def list_tasks(self, **kwargs):
        return [{'task_id': 'fake'}] if self.pending else []

    def list_unverified_completed(self, **kwargs):
        return [{'task_id': 'fake'}] if self.unverified else []

    def reconcile(self):
        pass


def test_recovery_worker_live_after_terminal_and_probe(coordinator, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    store = RecoveryStore()
    def worker(*args, **kwargs):
        store.pending = False
        entered.set()
        release.wait(2)
    monkeypatch.setattr('agent.recovery.runtime.execute_task', worker)
    service = RecoveryService(None, store, max_workers=1)
    try:
        service.scan_once()
        assert entered.wait(1)
        coordinator.close_admission()
        assert not coordinator.wait(.02)['drained']
        release.set()
        assert coordinator.wait(1)['drained']
        store.unverified = True
        assert 'recovery_unverified' in coordinator.wait(1)['blockers']
        store.unverified = False
        store.pending = True
        assert 'recovery_unsettled' in coordinator.wait(1)['blockers']
    finally:
        release.set()
        service.close(wait=True)


def test_verification_and_evolution_reject_new_roots(coordinator):
    coordinator.close_admission()
    with pytest.raises(drain.AdmissionClosed):
        verify_task(None, 'test')
    with pytest.raises(drain.AdmissionClosed):
        run_evolution_for_session(SimpleNamespace(), 'test')


def test_verification_remains_active_until_report_is_saved(coordinator, monkeypatch):
    from contextlib import nullcontext
    entered, release = threading.Event(), threading.Event()
    task = {'state': 'completed', 'attempt_id': 'attempt', 'verification': None,
            'spec': {'verification': {}}}
    class Store:
        def verification_lock(self, task_id):
            return nullcontext(task)
        def record_verification(self, *args):
            entered.set()
            release.wait(2)
            return True
        def get(self, task_id):
            return task
    monkeypatch.setattr('agent.recovery.verification._report', lambda task: {'checked_at': ''})
    worker = threading.Thread(target=verify_task, args=(Store(), 'fake'))
    worker.start()
    assert entered.wait(1)
    coordinator.close_admission()
    assert coordinator.wait(.02)['active']['recovery_verification'] == 1
    release.set()
    worker.join(1)
    assert coordinator.wait(1)['drained']


def test_recovery_multiple_stores_and_probe_failure_block(coordinator):
    first, second = RecoveryStore(), RecoveryStore()
    first.pending = False
    services = [RecoveryService(None, first), RecoveryService(None, second)]
    try:
        coordinator.close_admission()
        assert 'recovery_unsettled' in coordinator.wait(1)['blockers']
        second.pending = False
        def fail(**kwargs):
            raise OSError('private journal detail')
        second.list_tasks = fail
        receipt = coordinator.wait(1)
        assert 'probe_error:recovery' in receipt['blockers']
        assert 'private' not in str(receipt)
    finally:
        for service in services:
            service.close(wait=True)


def test_manual_reservation_covers_thread_start_race(coordinator):
    entered, proceed = threading.Event(), threading.Event()
    class Store(SchedulerStore):
        def get_task(self, task_id):
            entered.set()
            assert proceed.wait(2)
            return super().get_task(task_id)
    service = SchedulerService(Store(), lambda task: True)
    caller = threading.Thread(target=service.run_task_now, args=('fake',))
    caller.start()
    assert entered.wait(1)
    coordinator.close_admission()
    assert coordinator.wait(.02)['active']['scheduler_manual'] == 1
    proceed.set()
    caller.join(1)
    assert coordinator.wait(1)['drained']


def test_evolution_execution_is_tracked_until_return(coordinator, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    monkeypatch.setattr('agent.evolution.executor.get_evolution_config',
                        lambda: SimpleNamespace(enabled=True))
    class Bridge:
        def get_cached_agent(self, *args, **kwargs):
            entered.set()
            release.wait(2)
            return None
    worker = threading.Thread(target=run_evolution_for_session, args=(Bridge(), 'fake'))
    worker.start()
    assert entered.wait(1)
    coordinator.close_admission()
    assert coordinator.wait(.02)['active']['evolution_execution'] == 1
    release.set()
    worker.join(1)
    assert coordinator.wait(1)['drained']
