"""Derived native and enrolled-external sources. No probes or dispatch calls.

Callbacks here are trusted, same-process host capabilities. They must read and
validate real retained evidence, not copy flags from a model/task. All absent
integration observations remain unknown. The sources hold no identity database.
"""
from dataclasses import asdict, dataclass
import os
from types import SimpleNamespace

from agent.external import contract as external
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.operator_review import _snapshot
from agent.external.supervisor import ExternalSupervisor
from agent.permission.authority import derive_authority, restricted_authority

from .contracts import (
    AdmissionObservation, Candidate, CapabilityContract, CapabilityProof,
    DiscoveryError, model_id, sha256, token,
)


def _fresh(value, now):
    return value.issued_at <= now < value.expires_at


def task_spec_fingerprint(spec):
    """Target-independent exact semantic task, retaining all authority/content.

    Only runtime_id is omitted. Every candidate still needs its own current
    full-spec approval and exact enrolled caller scope at preview/dispatch.
    """
    normalized = external.normalize_spec(spec)
    return external.digest({key: value for key, value in normalized.items() if key != 'runtime_id'})


def _public_route(value, *, model=False):
    return value if (model_id(value) if model else token(value)) else None


def _attach(candidate, proof, admission, now):
    if proof is not None:
        if not isinstance(proof, CapabilityProof):
            candidate.reasons.append('untrusted_capability_evidence')
        elif proof.configuration_fingerprint != candidate.configuration_fingerprint:
            candidate.reasons.append('capability_configuration_mismatch')
            candidate.declared = candidate.declared or proof.contract
        elif not _fresh(proof, now):
            candidate.reasons.append('capability_evidence_stale')
            candidate.declared = candidate.declared or proof.contract
        else:
            candidate.proof = proof
            candidate.declared = candidate.declared or proof.contract
    if admission is not None:
        if not isinstance(admission, AdmissionObservation):
            candidate.reasons.append('untrusted_admission_evidence')
        elif admission.boundary_fingerprint != candidate.boundary_fingerprint:
            candidate.reasons.append('admission_binding_mismatch')
        elif not _fresh(admission, now) or now - admission.issued_at >= 30 or admission.expires_at - admission.issued_at > 30:
            candidate.reasons.append('admission_evidence_stale')
        else:
            candidate.admission = admission
    expiries = [v.expires_at for v in (candidate.proof, candidate.admission) if v]
    if candidate.expires_at is not None:
        expiries.append(candidate.expires_at)
    candidate.expires_at = min(expiries) if expiries else None
    candidate.state_fingerprint = external.digest({
        'configuration': candidate.configuration_fingerprint,
        'boundary': candidate.boundary_fingerprint, 'authority': candidate.authority,
        'proof': {'configuration': candidate.proof.configuration_fingerprint,
                  'contract': candidate.proof.contract.fingerprint,
                  'evidence': candidate.proof.evidence_fingerprint,
                  'provenance': candidate.proof.provenance} if candidate.proof else None,
        'admission': {'boundary': candidate.admission.boundary_fingerprint,
                      'health': candidate.admission.health,
                      'available_slots': candidate.admission.available_slots,
                      'active_load': candidate.admission.active_load} if candidate.admission else None,
        'approval': candidate.approval_state, 'state': candidate.state_fingerprint,
        'reasons': sorted(set(candidate.reasons)),
    })
    return candidate


