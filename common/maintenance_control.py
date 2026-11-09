"""Launch-only private OS-account control for a freshly initialized service.

This is not a human-presence check or an OS sandbox. Same-UID/root arbitrary
code already has this authority. There is no HTTP, tool, signal or exec path.
"""
import hashlib
from contextvars import Context
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

from agent.external.filesystem_trust import require_filesystem_ownership


PROTOCOL = 'cow.maintenance.drain/1'
GRANT = 'close-admission-and-observe'
MAX_BYTES = 65536
MAX_TIMEOUT = 60
_ID = re.compile(r'^[0-9a-f]{32}$')
_PUBLIC = re.compile(r'^[A-Za-z0-9_.:-]{1,160}$')


class MaintenanceControlError(ValueError):
    """Only fixed public reason codes may cross the operator boundary."""


def _fail():
    raise MaintenanceControlError('maintenance_control_unavailable')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            _fail()
        result[key] = value
    return result


def _decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: _fail())
    except (ValueError, UnicodeError, TypeError):
        _fail()


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


class _Directory:
    def __init__(self, path):
        self.path = Path(path)
        self.fd = None
        self.io_identity = None
        try:
            self._path_check()
            self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.identity = self._identity(os.fstat(self.fd))
            self.check()
        except Exception:
            self.close()
            _fail()

    @staticmethod
    def _identity(info):
        return info.st_dev, info.st_ino

    def _path_check(self):
        uid = os.getuid()
        if uid != os.geteuid() or not self.path.is_absolute() or self.path.resolve(strict=True) != self.path:
            _fail()
        for directory in (self.path, *self.path.parents):
            require_filesystem_ownership(directory)
            info = directory.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid)
                    or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                _fail()
        info = self.path.lstat()
        if info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
            _fail()

    def check(self):
        self._path_check()
        require_filesystem_ownership(fd=self.fd)
        info = os.fstat(self.fd)
        if (self._identity(info) != self.identity or self._identity(self.path.lstat()) != self.identity
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
            _fail()

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def sync(self):
        self.check()
        os.fsync(self.fd)

    def enable_io_lock(self, *, create=False):
        """Bootstrap before publishing service identity; preparation stays read-only."""
        self.check()
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        if create:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open('io.lock', flags, 0o600, dir_fd=self.fd)
        try:
            if create:
                os.fchmod(fd, 0o600)
                os.fsync(fd)
            self._check_lock(fd)
            self.io_identity = self._identity(os.fstat(fd))
            if create:
                self.sync()
        finally:
            os.close(fd)

    def _check_lock(self, fd):
        require_filesystem_ownership(fd=fd)
        info = os.fstat(fd)
        named = os.stat('io.lock', dir_fd=self.fd, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                or self._identity(info) != self._identity(named)
                or self.io_identity is not None and self._identity(info) != self.io_identity):
            _fail()

    @contextmanager
    def _locked(self, *, exclusive):
        import fcntl
        self.check()
        if self.io_identity is None:
            _fail()
        # A separate open-file description is required for each operation:
        # flock on a shared descriptor does not exclude another local thread.
        fd = os.open('io.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        try:
            self._check_lock(fd)
            deadline = time.monotonic() + 5
            while True:
                try:
                    fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        _fail()
                    time.sleep(0.005)
            self.check()
            self._check_lock(fd)
            yield
        finally:
            os.close(fd)

    def read(self, name):
        with self._locked(exclusive=False):
            value = self._read(name)
            # A writer can die after unlinking its temporary name but before
            # directory fsync. Readers independently commit the visible name
            # before accepting it; unavailable persistence always rejects.
            self.sync()
            return value

    def _read(self, name):
        self.check()
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        try:
            require_filesystem_ownership(fd=fd)
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                    or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                    or before.st_size > MAX_BYTES):
                _fail()
            raw = os.read(fd, MAX_BYTES + 1)
            after = os.fstat(fd)
            named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            if (len(raw) > MAX_BYTES
                    or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                    or self._identity(named) != self._identity(before)):
                _fail()
            self.check()
            return raw
        finally:
            os.close(fd)

    def publish(self, name, value):
        with self._locked(exclusive=True):
            self._publish(name, value)

    def _publish(self, name, value):
        self.check()
        raw = _encode(value)
        if len(raw) > MAX_BYTES:
            _fail()
        temporary = '.write-' + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=self.fd)
        linked = False
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
            self.check()
            os.link(temporary, name, src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False)
            linked = True
            os.unlink(temporary, dir_fd=self.fd)
            self.sync()
        except Exception:
            # Do not release the exclusive publication lock with an uncommitted
            # positive receipt visible after a reported persistence failure.
            if linked:
                os.unlink(name, dir_fd=self.fd)
            try:
                os.unlink(temporary, dir_fd=self.fd)
            except FileNotFoundError:
                pass
            try:
                self.sync()
            except Exception:
                pass
            raise
        finally:
            os.close(fd)


