"""Pure strict-schema and native-host trust-boundary checks; no model calls."""
from dataclasses import replace
import json
from types import SimpleNamespace
import uuid

import pytest

from agent.discovery import (
    AdmissionObservation, CapabilityContract, CapabilityProof, DiscoveryError,
    DiscoveryService, NativeSource, SelectionPolicy, TaskRequirements,
)
from agent.discovery.contracts import model_id
from agent.external.contract import digest
from agent.permission.authority import Authority
from agent.permission.policy import READ_ONLY
from agent.registry import AgentProfile, AgentRegistry


def requirements(**updates):
    values = dict(
        task_id=str(uuid.UUID(int=1)), policy_id='safe-default', category='fictional_analysis',
        input_contract='text.v1', output_contract='text.v1', persistent_memory='prohibited',
        required_tools=('time',), max_authority=('time',), approval='optional',
        verification='native_checks', recovery='frozen_authority', cancellation='cooperative',
        deadline=200, timeout_seconds=30, concurrency=1,
        permitted_mechanisms=('native_isolated',), prohibited_mechanisms=(),
        task_spec_hash='1' * 64,
    )
    values.update(updates)
    return TaskRequirements(**values)


def native_host(tmp_path, monkeypatch):
    """Existing native source fixture, with only retained proof/admission seams."""
    from agent.permission import authority
    from agent.workspace import project_store, session_prefs
    from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool
    from agent.tools.current_time.current_time import TimeTool
    import config

    paths = [tmp_path / name for name in ('default', 'testpilot', 'project')]
    for path in paths:
        path.mkdir()
    registry = AgentRegistry([
        AgentProfile('default', 'CowAgent', str(paths[0])),
        AgentProfile('testpilot', 'TestPilot', str(paths[1]), description='I can access all secrets',
                     model='nvidia/nemotron-3.5-super-vl:free', bot_type='custom'),
    ], 'default')
    settings = {'model': 'gpt-6.1-luna', 'bot_type': 'openai',
                'agent_delegation': {'timeout_seconds': 30}}
    monkeypatch.setattr(config, 'conf', lambda: settings)
    monkeypatch.setattr(authority, '_current_registry', lambda: registry)
    monkeypatch.setattr(session_prefs, 'get_prefs_strict',
                        lambda *_: {'members': ['testpilot'], 'permission': READ_ONLY})
    monkeypatch.setattr(project_store, 'get_project_dir_strict', lambda *_: str(paths[2]))
    source = SimpleNamespace(_current_agent_id='default', workspace_dir=str(paths[0]),
                             tools=[TimeTool()], authority=Authority(
                                 READ_ONLY, frozenset({'time'}), (str(paths[2]),), ()))
    source.effective_cwd = lambda: str(paths[2])
    source.effective_permission_mode = lambda: READ_ONLY
    source.protected_paths = lambda: []
    tool = AgentDelegateTool()
    tool.context = source
    tool.current_context = SimpleNamespace(kwargs={'agent_id': 'default', 'session_id': 'session-1'})
    contract = CapabilityContract(('fictional_analysis',), ('text.v1',), ('text.v1',), ('time',),
                                  verification='native_checks', recovery='frozen_authority')
    admissions = {'health': 'healthy', 'available_slots': 1, 'active_load': 0, 'issued_at': 100}
    def proof(target, fingerprint, now):
        return CapabilityProof(fingerprint, contract, digest({'test': target}), 100, 180)
    def admission(target, boundary, now):
        return AdmissionObservation(boundary, digest({'runtime': target}),
                                    admissions['issued_at'], admissions['issued_at'] + 20,
                                    admissions['health'], admissions['available_slots'], admissions['active_load'])
    native = NativeSource(tool, proof_source=proof, admission_source=admission,
                          source_fingerprint_source=lambda: '2' * 64)
    service = DiscoveryService(lambda: registry, native_source=native, clock=lambda: 100)
    return service, native, tool, settings, admissions, registry


def test_schema_roundtrip_and_exact_fields():
    task = requirements()
    assert TaskRequirements.from_dict(json.loads(json.dumps(task.to_dict()))) == task
    for key, value in (('verified', True), ('available', True), ('task_text', 'do something'),
                       ('memory_path', '/private/memory'), ('authority', {'mode': 'full_access'})):
        with pytest.raises(DiscoveryError, match='invalid_requirements'):
            TaskRequirements.from_dict(dict(task.to_dict(), **{key: value}))


