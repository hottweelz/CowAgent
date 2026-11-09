"""Trusted file/authority and actual non-dispatching IPC boundaries."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace
import uuid

import pytest

from agent.discovery import (
    ExistingRuntimeBinding, ReadOnlyNativeConfiguration, TaskRequirements,
    TrustedDiscoveryHost, task_spec_fingerprint,
)
from agent.external import contract
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.cowagent_adapter import CowAgentRuntime
from agent.external.inspection import native_snapshot
from agent.external.operator_control import OperatorControl
from agent.external.operator_review import build_enrollment_review, build_task_review
from agent.external.supervisor import ExternalSupervisor
from agent.external.transport import ExternalTransport, TransportUnavailable
from agent.registry import AgentProfile, AgentRegistry


def private_json(path, value, mode=0o600):
    path.write_text(json.dumps(value))
    path.chmod(mode)
    return path


@pytest.fixture
def trusted(tmp_path, monkeypatch):
    import config
    from agent.permission import authority
    from agent.external.cowagent_native import ROOT
    # macOS AF_UNIX paths are shorter than pytest's nested temporary roots.
    short_root = tempfile.TemporaryDirectory(prefix='cow-dr-', dir='/tmp')
    tmp_path = Path(short_root.name).resolve()
    tmp_path.chmod(0o700)
    settings = {'model': 'global-model', 'bot_type': 'openai', 'agent_workspace': str(tmp_path / 'owner')}
    monkeypatch.setattr(config, 'config', config.Config(settings))
    config_path = private_json(tmp_path / 'config.json', settings)
    profiles = [AgentProfile('default', 'Owner', str(tmp_path / 'owner')),
                AgentProfile('testpilot', 'TestPilot', str(tmp_path / 'pilot'), model='fixture-model', bot_type='openai')]
    registry = AgentRegistry(profiles, 'default')
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    current = native_snapshot(config_path, 'testpilot', registry)
    sources = {'agent/external/' + name: hashlib.sha256((ROOT / 'agent/external' / name).read_bytes()).hexdigest()
               for name in ('cowagent_native.py', 'cowagent_adapter.py', 'cowagent_cli.py', 'operator_review.py')}
    probe = private_json(tmp_path / 'probe.json', {
        'task': 'Final complete Python regression after operator journal sidecar unlink-race fix',
        'status': 'passed', 'application_state': {'native_source_fingerprint': current['source_sha256'],
            'native_source_fingerprint_matches_pre_run': True, 'changed_source_test_hashes': sources},
        'result': {'terminal_exit_code': 0, 'passed': 202, 'failed': 0, 'junit_errors': 0, 'junit_failures': 0}}, 0o644)
    enrollment = dict(current, probe_sha256=hashlib.sha256(probe.read_bytes()).hexdigest())
    now = time.time()
    credential = contract.Credential('host', 'cowagent.testpilot', 'key-1', b'x' * 32, now + 180, ('analyze_records',))
    tid = str(uuid.uuid4())
    scope = {'supervisor_id': 'host', 'owner_id': 'default', 'source_id': 'default',
             'conversation_id': 'conversation-1', 'runtime_id': credential.runtime_id}
    spec = {'task_id': tid, 'idempotency_key': 'analysis-1', **{k: scope[k] for k in scope if k != 'supervisor_id'},
            'task': {'operation': 'analyze_records', 'artifact': 'report.json',
                     'content': json.dumps({'schema_version': 1, 'currency': 'USD', 'records': [
                         {'id': 'fictional-1', 'amount_cents': 100, 'status': 'paid'}]})},
            'authority': {'operations': ['analyze_records'], 'resource': tid, 'expires_at': now + 180},
            'verification': {'acceptance': [], 'external_state': []}}
    control = OperatorControl(tmp_path / 'operator', initialize=True)
    journal = ApprovalJournal(control)

    def decision(action, payload, revision=0):
        return control.apply({'protocol': 'cow.external.operator-command/1', 'request_id': str(uuid.uuid4()),
                              'action': action, 'scope': scope, 'expected_revision': revision, 'payload': payload})

    review = build_enrollment_review(enrollment, current=current, observed_probe_sha256=enrollment['probe_sha256'])
    decision('enroll', {'review': review, 'expires_at': now + 180})
    task_review = build_task_review(spec, review, now=now)
    decision('approve_task', {'spec': spec, 'enrollment_revision': 1, 'task_review_id': task_review['review_id'],
                              'reviewed_at': now, 'expires_at': now + 180})
    journal.create('host', spec)
    native = SimpleNamespace(enrollment=enrollment, config_path=config_path)
    native.discover = lambda: pytest.fail('legacy native discovery invoked')
    native.prepare = lambda *a, **kw: pytest.fail('native execution invoked')
    runtime_dir = tmp_path / 'runtime'
    runtime_dir.mkdir(mode=0o700)
    runtime = CowAgentRuntime(runtime_dir, tmp_path / 'runtime.sock', credential, native, approval_gate=journal)
    thread = threading.Thread(target=runtime.serve, daemon=True)
    thread.start()
    deadline = time.monotonic() + 3
    while not runtime.socket_path.exists() and time.monotonic() < deadline:
        time.sleep(.01)
    assert runtime.socket_path.exists()
    supervisor = ExternalSupervisor(journal, ExternalTransport(runtime.socket_path, credential),
                                    owner_id='default', source_id='default', conversation_id='conversation-1')
    binding = ExistingRuntimeBinding(supervisor, spec, probe, config_path)
    host = TrustedDiscoveryHost(registry_source=lambda: registry, external_bindings_source=lambda: (binding,))
    task = TaskRequirements(task_id=tid, policy_id='safe-default', category='analyze_records',
                            input_contract='fictional_records.v1', output_contract='analysis_report.v1',
                            persistent_memory='required', required_tools=(), max_authority=('analyze_records',),
                            approval='required', verification='independent_analysis', recovery='intent_fenced',
                            cancellation='cooperative', deadline=now + 500, timeout_seconds=3600, concurrency=1,
                            permitted_mechanisms=('persistent_named',), prohibited_mechanisms=(),
                            task_spec_hash=task_spec_fingerprint(spec), requested_agent_id='testpilot')
    yield SimpleNamespace(**locals())
    runtime.close()
    thread.join(timeout=3)
    short_root.cleanup()


def named(result):
    return next(row for row in result['candidates'] if row['mechanism'] == 'persistent_named')


def snapshot(path):
    with sqlite3.connect(path) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: db.execute('SELECT * FROM ' + name).fetchall() for name in tables}


def test_real_inspection_selects_with_no_dml_or_execution(trusted, monkeypatch):
    f = trusted
    import subprocess
    from bridge.agent_bridge import AgentLLMModel
    from bridge.bridge import Bridge
    from agent.protocol.agent import Agent
    from agent.external.cowagent_native import CowAgentNative
    for cls in (AgentLLMModel, Bridge, Agent, CowAgentNative):
        monkeypatch.setattr(cls, '__init__', lambda *a, **kw: pytest.fail('runtime/model construction during observation'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('process launch during observation'))
    before_operator = snapshot(f.control.path)
    before_runtime = snapshot(f.runtime.root / 'runtime.db')
    traced = []
    f.runtime.db.set_trace_callback(traced.append)
    assert named(f.host.select(f.task))['proof_status'] == 'missing'
    with pytest.raises(ValueError, match='inspection_contact_not_authorized'):
        f.host.observe_external([f.credential.runtime_id])
    rows = f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    assert rows[0]['attestation'] == 'current'
    result = f.host.select(f.task)
    assert result['status'] == 'selected', named(result)['reasons']
    assert result['selected']['proof_status'] == 'verified'
    assert result['selected']['runtime_state']['receipt_provenance'] == 'approved_content_hash'
    assert result['selected']['runtime_state']['exact_task_approval'] == 'approved'
    assert result['dispatch_permitted'] is False
    assert f.host.revalidate(result, f.task)['valid'] is True
    assert snapshot(f.control.path) == before_operator
    assert snapshot(f.runtime.root / 'runtime.db') == before_runtime
    assert traced and all(sql.lstrip().upper().startswith('SELECT') for sql in traced)
    assert not f.runtime.workers
    public = contract.canonical(result)
    assert str(f.tmp_path) not in public and f.credential.secret.hex() not in public


def test_running_codex_inspection_leaves_unsafe_attestation_unknown(trusted):
    from agent.external.codex_adapter import CodexRuntime
    f = trusted
    credential = replace(f.credential, runtime_id='existing-codex')
    policy = SimpleNamespace(discover=lambda *a: pytest.fail('unsafe discover'),
                             launch=lambda *a: pytest.fail('unsafe CLI launch'))
    runtime = CodexRuntime(f.tmp_path / 'codex', f.tmp_path / 'codex.sock', credential, policy,
                           client_factory=lambda *a: pytest.fail('app-server launch'))
    before = snapshot(runtime.root / 'runtime.db')
    try:
        observed = runtime.handle(contract.envelope(credential, 'inspect', {}))
        assert observed['health'] == 'healthy'
        assert observed['attestation'] == 'unknown'
        assert observed['available_slots'] is None
        assert observed['native_capabilities'] is None
        assert snapshot(runtime.root / 'runtime.db') == before
    finally:
        runtime.close()


def test_disabled_profile_does_not_abort_other_candidates(trusted):
    f = trusted
    profiles = [*f.profiles, AgentProfile('disabled-pilot', 'Disabled', str(f.tmp_path / 'disabled'), enabled=False)]
    f.host.service.registry_source = lambda: AgentRegistry(profiles, 'default')
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    result = f.host.select(f.task)
    assert result['status'] == 'selected'
    disabled = next(row for row in result['candidates'] if row['target_id'] == 'disabled-pilot')
    assert disabled['runtime_state']['enabled'] is False
    assert 'identity_disabled' in disabled['reasons']
    assert result['selected']['target_id'] == 'testpilot'


def test_unavailable_observation_expires_to_unknown_and_invalidates_selection(trusted, monkeypatch):
    f = trusted
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    selected = f.host.select(f.task)
    assert selected['status'] == 'selected'
    clock = [time.time()]
    f.host.clock = f.host.service.clock = lambda: clock[0]
    monkeypatch.setattr(f.supervisor.transport, 'inspect', lambda: (_ for _ in ()).throw(TransportUnavailable()))
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    fresh = named(f.host.select(f.task))
    assert fresh['runtime_state']['health'] == 'unavailable'
    assert fresh['runtime_state']['observation_expires_at'] == clock[0] + 30
    assert f.host.revalidate(selected, f.task)['valid'] is False
    clock[0] += 30
    stale = named(f.host.select(f.task))
    assert stale['runtime_state']['health'] == 'unknown'
    assert stale['runtime_state']['availability'] == 'unknown'
    assert 'runtime_inspection_stale' in stale['reasons']
    assert stale['proof_status'] == 'stale'
    assert f.host.revalidate(selected, f.task)['valid'] is False


def test_running_native_frozen_enrollment_must_match_fresh_snapshot(trusted):
    f = trusted
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    selected = f.host.select(f.task)
    assert selected['status'] == 'selected'
    # The host records and current config still agree. The already running
    # adapter has a different frozen enrollment, so it cannot accept that grant.
    f.runtime.native.enrollment = dict(f.enrollment, model='old-enrolled-model')
    result = f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    assert result[0]['health'] == 'healthy'
    assert result[0]['attestation'] == 'unknown'
    assert f.host.select(f.task)['status'] == 'denied'
    assert f.host.revalidate(selected, f.task)['valid'] is False


def test_new_approved_receipt_requires_exact_running_full_enrollment(trusted):
    f = trusted
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    selected = f.host.select(f.task)
    assert selected['status'] == 'selected'
    # Identical tested source and native snapshot; only the valid receipt bytes
    # change. Real admission still requires the complete new enrollment.
    f.probe.write_bytes(f.probe.read_bytes() + b'\n')
    current = native_snapshot(f.config_path, 'testpilot', f.registry)
    enrollment = dict(current, probe_sha256=hashlib.sha256(f.probe.read_bytes()).hexdigest())
    review = build_enrollment_review(enrollment, current=current, observed_probe_sha256=enrollment['probe_sha256'])
    f.decision('enroll', {'review': review, 'expires_at': f.now + 180}, revision=1)
    task_review = build_task_review(f.spec, review, now=f.now)
    f.decision('approve_task', {'spec': f.spec, 'enrollment_revision': 2,
        'task_review_id': task_review['review_id'], 'reviewed_at': f.now, 'expires_at': f.now + 180}, revision=1)
    assert f.runtime.native.enrollment != enrollment
    observed = f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    assert observed[0]['attestation'] == 'current'
    row = named(f.host.select(f.task))
    assert row['runtime_state']['exact_task_approval'] == 'approved'
    assert 'runtime_enrollment_mismatch' in row['reasons']
    assert row['verified_capabilities'] is None
    assert f.host.revalidate(selected, f.task)['valid'] is False
    f.runtime.native.enrollment = enrollment
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    assert f.host.select(f.task)['status'] == 'selected'


@pytest.mark.parametrize('kind', ['focused_four_files', 'old_full_source'])
def test_reenrollment_cannot_promote_unbound_or_old_tested_source(trusted, monkeypatch, kind):
    f = trusted
    from agent.external import cowagent_native
    original = json.loads(f.probe.read_text())
    if kind == 'focused_four_files':
        weak = {'milestone': 'AGENT-ROUTING-003', 'exit_code': 0, 'summary': '202 passed in 5.02s',
                'source_sha256': original['application_state']['changed_source_test_hashes'],
                'test_files': ['tests/test_cowagent_adapter.py', 'tests/test_cowagent_native.py',
                    'tests/test_approved_dispatch.py', 'tests/test_external_operator_control.py',
                    'tests/test_external_contract.py', 'tests/test_external_supervisor.py']}
        f.probe.write_text(json.dumps(weak))
    else:
        # A dependency change can leave all four named adapter file hashes
        # intact. The original full tested source must still bind the proof.
        monkeypatch.setattr(cowagent_native, 'source_fingerprint', lambda: 'd' * 64)
    current = native_snapshot(f.config_path, 'testpilot', f.registry)
    enrollment = dict(current, probe_sha256=hashlib.sha256(f.probe.read_bytes()).hexdigest())
    review = build_enrollment_review(enrollment, current=current, observed_probe_sha256=enrollment['probe_sha256'])
    f.decision('enroll', {'review': review, 'expires_at': f.now + 180}, revision=1)
    task_review = build_task_review(f.spec, review, now=f.now)
    f.decision('approve_task', {'spec': f.spec, 'enrollment_revision': 2,
        'task_review_id': task_review['review_id'], 'reviewed_at': f.now, 'expires_at': f.now + 180}, revision=1)
    f.runtime.native.enrollment = enrollment
    observed = f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    assert observed[0]['attestation'] == 'current'
    row = named(f.host.select(f.task))
    assert row['runtime_state']['exact_task_approval'] == 'approved'
    assert row['runtime_state']['receipt_provenance'] == 'approved_content_hash'
    assert row['verified_capabilities'] is None
    assert row['proof_status'] == 'invalid'
    assert any(r in row['reasons'] for r in ('proof_receipt_source_binding_missing', 'proof_receipt_schema_unsupported'))


@pytest.mark.parametrize('mutation', ['mac', 'identity', 'action', 'nonce'])
def test_inspection_tamper_or_substitution_fails_closed(trusted, monkeypatch, mutation):
    f = trusted
    # Capture a real authenticated response and corrupt it without re-signing.
    observed = f.supervisor.transport.inspect()
    field = {'mac': 'mac', 'identity': 'runtime_id', 'action': 'action', 'nonce': 'request_id'}[mutation]
    observed[field] = 'tampered'
    monkeypatch.setattr(f.supervisor.transport, 'inspect', lambda: observed)
    assert f.host.observe_external([f.credential.runtime_id], contact_authorized=True)[0]['attestation'] == 'unknown'
    assert f.host.select(f.task)['status'] == 'denied'


@pytest.mark.parametrize('mutation', ['receipt', 'config', 'profile', 'source_receipt', 'operator_state'])
def test_provenance_and_current_fingerprints_reject_drift(trusted, mutation, monkeypatch):
    f = trusted
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    selected = f.host.select(f.task)
    assert selected['status'] == 'selected'
    if mutation == 'receipt':
        f.probe.write_text('{}')
    elif mutation == 'config':
        f.config_path.write_text('{"model":"changed"}')
    elif mutation == 'profile':
        altered = AgentRegistry([f.profiles[0], replace(f.profiles[1], model='changed')], 'default')
        f.host.service.registry_source = lambda: altered
    elif mutation == 'source_receipt':
        from agent.discovery import runtime_readers
        monkeypatch.setattr(runtime_readers, '_receipt', lambda *a: (_ for _ in ()).throw(
            runtime_readers.DiscoveryError('proof_receipt_source_drift')))
    else:
        with f.control._connect() as db:
            target = 'enrollment-' + contract.digest(f.scope)
            row = json.loads(db.execute('SELECT body FROM operator_state WHERE target_id=?', (target,)).fetchone()[0])
            row['expires_at'] += 999
            db.execute('UPDATE operator_state SET body=? WHERE target_id=?', (contract.canonical(row), target))
    current = f.host.select(f.task)
    assert current['status'] == 'denied'
    assert f.host.revalidate(selected, f.task)['valid'] is False


def test_revocation_expiry_and_capacity_remain_separate(trusted):
    f = trusted
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    with f.runtime.native_lock:
        f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
        row = named(f.host.select(f.task))
        assert row['runtime_state']['capacity'] == 'at_capacity'
        assert row['runtime_state']['authorized'] is True
        assert 'concurrency_limit' in row['reasons']
    f.host.observe_external([f.credential.runtime_id], contact_authorized=True)
    selected = f.host.select(f.task)
    f.decision('revoke_task', {'task_id': f.spec['task_id']}, revision=1)
    row = named(f.host.select(f.task))
    assert row['runtime_state']['revoked'] is True
    assert row['runtime_state']['exact_task_approval'] == 'revoked'
    assert f.host.revalidate(selected, f.task)['valid'] is False
    f.host.service.clock = lambda: f.now + 181
    row = named(f.host.select(replace(f.task, deadline=f.now + 500)))
    assert row['runtime_state']['expired'] is True
    assert row['runtime_state']['credential'] == 'expired'


def test_read_only_journal_opens_without_schema_creation_and_rejects_mutation(trusted):
    f = trusted
    before = snapshot(f.control.path)
    view = ApprovalJournal.open_read_only(f.control.directory)
    assert view.preview_admission(f.spec, f.credential)['task_approval_current'] is True
    with pytest.raises(sqlite3.DatabaseError):
        with view.control._connect() as db:
            db.execute('DELETE FROM external_tasks')
    assert snapshot(f.control.path) == before
    f.control.path.chmod(0o644)
    with pytest.raises(contract.ProtocolError):
        ApprovalJournal.open_read_only(f.control.directory)
    f.control.path.chmod(0o600)


def test_existing_private_files_factory_does_not_initialize(trusted):
    f = trusted
    cred = f.credential
    launch = private_json(f.tmp_path / 'launch.json', {'credential': {
        'supervisor_id': cred.supervisor_id, 'runtime_id': cred.runtime_id, 'key_id': cred.key_id,
        'secret_hex': cred.secret.hex(), 'expires_at': cred.expires_at, 'operations': list(cred.operations)},
        'socket': str(f.runtime.socket_path)})
    spec = private_json(f.tmp_path / 'task.json', f.spec)
    binding = ExistingRuntimeBinding.from_private_files(operator_dir=f.control.directory,
                credential_path=launch, spec_path=spec, probe_receipt_path=f.probe, config_path=f.config_path)
    assert binding.supervisor.journal.control.read_only is True
    assert binding.supervisor.transport.credential == cred
    assert binding.spec == contract.normalize_spec(f.spec)
    launch.chmod(0o644)
    with pytest.raises(ValueError, match='untrusted_record_file'):
        ExistingRuntimeBinding.from_private_files(operator_dir=f.control.directory, credential_path=launch, spec_path=spec)


def test_readonly_config_uses_actual_roster_and_route_without_initializers(tmp_path, monkeypatch):
    import config
    tmp_path = tmp_path.resolve()
    tmp_path.chmod(0o700)
    monkeypatch.setattr(config, 'load_config', lambda: pytest.fail('load_config invoked'))
    monkeypatch.setattr(config, 'config', config.Config({'model': 'wrong-global', 'bot_type': 'wrong-provider'}))
    root = tmp_path / 'work'
    (root / 'agents').mkdir(parents=True, mode=0o700)
    path = private_json(tmp_path / 'config.json', {'agent_workspace': str(root), 'model': 'real-model', 'bot_type': 'custom:existing-provider'})
    private_json(root / 'agents/team.json', {'agents': [
        {'id': 'default', 'name': 'Default'}, {'id': 'testpilot', 'name': 'TestPilot'},
        {'id': 'testpilot2', 'name': 'TestPilot2', 'model': 'override-model'}], 'default_agent_id': 'default'})
    view = ReadOnlyNativeConfiguration(path)
    assert [p.id for p in view.registry().list()] == ['default', 'testpilot', 'testpilot2']
    host = TrustedDiscoveryHost(native_configuration=view, clock=lambda: 100)
    requirements = TaskRequirements(task_id=str(uuid.uuid4()), policy_id='safe-default', category='analyze_records',
        input_contract='fictional_records.v1', output_contract='analysis_report.v1', persistent_memory='prohibited',
        required_tools=(), max_authority=(), approval='optional', verification='none', recovery='none', cancellation='none',
        deadline=200, timeout_seconds=30, concurrency=1, permitted_mechanisms=('native_isolated',),
        prohibited_mechanisms=(), task_spec_hash='a' * 64)
    result = host.select(requirements)
    assert len(result['candidates']) == 3
    assert {r['target_id']: r['model'] for r in result['candidates']} == {
        'default': 'real-model', 'testpilot': 'real-model', 'testpilot2': 'override-model'}
    assert all(r['native_policy']['context'] == 'unavailable' for r in result['candidates'])
    assert all(r['provider'] == 'custom:existing-provider' for r in result['candidates'])
    assert all(r['verified_capabilities'] is None for r in result['candidates'])
    assert result['status'] == 'denied'
    # Bad roster cannot fall back to a fictional singleton default identity.
    (root / 'agents/team.json').write_text('invalid json')
    assert host.select(requirements)['reasons'] == ['authoritative_state_unavailable']


@pytest.mark.parametrize('settings,pin,model', [
    ({'model': 'gpt-4o', 'bot_type': 'chatGPT'}, None, None),
    ({'model': 'claude-sonnet-4'}, None, None),
    ({'model': 'minimax-m2'}, None, None),
    ({'model': 'gpt-4o'}, 'chatGPT', 'gpt-4o'),
    ({'model': 'gpt-4o'}, 'custom:existing', 'custom-model'),
    ({'model': 'gpt-4o', 'use_linkai': True, 'linkai_api_key': 'fixture'}, None, None),
])
def test_file_route_matches_existing_runtime_precedence(monkeypatch, settings, pin, model):
    import config
    from bridge.agent_bridge import AgentLLMModel
    from agent.discovery.sources import NativeSource
    monkeypatch.setattr(config, 'config', config.Config(settings))
    profiles = [AgentProfile('default', 'Default', '/fixture-default'),
                AgentProfile('testpilot', 'Pilot', '/fixture-pilot', bot_type=pin, model=model)]
    registry = AgentRegistry(profiles, 'default')
    view = AgentLLMModel.__new__(AgentLLMModel)
    view.set_agent_default(pin, model)
    assert NativeSource._route(profiles[1], registry, settings) == (view.model, view._primary_provider_id(view.model))
