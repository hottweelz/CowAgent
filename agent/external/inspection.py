"""Non-dispatching observations of already running adapters.

This module never constructs a native runtime, runs preflight, loads config,
starts a process or invokes a model. Missing current attestation stays unknown.
"""
import hashlib
from pathlib import Path

from . import contract

INSPECTION_VERSION = 'cow.discovery.inspect/1'


def native_snapshot(config_path, agent_id, registry=None, settings=None):
    """Read the existing native public binding without native initialization.

    This is a trusted host operation. Configuration bytes are hashed, never
    returned; private prompts, memory and conversation databases are not read.
    """
    from config import conf
    from agent.permission.authority import _current_registry
    from agent.discovery.sources import NativeSource
    from .cowagent_native import KIND, source_fingerprint
    registry = _current_registry() if registry is None else registry
    profile = registry.get(agent_id, require_enabled=True)
    path = Path(config_path)
    if not path.is_absolute() or path.resolve(strict=True) != path or path.name != 'config.json':
        raise contract.ProtocolError('Existing native configuration required')
    settings = dict(conf()) if settings is None else dict(settings)
    model, provider = NativeSource._route(profile, registry, settings)
    if model is None or provider is None:
        raise contract.ProtocolError('Current native route unavailable')
    env_file = Path.home() / '.cow' / '.env'
    return {'runtime_kind': KIND, 'agent_id': profile.id, 'model': model, 'provider': provider,
            'profile_sha256': contract.digest(profile.to_dict()),
            'config_sha256': contract.digest({
                'file': hashlib.sha256(path.read_bytes()).hexdigest(), 'effective': settings,
                'environment_file': hashlib.sha256(env_file.read_bytes()).hexdigest() if env_file.exists() else None,
            }), 'source_sha256': source_fingerprint()}


def inspect_running(runtime, mechanism):
    """Called under the existing adapter mutex, before any replay-journal DML.

    Responses are nonce-bound by the existing transport HMAC. Inspection does
    not reserve a slot. Unknown capacity cannot become admission permission.
    """
    value = {'protocol': INSPECTION_VERSION, 'runtime_id': runtime.credential.runtime_id,
             'epoch': runtime.epoch, 'mechanism': mechanism,
             'native_capabilities': None, 'enrollment_fingerprint': None, 'attestation': 'unknown',
             'health': 'unavailable' if runtime.closed else 'healthy',
             'available_slots': None, 'active_load': None, 'max_concurrency': None}
    if runtime.closed:
        return value
    if mechanism == 'persistent_named':
        # Only the existing native object supplies the path/identity. Do not
        # call native.discover(): it constructs model/Bridge machinery.
        try:
            from .operator_review import _snapshot
            frozen = _snapshot(runtime.native.enrollment, enrollment=True)
            # Dispatch binds the entire approved enrollment, including probe.
            # Return only its opaque digest in the authenticated response.
            value['enrollment_fingerprint'] = contract.digest(frozen)
            snapshot = native_snapshot(
                runtime.native.config_path, frozen['agent_id'])
            value['native_capabilities'] = snapshot
            # Execution checks the native object's frozen enrollment. A new
            # host approval cannot update an already running adapter's binding.
            if snapshot == {k: v for k, v in frozen.items() if k != 'probe_sha256'}:
                value['attestation'] = 'current'
        except Exception:
            pass
        load = runtime.db.execute("SELECT count(*) FROM tasks WHERE state IN ('queued','running')").fetchone()[0]
        value.update(active_load=load, max_concurrency=1,
                     available_slots=0 if load or runtime.native_lock.locked() else 1)
    # Codex policy.discover() launches app-server and policy.launch() runs
    # --version. Neither is a safe inspection. No existing retained binary
    # attestation or coherent queue capacity reader exists; report unknown.
    return value
