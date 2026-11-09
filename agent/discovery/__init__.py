"""Internal host-only discovery. Importing this package does not run agents."""
from .contracts import (
    AdmissionObservation, CapabilityContract, CapabilityProof, DiscoveryError,
    SelectionPolicy, TaskRequirements,
)
from .service import DiscoveryService
from .sources import ExternalBinding, ExternalSource, NativeSource, task_spec_fingerprint

__all__ = [
    'AdmissionObservation', 'CapabilityContract', 'CapabilityProof', 'DiscoveryError',
    'SelectionPolicy', 'TaskRequirements', 'DiscoveryService', 'ExternalBinding',
    'ExternalSource', 'NativeSource', 'task_spec_fingerprint',
]
