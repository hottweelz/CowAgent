import copy
from concurrent.futures import Future
import threading

import pytest

from common import runtime_drain as drain


class FakeRuntime:
    def validate(self):
        pass


@pytest.fixture
def coordinator(monkeypatch):
    monkeypatch.setattr(drain, '_installed', None)
    monkeypatch.setattr(drain, '_validate_owner', lambda owner: FakeRuntime())
    result = drain.RuntimeDrain(required_components=('web',))
    result.bind_owner(object())
    result.register_component('web', lambda: [])
    drain.install(result)
    return result


def test_close_and_child_reservation(coordinator):
    admitted = threading.Event()
    continue_work = threading.Event()
    children = []

    def parent():
        with drain.work('root'):
            admitted.set()
            assert continue_work.wait(2)
            children.append(drain.reserve('child', 'agent1'))

    thread = threading.Thread(target=parent)
    thread.start()
    assert admitted.wait(2)
    coordinator.close_admission()
    with pytest.raises(drain.AdmissionClosed):
        drain.reserve('new')
    continue_work.set()
    thread.join(2)
    assert not thread.is_alive()
    receipt = coordinator.wait(0)
    assert not receipt['drained']
    assert receipt['active'] == {'child': 1}
    assert receipt['agents'] == {'agent1': 1}
    children[0].run(lambda: None)
    assert coordinator.wait(1)['drained']
    with pytest.raises(drain.AdmissionClosed):
        drain.reserve('new')


def test_copied_and_released_leases_cannot_authorize(coordinator):
    lease = drain.reserve('root')
    copied = copy.copy(lease)
    coordinator.close_admission()
    with pytest.raises(drain.AdmissionClosed):
        with copied.activate():
            pass
    with lease.activate():
        assert 'self_wait' in coordinator.wait(0)['blockers']
    lease.release()
    lease.release()
    with pytest.raises(drain.AdmissionClosed):
        with lease.activate():
            pass
    assert coordinator.wait(1)['drained']


def test_queued_cancellation_and_submit_failure_release(coordinator):
    class Queued:
        def submit(self, *args, **kwargs):
            return Future()
    future = drain.submit(Queued(), 'queued', lambda: None)
    coordinator.close_admission()
    assert coordinator.wait(0)['active'] == {'queued': 1}
    assert future.cancel()
    assert coordinator.wait(1)['drained']




def test_submit_failure_and_thread_start_failure(coordinator, monkeypatch):
    class Broken:
        def submit(self, *args, **kwargs):
            raise RuntimeError('failure')
    with pytest.raises(RuntimeError):
        drain.submit(Broken(), 'queued', lambda: None)
    def fail_start(self):
        raise RuntimeError('failure')
    monkeypatch.setattr(threading.Thread, 'start', fail_start)
    with pytest.raises(RuntimeError):
        drain.start_thread('thread', lambda: None)
    monkeypatch.undo()
    assert coordinator._leases == {}


def test_generator_keeps_lease_but_does_not_leak_context(coordinator):
    @drain.tracked_generator('stream')
    def stream():
        yield 'first'
        with drain.work('nested'):
            yield 'second'
    generator = stream()
    assert next(generator) == 'first'
    coordinator.close_admission()
    with pytest.raises(drain.AdmissionClosed):
        drain.reserve('outside')
    assert next(generator) == 'second'
    assert coordinator.wait(0)['active'] == {'nested': 1, 'stream': 1}
    generator.close()
    assert coordinator.wait(1)['drained']


def test_missing_coverage_probes_and_sticky_unsupported(monkeypatch):
    monkeypatch.setattr(drain, '_validate_owner', lambda owner: FakeRuntime())
    coordinator = drain.RuntimeDrain(('web', 'queue'))
    coordinator.bind_owner(object())
    coordinator.register_component('web', lambda: ['web_busy'])
    coordinator.mark_unsupported('unknown_transport')
    coordinator.close_admission()
    receipt = coordinator.wait(1)
    assert not receipt['drained']
    assert set(receipt['blockers']) == {'missing_component:queue', 'web_busy', 'unknown_transport'}
    assert receipt['required_components'] == ['queue', 'web']
    assert receipt['registered_components'] == ['web']
    assert receipt['pid'] == coordinator.pid and receipt['epoch'] == coordinator.epoch