class PreparedControl:
    """Not authority by itself; genuine runtime ownership is checked at bind."""
    def __init__(self, directory):
        self.directory = directory
        self.pid = os.getpid()
        self.bound = False

    def close(self):
        """Release an unbound preparation after startup fails."""
        if not self.bound:
            self.directory.close()


def prepare(control_dir):
    """Validate an operator-created empty private directory, without writes.

    Call only after successful startup-request authentication. A service must
    use a fresh directory for each launch; old claims must never be deleted for
    reuse. No runtime or logger is initialized here.
    """
    directory = _Directory(control_dir)
    try:
        if os.listdir(directory.fd):
            _fail()
        return PreparedControl(directory)
    except Exception:
        directory.close()
        _fail()


def _binding(value):
    keys = ('service_id', 'pid', 'uid', 'runtime_epoch', 'coordinator_epoch')
    return {key: value[key] for key in keys}


def _descriptor(value):
    if (not isinstance(value, dict)
            or set(value) != {'protocol', 'service_id', 'pid', 'uid', 'runtime_epoch',
                              'coordinator_epoch', 'grant', 'created_at'}
            or value['protocol'] != PROTOCOL or value['grant'] != GRANT
            or type(value['pid']) is not int or value['pid'] <= 0
            or type(value['uid']) is not int or value['uid'] != os.getuid()
            or not _finite(value['created_at'])
            or any(not isinstance(value[key], str) or not _ID.fullmatch(value[key])
                   for key in ('service_id', 'runtime_epoch', 'coordinator_epoch'))):
        _fail()
    return value


def bind_initialized(prepared, coordinator, owner):
    """Publish a single service binding after normal lifecycle owner binding."""
    from common import runtime_drain
    if (type(prepared) is not PreparedControl or prepared.bound or prepared.pid != os.getpid()
            or runtime_drain.current() is not coordinator or coordinator._owner is None
            or coordinator._owner.owner is not owner):
        _fail()
    coordinator._check_process()
    coordinator._owner.validate()
    prepared.directory.check()
    if os.listdir(prepared.directory.fd):
        _fail()
    prepared.bound = True
    try:
        return MaintenanceControl(prepared.directory, coordinator, owner)
    except Exception:
        prepared.directory.close()
        _fail()


class MaintenanceControl:
    def __init__(self, directory, coordinator, owner):
        self.directory, self.coordinator, self.owner = directory, coordinator, owner
        self.stop = threading.Event()
        self.descriptor = {
            'protocol': PROTOCOL, 'service_id': uuid.uuid4().hex, 'pid': os.getpid(),
            'uid': os.getuid(), 'runtime_epoch': coordinator._owner.epoch,
            'coordinator_epoch': coordinator.epoch, 'grant': GRANT, 'created_at': time.time(),
        }
        _descriptor(self.descriptor)
        directory.enable_io_lock(create=True)
        directory.publish('control.lock', {'protocol': PROTOCOL})
        directory.publish('service.json', self.descriptor)
        # This observer cannot carry an admitted-work context or block itself.
        # Python threads start with an empty context on supported Python 3.11/13.
        self.thread = threading.Thread(target=Context().run, args=(self._observe,),
                                       daemon=True, name='maintenance-control')
        self.thread.start()

    def close(self):
        """Stop only this observer, never reopen admission or stop the service."""
        self.stop.set()
        self.thread.join(MAX_TIMEOUT + 1)
        if not self.thread.is_alive():
            self.directory.close()

    def _request(self, value):
        now = time.time()
        if (not isinstance(value, dict)
                or set(value) != {'protocol', 'request_id', 'binding', 'grant', 'issued_at',
                                  'expires_at', 'timeout'}
                or value['protocol'] != PROTOCOL or value['grant'] != GRANT
                or _encode(value['binding']) != _encode(_binding(self.descriptor))
                or not _finite(value['issued_at']) or not _finite(value['expires_at'])
                or not value['issued_at'] <= now < value['expires_at']
                or not 0 < value['expires_at'] - value['issued_at'] <= MAX_TIMEOUT + 10
                or not _finite(value['timeout']) or not 0 <= value['timeout'] <= MAX_TIMEOUT
                or value['timeout'] > value['expires_at'] - now):
            _fail()

    def _poll(self):
        directory = self.directory
        try:
            raw = directory.read('request.json')
        except FileNotFoundError:
            return
        value = _decode(raw)
        identifier = value.get('request_id') if isinstance(value, dict) else None
        if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
            _fail()
        claimed = 'claimed-' + identifier + '.json'
        try:
            os.link('request.json', claimed, src_dir_fd=directory.fd,
                    dst_dir_fd=directory.fd, follow_symlinks=False)
        except FileExistsError:
            # A consumed request may never re-run or replace its first receipt.
            os.unlink('request.json', dir_fd=directory.fd)
            directory.sync()
            return
        os.unlink('request.json', dir_fd=directory.fd)
        directory.sync()  # A crash after here can lose a result, never replay work.
        if directory.read(claimed) != raw:
            _fail()
        receipt = {'protocol': PROTOCOL, 'request_id': identifier,
                   'binding': _binding(self.descriptor), 'request_digest': hashlib.sha256(raw).hexdigest(),
                   'status': 'rejected', 'drained': False, 'closed': False,
                   'active': {}, 'agents': {}, 'blockers': ['request_rejected'],
                   'required_components': [], 'registered_components': []}
        try:
            self._request(value)
            if _decode(directory.read('service.json')) != self.descriptor:
                _fail()
            self.coordinator._check_process()
            self.coordinator._owner.validate()
            if (self.coordinator._owner.owner is not self.owner
                    or self.coordinator._owner.epoch != self.descriptor['runtime_epoch']
                    or self.coordinator.epoch != self.descriptor['coordinator_epoch']):
                _fail()
            # The close barrier precedes all observations. Timeout never cancels
            # admitted work, and cannot reopen this monotonic barrier.
            self.coordinator.close_admission()
            result = self.coordinator.wait(value['timeout'])
            receipt.update(_sanitize_result(result))
            receipt['status'] = 'drained' if receipt['drained'] else 'closed_not_drained'
        except Exception:
            # Do not echo exception text, paths, profile/config data or request values.
            receipt.update(drained=False, closed=self.coordinator._closed,
                           blockers=['request_rejected'])
        receipt['finished_at'] = time.time()
        directory.publish('receipt-' + identifier + '.json', receipt)

    def _observe(self):
        while not self.stop.is_set():
            try:
                self._poll()
            except Exception:
                # Loss of control integrity invalidates future positive evidence.
                self.coordinator.mark_unsupported('maintenance_control_unavailable')
                self.stop.set()
                return
            self.stop.wait(0.02)


