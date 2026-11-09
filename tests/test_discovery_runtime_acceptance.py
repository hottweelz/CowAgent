"""Gate B acceptance tests for trusted discovery readers.

All external state is owned by pytest's temporary directory. IPC responses use
the real CowAgent envelope and transport, but the local fixture does not start
an adapter process or native model.
"""
import hashlib
import json
import os
from pathlib import Path
import socketserver
import tempfile
import threading
import time
import uuid

import pytest

from agent.discovery.contracts import TaskRequirements
from agent.discovery.runtime_readers import ExistingRuntimeBinding, TrustedDiscoveryHost
from agent.discovery.sources import task_spec_fingerprint
from agent.external import contract
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.operator_control import OperatorControl, VERSION as OPERATOR_VERSION
from agent.external.operator_review import build_enrollment_review, build_task_review
from agent.registry import AgentProfile, AgentRegistry
from tests.test_external_operator_control import SCOPE


def _command(action, payload, *, scope, expected_revision):
    return {
        'protocol': OPERATOR_VERSION,
        'request_id': str(uuid.uuid4()),
        'action': action,
        'scope': dict(scope),
        'expected_revision': expected_revision,
        'payload': payload,
    }


class _InspectHandler(socketserver.StreamRequestHandler):
    def handle(self):
        request = json.loads(self.rfile.readline())
        fixture = self.server.fixture
        fixture.requests.append(request)
        contract.authenticate(request, fixture.credential, kind='request')
        response = fixture.response(request)
        self.wfile.write(contract.canonical(response).encode() + b'\n')


class _InspectServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False