class NativeSource:
    """Inspect an already attached native delegation turn without creating Agents.

    proof_source(target_id, configuration_fingerprint, now) returns a verified
    CapabilityProof. admission_source(target_id, boundary_fingerprint, now)
    returns a bounded AdmissionObservation of the existing initialized recovery
    and receiver/session boundary. Neither callback may initialize/probe a model.
    source_fingerprint_source() supplies a trusted current executable digest;
    the default reuses CowAgent's existing source-fingerprint routine.
    """
    def __init__(self, tool, *, proof_source=None, admission_source=None,
                 source_fingerprint_source=None, declared_source=None):
        self.tool = tool
        self.proof_source = proof_source
        self.admission_source = admission_source
        self.source_fingerprint_source = source_fingerprint_source
        self.declared_source = declared_source

    def candidates(self, registry, task, now):
        from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool
        from agent.permission.policy import strict_global_mode, strict_mode
        from agent.workspace import project_store, session_prefs
        from agent.protocol.agent import Agent
        from config import conf

        tool = self.tool
        context = getattr(tool, 'current_context', None)
        values = getattr(context, 'kwargs', None)
        source_id = (values.get('speaker_agent_id') or values.get('agent_id')) if isinstance(values, dict) else None
        settings = dict(conf())
        configuration_source = None
        shared_reasons = []
        try:
            if not isinstance(tool, AgentDelegateTool) or not isinstance(values, dict):
                raise DiscoveryError('native_context_unavailable')
            if not token(source_id):
                raise DiscoveryError('native_source_identity_unavailable')
            source = registry.get(source_id)
            source_agent = getattr(tool, 'context', None)
            if source_agent is None or getattr(source_agent, '_current_agent_id', None) != source.id:
                raise DiscoveryError('native_source_identity_mismatch')
            policy = tool._policy()
            from agent.tools.agent_delegate.agent_delegate import DelegationPolicy
            recovery_policy = DelegationPolicy.from_config(settings.get('agent_delegation', {}))
            root_session = values.get('delegation_root_session') or values.get('session_id')
            owner_id = values.get('delegation_host_id') or values.get('agent_id')
            if not token(root_session) or not token(owner_id):
                raise DiscoveryError('native_context_unavailable')
            registry.get(owner_id)
            roster = session_prefs.get_prefs_strict(root_session, owner_id).get('members', [])
            if not isinstance(roster, (list, tuple)) or not all(token(v) for v in roster):
                raise DiscoveryError('native_roster_invalid')
            if source.id not in set(roster) | {owner_id}:
                raise DiscoveryError('native_source_outside_team')
            trace = values.get('delegation_trace') or (source.id,)
            depth = values.get('delegation_depth', len(trace) - 1)
            if (not isinstance(trace, (list, tuple)) or not trace
                    or not all(token(v) for v in trace) or len(set(trace)) != len(trace)
                    or trace[-1] != source.id or type(depth) is not int
                    or depth != len(trace) - 1 or depth + 1 > policy.max_depth
                    or depth + 1 > recovery_policy.max_depth):
                raise DiscoveryError('native_trace_or_depth_denied')
            parent = restricted_authority(source_agent)
            if self.source_fingerprint_source:
                configuration_source = self.source_fingerprint_source()
            else:
                from agent.external.cowagent_native import source_fingerprint
                configuration_source = source_fingerprint()
            if not sha256(configuration_source):
                raise DiscoveryError('native_source_fingerprint_unknown')
        except Exception:
            # Never expose arbitrary exceptions, profile text or private roots.
            shared_reasons.append('native_context_or_authority_unavailable')

        result = []
        for profile in registry.list(include_disabled=True):
            identity = external.digest(profile.to_dict())
            configuration = external.digest({'identity': identity, 'mechanism': 'native_isolated',
                                                'source': configuration_source, 'settings': settings})
            candidate = Candidate(profile.id, 'registered', 'native_isolated', identity,
                                  configuration, external.digest({'target': profile.id, 'unknown': True}),
                                  reasons=list(shared_reasons), max_concurrency=1)
            if not profile.enabled:
                candidate.reasons.append('identity_disabled')
            proof = admission = None
            try:
                if shared_reasons:
                    raise DiscoveryError('native_context_unavailable')
                if (profile.id not in set(roster) | {owner_id} or profile.id in trace
                        or not policy.allows(source.id, profile.id)
                        or not recovery_policy.allows(source.id, profile.id)):
                    candidate.reasons.append('native_team_policy_or_cycle_denied')
                target_session = tool._session_id(source.id, profile.id, root_session)
                selected = project_store.get_project_dir_strict(target_session, profile.id)
                prefs = session_prefs.get_prefs_strict(target_session, profile.id)
                receiver_root = selected or profile.workspace
                mode = strict_mode(prefs['permission']) if prefs.get('permission') else strict_global_mode()
                # Use the same authority methods as execution on a data-only
                # view. Do not construct Agent, model, tools, Bridge or memory.
                receiver = SimpleNamespace(workspace_dir=profile.workspace,
                                           _current_agent_id=profile.id, authority=None)
                receiver.effective_cwd = lambda root=receiver_root: root
                receiver.effective_permission_mode = lambda current=mode: current
                receiver.protected_paths = lambda view=receiver: Agent.protected_paths(view)
                authority = derive_authority(parent, restricted_authority(receiver))
                tools = self._tool_classes(source_agent, authority)
                candidate.authority = tuple(sorted(tools))
                candidate.model, candidate.provider = self._route(profile, registry, settings)
                candidate.configuration_fingerprint = external.digest({
                    'identity': identity, 'mechanism': candidate.mechanism,
                    'source': configuration_source, 'settings': settings,
                    'model': candidate.model, 'provider': candidate.provider,
                })
                candidate.boundary_fingerprint = external.digest({
                    'target': profile.id, 'source': source.id, 'owner': owner_id,
                    'session': target_session, 'root_session': root_session,
                    'roster': sorted(set(roster)), 'trace': trace, 'depth': depth,
                    'policy': asdict(policy), 'authority': self._authority_dict(authority),
                })
                candidate.configuration_fingerprint = external.digest({
                    'configuration': candidate.configuration_fingerprint,
                    'authority': self._authority_dict(authority),
                })
                candidate.state_fingerprint = external.digest({'timeout': policy.timeout_seconds})
                candidate.execution_budget_seconds = policy.timeout_seconds
                if (policy.timeout_seconds > task.timeout_seconds
                        or now + policy.timeout_seconds > task.deadline):
                    candidate.reasons.append('execution_budget_incompatible')
                if self.declared_source:
                    declared = self.declared_source(profile.id)
                    if declared is not None and not isinstance(declared, CapabilityContract):
                        raise DiscoveryError('invalid_capability_declaration')
                    candidate.declared = declared
                if self.proof_source:
                    proof = self.proof_source(profile.id, candidate.configuration_fingerprint, now)
                if self.admission_source:
                    admission = self.admission_source(profile.id, candidate.boundary_fingerprint, now)
            except Exception:
                if not shared_reasons:
                    candidate.reasons.append('native_observation_unavailable')
            result.append(_attach(candidate, proof, admission, now))
        return result

    @staticmethod
    def _authority_dict(authority):
        return {'mode': authority.mode, 'capabilities': sorted(authority.capabilities),
                'read_roots': authority.read_roots, 'write_roots': authority.write_roots,
                'denied_paths': authority.denied_paths, 'restricted': authority.restricted}

    @staticmethod
    def _tool_classes(source, authority):
        from agent.tools.read.read import Read
        from agent.tools.write.write import Write
        from agent.tools.edit.edit import Edit
        from agent.tools.ls.ls import Ls
        from agent.tools.search_files.search_files import SearchFiles
        from agent.tools.current_time.current_time import TimeTool
        from agent.subagent.templates import GENERAL_PURPOSE
        classes = {Read: 'fs.read', Ls: 'fs.read', SearchFiles: 'fs.read',
                   Write: 'fs.write', Edit: 'fs.write', TimeTool: 'time'}
        def usable(roots):
            for root in roots:
                if not os.path.isdir(root):
                    continue
                if not any(os.path.commonpath((root, denied)) == denied
                           for denied in authority.denied_paths):
                    return True
            return False
        permitted = set()
        for tool in GENERAL_PURPOSE.select_tools(list(source.tools)):
            effect = classes.get(type(tool))
            if effect not in authority.capabilities:
                continue
            if effect == 'fs.read' and not usable(authority.read_roots):
                continue
            if effect == 'fs.write' and not usable(authority.write_roots):
                continue
            permitted.add(effect)
        return permitted

    @staticmethod
    def _route(profile, registry, settings):
        # Read existing routing logic without constructing its model/Bridge.
        # A fallback chain can change the effective provider after selection.
        fallback = settings.get('chat_fallback') or {}
        if not isinstance(fallback, dict) or fallback.get('enabled'):
            return None, None
        from bridge.agent_bridge import AgentLLMModel
        route = AgentLLMModel.__new__(AgentLLMModel)
        default = profile.id == registry.default_agent_id
        route.set_agent_default(None if default else profile.bot_type,
                                None if default else profile.model)
        model = route.model
        provider = route._primary_provider_id(model)
        return _public_route(model, model=True), _public_route(provider)


