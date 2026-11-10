"""Launch-only, one-use discovery observation before channels accept traffic.

The existing private OS-account boundary authenticates the request. No HTTP,
tool, environment setting or app command-line argument installs a launch. This
does not protect against arbitrary same-UID/root code in the process. Source
measurements describe the selected launch, not all code loaded by Python.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time


PROTOCOL = 'cow.discovery.startup/1'
ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 1024 * 1024
MAX_ITEMS = 16
_pending = None


class StartupObservationError(ValueError):
    """Sanitized launch failure; never include paths or request content."""


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def source_manifest():
    """Measure source files; deliberately do not waive private-file guards."""
    paths = [ROOT / name for name in (
        'app.py', 'config.py', 'scripts/discovery_startup.py', 'scripts/maintenance_drain.py',
    )]
    for name in ('agent', 'bridge', 'common', 'models', 'channel', 'plugins'):
        paths.extend(sorted((ROOT / name).rglob('*.py')))
    result = {}
    for path in paths:
        if path.resolve(strict=True) != path or not path.is_relative_to(ROOT):
            raise StartupObservationError('startup_source_unavailable')
        result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _json_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise StartupObservationError('startup_request_invalid')
        result[key] = value
    return result


def _invalid_constant(_value):
    raise StartupObservationError('startup_request_invalid')


def _private_directory(path):
    from agent.external.filesystem_trust import require_filesystem_ownership
    if os.getuid() != os.geteuid() or not path.is_absolute() or path.resolve(strict=True) != path:
        raise StartupObservationError('startup_private_path_unavailable')
    for directory in (path, *path.parents):
        require_filesystem_ownership(directory)
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.getuid())
                or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise StartupObservationError('startup_private_path_unavailable')
    info = path.lstat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise StartupObservationError('startup_private_path_unavailable')


def _private_bytes(path):
    from .private_files import _owned_bytes
    _private_directory(path.parent)
    value = _owned_bytes(path, private=True)
    if stat.S_IMODE(path.lstat().st_mode) != 0o600 or len(value) > MAX_BYTES:
        raise StartupObservationError('startup_request_invalid')
    return value


def _sync_directory(path):
    from agent.external.filesystem_trust import require_filesystem_ownership
    _private_directory(path)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require_filesystem_ownership(fd=fd)
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise StartupObservationError('startup_private_path_unavailable')
        os.fsync(fd)
    finally:
        os.close(fd)


def _finite(value):
    import math
    return type(value) in (int, float) and math.isfinite(value)


def _validate_request(value, now, request_path):
    from .contracts import TaskRequirements
    fields = {'protocol', 'request_id', 'request_path', 'issued_at', 'expires_at', 'uid', 'manifest',
              'interpreter', 'data_root', 'contact_authorized', 'bindings', 'requirements'}
    if (not isinstance(value, dict) or set(value) != fields or value['protocol'] != PROTOCOL
            or not isinstance(value['request_id'], str)
            or re.fullmatch('[0-9a-f]{32}', value['request_id']) is None
            or type(value['uid']) is not int or value['uid'] != os.getuid() or os.getuid() != os.geteuid()
            or not _finite(now) or not _finite(value['issued_at']) or not _finite(value['expires_at'])
            or not value['issued_at'] <= now < value['expires_at']
            or not 0 < value['expires_at'] - value['issued_at'] <= 300
            or value['contact_authorized'] is not False):
        raise StartupObservationError('startup_request_invalid')
    if value['request_path'] != str(request_path):
        raise StartupObservationError('startup_launch_binding_mismatch')
    interpreter = {'executable': os.path.abspath(sys.executable), 'prefix': os.path.abspath(sys.prefix)}
    root = os.environ.get('COW_DATA_DIR')
    if (value['interpreter'] != interpreter or not isinstance(value['data_root'], str) or not root
            or Path(root).resolve(strict=True) != Path(value['data_root'])
            or not Path(value['data_root']).is_absolute() or not Path(value['data_root']).is_dir()):
        raise StartupObservationError('startup_launch_binding_mismatch')
    if value['manifest'] != source_manifest():
        raise StartupObservationError('startup_manifest_mismatch')
    bindings, requirements = value['bindings'], value['requirements']
    if (not isinstance(bindings, list) or len(bindings) > MAX_ITEMS
            or not isinstance(requirements, list) or not 1 <= len(requirements) <= MAX_ITEMS):
        raise StartupObservationError('startup_request_invalid')
    binding_fields = {'operator_dir', 'credential_path', 'spec_path', 'probe_receipt_path', 'config_path'}
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != binding_fields:
            raise StartupObservationError('startup_request_invalid')
        for key, path in binding.items():
            if path is None and key in ('probe_receipt_path', 'config_path'):
                continue
            if not isinstance(path, str) or not Path(path).is_absolute():
                raise StartupObservationError('startup_request_invalid')
    for requirements_value in requirements:
        task = TaskRequirements.from_dict(requirements_value)
        if task.deadline <= now:
            raise StartupObservationError('startup_request_invalid')


@dataclass
class _Launch:
    request: dict
    request_hash: str
    request_path: Path
    consumed_path: Path
    receipt_path: Path
    pid: int
    uid: int
    created_monotonic: float
    phase: str = 'prepared'
    # Optional private operator control, prepared only after launch authentication.
    # It is not populated from a model, HTTP request or environment setting.
    maintenance_control: object = None

    def validate(self, phase):
        if (self is not _pending or self.phase != phase or self.pid != os.getpid()
                or self.uid != os.getuid() or self.uid != os.geteuid()
                or os.environ.get('COW_DESKTOP') == '1'):
            raise StartupObservationError('startup_launch_unavailable')
        raw = _private_bytes(self.consumed_path)
        if hashlib.sha256(raw).hexdigest() != self.request_hash:
            raise StartupObservationError('startup_request_changed')
        _validate_request(self.request, time.time(), self.request_path)
        if self.receipt_path.exists() or self.receipt_path.is_symlink():
            raise StartupObservationError('startup_receipt_exists')


def prepare_launch(request_path):
    """Called by the launch helper before importing/running app.py.

    An exclusive hardlink claims a canonical existing request atomically. It is
    then unlinked at its original name. The consumed file remains as a one-use
    artifact; no database, credential or persistent service is introduced.
    """
    global _pending
    if _pending is not None or os.environ.get('COW_DESKTOP') == '1':
        raise StartupObservationError('startup_launch_unavailable')
    path = Path(request_path)
    if path.name.endswith('.consumed'):
        raise StartupObservationError('startup_request_consumed')
    raw = _private_bytes(path)
    value = json.loads(raw, object_pairs_hook=_json_pairs, parse_constant=_invalid_constant)
    _validate_request(value, time.time(), path)
    consumed = path.with_name('.cow-discovery-' + value['request_id'] + '.consumed')
    receipt = path.with_name(path.name + '.receipt.json')
    if receipt.exists() or receipt.is_symlink():
        raise StartupObservationError('startup_receipt_exists')
    # link() never replaces an existing destination: concurrent/replayed
    # launch attempts cannot both consume this request path.
    os.link(path, consumed, follow_symlinks=False)
    path.unlink()
    _sync_directory(path.parent)
    if _private_bytes(consumed) != raw:
        raise StartupObservationError('startup_request_changed')
    _pending = _Launch(value, hashlib.sha256(raw).hexdigest(), path, consumed, receipt,
                       os.getpid(), os.getuid(), time.monotonic())
    return _pending


def begin_startup(app_path):
    """Borrow a pending launch once. An ordinary app start returns None."""
    launch = _pending
    if launch is None:
        return None
    launch.validate('prepared')
    if Path(app_path).resolve(strict=True) != ROOT / 'app.py':
        raise StartupObservationError('startup_launch_binding_mismatch')
    launch.phase = 'initializing'
    return launch


def _safe_result(value):
    if (not isinstance(value, dict) or value.get('dispatch_permitted') is not False
            or value.get('execution_revalidation_required') is not True
            or value.get('status') not in ('selected', 'denied', 'approval_required')):
        raise StartupObservationError('startup_observation_invalid')
    for candidate in value.get('candidates', []):
        if (candidate.get('dispatch_permitted') is not False
                or candidate.get('execution_revalidation_required') is not True):
            raise StartupObservationError('startup_observation_invalid')


def observe_and_publish(launch, owner):
    """Observe actual initialization, without lazy getters or adapter contact."""
    from .runtime_readers import ExistingRuntimeBinding, TrustedDiscoveryHost
    from .sources import NativeSource, _public_route
    launch.validate('initializing')
    # Validate normal initialization before reopening any external authority.
    host = TrustedDiscoveryHost.from_initialized_runtime(owner)
    bindings = tuple(ExistingRuntimeBinding.from_private_files(**binding) for binding in launch.request['bindings'])
    host.bindings_source = lambda: bindings
    runtime = host._initialized_runtime
    registry, settings = runtime.registry(), runtime.settings()
    inventory = []
    for profile in registry.list(include_disabled=True):
        model, provider = NativeSource._route(profile, registry, settings)
        inventory.append({'target_id': profile.id, 'enabled': profile.enabled,
                          'identity_fingerprint': _digest(profile.to_dict()),
                          'configured_model': _public_route(model, model=True),
                          'configured_provider': _public_route(provider),
                          'active_caller': 'unknown', 'capability_proof': 'unknown'})
    decisions = []
    for requirements in launch.request['requirements']:
        selected = host.select(requirements)
        _safe_result(selected)
        current = host.revalidate(selected, requirements)
        if (not isinstance(current, dict) or current.get('dispatch_permitted') is not False
                or current.get('execution_revalidation_required') is not True):
            raise StartupObservationError('startup_observation_invalid')
        _safe_result(current.get('current'))
        decisions.append({'selection': selected, 'revalidation': current})
    runtime.validate()
    launch.validate('initializing')
    receipt = {'protocol': PROTOCOL, 'request_id': launch.request['request_id'],
               'request_sha256': launch.request_hash, 'uid': os.getuid(), 'euid': os.geteuid(),
               'pid': os.getpid(), 'ppid': os.getppid(), 'initialization_epoch': runtime.epoch,
               'created_at': time.time(), 'launch_monotonic': launch.created_monotonic,
               'manifest_sha256': _digest(launch.request['manifest']),
               'launcher_sha256': launch.request['manifest']['scripts/discovery_startup.py'],
               'interpreter_fingerprint': _digest(launch.request['interpreter']),
               'data_root_fingerprint': _digest(launch.request['data_root']),
               'source_measurement': 'launch_files_not_universal_loaded_code_attestation',
               'inventory': inventory, 'decisions': decisions,
               'adapter_contact': False, 'dispatch_permitted': False,
               'execution_revalidation_required': True}
    raw = json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_BYTES:
        raise StartupObservationError('startup_receipt_too_large')
    _private_directory(launch.receipt_path.parent)
    fd = os.open(launch.receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        from agent.external.filesystem_trust import require_filesystem_ownership
        require_filesystem_ownership(fd=fd)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    _sync_directory(launch.receipt_path.parent)
    if _private_bytes(launch.receipt_path) != raw:
        raise StartupObservationError('startup_receipt_invalid')
    launch.phase = 'published'
    return receipt