class _InspectFixture:
    def __init__(self, socket_path, credential):
        self.credential = credential
        self.requests = []
        self.payload = None
        self.mode = 'valid'
        self.server = _InspectServer(str(socket_path), _InspectHandler)
        self.server.fixture = self
        os.chmod(socket_path, 0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def response(self, request):
        issue_time = request['issued_at']
        payload = {'ok': True, 'data': dict(self.payload)}
        if self.mode == 'bad_runtime_id':
            payload['data']['runtime_id'] = 'cowagent.testpilot2'
        if self.mode == 'bad_enrollment_fingerprint':
            payload['data']['enrollment_fingerprint'] = '0' * 64
        if self.mode == 'unsupported_mechanism':
            payload['data']['mechanism'] = 'native_isolated'
        response = contract.envelope(
            self.credential, 'inspect', payload, request_id=request['request_id'],
            kind='response', now=issue_time,
        )
        if self.mode == 'tampered_mac':
            response['mac'] = '0' * 64
        elif self.mode == 'stale':
            response = contract.envelope(
                self.credential, 'inspect', payload, request_id=request['request_id'],
                kind='response', now=issue_time - 40,
            )
        elif self.mode == 'replayed_nonce':
            response['request_id'] = str(uuid.uuid4())
            unsigned = {k: v for k, v in response.items() if k != 'mac'}
            import hmac
            response['mac'] = hmac.new(self.credential.secret, contract.canonical(unsigned).encode(),
                                       hashlib.sha256).hexdigest()
        return response

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _snapshot(tmp_path, monkeypatch, *, receipt_variant='full'):
    """Create genuine temporary operator approval and host-owned evidence."""
    import config
    from agent.external import cowagent_native
    from agent.external import inspection
    from agent.permission import authority

    now = time.time()
    default_workspace = tmp_path / 'default-workspace'
    target_workspace = tmp_path / 'testpilot-workspace'
    default_workspace.mkdir(mode=0o700)
    target_workspace.mkdir(mode=0o700)
    registry = AgentRegistry([
        AgentProfile('default', 'CowAgent', str(default_workspace)),
        AgentProfile('testpilot', 'TestPilot', str(target_workspace),
                     model='gpt-6.1-luna', bot_type='openai'),
    ], 'default')
    settings = {'model': 'gpt-6.1-luna', 'bot_type': 'openai', 'chat_fallback': {'enabled': False}}
    monkeypatch.setattr(config, 'conf', lambda: settings)
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    home = tmp_path / 'home'
    home.mkdir(mode=0o700)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))

    config_dir = tmp_path / 'native'
    config_dir.mkdir(mode=0o700)
    config_path = config_dir / 'config.json'
    config_path.write_text('{"fixture": true}\n', encoding='utf-8')
    config_path.chmod(0o600)
    current = inspection.native_snapshot(config_path, 'testpilot', registry)

    sources = {}
    for name in ('cowagent_native.py', 'cowagent_adapter.py', 'cowagent_cli.py', 'operator_review.py'):
        path = Path(cowagent_native.ROOT) / 'agent' / 'external' / name
        sources['agent/external/' + name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if receipt_variant == 'full':
        receipt = {
            'task': 'Final complete Python regression after operator journal sidecar unlink-race fix',
            'status': 'passed',
            'result': {'terminal_exit_code': 0, 'passed': 1, 'failed': 0,
                       'junit_errors': 0, 'junit_failures': 0},
            'application_state': {
                'native_source_fingerprint': current['source_sha256'],
                'native_source_fingerprint_matches_pre_run': True,
                'changed_source_test_hashes': sources,
            },
        }
    else:
        # A genuinely approved older receipt can still be too weak to prove
        # the current complete native source tree.
        receipt = {
            'milestone': 'AGENT-ROUTING-003', 'exit_code': 0, 'summary': '1 passed in 0.1s',
            'test_files': [
                'tests/test_cowagent_adapter.py', 'tests/test_cowagent_native.py',
                'tests/test_approved_dispatch.py', 'tests/test_external_operator_control.py',
                'tests/test_external_contract.py', 'tests/test_external_supervisor.py',
            ],
            'final_source_sha256': sources,
        }
    receipt_path = tmp_path / 'focused-receipt.json'
    receipt_bytes = contract.canonical(receipt).encode('utf-8')
    receipt_path.write_bytes(receipt_bytes)
    receipt_path.chmod(0o600)
    probe_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    enrollment = dict(current, probe_sha256=probe_sha256)
    review = build_enrollment_review(enrollment, current=current,
                                     observed_probe_sha256=probe_sha256)

    scope = dict(SCOPE, runtime_id='cowagent.testpilot')
    state_dir = (tmp_path / 'operator-state').resolve()
    control = OperatorControl(state_dir, initialize=True)
    journal = ApprovalJournal(control)
    control.apply(_command('enroll', {'review': review, 'expires_at': now + 500},
                           scope=scope, expected_revision=0), now=now)
    task_id = str(uuid.uuid4())
    spec = {
        'task_id': task_id, 'idempotency_key': 'idem-' + task_id,
        'owner_id': scope['owner_id'], 'source_id': scope['source_id'],
        'conversation_id': scope['conversation_id'], 'runtime_id': scope['runtime_id'],
        'task': {'operation': 'analyze_records', 'artifact': 'analysis.json',
                 'content': json.dumps({'schema_version': 1, 'currency': 'USD',
                                        'records': [{'id': 'fictional-1', 'amount_cents': 50,
                                                     'status': 'paid'}]})},
        'authority': {'operations': ['analyze_records'], 'resource': task_id,
                      'expires_at': now + 400},
        'verification': {'acceptance': [], 'external_state': []},
    }
    task_review = build_task_review(spec, review, now=now)
    control.apply(_command('approve_task', {
        'spec': spec, 'enrollment_revision': 1, 'task_review_id': task_review['review_id'],
        'reviewed_at': now, 'expires_at': now + 350,
    }, scope=scope, expected_revision=0), now=now)
    journal.create(scope['supervisor_id'], spec)

    credential = contract.Credential(scope['supervisor_id'], scope['runtime_id'], 'fixture-key',
                                     b'k' * 32, now + 500, ('analyze_records',))
    credential_path = tmp_path / 'credential.json'
    credential_path.write_text(json.dumps({
        'supervisor_id': credential.supervisor_id, 'runtime_id': credential.runtime_id,
        'key_id': credential.key_id, 'secret_hex': credential.secret.hex(),
        'expires_at': credential.expires_at, 'operations': list(credential.operations),
    }), encoding='utf-8')
    credential_path.chmod(0o600)
    spec_path = tmp_path / 'task-spec.json'
    spec_path.write_text(contract.canonical(spec), encoding='utf-8')
    spec_path.chmod(0o600)
    socket_dir = Path(tempfile.mkdtemp(prefix='cd-', dir='/tmp')).resolve()
    socket_dir.chmod(0o700)
    socket_path = socket_dir / 'r.sock'
    inspect = _InspectFixture(socket_path, credential)
    binding = ExistingRuntimeBinding.from_private_files(
        operator_dir=state_dir, credential_path=credential_path, spec_path=spec_path,
        probe_receipt_path=receipt_path, config_path=config_path, socket_path=socket_path,
    )
    host = TrustedDiscoveryHost(registry_source=lambda: registry,
                                external_bindings_source=lambda: (binding,), clock=time.time)
    requirements = TaskRequirements(
        task_id=task_id, policy_id='safe-default', category='analyze_records',
        input_contract='fictional_records.v1', output_contract='analysis_report.v1',
        persistent_memory='required', required_tools=(), max_authority=('analyze_records',),
        approval='required', verification='independent_analysis', recovery='intent_fenced',
        cancellation='cooperative', deadline=now + 600, timeout_seconds=600, concurrency=1,
        permitted_mechanisms=('persistent_named',), prohibited_mechanisms=(),
        task_spec_hash=task_spec_fingerprint(spec), requested_agent_id='testpilot',
    )
    inspect.payload = {
        'protocol': 'cow.discovery.inspect/1', 'runtime_id': credential.runtime_id,
        'epoch': 'fixture-epoch-1', 'mechanism': 'persistent_named',
        'enrollment_fingerprint': contract.digest(enrollment),
        'native_capabilities': current, 'attestation': 'current', 'health': 'healthy',
        'available_slots': 1, 'active_load': 0, 'max_concurrency': 1,
    }
    return locals()


@pytest.fixture
def environment(tmp_path, monkeypatch):
    state = _snapshot(tmp_path, monkeypatch)
    try:
        yield state
    finally:
        state['inspect'].close()
        import shutil
        shutil.rmtree(state['socket_dir'])


@pytest.fixture
def weak_receipt_environment(tmp_path, monkeypatch):
    state = _snapshot(tmp_path, monkeypatch, receipt_variant='weak')
    try:
        yield state
    finally:
        state['inspect'].close()
        import shutil
        shutil.rmtree(state['socket_dir'])


def _counts(control):
    with control._connect() as db:
        return {
            table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            for table in ('operator_state', 'operator_decisions', 'external_tasks',
                          'external_events', 'external_approval_bindings')
        }


def _observe(environment):
    return environment['host'].observe_external(['cowagent.testpilot'], contact_authorized=True)


def test_authenticated_inspection_and_selection_are_advisory_and_read_only(environment, monkeypatch):
    state = environment
    import subprocess
    from agent.external import cowagent_native
    from agent.protocol.agent import Agent
    from bridge.agent_bridge import AgentLLMModel
    from bridge.bridge import Bridge

    def forbidden(*_args, **_kwargs):
        raise AssertionError('inspection or selection constructed a runtime/model or launched a process')

    monkeypatch.setattr(Agent, '__init__', forbidden)
    monkeypatch.setattr(Bridge, '__init__', forbidden)
    monkeypatch.setattr(AgentLLMModel, '__init__', forbidden)
    monkeypatch.setattr(cowagent_native.CowAgentNative, '__init__', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    before = _counts(state['control'])
    receipt_before = state['receipt_path'].read_bytes()
    response = state['binding'].supervisor.transport.inspect()
    assert contract.authenticate(response, state['credential'], kind='response', action='inspect')
    assert _observe(state) == [{'runtime_id': 'cowagent.testpilot', 'health': 'healthy',
                               'attestation': 'current', 'dispatch_permitted': False}]
    requests_after_inspect = len(state['inspect'].requests)
    selected = state['host'].select(state['requirements'])
    candidate = next(v for v in selected['candidates'] if v['mechanism'] == 'persistent_named')
    assert selected['status'] == 'selected', json.dumps(candidate, sort_keys=True)
    assert selected['dispatch_permitted'] is False
    assert selected['selected']['capability_provenance'] == 'approved_enrollment'
    assert selected['selected']['runtime_state']['exact_task_approval'] == 'approved'
    assert len(state['inspect'].requests) == requests_after_inspect  # select does not contact IPC
    assert _counts(state['control']) == before
    assert state['receipt_path'].read_bytes() == receipt_before
    assert str(state['tmp_path']) not in json.dumps(selected)
    assert state['credential'].secret.hex() not in json.dumps(selected)


@pytest.mark.parametrize('mode', ['tampered_mac', 'stale', 'replayed_nonce', 'bad_runtime_id',
                                  'unsupported_mechanism', 'bad_enrollment_fingerprint'])
def test_untrusted_or_substituted_inspection_never_yields_proof(environment, mode):
    state = environment
    state['inspect'].mode = mode
    observation = _observe(state)
    assert observation[0]['dispatch_permitted'] is False
    selected = state['host'].select(state['requirements'])
    assert selected['status'] == 'denied'
    assert selected['dispatch_permitted'] is False
    candidate = next(v for v in selected['candidates'] if v['mechanism'] == 'persistent_named')
    assert candidate['verification_status'] == 'unverified'


def test_probe_receipt_tamper_and_stale_operator_approval_are_distinct(environment):
    state = environment
    _observe(state)
    state['receipt_path'].write_bytes(state['receipt_path'].read_bytes() + b' ')
    denied = state['host'].select(state['requirements'])
    row = next(v for v in denied['candidates'] if v['mechanism'] == 'persistent_named')
    assert 'proof_receipt_hash_mismatch' in row['reasons']
    assert row['verification_status'] == 'unverified'


def test_approved_legacy_probe_without_full_source_binding_is_not_proof(weak_receipt_environment):
    state = weak_receipt_environment
    _observe(state)
    result = state['host'].select(state['requirements'])
    assert result['status'] == 'denied'
    candidate = next(v for v in result['candidates'] if v['mechanism'] == 'persistent_named')
    assert candidate['verification_status'] == 'unverified'
    assert 'proof_receipt_source_binding_missing' in candidate['reasons']


def test_current_task_revocation_invalidates_retained_selection(environment):
    state = environment
    _observe(state)
    selected = state['host'].select(state['requirements'])
    candidate = next(v for v in selected['candidates'] if v['mechanism'] == 'persistent_named')
    assert selected['status'] == 'selected', json.dumps(candidate, sort_keys=True)
    scope = dict(SCOPE, runtime_id='cowagent.testpilot')
    state['control'].apply(_command('revoke_task', {'task_id': state['spec']['task_id']},
                                    scope=scope, expected_revision=1), now=time.time())
    result = state['host'].revalidate(selected, state['requirements'])
    assert result['valid'] is False
    assert result['dispatch_permitted'] is False
    current = next(v for v in result['current']['candidates'] if v['mechanism'] == 'persistent_named')
    assert current['runtime_state']['revoked'] is True


def test_native_config_drift_invalidates_retained_selection(environment):
    state = environment
    _observe(state)
    selected = state['host'].select(state['requirements'])
    assert selected['status'] == 'selected'
    state['config_path'].write_text('{"fixture": "changed"}\n', encoding='utf-8')
    result = state['host'].revalidate(selected, state['requirements'])
    assert result['valid'] is False
    candidate = next(v for v in result['current']['candidates'] if v['mechanism'] == 'persistent_named')
    assert candidate['proof_status'] == 'invalid'
    assert 'capability_configuration_mismatch' in candidate['reasons']


def test_requested_identity_substitution_does_not_select_another_target(environment):
    state = environment
    _observe(state)
    request = TaskRequirements.from_dict(dict(
        state['requirements'].to_dict(), requested_agent_id='testpilot2'))
    result = state['host'].select(request)
    assert result['status'] == 'denied'
    assert result['selected'] is None
    candidate = next(v for v in result['candidates'] if v['target_id'] == 'testpilot')
    assert 'requested_identity_mismatch' in candidate['reasons']


def test_enrollment_revocation_and_expiry_are_not_reported_as_current(environment):
    state = environment
    _observe(state)
    scope = dict(SCOPE, runtime_id='cowagent.testpilot')
    state['control'].apply(_command('revoke_enrollment', {}, scope=scope,
                                    expected_revision=1), now=time.time())
    result = state['host'].select(state['requirements'])
    candidate = next(v for v in result['candidates'] if v['mechanism'] == 'persistent_named')
    assert candidate['runtime_state']['revoked'] is True
    assert candidate['runtime_state']['authorized'] is False
    assert result['status'] == 'denied'


def test_expired_task_approval_and_old_inspection_are_not_current(environment):
    state = environment
    _observe(state)
    future = state['now'] + 360
    state['host'].clock = lambda: future
    state['host'].service.clock = lambda: future
    result = state['host'].select(state['requirements'])
    candidate = next(v for v in result['candidates'] if v['mechanism'] == 'persistent_named')
    assert candidate['runtime_state']['expired'] is True
    assert candidate['runtime_state']['exact_task_approval'] == 'expired'
    assert candidate['runtime_state']['health'] == 'unknown'
    assert result['status'] == 'denied'


def test_task_substitution_and_coding_claim_are_denied(environment):
    state = environment
    _observe(state)
    substituted = TaskRequirements.from_dict(dict(
        state['requirements'].to_dict(), task_id=str(uuid.uuid4())))
    result = state['host'].select(substituted)
    assert result['status'] == 'denied'
    candidate = next(v for v in result['candidates'] if v['mechanism'] == 'persistent_named')
    assert 'task_binding_mismatch' in candidate['reasons']

    coding = TaskRequirements.from_dict(dict(
        state['requirements'].to_dict(), category='coding', input_contract='source_code.v1',
        output_contract='patch.v1'))
    result = state['host'].select(coding)
    candidate = next(v for v in result['candidates'] if v['mechanism'] == 'persistent_named')
    assert 'unsupported_adapter_contract' in candidate['reasons']
    assert result['status'] == 'denied'


def test_operator_scope_and_credential_identity_substitution_fail_closed(environment):
    state = environment
    substituted = dict(state['spec'], source_id='different-source')
    state['spec_path'].write_text(contract.canonical(substituted), encoding='utf-8')
    binding = ExistingRuntimeBinding.from_private_files(
        operator_dir=state['state_dir'], credential_path=state['credential_path'],
        spec_path=state['spec_path'], probe_receipt_path=state['receipt_path'],
        config_path=state['config_path'], socket_path=state['socket_path'],
    )
    host = TrustedDiscoveryHost(registry_source=lambda: state['registry'],
                                external_bindings_source=lambda: (binding,), clock=time.time)
    host.observe_external(['cowagent.testpilot'], contact_authorized=True)
    denied = host.select(state['requirements'])
    candidate = next(v for v in denied['candidates'] if v['mechanism'] == 'persistent_named')
    assert denied['status'] == 'denied'
    assert candidate['capability_provenance'] == 'unverified'

    state['spec_path'].write_text(contract.canonical(state['spec']), encoding='utf-8')
    state['credential_path'].write_text(json.dumps({
        'supervisor_id': state['credential'].supervisor_id,
        'runtime_id': 'cowagent.testpilot2', 'key_id': state['credential'].key_id,
        'secret_hex': state['credential'].secret.hex(),
        'expires_at': state['credential'].expires_at,
        'operations': list(state['credential'].operations),
    }), encoding='utf-8')
    with pytest.raises(contract.ProtocolError):
        ExistingRuntimeBinding.from_private_files(
            operator_dir=state['state_dir'], credential_path=state['credential_path'],
            spec_path=state['spec_path'], probe_receipt_path=state['receipt_path'],
            config_path=state['config_path'], socket_path=state['socket_path'],
        )
@pytest.mark.parametrize(('health', 'slots', 'availability'), [
    ('healthy', None, 'unknown'), ('healthy', 0, 'at_capacity'),
    ('unavailable', 1, 'available'), ('unknown', 1, 'available'),
])
def test_health_and_capacity_states_do_not_collapse(environment, health, slots, availability):
    state = environment
    state['inspect'].payload['health'] = health
    state['inspect'].payload['available_slots'] = slots
    _observe(state)
    result = state['host'].select(state['requirements'])
    candidate = next(v for v in result['candidates'] if v['mechanism'] == 'persistent_named')
    assert candidate['runtime_state']['availability'] == availability
    assert candidate['runtime_state']['health'] == health
    assert result['dispatch_permitted'] is False
    if health != 'healthy' or availability in ('unknown', 'at_capacity'):
        assert result['status'] == 'denied'


def test_native_offline_registry_facts_do_not_forge_turn_proof(tmp_path, monkeypatch):
    import config
    from agent.permission import authority

    default_workspace = tmp_path / 'default-workspace'
    target_workspace = tmp_path / 'testpilot-workspace'
    default_workspace.mkdir()
    target_workspace.mkdir()
    registry = AgentRegistry([
        AgentProfile('default', 'CowAgent', str(default_workspace)),
        AgentProfile('testpilot', 'TestPilot', str(target_workspace), model='gpt-6.1-luna', bot_type='openai'),
    ], 'default')
    monkeypatch.setattr(config, 'conf', lambda: {'model': 'gpt-6.1-luna', 'bot_type': 'openai',
                                                 'chat_fallback': {'enabled': False}})
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    host = TrustedDiscoveryHost(registry_source=lambda: registry, clock=lambda: time.time())
    task = TaskRequirements(
        task_id=str(uuid.uuid4()), policy_id='safe-default', category='analyze_records',
        input_contract='fictional_records.v1', output_contract='analysis_report.v1',
        persistent_memory='prohibited', required_tools=(), max_authority=('analyze_records',),
        approval='optional', verification='none', recovery='none', cancellation='none',
        deadline=time.time() + 100, timeout_seconds=30, concurrency=1,
        permitted_mechanisms=('native_isolated',), prohibited_mechanisms=(), task_spec_hash='a' * 64,
    )
    result = host.select(task)
    assert result['status'] == 'denied'
    native = next(v for v in result['candidates'] if v['mechanism'] == 'native_isolated'
                  and v['target_id'] == 'testpilot')
    assert native['runtime_state']['registered'] is True
    assert native['runtime_state']['health'] == 'unknown'
    assert native['verification_status'] == 'unverified'
    assert 'runtime_admission_unknown' in native['reasons']
    assert result['dispatch_permitted'] is False
