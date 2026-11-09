"""Strict public requirements and trusted-host evidence for derived discovery.

Only TaskRequirements and SelectionPolicy accept untrusted JSON. Evidence objects
are capabilities of the trusted host integration, never model-facing arguments.
No object in this module grants execution authority.
"""
from dataclasses import MISSING, asdict, dataclass, field
import re

from agent.external.contract import canonical, digest, finite, identifier, task_id

VERSION = 'cow.discovery/1'
TASK_VERSION = 'cow.discovery.task/1'
POLICY_VERSION = 'cow.discovery.policy/1'
CAPABILITY_VERSION = 'cow.discovery.capability/1'
MECHANISMS = ('native_isolated', 'persistent_named', 'external_runtime')
EFFECTS = frozenset({'fs.read', 'fs.write', 'time', 'analyze_records'})
VERIFICATION = ('none', 'native_checks', 'independent_analysis')
RECOVERY = ('none', 'frozen_authority', 'intent_fenced')
CANCELLATION = ('none', 'cooperative')


class DiscoveryError(ValueError):
    """A public reason code; never include task values or raw exceptions."""


def sha256(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def token(value):
    return identifier(value) and value not in ('.', '..')


def model_id(value):
    """Bounded opaque provider/model IDs; exclude paths, URLs and controls."""
    return (isinstance(value, str) and len(value) <= 128
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*(?:/[A-Za-z0-9][A-Za-z0-9_.:-]*)?', value) is not None
            and '..' not in value and '://' not in value)


def tokens(value, *, choices=None):
    return (isinstance(value, (list, tuple)) and len(value) <= 64
            and all(token(item) and (choices is None or item in choices) for item in value)
            and len(set(value)) == len(value))


def positive(value):
    return type(value) is int and 1 <= value <= 1024


@dataclass(frozen=True)
class TaskRequirements:
    task_id: str
    policy_id: str
    category: str
    input_contract: str
    output_contract: str
    persistent_memory: str
    required_tools: tuple
    max_authority: tuple
    approval: str
    verification: str
    recovery: str
    cancellation: str
    deadline: float
    timeout_seconds: float
    concurrency: int
    permitted_mechanisms: tuple
    prohibited_mechanisms: tuple
    task_spec_hash: str
    persistent_context: str = 'optional'
    model: str | None = None
    provider: str | None = None
    requested_agent_id: str | None = None
    protocol: str = TASK_VERSION

    def __post_init__(self):
        for name in ('required_tools', 'max_authority', 'permitted_mechanisms', 'prohibited_mechanisms'):
            value = getattr(self, name)
            if not tokens(value, choices=MECHANISMS if 'mechanisms' in name else None):
                raise DiscoveryError('invalid_requirements')
            object.__setattr__(self, name, tuple(value))
        if (self.protocol != TASK_VERSION or not task_id(self.task_id)
                or not all(token(getattr(self, name)) for name in
                           ('policy_id', 'category', 'input_contract', 'output_contract'))
                or not sha256(self.task_spec_hash)
                or self.persistent_memory not in ('required', 'prohibited', 'optional')
                or self.persistent_context not in ('required', 'prohibited', 'optional')
                or self.approval not in ('required', 'optional', 'prohibited')
                or self.verification not in VERIFICATION or self.recovery not in RECOVERY
                or self.cancellation not in CANCELLATION
                or not finite(self.deadline) or not finite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 3600 or not positive(self.concurrency)
                or not self.permitted_mechanisms
                or not set(self.max_authority) <= EFFECTS
                or self.model is not None and not model_id(self.model)
                or any(value is not None and not token(value)
                       for value in (self.provider, self.requested_agent_id))):
            raise DiscoveryError('invalid_requirements')
        if (set(self.permitted_mechanisms) & set(self.prohibited_mechanisms)
                or self.persistent_memory == 'required' and self.persistent_context == 'prohibited'
                or self.persistent_memory == 'prohibited' and self.persistent_context == 'required'
                or self.persistent_memory == 'required'
                and not set(self.permitted_mechanisms) - set(self.prohibited_mechanisms)
                & {'persistent_named', 'external_runtime'}):
            raise DiscoveryError('conflicting_requirements')

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise DiscoveryError('invalid_requirements')
        required = {name for name, item in cls.__dataclass_fields__.items()
                    if item.default is MISSING and item.default_factory is MISSING}
        allowed = set(cls.__dataclass_fields__)
        if set(value) - allowed or not required <= set(value):
            raise DiscoveryError('invalid_requirements')
        try:
            return cls(**value)
        except DiscoveryError:
            raise
        except (TypeError, ValueError, OverflowError):
            raise DiscoveryError('invalid_requirements') from None

    def to_dict(self):
        return __import__('json').loads(canonical(asdict(self)))

    @property
    def fingerprint(self):
        return digest(self.to_dict())


@dataclass(frozen=True)
class SelectionPolicy:
    policy_id: str = 'safe-default'
    revision: int = 1
    preferred_targets: tuple = ()
    preferred_models: tuple = ()
    protocol: str = POLICY_VERSION

    def __post_init__(self):
        if (self.protocol != POLICY_VERSION or not token(self.policy_id)
                or type(self.revision) is not int or self.revision < 1
                or not tokens(self.preferred_targets)
                or not isinstance(self.preferred_models, (list, tuple))
                or len(self.preferred_models) > 64 or not all(model_id(v) for v in self.preferred_models)
                or len(set(self.preferred_models)) != len(self.preferred_models)):
            raise DiscoveryError('invalid_policy')
        object.__setattr__(self, 'preferred_targets', tuple(self.preferred_targets))
        object.__setattr__(self, 'preferred_models', tuple(self.preferred_models))

    @property
    def fingerprint(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class CapabilityContract:
    """Machine-readable claim. A claim alone never passes eligibility."""
    categories: tuple
    input_contracts: tuple
    output_contracts: tuple
    tools: tuple = ()
    verification: str = 'none'
    recovery: str = 'none'
    cancellation: str = 'cooperative'
    timeout_ceiling: float = 600
    protocol: str = CAPABILITY_VERSION

    def __post_init__(self):
        for name in ('categories', 'input_contracts', 'output_contracts', 'tools'):
            if not tokens(getattr(self, name)):
                raise DiscoveryError('invalid_capability_contract')
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if (self.protocol != CAPABILITY_VERSION or self.verification not in VERIFICATION
                or self.recovery not in RECOVERY or self.cancellation not in CANCELLATION
                or not finite(self.timeout_ceiling) or not 0 < self.timeout_ceiling <= 3600):
            raise DiscoveryError('invalid_capability_contract')

    @property
    def fingerprint(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class CapabilityProof:
    """A receipt supplied only by a trusted host verifier, bound to current code.

    configuration_fingerprint covers identity, source, configuration, profile,
    model/provider and mechanism. Evidence is not accepted from TaskRequirements.
    The host must authenticate/validate its receipt before constructing this type.
    """
    configuration_fingerprint: str
    contract: CapabilityContract
    evidence_fingerprint: str
    issued_at: float
    expires_at: float
    provenance: str = 'trusted_test'

    def __post_init__(self):
        if (not sha256(self.configuration_fingerprint) or not sha256(self.evidence_fingerprint)
                or not isinstance(self.contract, CapabilityContract)
                or self.provenance not in ('trusted_test', 'approved_enrollment')
                or not finite(self.issued_at) or not finite(self.expires_at)
                or self.expires_at <= self.issued_at):
            raise DiscoveryError('invalid_capability_proof')


@dataclass(frozen=True)
class AdmissionObservation:
    """Trusted host observation of an existing admission boundary, never a lease.

    boundary_fingerprint binds the concrete current receiver/session or enrolled
    runtime. Missing admission observations fail closed. No slot is reserved.
    """
    boundary_fingerprint: str
    evidence_fingerprint: str
    issued_at: float
    expires_at: float
    health: str = 'unknown'
    available_slots: int | None = None
    active_load: int | None = None

    def __post_init__(self):
        if (not sha256(self.boundary_fingerprint) or not sha256(self.evidence_fingerprint)
                or not finite(self.issued_at) or not finite(self.expires_at)
                or self.expires_at <= self.issued_at or self.health not in ('healthy', 'unavailable', 'unknown')
                or any(v is not None and (type(v) is not int or not 0 <= v <= 1024)
                       for v in (self.available_slots, self.active_load))):
            raise DiscoveryError('invalid_admission_observation')


@dataclass
class Candidate:
    """Internal derived state. Only public() is returned to the supervisor."""
    target_id: str
    identity_kind: str
    mechanism: str
    identity_fingerprint: str
    configuration_fingerprint: str
    boundary_fingerprint: str
    model: str | None = None
    provider: str | None = None
    declared: CapabilityContract | None = None
    proof: CapabilityProof | None = None
    admission: AdmissionObservation | None = None
    authority: tuple = ()
    reasons: list = field(default_factory=list)
    approval_state: str = 'not_required'
    state_fingerprint: str = ''
    expires_at: float | None = None
    runtime_id: str | None = None
    max_concurrency: int | None = None
    execution_budget_seconds: float | None = None

    @property
    def key(self):
        return self.target_id + ':' + self.mechanism

    def public(self):
        persistent = self.mechanism == 'persistent_named'
        isolated = self.mechanism == 'native_isolated'
        contract = self.proof.contract if self.proof else self.declared
        return {
            'target_id': self.target_id, 'display_name': self.target_id,
            'role': 'registered_agent' if self.identity_kind == 'registered' else 'external_runtime',
            'identity_kind': self.identity_kind, 'runtime_id': self.runtime_id,
            'mechanism': self.mechanism, 'capability_version': CAPABILITY_VERSION,
            'declared_capabilities': asdict(self.declared) if self.declared else None,
            'verified_capabilities': asdict(self.proof.contract) if self.proof else None,
            'capability_provenance': self.proof.provenance if self.proof else 'unverified',
            'model': self.model, 'provider': self.provider,
            'persistent_context': True if persistent else False if isolated else None,
            'persistent_memory': True if persistent else False if isolated else None,
            'memory_owner': self.target_id if persistent else 'none' if isolated else 'runtime',
            'prior_manual_transcript_restored': False,
            'supported_tools': list(contract.tools) if contract else [],
            'authority': list(self.authority), 'approval_state': self.approval_state,
            'health': self.admission.health if self.admission else 'unknown',
            'available_slots': self.admission.available_slots if self.admission else None,
            'active_load': self.admission.active_load if self.admission else None,
            'concurrency': {'boundary_fingerprint': self.boundary_fingerprint,
                            'max_concurrent': self.max_concurrency,
                            'provider_parallelism': 'unknown'},
            'verification': contract.verification if contract else 'unknown',
            'recovery': contract.recovery if contract else 'unknown',
            'cancellation': contract.cancellation if contract else 'unknown',
            'execution_budget_seconds': self.execution_budget_seconds,
            'execution_budget_semantics': 'cooperative_cancellation_fence',
            'identity_fingerprint': self.identity_fingerprint,
            'configuration_fingerprint': self.configuration_fingerprint,
            'evidence_fingerprint': self.proof.evidence_fingerprint if self.proof else None,
            'state_fingerprint': self.state_fingerprint, 'expires_at': self.expires_at,
        }