def _sanitize_result(result):
    if (type(result.get('drained')) is not bool or type(result.get('closed')) is not bool
            or not isinstance(result.get('blockers'), list)
            or any(not isinstance(code, str) or not _PUBLIC.fullmatch(code) for code in result['blockers'])):
        _fail()
    clean = {key: result[key] for key in ('drained', 'closed', 'blockers')}
    for key in ('required_components', 'registered_components'):
        values = result.get(key)
        if (not isinstance(values, list)
                or any(not isinstance(name, str) or not _PUBLIC.fullmatch(name) for name in values)):
            _fail()
        clean[key] = values
    for key in ('active', 'agents'):
        values = result.get(key)
        if (not isinstance(values, dict) or any(not isinstance(name, str) or not _PUBLIC.fullmatch(name)
                or type(count) is not int or count < 0 for name, count in values.items())):
            _fail()
        clean[key] = values
    return clean


def submit_drain(control_dir, *, grant, timeout=30, request_id=None):
    """Authenticate local OS-account authority and submit one bounded request.

    A busy operator lock rejects instead of running concurrent requests. A new
    explicit request can observe the same closed runtime after an earlier timeout.
    No PID liveness inference, process signalling or execution is performed.
    """
    if grant != GRANT or not _finite(timeout) or not 0 <= timeout <= MAX_TIMEOUT:
        _fail()
    identifier = request_id if request_id is not None else uuid.uuid4().hex
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        _fail()
    directory = None
    lock_fd = None
    try:
        import fcntl
        directory = _Directory(control_dir)
        directory.enable_io_lock()
        descriptor = _descriptor(_decode(directory.read('service.json')))
        directory.read('control.lock')
        lock_fd = os.open('control.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory.fd)
        info = os.fstat(lock_fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            _fail()
        require_filesystem_ownership(fd=lock_fd)
        if directory._identity(info) != directory._identity(
                os.stat('control.lock', dir_fd=directory.fd, follow_symlinks=False)):
            _fail()
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for prefix in ('claimed-', 'receipt-'):
            try:
                os.stat(prefix + identifier + '.json', dir_fd=directory.fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                _fail()
        now = time.time()
        request = {'protocol': PROTOCOL, 'request_id': identifier, 'binding': _binding(descriptor),
                   'grant': GRANT, 'issued_at': now, 'expires_at': now + timeout + 5,
                   'timeout': timeout}
        directory.publish('request.json', request)
        deadline = time.monotonic() + timeout + 5
        while time.monotonic() < deadline:
            if _decode(directory.read('service.json')) != descriptor:
                _fail()
            try:
                receipt = _decode(directory.read('receipt-' + identifier + '.json'))
            except FileNotFoundError:
                time.sleep(0.02)
                continue
            if (not isinstance(receipt, dict) or receipt.get('protocol') != PROTOCOL
                    or receipt.get('request_id') != identifier or receipt.get('binding') != _binding(descriptor)
                    or receipt.get('request_digest') != hashlib.sha256(_encode(request)).hexdigest()
                    or receipt.get('status') not in ('rejected', 'drained', 'closed_not_drained')):
                _fail()
            _sanitize_result(receipt)
            return receipt
        raise MaintenanceControlError('maintenance_receipt_unavailable')
    except MaintenanceControlError:
        raise
    except Exception:
        _fail()
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if directory is not None:
            directory.close()