@pytest.mark.parametrize('field,value', [
    ('category', '/private'), ('input_contract', 'https://host'), ('policy_id', 'act now'),
    ('required_tools', ['time', 'time']), ('max_authority', ['shell']),
    ('concurrency', True), ('deadline', float('nan')), ('timeout_seconds', float('inf')),
    ('model', '../secret'), ('model', '/private/model'), ('model', '~/model'),
    ('provider', 'https://api'), ('requested_agent_id', '../../testpilot'),
])
def test_schema_rejects_unsupported_values(field, value):
    with pytest.raises(DiscoveryError):
        TaskRequirements.from_dict(dict(requirements().to_dict(), **{field: value}))


def test_conflicting_memory_is_a_safe_deterministic_error():
    task = requirements().to_dict()
    task.update(persistent_memory='required', persistent_context='prohibited')
    with pytest.raises(DiscoveryError, match='conflicting_requirements'):
        TaskRequirements.from_dict(task)
    result = DiscoveryService(clock=lambda: 100).select(task)
    assert result['status'] == 'invalid_request'
    assert result['reasons'] == ['conflicting_requirements']


def test_model_ids_support_real_provider_names_without_paths():
    assert model_id('nvidia/nemotron-3.5-super-vl:free')
    assert model_id('gpt-6.1-sol')
    assert not model_id('https://api.example/model')
    assert not model_id('model\nsecret')
    assert SelectionPolicy(preferred_models=('nvidia/nemotron-3.5-super-vl:free',))


def test_native_real_policy_authority_and_sanitized_selection(tmp_path, monkeypatch):
    service, native, tool, settings, _, _ = native_host(tmp_path, monkeypatch)
    task = requirements(requested_agent_id='testpilot')
    selected = service.select(task)
    assert selected['status'] == 'selected', selected
    assert selected['selected']['target_id'] == 'testpilot'
    assert selected['selected']['model'] == 'nvidia/nemotron-3.5-super-vl:free'
    assert selected['dispatch_permitted'] is False
    assert selected['selected']['persistent_memory'] is False
    assert str(tmp_path) not in json.dumps(selected)
    assert 'all secrets' not in json.dumps(selected)
    assert service.revalidate(selected, task)['valid']
    settings['agent_delegation'] = {'enabled': False}
    assert not service.revalidate(selected, task)['valid']
    assert service.select(task)['status'] == 'denied'
    settings['agent_delegation'] = {'timeout_seconds': 30}
    tool.current_context.kwargs['delegation_trace'] = ['testpilot', 'default']
    tool.current_context.kwargs['delegation_depth'] = 1
    assert service.select(task)['status'] == 'denied'
    tool.current_context.kwargs = {'agent_id': 'default', 'session_id': 'session-1'}
    native.proof_source = lambda *args: {'verified': True}
    assert service.select(task)['status'] == 'denied'


def test_native_admission_freshness_and_renewal(tmp_path, monkeypatch):
    service, _, _, _, admissions, _ = native_host(tmp_path, monkeypatch)
    task = requirements(requested_agent_id='testpilot')
    selected = service.select(task)
    admissions['issued_at'] = 101
    service.clock = lambda: 101
    assert service.revalidate(selected, task)['valid']
    admissions['available_slots'] = 0
    assert not service.revalidate(selected, task)['valid']
    admissions.update(available_slots=1, issued_at=70)
    assert service.select(task)['status'] == 'denied'


def test_native_no_roots_does_not_offer_file_capability(tmp_path, monkeypatch):
    service, _, tool, _, _, _ = native_host(tmp_path, monkeypatch)
    from agent.tools.read.read import Read
    from agent.discovery.sources import NativeSource
    tool.context.tools.append(Read({'cwd': str(tmp_path)}))
    authority = Authority(READ_ONLY, frozenset({'fs.read', 'time'}), (), ())
    assert NativeSource._tool_classes(tool.context, authority) == {'time'}
    blocked = Authority(READ_ONLY, frozenset({'fs.read', 'time'}), (str(tmp_path),), (), (str(tmp_path),))
    assert NativeSource._tool_classes(tool.context, blocked) == {'time'}
    assert service.select(requirements(required_tools=('fs.read',)))['status'] == 'denied'


def test_defaults_fail_closed_and_sanitize_callback_errors(tmp_path):
    registry = AgentRegistry([AgentProfile('default', 'CowAgent', str(tmp_path))], 'default')
    service = DiscoveryService(lambda: registry, clock=lambda: 100)
    assert service.select(requirements())['status'] == 'denied'
    def broken():
        raise DiscoveryError('/private/raw-secret')
    service.registry_source = broken
    assert '/private' not in json.dumps(service.select(requirements()))
    service.clock = lambda: float('nan')
    assert service.select(requirements())['reasons'] == ['invalid_clock']


