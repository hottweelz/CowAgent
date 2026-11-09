"""Disposable private-file operator tests. No live process or data access."""
import json
import multiprocessing
import os
import subprocess
import threading
import time
import uuid

import pytest

from common import maintenance_control as control
from common import runtime_drain as drain


class Runtime:
    def __init__(self, owner):
        self.owner = owner
        self.epoch = uuid.uuid4().hex

    def validate(self):
        pass


@pytest.fixture
def private(tmp_path):
    path = (tmp_path / 'control').resolve()
    path.mkdir(mode=0o700)
    return path


@pytest.fixture
def service(private, monkeypatch):
    monkeypatch.setattr(drain, '_installed', None)
    monkeypatch.setattr(drain, '_validate_owner', Runtime)
    owner = object()
    coordinator = drain.install(drain.RuntimeDrain(('scheduler', 'recovery')))
    coordinator.bind_owner(owner)
    coordinator.register_component('scheduler')
    coordinator.register_component('recovery')
    prepared = control.prepare(private)
    instance = control.bind_initialized(prepared, coordinator, owner)
    yield instance
    instance.close()


def submit(service, **kwargs):
    return control.submit_drain(service.directory.path, grant=control.GRANT, **kwargs)


def until(predicate):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    assert predicate()


def request(service, **changes):
    now = time.time()
    value = {'protocol': control.PROTOCOL, 'request_id': uuid.uuid4().hex,
             'binding': control._binding(service.descriptor), 'grant': control.GRANT,
             'issued_at': now, 'expires_at': now + 5, 'timeout': 0}
    value.update(changes)
    return value


def raw_receipt(service, value):
    service.directory.publish('request.json', value)
    path = service.directory.path / ('receipt-' + value['request_id'] + '.json')
    until(path.exists)
    return json.loads(path.read_bytes())


def test_prepare_is_read_only_and_requires_empty_private_directory(private):
    prepared = control.prepare(private)
    assert list(private.iterdir()) == []
    prepared.directory.close()
    (private / 'prior').touch(mode=0o600)
    with pytest.raises(control.MaintenanceControlError):
        control.prepare(private)


@pytest.mark.parametrize('mode', [0o755, 0o770, 0o777])
def test_unsafe_directory_permissions_rejected(private, mode):
    private.chmod(mode)
    with pytest.raises(control.MaintenanceControlError):
        control.prepare(private)


def test_symlink_path_rejected(private):
    alias = private.parent / 'alias'
    alias.symlink_to(private, target_is_directory=True)
    with pytest.raises(control.MaintenanceControlError):
        control.prepare(alias)


def test_unauthorized_effective_uid_rejected_before_writes(private, monkeypatch):
    monkeypatch.setattr(os, 'geteuid', lambda: os.getuid() + 1)
    with pytest.raises(control.MaintenanceControlError):
        control.prepare(private)
    assert list(private.iterdir()) == []


def test_ownership_ignored_or_unknown_filesystem_rejected(private, monkeypatch):
    def denied(*args, **kwargs):
        raise OSError('private location must not leak')
    monkeypatch.setattr(control, 'require_filesystem_ownership', denied)
    with pytest.raises(control.MaintenanceControlError, match='^maintenance_control_unavailable$'):
        control.prepare(private)
    assert list(private.iterdir()) == []


def test_unbound_owner_rejected_before_publication(private, monkeypatch):
    monkeypatch.setattr(drain, '_installed', None)
    coordinator = drain.install(drain.RuntimeDrain())
    prepared = control.prepare(private)
    try:
        with pytest.raises(control.MaintenanceControlError):
            control.bind_initialized(prepared, coordinator, object())
        assert list(private.iterdir()) == []
    finally:
        prepared.directory.close()


def test_explicit_scope_and_private_descriptor_required(service):
    with pytest.raises(control.MaintenanceControlError):
        control.submit_drain(service.directory.path, grant='restart', timeout=0)
    (service.directory.path / 'service.json').chmod(0o644)
    with pytest.raises(control.MaintenanceControlError):
        submit(service, timeout=0)
    assert not service.coordinator._closed