@dataclass(frozen=True)
class ExternalBinding:
    """Existing enrolled supervisor plus trusted observation readers only.

    discovery_envelope_source() returns a retained authenticated discover response
    envelope from an explicitly requested prior probe. Selection never probes.
    admission_source(runtime_id,boundary_fingerprint,now) observes the current
    admission boundary without reserving/consuming a slot.
    spec_source(task_id) returns the trusted frozen external task spec. This is
    separate from Luna's requirements and must match task_spec_hash exactly.
    """
    supervisor: ExternalSupervisor
    discovery_envelope_source: object
    admission_source: object
    spec_source: object


ANALYSIS_CONTRACT = CapabilityContract(
    ('analyze_records',), ('fictional_records.v1',), ('analysis_report.v1',),
    verification='independent_analysis', recovery='intent_fenced',
    cancellation='cooperative', timeout_ceiling=3600,
)


class ExternalSource:
    """Derive identities from existing supervisor credential bindings only."""
    def __init__(self, bindings_source):
        self.bindings_source = bindings_source

    def candidates(self, registry, task, now):
        result = []
        bindings = tuple(self.bindings_source())
        for binding in bindings:
            if not isinstance(binding, ExternalBinding) or not isinstance(binding.supervisor, ExternalSupervisor):
                raise DiscoveryError('invalid_external_binding')
            supervisor = binding.supervisor
            credential = supervisor.transport.credential
            runtime_id = credential.runtime_id
            named = runtime_id.startswith('cowagent.')
            target_id = runtime_id[len('cowagent.'):] if named else runtime_id
            mechanism = 'persistent_named' if named else 'external_runtime'
            scope = {'supervisor_id': credential.supervisor_id,
                     'owner_id': supervisor.owner_id, 'source_id': supervisor.source_id,
                     'conversation_id': supervisor.conversation_id, 'runtime_id': runtime_id}
            identity = external.digest({'scope': scope, 'credential': {
                'key_id': credential.key_id, 'expires_at': credential.expires_at,
                'operations': credential.operations}})
            candidate = Candidate(target_id, 'registered' if named else 'external', mechanism,
                                  identity, identity, external.digest({'identity': identity}),
                                  declared=ANALYSIS_CONTRACT, authority=('analyze_records',),
                                  runtime_id=runtime_id, max_concurrency=1 if named else None)
            proof = admission = None
            try:
                if not isinstance(supervisor.journal, ApprovalJournal):
                    raise DiscoveryError('operator_control_unavailable')
                control = supervisor.journal.control
                approved = control.status(scope, now=now)
                if not approved['approval_current']:
                    candidate.reasons.append('enrollment_not_current')
                if named:
                    profile = registry.get(target_id)
                    if target_id not in ('testpilot', 'testpilot2'):
                        raise DiscoveryError('unsupported_named_identity')
                    candidate.identity_fingerprint = external.digest(profile.to_dict())
                spec = external.normalize_spec(binding.spec_source(task.task_id))
                supervisor._identity(spec)
                if spec['task_id'] != task.task_id or task_spec_fingerprint(spec) != task.task_spec_hash:
                    raise DiscoveryError('task_binding_mismatch')
                if (spec['task']['operation'] != 'analyze_records'
                        or task.category != 'analyze_records'
                        or task.input_contract != 'fictional_records.v1'
                        or task.output_contract != 'analysis_report.v1'):
                    candidate.reasons.append('unsupported_adapter_contract')
                preview = supervisor.journal.preview_admission(spec, credential, now=now)
                candidate.reasons.extend(preview['reasons'])
                if (not preview['enrollment_approval_current']
                        or preview['enrollment_revision'] != approved['revision']
                        or preview['enrollment_review_id'] != approved.get('review_id')):
                    candidate.reasons.append('enrollment_not_current')
                candidate.approval_state = 'current' if preview['task_approval_current'] else preview['task_approval_status']
                if not preview['task_approval_current']:
                    candidate.reasons.append('approval_required' if candidate.approval_state in ('missing', 'expired')
                                             else 'task_approval_denied')
                candidate.state_fingerprint = external.digest(preview)
                expiries = [credential.expires_at, spec['authority']['expires_at']]
                expiries.extend(v for v in (preview['task_expires_at'], preview['enrollment_expires_at']) if v)
                candidate.expires_at = min(expiries)
                candidate.execution_budget_seconds = candidate.expires_at - now
                # Discovery does not rewrite the runtime's turn_timeout. The
                # current existing approval/credential/authority expiry is a
                # conservative effect/cancellation fence, not a promise that a
                # model or every descendant has exited by this instant.
                if (candidate.expires_at > task.deadline
                        or candidate.expires_at - now > task.timeout_seconds):
                    candidate.reasons.append('execution_budget_incompatible')
                envelope = binding.discovery_envelope_source()
                payload = external.authenticate(envelope, credential, kind='response', action='discover', now=now)
                if set(payload) != {'ok', 'data'} or payload['ok'] is not True:
                    raise DiscoveryError('authenticated_discovery_unavailable')
                discovery = external.validate_discovery(payload['data'], credential)
                native = _snapshot(discovery.get('native_capabilities'))
                enrollment = approved.get('review', {}).get('enrollment')
                if (not isinstance(enrollment, dict)
                        or native != {k: v for k, v in enrollment.items() if k != 'probe_sha256'}
                        or not approved['approval_current']):
                    candidate.reasons.append('capability_configuration_mismatch')
                else:
                    if named and (native.get('agent_id') != target_id
                                  or native.get('profile_sha256') != candidate.identity_fingerprint):
                        raise DiscoveryError('named_identity_or_profile_mismatch')
                    if not named and 'runtime_kind' in native:
                        raise DiscoveryError('external_identity_kind_mismatch')
                    model = native.get('model')
                    provider = native.get('provider') if named else native.get('modelProvider')
                    candidate.model, candidate.provider = _public_route(model, model=True), _public_route(provider)
                    if discovery['model'] != model or discovery['operations'] != ['analyze_records']:
                        raise DiscoveryError('unsupported_adapter_contract')
                    candidate.configuration_fingerprint = external.digest({
                        'identity': candidate.identity_fingerprint, 'credential': identity,
                        'mechanism': mechanism, 'native': native,
                        'contract': ANALYSIS_CONTRACT.fingerprint,
                        'enrollment_review_id': approved['review_id'],
                        'enrollment_revision': approved['revision'],
                    })
                    candidate.boundary_fingerprint = external.digest({
                        'identity': identity, 'epoch': discovery['epoch'],
                        'mechanism': mechanism, 'enrollment_revision': approved['revision'],
                    })
                    proof = CapabilityProof(candidate.configuration_fingerprint, ANALYSIS_CONTRACT,
                                            external.digest({'native': native, 'review': approved['review_id'],
                                                             'probe': enrollment['probe_sha256']}),
                                            envelope['issued_at'], min(envelope['expires_at'], approved['expires_at']),
                                            'approved_enrollment')
                    if binding.admission_source:
                        admission = binding.admission_source(runtime_id, candidate.boundary_fingerprint, now)
            except Exception:
                candidate.reasons.append('external_binding_or_observation_unavailable')
            result.append(_attach(candidate, proof, admission, now))
        return result
