#!/usr/bin/env python3
"""Read-only live BULLGOD-DISCOVERY-002 acceptance against retained records.

All private paths are CLI inputs. The report contains no paths, task/spec text,
credential values, prompts, transcripts, or private memory content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import time

STAGE = 'startup'
AGENTS = ('default', 'testpilot', 'testpilot2')
INTENT_KINDS = ('submit_intent', 'native_intent', 'publication_intent')
WRITE_WORDS = {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'DROP', 'ALTER',
               'ATTACH', 'DETACH', 'VACUUM', 'REINDEX'}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True)
    p.add_argument('--service-metadata', required=True,
                   help='Private input JSON from the existing read-only runtime snapshot helper.')
    p.add_argument('--evidence-dir', required=True)
    p.add_argument('--named-probe', required=True)
    p.add_argument('--codex-probe', required=True)
    for label in ('testpilot', 'testpilot2', 'codex'):
        p.add_argument('--' + label + '-launch', required=True)
        p.add_argument('--' + label + '-task', required=True)
        p.add_argument('--' + label + '-operator-dir', required=True)
        p.add_argument('--' + label + '-socket')
    return p.parse_args()


ARGS = parse_args()
EVIDENCE = Path(ARGS.evidence_dir).resolve(strict=True)
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if REPO == EVIDENCE or REPO in EVIDENCE.parents:
    raise SystemExit('evidence directory must be outside the repository')
ISOLATED_DATA = EVIDENCE / 'observer-data'
ISOLATED_DATA.mkdir(mode=0o700, exist_ok=True)
os.chmod(ISOLATED_DATA, 0o700)
# common.log writes run.log during import. Keep it task-owned and outside live data.
os.environ['COW_DATA_DIR'] = str(ISOLATED_DATA)
os.environ['COW_LOG_DIR'] = str(ISOLATED_DATA)

# Counters are installed before CowAgent imports. No process or socket operation
# is allowed during selection. SQLite connections must use mode=ro and query_only.
GUARDS = {
    'subprocess_attempts': 0,
    'socket_connect_attempts': 0,
    'native_or_model_constructor_attempts': 0,
    'forbidden_supervisor_method_attempts': 0,
    'forbidden_transport_method_attempts': 0,
    'writable_sqlite_open_attempts': 0,
    'sqlite_write_statement_attempts': 0,
    'private_workspace_content_read_attempts': 0,
    'synthetic_unavailable_inspections': 0,
    'authorized_file_reads': {},
}
_REAL_SQLITE_CONNECT = sqlite3.connect


def sqlite_write_trace(statement):
    token = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else ''
    if token in WRITE_WORDS:
        GUARDS['sqlite_write_statement_attempts'] += 1


def guarded_sqlite_connect(database, *args, **kwargs):
    uri = kwargs.get('uri', False)
    if len(args) >= 5:
        uri = args[4]
    if not uri or not isinstance(database, str) or 'mode=ro' not in database:
        GUARDS['writable_sqlite_open_attempts'] += 1
        raise PermissionError('observer requires SQLite mode=ro')
    db = _REAL_SQLITE_CONNECT(database, *args, **kwargs)
    db.execute('PRAGMA query_only=ON')
    db.set_trace_callback(sqlite_write_trace)
    return db


sqlite3.connect = guarded_sqlite_connect


def forbidden_process(*args, **kwargs):
    GUARDS['subprocess_attempts'] += 1
    raise PermissionError('process launch denied by observer')


for method in ('Popen', 'run', 'call', 'check_call', 'check_output'):
    setattr(subprocess, method, forbidden_process)
os.system = forbidden_process
if hasattr(os, 'posix_spawn'):
    os.posix_spawn = forbidden_process

_REAL_SOCKET = socket.socket


class BlockedSocket(_REAL_SOCKET):
    def connect(self, *args, **kwargs):
        GUARDS['socket_connect_attempts'] += 1
        raise PermissionError('socket connect denied by observer')

    def connect_ex(self, *args, **kwargs):
        GUARDS['socket_connect_attempts'] += 1
        raise PermissionError('socket connect denied by observer')


socket.socket = BlockedSocket
socket.create_connection = forbidden_process


def file_stat(path):
    try:
        st = Path(path).stat()
        return {'available': True, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns,
                'inode': st.st_ino}
    except OSError as exc:
        return {'available': False, 'error': type(exc).__name__}


def safe_count_connection(path, allowed_columns):
    uri = Path(path).as_uri() + '?mode=ro'
    db = sqlite3.connect(uri, uri=True, timeout=3)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')

    def authorize(action, arg1, arg2, database, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and arg1 in allowed_columns and (arg2 == '' or arg2 in allowed_columns[arg1]):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() == 'count':
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    db.set_authorizer(authorize)
    return db


def journal_snapshot(label, operator_dir):
    directory = Path(operator_dir)
    db_path = directory / 'operator.db'
    before = file_stat(db_path)
    if not before['available']:
        return {'available': False, 'reason': 'journal_missing', 'file_stat': before}
    allowed = {
        'operator_state': {'target_id'},
        'operator_decisions': {'sequence'},
        'external_tasks': {'task_id', 'submission_started'},
        'external_events': {'event_id', 'kind'},
        'external_verifications': {'verification_id'},
        'external_approval_bindings': {'task_id', 'native_intent', 'publication_intent'},
    }
    queries = {
        'operator_state_rows': ('SELECT COUNT(target_id) FROM operator_state', ()),
        'operator_decision_rows': ('SELECT COUNT(sequence) FROM operator_decisions', ()),
        'external_task_rows': ('SELECT COUNT(task_id) FROM external_tasks', ()),
        'submitted_task_rows': ('SELECT COUNT(task_id) FROM external_tasks WHERE submission_started=1', ()),
        'external_verification_rows': ('SELECT COUNT(verification_id) FROM external_verifications', ()),
        'approval_binding_rows': ('SELECT COUNT(task_id) FROM external_approval_bindings', ()),
        'native_intent_binding_rows': ('SELECT COUNT(native_intent) FROM external_approval_bindings', ()),
        'publication_intent_binding_rows': ('SELECT COUNT(publication_intent) FROM external_approval_bindings', ()),
    }
    try:
        db = safe_count_connection(db_path, allowed)
        try:
            counts = {name: db.execute(sql, params).fetchone()[0]
                      for name, (sql, params) in queries.items()}
            rows = db.execute(
                "SELECT kind, COUNT(event_id) FROM external_events "
                "WHERE kind IN ('submit_intent','native_intent','publication_intent') "
                'GROUP BY kind'
            ).fetchall()
            intents = {kind: 0 for kind in INTENT_KINDS}
            intents.update({row[0]: row[1] for row in rows})
        finally:
            db.close()
        after = file_stat(db_path)
        return {'available': True, 'counts': counts, 'intent_event_counts': intents,
                'file_stat_before': before, 'file_stat_after': after}
    except (sqlite3.Error, OSError) as exc:
        return {'available': False, 'reason': 'metadata_query_unavailable',
                'error': type(exc).__name__, 'file_stat_before': before,
                'file_stat_after': file_stat(db_path)}


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_candidate(row):
    state = row.get('runtime_state') or {}
    state_keys = (
        'registered', 'enabled', 'enrolled', 'authorized', 'exact_task_approval',
        'credential', 'health', 'availability', 'capacity', 'revoked', 'expired',
        'operator_provenance', 'receipt_provenance', 'approved_model', 'approved_provider',
        'current_source_fingerprint', 'current_profile_fingerprint',
        'current_configuration_fingerprint', 'observation_expires_at',
        'enrollment_expires_at', 'task_expires_at', 'credential_expires_at',
    )
    safe_state = {key: state[key] for key in state_keys if key in state}
    return {key: row.get(key) for key in (
        'target_id', 'identity_kind', 'mechanism', 'model', 'provider', 'eligible_for_admission',
        'verification_status', 'dispatch_permitted', 'execution_revalidation_required',
        'proof_status', 'approval_state', 'reasons') if key in row} | {'runtime_state': safe_state}


def safe_selection(result):
    return {
        'status': result.get('status'),
        'dispatch_permitted': result.get('dispatch_permitted'),
        'execution_revalidation_required': result.get('execution_revalidation_required'),
        'reasons': result.get('reasons', []),
        'candidates': [safe_candidate(row) for row in result.get('candidates', [])],
        'rejected_alternatives': [
            {k: row.get(k) for k in ('target_id', 'mechanism', 'reasons')}
            for row in result.get('rejected_alternatives', [])
        ],
    }


def all_dispatch_false(value):
    if isinstance(value, dict):
        return all(v is False for k, v in value.items() if k == 'dispatch_permitted') and all(
            all_dispatch_false(v) for v in value.values())
    if isinstance(value, list):
        return all(all_dispatch_false(v) for v in value)
    return True


def make_requirements(spec, runtime_id, mechanism, *, persistent, coding=False):
    from agent.discovery.contracts import TaskRequirements
    from agent.discovery.sources import ANALYSIS_CONTRACT, task_spec_fingerprint
    now = time.time()
    target = runtime_id[len('cowagent.'):] if runtime_id.startswith('cowagent.') else runtime_id
    category = 'coding' if coding else ANALYSIS_CONTRACT.categories[0]
    input_contract = 'source_code.v1' if coding else ANALYSIS_CONTRACT.input_contracts[0]
    output_contract = 'code_review.v1' if coding else ANALYSIS_CONTRACT.output_contracts[0]
    return TaskRequirements(
        task_id=spec['task_id'], policy_id='safe-default', category=category,
        input_contract=input_contract, output_contract=output_contract,
        persistent_memory='required' if persistent else 'prohibited',
        persistent_context='required' if persistent else 'prohibited',
        required_tools=(), max_authority=('analyze_records',), approval='required',
        verification='independent_analysis', recovery='intent_fenced', cancellation='cooperative',
        deadline=now + 300, timeout_seconds=300, concurrency=1,
        permitted_mechanisms=(mechanism,), prohibited_mechanisms=(),
        task_spec_hash=task_spec_fingerprint(spec), requested_agent_id=target,
    )


def set_method_guard(cls, name, key):
    original = getattr(cls, name)

    def guarded(self, *args, **kwargs):
        GUARDS[key] += 1
        raise PermissionError('forbidden execution method denied')

    setattr(cls, name, guarded)
    return original


def main():
    global STAGE
    STAGE = 'application_imports'
    from agent.discovery.runtime_readers import (
        ExistingRuntimeBinding, ReadOnlyNativeConfiguration, TrustedDiscoveryHost,
    )
    from agent.discovery import runtime_readers
    from agent.external import contract as ext_contract
    from agent.external.supervisor import ExternalSupervisor
    from agent.external.transport import ExternalTransport, TransportUnavailable
    from agent.registry import AgentRegistry
    from agent import team
    from agent.discovery.sources import NativeSource

    # Paths enter only as host-supplied CLI input and remain private in memory.
    config_path = Path(ARGS.config).resolve(strict=True)
    service_file = Path(ARGS.service_metadata).resolve(strict=True)
    service_meta = json.loads(service_file.read_text(encoding='utf-8'))
    service_runtime = service_meta.get('runtime', service_meta)
    service_agents = service_runtime.get('agent_declarations', {})
    service_profiles = service_runtime.get('profile_sha256', {})
    service_models = service_runtime.get('model_config', {})
    STAGE = 'read_actual_config'
    view = ReadOnlyNativeConfiguration(config_path)
    settings = view.settings()
    roster_path = team.team_file(settings).resolve(strict=False)

    path_args = {
        'config': config_path,
        'named_probe': Path(ARGS.named_probe).resolve(strict=True),
        'codex_probe': Path(ARGS.codex_probe).resolve(strict=True),
        'testpilot_launch': Path(ARGS.testpilot_launch).resolve(strict=True),
        'testpilot_task': Path(ARGS.testpilot_task).resolve(strict=True),
        'testpilot2_launch': Path(ARGS.testpilot2_launch).resolve(strict=True),
        'testpilot2_task': Path(ARGS.testpilot2_task).resolve(strict=True),
        'codex_launch': Path(ARGS.codex_launch).resolve(strict=True),
        'codex_task': Path(ARGS.codex_task).resolve(strict=True),
    }
    allowed_file_reads = {str(path): name for name, path in path_args.items()}
    allowed_file_reads[str(roster_path)] = 'team_roster_metadata'
    GUARDS['authorized_file_reads'] = {name: 0 for name in allowed_file_reads.values()}
    allowed_workspace_paths = set()
    original_owned_bytes = runtime_readers._owned_bytes

    def guarded_owned_bytes(path, *, private=False):
        canonical = str(Path(path).resolve(strict=False))
        label = allowed_file_reads.get(canonical)
        if label is None:
            if any(Path(canonical) == workspace or workspace in Path(canonical).parents
                   for workspace in allowed_workspace_paths):
                GUARDS['private_workspace_content_read_attempts'] += 1
            raise PermissionError('observer file-read allowlist denied')
        GUARDS['authorized_file_reads'][label] = GUARDS['authorized_file_reads'].get(label, 0) + 1
        return original_owned_bytes(path, private=private)

    runtime_readers._owned_bytes = guarded_owned_bytes
    STAGE = 'read_team_roster_and_registry'
    registry = view.registry()
    if not isinstance(registry, AgentRegistry):
        raise RuntimeError('registry unavailable')
    profiles = registry.list(include_disabled=True)
    allowed_workspace_paths.update(Path(p.workspace).resolve(strict=False) for p in profiles)

    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def guarded_path_read(method, self, *args, **kwargs):
        canonical = Path(self).resolve(strict=False)
        is_workspace = any(canonical == workspace or workspace in canonical.parents
                           for workspace in allowed_workspace_paths)
        if is_workspace and str(canonical) != str(roster_path):
            GUARDS['private_workspace_content_read_attempts'] += 1
            raise PermissionError('private workspace read denied')
        return method(self, *args, **kwargs)

    Path.read_bytes = lambda self, *a, **kw: guarded_path_read(original_read_bytes, self, *a, **kw)
    Path.read_text = lambda self, *a, **kw: guarded_path_read(original_read_text, self, *a, **kw)

    registry_profiles = {}
    declaration_checks = {}
    profile_hashes = {}
    effective_routes = {}
    for profile in profiles:
        registry_profiles[profile.id] = {
            'enabled': profile.enabled, 'model': profile.model, 'bot_type': profile.bot_type,
        }
        expected = service_agents.get(profile.id)
        declaration_checks[profile.id] = expected == registry_profiles[profile.id]
        # Match the metadata helper's public projection without exposing workspaces.
        profile_hashes[profile.id] = ext_contract.digest(profile.to_dict())
        model, provider = NativeSource._route(profile, registry, settings)
        effective_routes[profile.id] = {'model': model, 'provider': provider}
    ids_match = set(registry_profiles) == set(AGENTS) == set(service_agents)
    model_matches_default_service = effective_routes.get(registry.default_agent_id) == {
        'model': service_models.get('chat_model'), 'provider': service_models.get('chat_provider')}
    source_crosscheck = {
        'registry_ids': sorted(registry_profiles),
        'public_service_ids': sorted(service_agents),
        'ids_match': ids_match,
        'profile_enabled_model_provider_declarations_match': declaration_checks,
        'all_profile_declarations_match': all(declaration_checks.values()) and ids_match,
        'registry_profile_hashes': profile_hashes,
        'public_service_profile_hashes': service_profiles,
        'default_effective_route_matches_public_models_metadata': model_matches_default_service,
        'file_config_sha256': sha_file(config_path),
        'live_config_attested': False,
        'limit': ('Config/roster declarations are compared with public service metadata. '
                  'This does not attest process environment or current memory settings. '
                  'Environment-file digest uses the real user home; logs use isolated COW_DATA_DIR.'),
    }
    if not source_crosscheck['all_profile_declarations_match'] or not model_matches_default_service:
        raise RuntimeError('registry_service_metadata_mismatch')

    STAGE = 'install_execution_guards'
    # Guard all execution methods after imports, before any binding or selection.
    originals = []
    for method in ('prepare', 'submit', 'delegate', 'approve', 'reconcile', 'cancel',
                   'status', 'result', 'flush_pending_cancellations'):
        if hasattr(ExternalSupervisor, method):
            originals.append((ExternalSupervisor, method,
                              set_method_guard(ExternalSupervisor, method,
                                               'forbidden_supervisor_method_attempts')))
    for method in ('submit', 'discover', 'status', 'cancel', 'result', 'inspect'):
        if hasattr(ExternalTransport, method):
            originals.append((ExternalTransport, method,
                              set_method_guard(ExternalTransport, method,
                                               'forbidden_transport_method_attempts')))

    from agent.protocol.agent import Agent
    from bridge.agent_bridge import AgentLLMModel
    from bridge.bridge import Bridge
    from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool
    from agent.external.cowagent_native import CowAgentNative
    for cls in (Agent, AgentLLMModel, Bridge, AgentDelegateTool, CowAgentNative):
        if hasattr(cls, '__init__'):
            originals.append((cls, '__init__', set_method_guard(
                cls, '__init__', 'native_or_model_constructor_attempts')))

    STAGE = 'snapshot_operator_records_before'
    # Read-only count snapshots include records and intent counts only.
    journal_dirs = {
        'testpilot': Path(ARGS.testpilot_operator_dir),
        'testpilot2': Path(ARGS.testpilot2_operator_dir),
        'codex': Path(ARGS.codex_operator_dir),
    }
    journals_before = {k: journal_snapshot(k, v) for k, v in journal_dirs.items()}

    STAGE = 'load_actual_bindings'
    bindings = []
    private_hashes = {}
    specs = {}
    entries = [
        ('testpilot', ARGS.testpilot_operator_dir, ARGS.testpilot_launch, ARGS.testpilot_task,
         ARGS.named_probe, ARGS.testpilot_socket),
        ('testpilot2', ARGS.testpilot2_operator_dir, ARGS.testpilot2_launch, ARGS.testpilot2_task,
         ARGS.named_probe, ARGS.testpilot2_socket),
        ('codex', ARGS.codex_operator_dir, ARGS.codex_launch, ARGS.codex_task,
         ARGS.codex_probe, ARGS.codex_socket),
    ]
    for label, operator_dir, launch, task, probe, endpoint in entries:
        for key, value in ((label + '_launch', launch), (label + '_task', task),
                           (label + '_probe', probe)):
            private_hashes[key + '_sha256'] = sha_file(value)
        binding = ExistingRuntimeBinding.from_private_files(
            operator_dir=operator_dir, credential_path=launch, spec_path=task,
            probe_receipt_path=probe, config_path=config_path, socket_path=endpoint)
        bindings.append(binding)
        specs[label] = binding.spec
    expected_runtimes = {
        'testpilot': 'cowagent.testpilot', 'testpilot2': 'cowagent.testpilot2',
        'codex': 'acceptance-runtime',
    }
    actual_runtimes = {label: b.supervisor.transport.credential.runtime_id
                        for label, b in zip(('testpilot', 'testpilot2', 'codex'), bindings)}
    if actual_runtimes != expected_runtimes:
        raise RuntimeError('retained_runtime_identity_mismatch')

    STAGE = 'select_actual_candidates'
    host = TrustedDiscoveryHost(native_configuration=view,
                                external_bindings_source=lambda: tuple(bindings))
    requirements = {
        label: make_requirements(specs[label], actual_runtimes[label],
                                 'external_runtime' if label == 'codex' else 'persistent_named',
                                 persistent=True)
        for label in ('testpilot', 'testpilot2', 'codex')
    }
    results = {}
    for label, req in requirements.items():
        results[label + '_analysis_before_observation'] = safe_selection(host.select(req))
    codex_coding = make_requirements(specs['codex'], actual_runtimes['codex'],
                                     'external_runtime', persistent=True, coding=True)
    results['codex_unsupported_coding'] = safe_selection(host.select(codex_coding))
    native_req = make_requirements(specs['testpilot'], actual_runtimes['testpilot'],
                                   'native_isolated', persistent=False)
    native_result = host.select(native_req)
    results['native_stateless_analysis'] = safe_selection(native_result)

    # Inject an in-process unavailable response for actual IDs. This object has
    # no socket API. Real endpoints are never contacted; the evidence labels it synthetic.
    synthetic_observations = []
    old_transports = []

    class SyntheticUnavailable:
        def __init__(self, credential):
            self.credential = credential

        def inspect(self):
            GUARDS['synthetic_unavailable_inspections'] += 1
            raise TransportUnavailable('controlled in-process unavailable observation')

    try:
        for binding in bindings:
            old_transports.append(binding.supervisor.transport)
            binding.supervisor.transport = SyntheticUnavailable(binding.supervisor.transport.credential)
        synthetic_observations = host.observe_external(
            list(actual_runtimes.values()), contact_authorized=True)
    finally:
        for binding, transport in zip(bindings, old_transports):
            binding.supervisor.transport = transport
    results['scenario7_synthetic_unavailable'] = {
        'label': 'controlled in-process synthetic unavailable observation; no real endpoint contact',
        'observations': [{'runtime_id': row.get('runtime_id'), 'health': row.get('health'),
                          'attestation': row.get('attestation'),
                          'dispatch_permitted': row.get('dispatch_permitted')}
                         for row in synthetic_observations],
        'selection_after_observation': {
            label: safe_selection(host.select(req)) for label, req in requirements.items()
        },
    }
    # The host is advisory only. No actual candidate was selected, so live
    # positive drift/revoke revalidation is not claimed.
    results['scenario8_drift_revoke'] = {
        'live_status': 'not_mutated; current real records remain expired or drifted',
        'positive_selected_then_changed_claim': False,
        'disposable_test_evidence': [
            'test_current_task_revocation_invalidates_retained_selection',
            'test_native_config_drift_invalidates_retained_selection',
            'test_enrollment_revocation_and_expiry_are_not_reported_as_current',
        ],
    }
    results['scenario9_selection_revalidation'] = {
        'live_status': 'no live candidate selected; positive live revalidation not claimed',
        'selected_candidate_before': False,
        'disposable_test_evidence': [
            'test_current_task_revocation_invalidates_retained_selection',
            'test_native_config_drift_invalidates_retained_selection',
        ],
    }
    results['scenario5_missing_or_stale_proof'] = {
        'live_status': 'reported in actual named/Codex candidate states above; no proof refreshed',
    }
    results['scenario6_approval_state'] = {
        'live_status': 'reported in actual candidate runtime_state above; no approval created',
    }

    STAGE = 'snapshot_operator_records_after'
    journals_after = {k: journal_snapshot(k, v) for k, v in journal_dirs.items()}
    journal_deltas = {}
    for label in journal_dirs:
        before = journals_before[label]
        after = journals_after[label]
        equal = (before.get('counts') == after.get('counts')
                 and before.get('intent_event_counts') == after.get('intent_event_counts'))
        journal_deltas[label] = {'before': before, 'after': after, 'counts_and_intents_unchanged': equal}

    no_record_changes = all(v['counts_and_intents_unchanged'] for v in journal_deltas.values())
    all_results_dispatch_false = all_dispatch_false(results)
    zero_guard_attempts = all(GUARDS[k] == 0 for k in (
        'subprocess_attempts', 'socket_connect_attempts',
        'native_or_model_constructor_attempts', 'forbidden_supervisor_method_attempts',
        'forbidden_transport_method_attempts', 'writable_sqlite_open_attempts',
        'sqlite_write_statement_attempts', 'private_workspace_content_read_attempts'))
    report = {
        'schema': 'bullgod-discovery-002-readonly-live-acceptance/1',
        'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'status': ('PARTIAL' if no_record_changes and all_results_dispatch_false and zero_guard_attempts
                   else 'BLOCKED'),
        'scope': 'actual retained private enrollments and existing runtime metadata; advisory selection only',
        'service_config_crosscheck': source_crosscheck,
        'actual_runtime_ids': actual_runtimes,
        'private_input_sha256': private_hashes,
        'scenarios': results,
        'operator_external_metadata': journal_deltas,
        'no_new_operator_or_external_rows_or_intents': no_record_changes,
        'no_dispatch_permitted_in_any_selection': all_results_dispatch_false,
        'guard_counters': GUARDS,
        'guards_all_zero': zero_guard_attempts,
        'live_limitations': [
            ('File configuration does not attest live in-memory settings or process environment; '
             'observer COW_DATA_DIR isolates logs only.'),
            'Socket files are not health evidence; the script did not contact any external runtime.',
            'Current retained approvals/credentials are expired and named source evidence is drifted.',
            'No live positive selection or selected-then-drift/revoke revalidation was available.',
            'Conversation message counts are recorded by the separate B6 metadata snapshot script.',
            'Usage telemetry is omitted because stored usage data is in message extras.',
            'No task, conversation, native execution, publication, or model request was submitted.',
        ],
        'scope_limits': ('No agent workspace content was opened except team roster metadata. '
                         'The trusted factory loaded task/spec and credential bytes. '
                         'Output contains hashes and status only.'),
    }
    output_path = EVIDENCE / 'readonly-live-acceptance.json'
    if REPO == output_path or REPO in output_path.parents:
        raise SystemExit('output path must remain private')
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.chmod(output_path, 0o600)
    print(json.dumps({'status': report['status'], 'output_file': output_path.name,
                      'no_new_operator_or_external_rows_or_intents': no_record_changes,
                      'no_dispatch_permitted_in_any_selection': all_results_dispatch_false,
                      'guards_all_zero': zero_guard_attempts,
                      'scenario_keys': sorted(results)}, sort_keys=True))
    return 0 if report['status'] == 'PARTIAL' else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        # Never print exception text or path-bearing stack traces.
        failure = {'schema': 'bullgod-discovery-002-readonly-live-acceptance/1',
                   'status': 'BLOCKED', 'stage': STAGE, 'error_class': type(exc).__name__,
                   'authorized_file_read_counts': GUARDS.get('authorized_file_reads', {}),
                   'error_code': str(exc) if re.fullmatch(r'[a-z0-9_]{1,64}', str(exc)) else 'acceptance_setup_failed'}
        target = EVIDENCE / 'readonly-live-acceptance-failure.json'
        target.write_text(json.dumps(failure, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.chmod(target, 0o600)
        print(json.dumps({'status': 'BLOCKED', 'output_file': target.name,
                          'error_code': failure['error_code']}, sort_keys=True))
        raise SystemExit(2) from None