def test_positive_receipt_is_bound_and_durable_without_exec(service, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('operator must never execute or signal')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(os, 'kill', forbidden)
    monkeypatch.setattr(os, 'execv', forbidden)
    receipt = submit(service, timeout=0.2)
    assert receipt['drained'] and receipt['closed']
    assert receipt['status'] == 'drained'
    assert receipt['binding'] == control._binding(service.descriptor)
    assert receipt['required_components'] == ['recovery', 'scheduler']
    identifier = receipt['request_id']
    assert (service.directory.path / ('claimed-' + identifier + '.json')).exists()
    assert (service.directory.path / ('receipt-' + identifier + '.json')).exists()
    assert not (service.directory.path / 'request.json').exists()
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in service.directory.path.iterdir())


@pytest.mark.parametrize('field', ['pid', 'runtime_epoch', 'coordinator_epoch', 'service_id', 'uid'])
def test_stale_process_or_runtime_binding_cannot_drain(service, field):
    value = request(service)
    value['binding'][field] = 999999 if field in ('pid', 'uid') else uuid.uuid4().hex
    receipt = raw_receipt(service, value)
    assert receipt['status'] == 'rejected' and not receipt['drained']
    assert not service.coordinator._closed


@pytest.mark.parametrize('change', [
    {'grant': 'execute'}, {'expires_at': 1}, {'issued_at': time.time() + 1000},
    {'timeout': -1}, {'timeout': 61}, {'timeout': True},
])
def test_invalid_or_expired_request_consumed_without_closing(service, change):
    receipt = raw_receipt(service, request(service, **change))
    assert receipt['status'] == 'rejected'
    assert not service.coordinator._closed


def test_replay_denied_and_new_explicit_request_may_observe_again(service):
    identifier = uuid.uuid4().hex
    first = submit(service, timeout=0, request_id=identifier)
    with pytest.raises(control.MaintenanceControlError):
        submit(service, timeout=0, request_id=identifier)
    second = submit(service, timeout=0)
    assert first['drained'] and second['drained']
    assert first['request_id'] != second['request_id']


def test_timeout_preserves_children_scheduler_recovery_and_later_completion(service):
    parent = service.coordinator.reserve('parent')
    scheduler = service.coordinator.reserve('scheduler')
    recovery = service.coordinator.reserve('recovery')
    first = submit(service, timeout=0.02)
    assert first['status'] == 'closed_not_drained'
    assert first['active'] == {'parent': 1, 'scheduler': 1, 'recovery': 1}
    with pytest.raises(drain.AdmissionClosed):
        service.coordinator.reserve('late_root')
    with parent.activate():
        child = service.coordinator.reserve('child', 'testpilot')
    parent.release()
    scheduler.release()
    recovery.release()
    second = submit(service, timeout=0)
    assert second['active'] == {'child': 1} and second['agents'] == {'testpilot': 1}
    child.release()
    final = submit(service, timeout=0.2)
    assert final['drained'] and service.coordinator._closed
    assert json.loads((service.directory.path / ('receipt-' + first['request_id'] + '.json')).read_bytes()) == first


def test_concurrent_operator_request_rejected_without_cancelling_work(service):
    lease = service.coordinator.reserve('held')
    results = []
    thread = threading.Thread(target=lambda: results.append(submit(service, timeout=0.2)))
    thread.start()
    try:
        until(lambda: service.coordinator._closed)
        with pytest.raises(control.MaintenanceControlError):
            submit(service, timeout=0)
        assert service.coordinator.snapshot()['active'] == {'held': 1}
    finally:
        thread.join(2)
        lease.release()
    assert not thread.is_alive() and results[0]['status'] == 'closed_not_drained'


def test_unknown_coverage_never_qualifies(service):
    service.coordinator.mark_unsupported('unknown_detached_plugin')
    receipt = submit(service, timeout=0.1)
    assert receipt['closed'] and not receipt['drained']
    assert 'unknown_detached_plugin' in receipt['blockers']


