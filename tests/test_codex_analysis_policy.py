"""Analysis enrollment and native configuration boundaries; no real Codex."""
import hashlib

import pytest

from agent.external.codex_policy import (
    ANALYSIS_DISABLED_FEATURES, ANALYSIS_POLICY_REVISION, ANALYSIS_PROFILE,
    CodexAnalysisPolicy, SafetyGateError, VERSION,
)
from tests.test_codex_policy import (
    MODEL, PROVIDER, StubClient, enrolled_policy, inspection_responses,
    mock_codex_version, start_thread_responses,
)


def setup_policy(tmp_path, monkeypatch, *, enrolled=True):
    base, config, auth = enrolled_policy(tmp_path, monkeypatch)
    mock_codex_version(monkeypatch)
    policy = CodexAnalysisPolicy(base.executable)
    if enrolled:
        policy.enrollment = {'cli_version': VERSION, 'model': MODEL, 'modelProvider': PROVIDER,
                             'policy_revision': ANALYSIS_POLICY_REVISION, 'probe_sha256': 'a' * 64,
                             'provider_config_sha256': policy._provider_digest(),
                             'config_sha256': policy._config_digest()}
    cwd = tmp_path / 'workspace'
    cwd.mkdir()
    return policy, cwd, config, auth


def analysis_responses(profile=None):
    result = inspection_responses()
    result['config/read']['config'].update({'memories': {'generate_memories': False, 'use_memories': True},
                                           'agents': {'enabled': True, 'max_concurrent_threads_per_session': 2}})
    if profile is not None:
        result['config/read']['config']['permissions'] = {ANALYSIS_PROFILE: profile}
    for feature in result['experimentalFeature/list']['data']:
        feature['enabled'] = feature['name'] not in ANALYSIS_DISABLED_FEATURES
    return result


def test_analysis_launch_preserves_native_delegation_memory_and_config(tmp_path, monkeypatch):
    policy, cwd, config, auth = setup_policy(tmp_path, monkeypatch)
    before = [hashlib.sha256(f.read_bytes()).hexdigest() for f in (config, auth)]
    argv, _, _ = policy.launch(cwd)
    assert 'multi_agent' not in argv and 'multi_agent_v2' not in argv
    assert 'code_mode_host' not in argv and 'memories' not in argv
    assert 'memories.generate_memories=false' in argv
    assert not any('use_memories' in arg for arg in argv)
    assert any('projects={' in arg and str(cwd) in arg for arg in argv)
    fs = next(arg for arg in argv if '.filesystem=' in arg)
    assert '":workspace_roots"={"."="read"' in fs and '"write"' not in fs
    assert before == [hashlib.sha256(f.read_bytes()).hexdigest() for f in (config, auth)]


def test_analysis_thread_requires_readonly_and_keeps_model_implicit(tmp_path, monkeypatch):
    policy, cwd, _, _ = setup_policy(tmp_path, monkeypatch)
    responses = start_thread_responses(cwd)
    responses['permissionProfile/list']['data'][0]['id'] = ANALYSIS_PROFILE
    responses['thread/start']['activePermissionProfile']['id'] = ANALYSIS_PROFILE
    responses['thread/start']['sandbox'] = {'type': 'readOnly', 'networkAccess': False}
    client = StubClient(responses)
    policy.start_thread(client, cwd)
    assert 'model' not in client.calls[-1][1]
    responses['thread/start']['sandbox']['type'] = 'workspaceWrite'
    with pytest.raises(SafetyGateError, match='authority'):
        policy.start_thread(client, cwd)


@pytest.mark.parametrize('enrolled,drift', [(True, False), (False, False), (True, True)])
def test_effect_confinement_needs_enrollment_and_current_provider(tmp_path, monkeypatch, enrolled, drift):
    policy, cwd, config, _ = setup_policy(tmp_path, monkeypatch, enrolled=enrolled)
    _, _, expected = policy.launch(cwd)
    thread = {'model': MODEL, 'modelProvider': PROVIDER,
              'thread': {'id': 'native-owned', 'reasoningEffort': 'high'}}
    if drift:
        with config.open('a') as f:
            f.write('base_url = "https://changed.example.invalid"\n')
    client = StubClient(analysis_responses(expected['permissions_profile']))
    if enrolled and not drift:
        policy.attest_configuration(client, cwd, thread, expected)
        assert policy.task_effects_confined
    else:
        with pytest.raises(SafetyGateError, match='enrollment'):
            policy.attest_configuration(client, cwd, thread, expected)
        assert not policy.task_effects_confined


def test_discovery_uses_native_public_metadata_without_a_turn(tmp_path, monkeypatch):
    policy, cwd, _, _ = setup_policy(tmp_path, monkeypatch)
    responses = analysis_responses()
    responses['initialize'] = {}
    responses['permissionProfile/list'] = {'data': [{'id': ANALYSIS_PROFILE, 'allowed': True}]}
    client = StubClient(responses)
    client.close = lambda: None
    monkeypatch.setattr('agent.external.codex_client.CodexClient', lambda *args: client)
    result = policy.discover(cwd)
    assert result['model'] == MODEL and result['modelProvider'] == PROVIDER
    assert result['authority_enrollment'] == 'matched_tested_configuration'
    assert result['profile_available'] is True
    assert not any(method in ('thread/start', 'turn/start') for method, _, _ in client.calls)


def test_layered_outside_profile_grant_is_rejected(tmp_path, monkeypatch):
    import copy
    policy, cwd, _, _ = setup_policy(tmp_path, monkeypatch)
    _, _, expected = policy.launch(cwd)
    profile = copy.deepcopy(expected['permissions_profile'])
    profile['filesystem']['/unapproved-outside-fixture'] = 'read'
    thread = {'model': MODEL, 'modelProvider': PROVIDER,
              'thread': {'id': 'native-owned', 'reasoningEffort': 'high'}}
    with pytest.raises(SafetyGateError, match='configuration'):
        policy.attest_configuration(StubClient(analysis_responses(profile)), cwd, thread, expected)
    assert not policy.task_effects_confined


def test_nonprovider_configuration_drift_invalidates_enrollment(tmp_path, monkeypatch):
    policy, cwd, config, _ = setup_policy(tmp_path, monkeypatch)
    config.write_text(config.read_text() + '\n[permissions.changed]\nextends = ":danger-full-access"\n')
    _, _, expected = policy.launch(cwd)
    thread = {'model': MODEL, 'modelProvider': PROVIDER,
              'thread': {'id': 'native-owned', 'reasoningEffort': 'high'}}
    with pytest.raises(SafetyGateError, match='enrollment'):
        policy.attest_configuration(StubClient(analysis_responses(expected['permissions_profile'])), cwd, thread, expected)
    assert not policy.task_effects_confined


def test_analysis_authority_is_not_added_to_legacy_credentials():
    import time
    from agent.external.contract import Credential
    credential = Credential('host', 'runtime', 'key', b'x' * 32, time.time() + 60)
    assert credential.operations == ('write_artifact', 'record_effect')
