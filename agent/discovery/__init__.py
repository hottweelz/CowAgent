"""Internal host-only discovery with lazy public exports.

Cold request validation must not import the runtime's logging/configuration
graph. Explicitly accessing an exported runtime API loads its normal module;
the public objects and import paths remain the same.
"""
from importlib import import_module

__all__ = [
    'AdmissionObservation', 'CapabilityContract', 'CapabilityProof', 'DiscoveryError',
    'SelectionPolicy', 'TaskRequirements', 'DiscoveryService', 'ExternalBinding',
    'ExternalSource', 'NativeSource', 'task_spec_fingerprint',
    'ExistingRuntimeBinding', 'ReadOnlyNativeConfiguration', 'TrustedDiscoveryHost',
]

_EXPORT_MODULES = {
    **dict.fromkeys(('AdmissionObservation', 'CapabilityContract', 'CapabilityProof',
                     'DiscoveryError', 'SelectionPolicy', 'TaskRequirements'), 'contracts'),
    'DiscoveryService': 'service',
    **dict.fromkeys(('ExternalBinding', 'ExternalSource', 'NativeSource', 'task_spec_fingerprint'), 'sources'),
    **dict.fromkeys(('ExistingRuntimeBinding', 'ReadOnlyNativeConfiguration',
                     'TrustedDiscoveryHost'), 'runtime_readers'),
}


def __getattr__(name):
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    value = getattr(import_module('.' + module, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
