"""Trusted host readers for existing authorities. No dispatch or auto-probes.

Paths, credentials and attached native objects are trusted host dependencies,
never task/model arguments. Operator provenance means the existing private POSIX
account plus matching audit snapshots and approved receipt bytes. It is not a
signed audit log, proof of human presence or protection from the same UID/root.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time

from agent.external import contract
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.inspection import INSPECTION_VERSION, native_snapshot
from agent.external.filesystem_trust import require_filesystem_ownership
from agent.external.operator_control import _scope
from agent.external.operator_review import _enrollment_packet, _snapshot
from agent.external.supervisor import ExternalSupervisor
from agent.external.transport import ExternalTransport, TransportUnavailable
from agent.permission.authority import _current_registry

from .contracts import AdmissionObservation, Candidate, CapabilityProof, DiscoveryError, sha256, token
from .service import DiscoveryService
from .sources import ANALYSIS_CONTRACT, NativeSource, _attach, _public_route, task_spec_fingerprint


def _owned_bytes(path, *, private=False):
    """Read an existing regular file without following replaceable symlinks."""
    path = Path(path)
    uid = os.getuid()
    if os.geteuid() != uid or not path.is_absolute() or path.resolve(strict=True) != path:
        raise DiscoveryError('untrusted_record_path')
    for parent in path.parents:
        require_filesystem_ownership(parent)
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid)
                or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise DiscoveryError('untrusted_record_path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require_filesystem_ownership(fd=fd)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1
                or info.st_mode & (0o077 if private else 0o022)
                or info.st_size > contract.MAX_MESSAGE_BYTES):
            raise DiscoveryError('untrusted_record_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(contract.MAX_MESSAGE_BYTES + 1)
        if len(data) > contract.MAX_MESSAGE_BYTES:
            raise DiscoveryError('untrusted_record_file')
        return data
    finally:
        os.close(fd)


class ReadOnlyNativeConfiguration:
    """Strict existing config/roster view without load_config or global writes.

    File settings are declarations, not a live turn. The host may supply a
    verified running-service effective_settings_source (including its env
    overrides); model/task JSON cannot supply this source.
    """
    def __init__(self, config_path, *, effective_settings_source=None):
        self.config_path = Path(config_path)
        self.effective_settings_source = effective_settings_source

    def settings(self):
        from config import _merge_legacy_namespace, _migrate_chat_fallback
        value = json.loads(_owned_bytes(self.config_path).decode('utf-8-sig'))
        if not isinstance(value, dict):
            raise DiscoveryError('native_configuration_invalid')
        _merge_legacy_namespace(value, legacy='tool', canonical='tools')
        _merge_legacy_namespace(value, legacy='skill', canonical='skills')
        _migrate_chat_fallback(value)
        if self.effective_settings_source is not None:
            value = dict(self.effective_settings_source())
        return value

    def registry(self):
        from agent import team
        from agent.registry import AgentRegistry
        settings = self.settings()
        path = team.team_file(settings)
        try:
            roster = json.loads(_owned_bytes(path).decode('utf-8-sig'))
        except FileNotFoundError:
            pass
        else:
            if not isinstance(roster, dict):
                raise DiscoveryError('native_registry_invalid')
            settings.update({key: roster[key] for key in team.TEAM_KEYS if key in roster})
        return AgentRegistry.from_config(settings)


@dataclass(frozen=True)
class ExistingRuntimeBinding:
    """Existing enrolled supervisor, frozen trusted task and retained evidence.

    The factory does not initialize a journal, start an adapter, or refresh any
    approval. Existing in-memory supervisors can also be supplied directly.
    """
    supervisor: ExternalSupervisor
    spec: dict
    probe_receipt_path: object = None
    config_path: object = None

    @classmethod
    def from_private_files(cls, *, operator_dir, credential_path, spec_path,
                           probe_receipt_path=None, config_path=None, socket_path=None):
        journal = ApprovalJournal.open_read_only(operator_dir)
        spec = contract.normalize_spec(json.loads(_owned_bytes(spec_path, private=True)))
        record = json.loads(_owned_bytes(credential_path, private=True))
        cred = record.get('credential', record)
        if 'supervisor_id' not in cred:
            # Legacy Codex key files contain only secret/expiry. Recover the
            # identity from actual existing task/approval rows, never invent it.
            with journal.control._connect() as db:
                row = db.execute('SELECT supervisor_id FROM external_tasks WHERE task_id=? AND spec_hash=?',
                                 (spec['task_id'], contract.digest(spec))).fetchone()
                binding = db.execute('SELECT receipt FROM external_approval_bindings WHERE task_id=?',
                                     (spec['task_id'],)).fetchone()
                if row is None or binding is None:
                    raise DiscoveryError('credential_identity_unavailable')
                approved = json.loads(binding['receipt'])
                if (approved['supervisor_id'] != row['supervisor_id']
                        or approved['task_hash'] != contract.digest(spec)
                        or approved['credential_expires_at'] != cred['expires_at']):
                    raise DiscoveryError('credential_identity_mismatch')
                cred = dict(cred, supervisor_id=row['supervisor_id'], runtime_id=spec['runtime_id'],
                            key_id=approved['credential_key_id'], operations=approved['credential_operations'])
        secret = cred.get('secret_hex', cred.get('secret'))
        credential = contract.Credential(cred['supervisor_id'], cred['runtime_id'], cred['key_id'],
                                         bytes.fromhex(secret), cred['expires_at'], tuple(cred['operations']))
        endpoint = socket_path or record.get('socket')
        if endpoint is None:
            # An absent endpoint stays a non-contactable existing binding.
            transport = _OfflineTransport(credential)
        else:
            transport = ExternalTransport(endpoint, credential)
        supervisor = ExternalSupervisor(journal, transport, owner_id=spec['owner_id'],
                                        source_id=spec['source_id'], conversation_id=spec['conversation_id'])
        supervisor._identity(spec)
        return cls(supervisor, spec, probe_receipt_path, config_path)


class _OfflineTransport:
    def __init__(self, credential):
        self.credential = credential

    def inspect(self):
        raise TransportUnavailable('No existing runtime endpoint')


def _authority(binding, now):
    """Read current state and authenticate its retained audit provenance."""
    supervisor = binding.supervisor
    journal = supervisor.journal
    credential = supervisor.transport.credential
    spec = contract.normalize_spec(binding.spec)
    supervisor._identity(spec)
    if not isinstance(journal, ApprovalJournal):
        raise DiscoveryError('operator_control_unavailable')
    # Even an existing writable supervisor is observed through an enforced RO
    # view. In particular, never construct ApprovalJournal(control) here.
    journal = ApprovalJournal.open_read_only(journal.control.directory)
    scope = _scope({'supervisor_id': credential.supervisor_id, **{k: spec[k] for k in
                    ('owner_id', 'source_id', 'conversation_id', 'runtime_id')}})
    with journal.control._connect() as db:
        db.execute('BEGIN')
        states = []
        for target in ('enrollment-' + contract.digest(scope), 'task-' + spec['task_id']):
            row = db.execute('SELECT revision,body,scope_hash FROM operator_state WHERE target_id=?', (target,)).fetchone()
            current = journal.control._current(db, target, scope, now)
            if row is not None:
                body = json.loads(row['body'])
                if (row['scope_hash'] != contract.digest(scope) or body.get('scope') != scope
                        or body.get('target_id') != target or body.get('operator_uid') != journal.control.uid
                        or body.get('revision') != row['revision']):
                    raise DiscoveryError('operator_provenance_invalid')
                audit = [json.loads(v['receipt']) for v in db.execute(
                    'SELECT receipt FROM operator_decisions WHERE scope_hash=? ORDER BY sequence', (contract.digest(scope),))]
                matching = [v for v in audit if v.get('target_id') == target]
                if (not matching or matching[-1].get('snapshot') != body
                        or matching[-1].get('operator_uid') != journal.control.uid
                        or matching[-1].get('revision') != body['revision']
                        or matching[-1].get('review_id') != body.get('review_id')
                        or matching[-1].get('recorded_at') != body.get('decided_at')
                        or not contract.finite(body.get('decided_at')) or body['decided_at'] > now
                        or body.get('decision') not in ('approved', 'revoked')):
                    raise DiscoveryError('operator_provenance_invalid')
            states.append(current)
        enrollment, task = states
        if enrollment.get('review'):
            _enrollment_packet(enrollment['review'])
        row = db.execute('SELECT spec_hash,supervisor_id,cancel_requested,submission_started FROM external_tasks WHERE task_id=?',
                         (spec['task_id'],)).fetchone()
        reasons = []
        if row:
            if row['spec_hash'] != contract.digest(spec) or row['supervisor_id'] != credential.supervisor_id:
                reasons.append('task_binding_mismatch')
            if row['cancel_requested']:
                reasons.append('task_cancelled')
            if row['submission_started']:
                reasons.append('submission_already_started')
        if task.get('task_hash') is not None and task['task_hash'] != contract.digest(spec):
            reasons.append('task_binding_mismatch')
        return enrollment, task, reasons, contract.digest(states)


def _receipt(binding, enrollment, state=None):
    """Validate approved source-bound test receipts, not free-form claims.

    Native capability proof requires the full tested executable fingerprint.
    Older focused receipts cover only a few files and cannot certify present
    applicability after dependency changes, even if the host re-enrolls them.
    An approved digest alone does not prove successful tests or current code.
    """
    if binding.probe_receipt_path is None:
        raise DiscoveryError('proof_receipt_missing')
    raw = _owned_bytes(binding.probe_receipt_path)
    approved = enrollment['review']['enrollment']
    if hashlib.sha256(raw).hexdigest() != approved['probe_sha256']:
        raise DiscoveryError('proof_receipt_hash_mismatch')
    if state is not None:
        state['receipt_provenance'] = 'approved_content_hash'
    receipt = json.loads(raw)
    if 'runtime_kind' not in approved:
        # Existing EXTERNAL-002B authority-probe schema. This authenticates only
        # those observed analysis constraints; current Codex executable/native
        # attestation is still independently required and currently unavailable.
        assertions = receipt.get('assertions', {})
        thread = receipt.get('preflight', {}).get('thread', {})
        if (receipt.get('schema_version') != 1
                or receipt.get('task') != 'EXTERNAL-002B native collaboration authority enrollment'
                or receipt.get('cli_version') != approved.get('cli_version')
                or receipt.get('policy_revision') != approved.get('policy_revision')
                or thread.get('model') != approved.get('model')
                or thread.get('modelProvider') != approved.get('modelProvider')
                or any(assertions.get(k) is not True for k in (
                    'native_child_mapping', 'inside_and_outside_write_approval_declined',
                    'markers_absent', 'root_model_provider_effort_unchanged', 'global_config_unchanged'))):
            raise DiscoveryError('proof_receipt_schema_unsupported')
        return approved['probe_sha256']
    if receipt.get('task') == 'Final complete Python regression after operator journal sidecar unlink-race fix':
        result = receipt.get('result', {})
        application = receipt.get('application_state', {})
        if (receipt.get('status') != 'passed' or result.get('terminal_exit_code') != 0
                or type(result.get('passed')) is not int or result['passed'] <= 0
                or any(result.get(k) != 0 for k in ('failed', 'junit_errors', 'junit_failures'))
                or application.get('native_source_fingerprint') != approved.get('source_sha256')
                or application.get('native_source_fingerprint_matches_pre_run') is not True):
            raise DiscoveryError('proof_receipt_schema_unsupported')
        sources = application.get('changed_source_test_hashes')
    else:
        raise DiscoveryError('proof_receipt_source_binding_missing')
    from agent.external.cowagent_native import source_fingerprint
    if application['native_source_fingerprint'] != source_fingerprint():
        raise DiscoveryError('proof_receipt_source_drift')
    required = {'agent/external/' + name for name in (
        'cowagent_native.py', 'cowagent_adapter.py', 'cowagent_cli.py', 'operator_review.py')}
    from agent.external.cowagent_native import ROOT
    if not isinstance(sources, dict) or not required <= set(sources):
        raise DiscoveryError('proof_receipt_source_missing')
    for name in required:
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sources[name]:
            raise DiscoveryError('proof_receipt_source_drift')
    return approved['probe_sha256']


def _inspection(envelope, credential, now):
    payload = contract.authenticate(envelope, credential, kind='response', action='inspect', now=now)
    if set(payload) != {'ok', 'data'} or payload['ok'] is not True:
        raise DiscoveryError('runtime_inspection_rejected')
    value = payload['data']
    fields = {'protocol', 'runtime_id', 'epoch', 'mechanism', 'native_capabilities', 'attestation',
              'health', 'available_slots', 'active_load', 'max_concurrency', 'enrollment_fingerprint'}
    if (not isinstance(value, dict) or set(value) != fields
            or value['protocol'] != INSPECTION_VERSION or value['runtime_id'] != credential.runtime_id
            or not token(value['epoch']) or value['attestation'] not in ('current', 'unknown')
            or value['mechanism'] not in ('persistent_named', 'external_runtime')
            or value['health'] not in ('healthy', 'unknown', 'unavailable')
            or value['enrollment_fingerprint'] is not None and not sha256(value['enrollment_fingerprint'])
            or any(v is not None and (type(v) is not int or not 0 <= v <= 1024)
                   for v in (value['available_slots'], value['active_load'], value['max_concurrency']))
            or envelope['issued_at'] > now):
        raise DiscoveryError('runtime_inspection_invalid')
    return value


class _TrustedExternalSource:
    def __init__(self, host):
        self.host = host

    def candidates(self, registry, task, now):
        return [self._candidate(binding, registry, task, now) for binding in self.host._bindings()]

    def _candidate(self, binding, registry, requirements, now):
        supervisor = binding.supervisor
        credential = supervisor.transport.credential
        rid = credential.runtime_id
        named = rid.startswith('cowagent.')
        target = rid[len('cowagent.'):] if named else rid
        mechanism = 'persistent_named' if named else 'external_runtime'
        identity = contract.digest({'runtime_id': rid, 'supervisor_id': credential.supervisor_id,
                                    'key_id': credential.key_id, 'scope': [supervisor.owner_id,
                                        supervisor.source_id, supervisor.conversation_id]})
        candidate = Candidate(target, 'registered' if named else 'external', mechanism, identity,
                              identity, identity, runtime_id=rid, declared=ANALYSIS_CONTRACT,
                              authority=('analyze_records',), max_concurrency=1 if named else None)
        state = candidate.runtime_state = {
            'registered': None, 'enabled': None, 'enrolled': 'unknown', 'authorized': 'unknown',
            'exact_task_approval': 'unknown', 'credential': 'expired' if credential.expires_at <= now else 'valid',
            'health': 'unknown', 'availability': 'unknown', 'capacity': 'unknown',
            'revoked': False, 'expired': credential.expires_at <= now,
            'operator_provenance': 'unknown', 'receipt_provenance': 'unknown',
            'enrollment_expires_at': None, 'task_expires_at': None,
            'credential_expires_at': credential.expires_at,
        }
        proof = admission = None
        try:
            if named:
                profile = registry.get(target)
                state.update(registered=True, enabled=profile.enabled)
                candidate.identity_fingerprint = contract.digest(profile.to_dict())
                candidate.model, candidate.provider = NativeSource._route(profile, registry, self.host._settings())
                if not profile.enabled:
                    candidate.reasons.append('identity_disabled')
                if target not in ('testpilot', 'testpilot2'):
                    raise DiscoveryError('unsupported_named_identity')
            enrollment, approved_task, reasons, authority_hash = _authority(binding, now)
            state.update(operator_provenance='private_operator_account',
                         enrolled=enrollment['approval_status'], authorized=enrollment['approval_current'] and credential.expires_at > now,
                         exact_task_approval=approved_task['approval_status'],
                         revoked='revoked' in (enrollment['approval_status'], approved_task['approval_status']),
                         expired=state['expired'] or any('expired' in v['approval_status'] for v in (enrollment, approved_task)),
                         enrollment_expires_at=enrollment.get('expires_at'), task_expires_at=approved_task.get('expires_at'))
            candidate.state_fingerprint = authority_hash
            candidate.reasons.extend(reasons)
            candidate.approval_state = 'current' if approved_task['approval_current'] else approved_task['approval_status']
            if not enrollment['approval_current']:
                candidate.reasons.append('enrollment_not_current')
            if not approved_task['approval_current']:
                candidate.reasons.append('approval_required' if candidate.approval_state in ('missing', 'expired') else 'task_approval_denied')
            spec = contract.normalize_spec(binding.spec)
            expiries = [credential.expires_at, spec['authority']['expires_at']]
            expiries += [v['expires_at'] for v in (enrollment, approved_task) if v.get('expires_at') is not None]
            candidate.expires_at = min(expiries)
            candidate.execution_budget_seconds = candidate.expires_at - now
            if spec['task_id'] != requirements.task_id or task_spec_fingerprint(spec) != requirements.task_spec_hash:
                raise DiscoveryError('task_binding_mismatch')
            if (spec['task']['operation'] != 'analyze_records' or spec['authority']['operations'] != ['analyze_records']
                    or requirements.category != 'analyze_records' or requirements.input_contract != 'fictional_records.v1'
                    or requirements.output_contract != 'analysis_report.v1'):
                raise DiscoveryError('unsupported_adapter_contract')
            if credential.expires_at <= now:
                candidate.reasons.append('credential_expired')
            elif not set(spec['authority']['operations']) <= set(credential.operations):
                candidate.reasons.append('credential_operation_denied')
            if spec['authority']['expires_at'] <= now:
                candidate.reasons.append('task_authority_expired')
            approved_native = enrollment.get('review', {}).get('enrollment')
            if approved_native:
                state.update(approved_model=_public_route(approved_native.get('model'), model=True),
                             approved_provider=_public_route(approved_native.get('provider') if named else approved_native.get('modelProvider')))
            # Present host file/config/profile/source equality is independent of
            # both operator approval and the fresh runtime's authenticated claim.
            current_native = None
            if named and binding.config_path is not None:
                current_native = native_snapshot(binding.config_path, target, registry, self.host._settings())
                candidate.model = _public_route(current_native['model'], model=True)
                candidate.provider = _public_route(current_native['provider'])
                state.update(current_source_fingerprint=current_native['source_sha256'],
                             current_profile_fingerprint=current_native['profile_sha256'],
                             current_configuration_fingerprint=current_native['config_sha256'])
                candidate.configuration_fingerprint = contract.digest({'identity': candidate.identity_fingerprint,
                                                                       'mechanism': mechanism, 'native': current_native})
                if not approved_native or current_native != {k: v for k, v in approved_native.items() if k != 'probe_sha256'}:
                    candidate.reasons.append('capability_configuration_mismatch')
                    candidate.proof_status = 'invalid'
            try:
                receipt_hash = _receipt(binding, enrollment, state)
            except (DiscoveryError, KeyError, TypeError, ValueError, OSError) as exc:
                reason = str(exc) if isinstance(exc, DiscoveryError) else 'proof_receipt_invalid'
                candidate.reasons.append(reason)
                candidate.proof_status = 'invalid' if binding.probe_receipt_path else 'missing'
                receipt_hash = None
            record = self.host._observations.get(rid)
            if record is None:
                raise DiscoveryError('runtime_inspection_missing')
            if record.get('unavailable'):
                issued, expiry = record.get('issued_at'), record.get('expires_at')
                if contract.finite(expiry):
                    state['observation_expires_at'] = expiry
                if (not contract.finite(issued) or not contract.finite(expiry)
                        or not issued <= now < expiry or not 0 < expiry - issued <= 30
                        or now - issued >= 30):
                    if candidate.proof_status != 'invalid':
                        candidate.proof_status = 'stale'
                    raise DiscoveryError('runtime_inspection_stale')
                candidate.expires_at = min(candidate.expires_at, expiry)
                state.update(health='unavailable', availability='unavailable')
                raise DiscoveryError('runtime_unavailable')
            envelope = record['envelope']
            if contract.finite(envelope.get('expires_at')):
                state['observation_expires_at'] = envelope['expires_at']
                if envelope['expires_at'] <= now:
                    if candidate.proof_status != 'invalid':
                        candidate.proof_status = 'stale'
                    raise DiscoveryError('runtime_inspection_stale')
            observed = _inspection(envelope, credential, now)
            if observed['mechanism'] != mechanism:
                raise DiscoveryError('runtime_identity_substitution')
            state.update(health=observed['health'],
                         availability='unknown' if observed['available_slots'] is None else 'available' if observed['available_slots'] else 'at_capacity',
                         capacity='unknown' if observed['available_slots'] is None else 'at_capacity' if not observed['available_slots'] else 'available')
            candidate.max_concurrency = observed['max_concurrency']
            boundary = contract.digest({'identity': identity, 'epoch': observed['epoch'], 'mechanism': mechanism,
                                        'enrollment_revision': enrollment['revision']})
            candidate.boundary_fingerprint = boundary
            admission = AdmissionObservation(boundary, contract.digest(envelope), envelope['issued_at'], envelope['expires_at'],
                                             observed['health'], observed['available_slots'], observed['active_load'])
            if observed['attestation'] != 'current' or current_native is None:
                raise DiscoveryError('current_runtime_attestation_unknown')
            if not approved_native or observed['enrollment_fingerprint'] != contract.digest(approved_native):
                candidate.proof_status = 'invalid'
                raise DiscoveryError('runtime_enrollment_mismatch')
            native = _snapshot(observed['native_capabilities'])
            if native != current_native or not approved_native or native != {k: v for k, v in approved_native.items() if k != 'probe_sha256'}:
                candidate.proof_status = 'invalid'
                raise DiscoveryError('capability_configuration_mismatch')
            candidate.configuration_fingerprint = contract.digest({
                'identity': candidate.identity_fingerprint, 'credential_identity': identity,
                'credential_expiry': credential.expires_at, 'credential_operations': credential.operations,
                'mechanism': mechanism, 'native': native, 'contract': ANALYSIS_CONTRACT.fingerprint,
                'review': enrollment['review_id'], 'revision': enrollment['revision']})
            if enrollment['approval_current'] and receipt_hash and candidate.proof_status != 'invalid':
                proof = CapabilityProof(candidate.configuration_fingerprint, ANALYSIS_CONTRACT,
                                        contract.digest({'receipt': receipt_hash, 'audit': authority_hash, 'native': native}),
                                        envelope['issued_at'], min(envelope['expires_at'], enrollment['expires_at']),
                                        'approved_enrollment')
                candidate.proof_status = 'verified'
            # Detect authority replacement during independent file/IPC reads.
            if _authority(binding, now)[3] != authority_hash:
                proof = None
                raise DiscoveryError('operator_state_changed')
        except DiscoveryError as exc:
            candidate.reasons.append(str(exc))
        except Exception:
            candidate.reasons.append('trusted_runtime_observation_unavailable')
        return _attach(candidate, proof, admission, now)


class _ObservedNativeSource(NativeSource):
    def __init__(self, tool, recovery_service=None, settings_source=None):
        super().__init__(tool)
        self.recovery_service = recovery_service
        self.settings_source = settings_source

    def candidates(self, registry, task, now):
        candidates = super().candidates(registry, task, now)
        from config import conf
        from agent.tools.agent_delegate.agent_delegate import DelegationPolicy
        settings = self.settings_source() if self.settings_source else dict(conf())
        policy = DelegationPolicy.from_config(settings.get('agent_delegation', {}))
        for candidate in candidates:
            profile = registry.get(candidate.target_id, require_enabled=False)
            # Offline facts are useful but cannot substitute for attached turn
            # authority, source identity, roster or live receiver observation.
            candidate.model, candidate.provider = self._route(profile, registry, settings)
            candidate.native_policy = {'context': 'attached' if not any(
                'native_context' in v for v in candidate.reasons) else 'unavailable',
                'persistent_context': False, 'persistent_memory': False,
                'max_depth': policy.max_depth, 'timeout_seconds': policy.timeout_seconds,
                'enabled': policy.enabled, 'supported_verified_contracts': [],
                'caller_receiver_restrictions': {
                    source: list(targets) for source, targets in (policy.allowed_targets or {}).items()
                    if token(source) and all(token(target) or target == '*' for target in targets)},
                'cancellation': 'cooperative', 'recovery': 'frozen_authority',
                'contract_proof': 'unavailable', 'hard_termination': False}
            candidate.runtime_state = {'registered': True, 'enabled': profile.enabled,
                                       'enrolled': 'not_applicable', 'authorized': 'unknown',
                                       'exact_task_approval': 'not_applicable', 'health': 'unknown',
                                       'availability': 'unknown', 'capacity': 'unknown'}
            if candidate.native_policy['context'] == 'attached':
                from agent.workspace import session_prefs
                turn_policy = self.tool._policy()
                values = self.tool.current_context.kwargs
                source = values.get('speaker_agent_id') or values.get('agent_id')
                owner = values.get('delegation_host_id') or values.get('agent_id')
                root = values.get('delegation_root_session') or values.get('session_id')
                members = session_prefs.get_prefs_strict(root, owner).get('members', [])
                trace = values.get('delegation_trace') or (source,)
                candidate.native_policy.update(source_agent_id=source,
                    enabled=policy.enabled and turn_policy.enabled,
                    max_depth=min(policy.max_depth, turn_policy.max_depth),
                    timeout_seconds=turn_policy.timeout_seconds,
                    global_recovery_restrictions=candidate.native_policy['caller_receiver_restrictions'],
                    caller_receiver_restrictions={source: list(targets) for source, targets in
                        (turn_policy.allowed_targets or {}).items() if token(source) and
                        all(token(target) or target == '*' for target in targets)},
                    receiver_allowed=policy.allows(source, candidate.target_id) and
                        turn_policy.allows(source, candidate.target_id),
                    team_members=sorted(set(members) | {owner}),
                    delegation_depth=values.get('delegation_depth', len(trace) - 1),
                    cycle_denied=candidate.target_id in trace)
                self._observe_admission(candidate, now)
            candidate.state_fingerprint = contract.digest({'prior': candidate.state_fingerprint,
                                                           'state': candidate.runtime_state,
                                                           'native_policy': candidate.native_policy})
        return candidates

    def _observe_admission(self, candidate, now):
        # The current implementation has no coherent global free-capacity
        # snapshot. Observe existing recovery liveness and any existing receiver
        # lock, but never turn these partial facts into a free-slot assertion.
        service = self.recovery_service
        try:
            from agent.recovery.service import RecoveryService
            from agent.tools.agent_delegate.agent_delegate import _relay_locks_guard, _relay_locks
            if not isinstance(service, RecoveryService) or service._thread is None:
                return
            healthy = service._thread.is_alive() and not service._stop.is_set() and service.last_error is None
            health = 'healthy' if healthy else 'unavailable'
            context = self.tool.current_context.kwargs
            source = context.get('speaker_agent_id') or context.get('agent_id')
            root = context.get('delegation_root_session') or context.get('session_id')
            session = self.tool._session_id(source, candidate.target_id, root)
            with _relay_locks_guard:
                receiver = _relay_locks.get(session)
                busy = receiver is not None and receiver.locked()
            # Existing initialized journal, metadata columns only. Do not call
            # get_task_store(), reconcile(), list_tasks() or acquire a new lock.
            path = service.store.path
            path = Path(path)
            if path.resolve(strict=True) != path:
                return
            for parent in path.parents:
                require_filesystem_ownership(parent)
                info = parent.lstat()
                if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.getuid())
                        or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                    return
            for item in (path, *(Path(str(path) + suffix) for suffix in ('-wal', '-shm', '-journal'))):
                try:
                    info = item.lstat()
                except FileNotFoundError:
                    if item == path:
                        return
                    continue
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_mode & 0o077 or info.st_nlink != 1):
                    return
            db = sqlite3.connect(Path(path).as_uri() + '?mode=ro', uri=True)
            try:
                table = db.execute("SELECT type FROM sqlite_master WHERE name='recovery_tasks'").fetchone()
                if table is None or table[0] != 'table':
                    return
                active = db.execute("SELECT count(*) FROM recovery_tasks WHERE state IN ('queued','running')").fetchone()[0]
            finally:
                db.close()
            candidate.runtime_state.update(health=health,
                                           availability='at_capacity' if busy else 'unknown',
                                           capacity='at_capacity' if busy else 'unknown')
            candidate.admission = AdmissionObservation(candidate.boundary_fingerprint,
                                                       contract.digest({'boundary': candidate.boundary_fingerprint,
                                                                        'healthy': healthy, 'receiver_busy': busy,
                                                                        'active': active}),
                                                       now, now + 5, health, 0 if busy else None, min(active, 1024))
            candidate.expires_at = min(candidate.expires_at or now + 5, now + 5)
        except Exception:
            return


class TrustedDiscoveryHost:
    """Supported internal read-only integration. Selection never contacts IPC.

    Call observe_external explicitly with separate trusted host authorization.
    A retained observation is bounded to 30 seconds and selection revalidates
    authoritative files/operator state each time. This object cannot dispatch.
    """
    def __init__(self, *, registry_source=_current_registry, native_tool=None, recovery_service=None,
                 native_configuration=None,
                 external_bindings_source=lambda: (), policy=None, clock=time.time):
        self.bindings_source = external_bindings_source
        self.clock = clock
        self.native_configuration = native_configuration
        self._observations = {}
        if native_configuration is not None:
            if native_tool is not None:
                raise DiscoveryError('offline_configuration_cannot_supply_live_context')
            registry_source = native_configuration.registry
        self.service = DiscoveryService(registry_source, native_source=_ObservedNativeSource(native_tool, recovery_service, self._settings),
                                        external_source=_TrustedExternalSource(self), policy=policy, clock=clock)

    def _settings(self):
        if self.native_configuration is not None:
            return self.native_configuration.settings()
        from config import conf
        return dict(conf())

    def _bindings(self):
        bindings = tuple(self.bindings_source())
        if any(not isinstance(v, ExistingRuntimeBinding) or not isinstance(v.supervisor, ExternalSupervisor)
               for v in bindings):
            raise DiscoveryError('invalid_external_binding')
        return bindings

    def observe_external(self, runtime_ids, *, contact_authorized=False):
        if contact_authorized is not True:
            raise DiscoveryError('inspection_contact_not_authorized')
        if not isinstance(runtime_ids, (list, tuple, set)) or not all(token(v) for v in runtime_ids):
            raise DiscoveryError('invalid_inspection_targets')
        result = []
        for binding in self._bindings():
            credential = binding.supervisor.transport.credential
            rid = credential.runtime_id
            if rid not in runtime_ids:
                continue
            try:
                response = binding.supervisor.transport.inspect()
                value = _inspection(response, credential, self.clock())
                # Preserve the actual response MAC/action/nonce. No host signing.
                self._observations[rid] = {'envelope': json.loads(contract.canonical(response))}
                result.append({'runtime_id': rid, 'health': value['health'], 'attestation': value['attestation'],
                               'dispatch_permitted': False})
            except TransportUnavailable:
                observed_at = self.clock()
                if contract.finite(observed_at):
                    self._observations[rid] = {'unavailable': True, 'issued_at': observed_at,
                                               'expires_at': min(observed_at + 30, credential.expires_at)}
                else:
                    self._observations.pop(rid, None)
                result.append({'runtime_id': rid, 'health': 'unavailable', 'attestation': 'unknown',
                               'dispatch_permitted': False})
            except Exception:
                self._observations.pop(rid, None)
                result.append({'runtime_id': rid, 'health': 'unknown', 'attestation': 'unknown',
                               'dispatch_permitted': False})
        return result

    def select(self, requirements):
        return self.service.select(requirements)

    def discover(self, requirements):
        return self.select(requirements)

    def revalidate(self, selection, requirements):
        return self.service.revalidate(selection, requirements)