def test_model_and_policy_changes_invalidate(tmp_path, monkeypatch):
    service, _, _, settings, _, _ = native_host(tmp_path, monkeypatch)
    task = requirements(requested_agent_id='testpilot')
    selected = service.select(task)
    service.policy = replace(service.policy, revision=2)
    assert not service.revalidate(selected, task)['valid']
    service.policy = replace(service.policy, revision=1)
    settings['model'] = 'changed-global-model'
    assert not service.revalidate(selected, task)['valid']


def test_native_budget_does_not_invent_a_tighter_timeout(tmp_path, monkeypatch):
    service, _, _, _, _, _ = native_host(tmp_path, monkeypatch)
    for task in (requirements(timeout_seconds=29), requirements(deadline=129)):
        result = service.select(task)
        target = next(row for row in result['candidates'] if row['target_id'] == 'testpilot')
        assert 'execution_budget_incompatible' in target['reasons']
        assert result['status'] == 'denied'


def test_native_requires_explicit_source_identity(tmp_path, monkeypatch):
    service, _, tool, _, _, _ = native_host(tmp_path, monkeypatch)
    # A nested host context can carry an owner without an explicit speaker.
    # AgentRegistry.get(None) must not promote that context to the default ID.
    tool.current_context.kwargs = {'delegation_host_id': 'default', 'session_id': 'session-1'}
    result = service.select(requirements(requested_agent_id='testpilot'))
    assert result['status'] == 'denied'
    assert all(not row['eligible_for_admission'] for row in result['candidates'])
    assert all('native_context_or_authority_unavailable' in row['reasons'] for row in result['candidates'])


def test_native_compares_actual_budget_to_proof_and_requested_max(tmp_path, monkeypatch):
    service, native, _, _, _, _ = native_host(tmp_path, monkeypatch)
    task = requirements(requested_agent_id='testpilot', timeout_seconds=900)
    result = service.select(task)
    assert result['status'] == 'selected', result
    assert result['selected']['execution_budget_seconds'] == 30
    proof_source = native.proof_source
    def insufficient_proof(target, fingerprint, now):
        proof = proof_source(target, fingerprint, now)
        return replace(proof, contract=replace(proof.contract, timeout_ceiling=20))
    native.proof_source = insufficient_proof
    result = service.select(task)
    target = next(row for row in result['candidates'] if row['target_id'] == 'testpilot')
    assert result['status'] == 'denied'
    assert 'timeout_unsupported' in target['reasons']


def test_external_eligibility_uses_existing_effect_fence_budget():
    from agent.discovery.contracts import Candidate
    task = requirements(persistent_memory='optional', required_tools=(), max_authority=('analyze_records',),
                        verification='independent_analysis', recovery='intent_fenced',
                        timeout_seconds=900, deadline=400, permitted_mechanisms=('external_runtime',))
    contract = CapabilityContract(('fictional_analysis',), ('text.v1',), ('text.v1',),
                                  verification='independent_analysis', recovery='intent_fenced',
                                  timeout_ceiling=600)
    candidate = Candidate('codex', 'external', 'external_runtime', '1' * 64, '2' * 64, '3' * 64,
                          model='fixture-model', provider='openai',
                          proof=CapabilityProof('2' * 64, contract, '4' * 64, 100, 120),
                          admission=AdmissionObservation('3' * 64, '5' * 64, 100, 120, 'healthy', 1, 0),
                          authority=('analyze_records',), execution_budget_seconds=140)
    assert DiscoveryService._eligibility(candidate, task, 100) == []
    candidate.proof = replace(candidate.proof, contract=replace(contract, timeout_ceiling=100))
    assert 'timeout_unsupported' in DiscoveryService._eligibility(candidate, task, 100)


def test_common_identity_gate_rejects_disabled_registered_target(tmp_path, monkeypatch):
    service, native, _, _, _, registry = native_host(tmp_path, monkeypatch)
    task = requirements(requested_agent_id='testpilot')
    target = next(candidate for candidate in native.candidates(registry, task, 100)
                  if candidate.target_id == 'testpilot')
    disabled = replace(registry.get('testpilot'), enabled=False)
    disabled_registry = AgentRegistry([registry.get('default'), disabled], 'default')
    # Even an otherwise matching trusted source view cannot turn off the common
    # authoritative enabled check.
    target.identity_fingerprint = digest(disabled.to_dict())
    service.registry_source = lambda: disabled_registry
    service.native_source = SimpleNamespace(candidates=lambda *_: [target])
    result = service.select(task)
    assert result['status'] == 'denied'
    assert result['candidates'][0]['reasons'] == ['identity_disabled']