def test_claim_is_durable_before_close_and_survives_receipt_failure(service, monkeypatch):
    service.stop.set()
    service.thread.join(2)
    value = request(service)
    service.directory.publish('request.json', value)
    original = service.directory.publish
    def fail_receipt(name, content):
        if name.startswith('receipt-'):
            raise OSError('simulated crash after admission close')
        return original(name, content)
    monkeypatch.setattr(service.directory, 'publish', fail_receipt)
    with pytest.raises(OSError):
        service._poll()
    assert service.coordinator._closed
    assert (service.directory.path / ('claimed-' + value['request_id'] + '.json')).exists()
    monkeypatch.setattr(service.directory, 'publish', original)
    service.directory.publish('request.json', value)
    def cannot_repeat():
        pytest.fail('consumed request repeated')
    monkeypatch.setattr(service.coordinator, 'close_admission', cannot_repeat)
    service._poll()
    assert not (service.directory.path / 'request.json').exists()
    assert not (service.directory.path / ('receipt-' + value['request_id'] + '.json')).exists()


def test_claim_sync_failure_never_closes_admission(service, monkeypatch):
    service.stop.set()
    service.thread.join(2)
    service.directory.publish('request.json', request(service))
    def fail_sync():
        raise OSError('simulated directory persistence failure')
    monkeypatch.setattr(service.directory, 'sync', fail_sync)
    with pytest.raises(OSError):
        service._poll()
    assert not service.coordinator._closed


def test_symlink_or_hardlinked_request_cannot_close(service):
    service.stop.set()
    service.thread.join(2)
    external = service.directory.path.parent / 'outside'
    external.write_text(json.dumps(request(service)))
    external.chmod(0o600)
    inbox = service.directory.path / 'request.json'
    inbox.symlink_to(external)
    with pytest.raises(OSError):
        service._poll()
    inbox.unlink()
    os.link(external, inbox)
    with pytest.raises(control.MaintenanceControlError):
        service._poll()
    assert not service.coordinator._closed


def test_directory_permission_change_stops_observer_and_denies_positive_evidence(service):
    service.directory.path.chmod(0o755)
    until(service.stop.is_set)
    service.coordinator.close_admission()
    assert 'maintenance_control_unavailable' in service.coordinator.wait(0)['blockers']
    service.directory.path.chmod(0o700)


def test_public_receipt_does_not_echo_private_exception(service, monkeypatch):
    def fail():
        raise ValueError('/private/secret/access-token')
    monkeypatch.setattr(service.coordinator._owner, 'validate', fail)
    receipt = submit(service, timeout=0)
    assert receipt['status'] == 'rejected'
    assert 'secret' not in json.dumps(receipt)
    assert 'access-token' not in json.dumps(receipt)
    assert not service.coordinator._closed


def test_dead_descriptor_is_bounded_without_pid_signals(service, monkeypatch):
    # A descriptor is not a liveness claim. No observer means no positive receipt.
    service.stop.set()
    service.thread.join(2)
    clock = [100.0]
    monkeypatch.setattr(control.time, 'monotonic', lambda: clock[0])
    def advance(_duration):
        clock[0] += 10
    monkeypatch.setattr(control.time, 'sleep', advance)
    with pytest.raises(control.MaintenanceControlError, match='maintenance_receipt_unavailable'):
        submit(service, timeout=0)
    assert not service.coordinator._closed


def _publication_reader(path, name, connection):
    """Separate process: lock behavior must not rely on a Python thread mutex."""
    directory = control._Directory(path)
    try:
        directory.enable_io_lock()
        connection.send('ready')
        try:
            connection.send(('value', directory.read(name)))
        except Exception as error:
            connection.send(('error', type(error).__name__))
    finally:
        directory.close()
        connection.close()