def test_invalid_owner_and_probe_error(coordinator):
    class Invalid:
        def validate(self):
            raise RuntimeError('private message')
    coordinator._owner = Invalid()
    coordinator._components['web'] = lambda: 1 / 0
    coordinator.close_admission()
    receipt = coordinator.wait(1)
    assert set(receipt['blockers']) == {'invalid_owner', 'probe_error:web'}
    assert 'private message' not in repr(receipt)


def test_uninitialized_owner_rejected():
    from agent.discovery.contracts import DiscoveryError
    coordinator = drain.RuntimeDrain()
    with pytest.raises(DiscoveryError):
        coordinator.bind_owner(object())
    coordinator.close_admission()
    assert 'missing_owner' in coordinator.wait(0)['blockers']


def test_absent_coordinator_is_noop(monkeypatch):
    monkeypatch.setattr(drain, '_installed', None)
    with drain.work('ordinary'):
        assert drain.reserve('child').run(lambda: 42) == 42
    drain.register_component('web')
    drain.mark_unsupported('unknown')


def test_release_does_not_hide_running_activation(coordinator):
    entered = threading.Event()
    leave = threading.Event()
    lease = drain.reserve('running')
    def execute():
        with lease.activate():
            entered.set()
            assert leave.wait(2)
    thread = threading.Thread(target=execute)
    thread.start()
    assert entered.wait(2)
    lease.release()
    coordinator.close_admission()
    assert coordinator.wait(0)['active'] == {'running': 1}
    leave.set()
    thread.join(2)
    assert not thread.is_alive()
    assert coordinator.wait(1)['drained']


def test_unsettled_probe_blocks_bounded_wait(monkeypatch):
    monkeypatch.setattr(drain, '_validate_owner', lambda owner: FakeRuntime())
    entered = threading.Event()
    leave = threading.Event()
    def probe():
        entered.set()
        leave.wait(2)
        return []
    coordinator = drain.RuntimeDrain(('web',))
    coordinator.bind_owner(object())
    coordinator.register_component('web', probe)
    coordinator.close_admission()
    receipt = coordinator.wait(0)
    assert entered.wait(2)
    assert not receipt['drained']
    assert 'probe_pending:web' in receipt['blockers']
    leave.set()


def test_probes_never_accept_a_sample_taken_during_active_work(monkeypatch):
    monkeypatch.setattr(drain, '_validate_owner', lambda owner: FakeRuntime())
    entered = threading.Event()
    finish = threading.Event()
    sampled = threading.Event()
    pending = []
    coordinator = drain.RuntimeDrain(('recovery', 'trigger'))
    coordinator.bind_owner(object())
    def recovery_probe():
        sampled.set()
        return ['recovery_pending'] if pending else []
    def trigger_probe():
        finish.set()
        return []
    coordinator.register_component('recovery', recovery_probe)
    coordinator.register_component('trigger', trigger_probe)
    def worker():
        with coordinator.work('worker'):
            entered.set()
            assert finish.wait(2)
            pending.append(True)
    thread = threading.Thread(target=worker)
    thread.start()
    assert entered.wait(2)
    coordinator.close_admission()
    receipt = coordinator.snapshot()
    assert not receipt['drained']
    assert 'probe_stale' in receipt['blockers']
    assert not sampled.is_set()
    finish.set()
    thread.join(2)
    assert not thread.is_alive()
    receipt = coordinator.wait(1)
    assert sampled.is_set()
    assert not receipt['drained']
    assert 'recovery_pending' in receipt['blockers']