@pytest.mark.parametrize('pause_at', ['after_link', 'before_directory_fsync'])
def test_reader_waits_for_atomic_durable_publication(service, monkeypatch, pause_at):
    ready, release = threading.Event(), threading.Event()
    original_link, original_sync = os.link, service.directory.sync
    name = 'receipt-proof.json'
    writer_ident = []
    failures = []
    def pause():
        ready.set()
        assert release.wait(3)
    def linked(source, destination, **kwargs):
        result = original_link(source, destination, **kwargs)
        if destination == name and pause_at == 'after_link':
            pause()
        return result
    def synced():
        if (pause_at == 'before_directory_fsync' and writer_ident
                and threading.get_ident() == writer_ident[0]):
            pause()
        return original_sync()
    monkeypatch.setattr(os, 'link', linked)
    monkeypatch.setattr(service.directory, 'sync', synced)
    def write():
        writer_ident.append(threading.get_ident())
        try:
            service.directory.publish(name, {'drained': True})
        except Exception as error:
            failures.append(error)
    writer = threading.Thread(target=write)
    writer.start()
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe()
    reader = context.Process(target=_publication_reader,
                             args=(str(service.directory.path), name, child))
    try:
        assert ready.wait(2)
        assert (service.directory.path / name).stat().st_nlink == (2 if pause_at == 'after_link' else 1)
        reader.start()
        child.close()
        assert parent.poll(3) and parent.recv() == 'ready'
        assert not parent.poll(0.05), 'reader consumed an uncommitted publication'
        release.set()
        writer.join(2)
        assert not writer.is_alive() and not failures
        assert parent.poll(3)
        kind, raw = parent.recv()
        assert kind == 'value' and json.loads(raw) == {'drained': True}
    finally:
        release.set()
        writer.join(3)
        if reader.pid is not None:
            reader.join(3)
            if reader.is_alive():
                reader.terminate()
                reader.join(3)
        parent.close()
        child.close()


def test_failed_publication_fsync_cannot_yield_positive_receipt(service, monkeypatch):
    name = 'receipt-proof.json'
    original_sync = service.directory.sync
    def failed():
        raise OSError('simulated final directory fsync failure')
    monkeypatch.setattr(service.directory, 'sync', failed)
    with pytest.raises(OSError):
        service.directory.publish(name, {'drained': True})
    monkeypatch.setattr(service.directory, 'sync', original_sync)
    assert not (service.directory.path / name).exists()
    with pytest.raises(FileNotFoundError):
        service.directory.read(name)
    assert not list(service.directory.path.glob('.write-*'))


def test_reader_fsync_failure_rejects_even_visible_receipt(service, monkeypatch):
    name = 'receipt-proof.json'
    service.directory.publish(name, {'drained': True})
    def failed():
        raise OSError('independent reader persistence unavailable')
    monkeypatch.setattr(service.directory, 'sync', failed)
    with pytest.raises(OSError):
        service.directory.read(name)


def test_same_directory_threads_use_distinct_lock_descriptions(service, monkeypatch):
    name = 'receipt-proof.json'
    linked, release, reading, finished = (threading.Event() for _ in range(4))
    original_link = os.link
    results = []
    errors = []
    def paused_link(source, destination, **kwargs):
        result = original_link(source, destination, **kwargs)
        if destination == name:
            linked.set()
            assert release.wait(2)
        return result
    monkeypatch.setattr(os, 'link', paused_link)
    def write():
        try:
            service.directory.publish(name, {'drained': True})
        except Exception as error:
            errors.append(error)
    def read():
        reading.set()
        try:
            results.append(service.directory.read(name))
        except Exception as error:
            errors.append(error)
        finally:
            finished.set()
    writer, reader = threading.Thread(target=write), threading.Thread(target=read)
    writer.start()
    try:
        assert linked.wait(2)
        reader.start()
        assert reading.wait(2)
        assert not finished.wait(0.05)
        release.set()
        writer.join(2)
        reader.join(2)
        assert not errors and json.loads(results[0]) == {'drained': True}
    finally:
        release.set()
        writer.join(2)
        if reader.ident is not None:
            reader.join(2)
