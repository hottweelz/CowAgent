import hashlib
import json
from types import SimpleNamespace

import pytest

from agent.permission.authority import Authority
from agent.protocol.agent import Agent
from agent.recovery import runtime
from agent.recovery.__main__ import main
from agent.recovery.store import TaskStore
from agent.recovery.verification import normalize_contract, outcome_summary, verify_task
from agent.tools.write.write import Write


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    import config
    project = tmp_path / 'project'
    project.mkdir()
    profile = SimpleNamespace(id='owner', enabled=True, workspace=str(project),
                              bot_type='fixture', model='fixture-model')
    monkeypatch.setattr(config, 'config', config.Config({'agent_workspace': str(tmp_path / 'state'),
                        'default_agent_id': 'owner', 'bot_type': 'fixture', 'model': 'fixture-model',
                        'agent_permission_mode': 'workspace-write'}))
    monkeypatch.setattr(runtime, '_registry_profiles', lambda: [profile])
    monkeypatch.setattr('agent.permission.authority._registry_profiles', lambda: [profile])
    prefs = {'permission': 'workspace-write'}
    monkeypatch.setattr(runtime.session_prefs, 'get_prefs_strict', lambda *_: prefs)
    monkeypatch.setattr(runtime.project_store, 'get_project_dir_strict', lambda *_: str(project))
    store = TaskStore(tmp_path / 'journal/tasks.db')

    def task(contract=None):
        child = Agent('fixture worker', tools=[Write({'cwd': str(project)})], workspace_dir=str(project),
                      enable_skills=False, skip_context_files=True)
        child.project_dir = str(project)
        child._current_agent_id = 'owner'
        child.permission_mode = 'workspace-write'
        child.authority = Authority('workspace-write', frozenset({'fs.read', 'fs.write'}),
                                    (str(project),), (str(project),))
        spec = runtime.snapshot_child(child, 'fixture task', owner_id='owner', session_id='s',
            kind='subagent', source_agent_id='owner', target_agent_id='owner', verification=contract)
        row = store.submit('owner', 's', 'subagent', spec)
        with store.claim(row['task_id']) as claim:
            store.finish(claim, 'completed', result={'summary': 'I verified everything; success'})
        return row['task_id']
    return SimpleNamespace(project=project, store=store, task=task, prefs=prefs, profile=profile)


def contract(path='result.txt', expected='correct'):
    return {group: [{'id': group, 'type': 'text_equals', 'path': path, 'expected': expected}]
            for group in ('acceptance', 'external_state')}


def test_independent_readback_and_reverification_keep_execution(fixture, monkeypatch, capsys):
    f = fixture
    path = f.project / 'result.txt'
    path.write_text('correct')
    task_id = f.task(contract())
    monkeypatch.setattr(Agent, 'run_stream', lambda *a, **k: pytest.fail('verification executed worker'))
    row = verify_task(f.store, task_id)
    summary = outcome_summary(row)
    assert (summary['execution_status'], summary['acceptance_status'], summary['external_state_status']) == (
        'completed', 'passed', 'confirmed')
    assert summary['verified']
    report = row['verification']
    assert report['verifier'] == 'native-file-verifier-v1' and report['checked_at']
    assert report['acceptance']['checks'][0]['observed_sha256'] == hashlib.sha256(b'correct').hexdigest()
    assert 'correct' not in json.dumps(report)  # Store hashes/outcomes, not the read contents.
    path.write_text('wrong')
    assert main(['verify', task_id, '--owner', 'owner'], store=f.store) == 0
    updated = json.loads(capsys.readouterr().out)
    assert updated['outcomes']['acceptance_status'] == 'failed'
    assert updated['outcomes']['external_state_status'] == 'failed'
    assert not updated['outcomes']['verified']
    reopened = TaskStore(f.store.path).get(task_id)
    assert reopened['state'] == 'completed' and reopened['attempt_count'] == 1
    assert len(reopened['attempts'][0]['verifications']) == 2
    assert reopened['result']['summary'].startswith('I verified')
    with pytest.raises(ValueError, match='cannot be retried'):
        f.store.retry(task_id)


def test_missing_and_unsupported_checks_are_not_passes(fixture):
    f = fixture
    row = verify_task(f.store, f.task())
    assert outcome_summary(row)['acceptance_status'] == 'unverified'
    assert outcome_summary(row)['external_state_status'] == 'unverified'
    (f.project / 'result.txt').write_text('correct')
    spec = contract()
    spec['external_state'] = [{'id': 'publish', 'type': 'http_status', 'url': 'https://example.invalid'}]
    row = verify_task(f.store, f.task(spec))
    assert outcome_summary(row)['acceptance_status'] == 'passed'
    assert outcome_summary(row)['external_state_status'] == 'unverified'
    assert not outcome_summary(row)['verified']


def test_missing_artifact_fails_but_denied_paths_remain_unverified(fixture, tmp_path):
    f = fixture
    assert outcome_summary(verify_task(f.store, f.task(contract())))['acceptance_status'] == 'failed'
    (tmp_path / 'outside.txt').write_text('correct')
    (f.project / 'alias.txt').symlink_to(tmp_path / 'outside.txt')
    for path in ('../outside.txt', 'alias.txt', 'MEMORY.md'):
        if path == 'MEMORY.md':
            (f.project / path).write_text('correct')
        row = verify_task(f.store, f.task(contract(path)))
        assert outcome_summary(row)['acceptance_status'] == 'unverified'
        assert outcome_summary(row)['external_state_status'] == 'unverified'
        assert not outcome_summary(row)['verified']


def test_each_native_check_reads_artifact_and_json_types(fixture):
    f = fixture
    (f.project / 'data.json').write_text('{"value": 1}')
    checks = [
        {'id': 'exists', 'type': 'file_exists', 'path': 'data.json'},
        {'id': 'json', 'type': 'json_equals', 'path': 'data.json', 'expected': {'value': 1}},
        {'id': 'digest', 'type': 'sha256', 'path': 'data.json',
         'expected': hashlib.sha256(b'{"value": 1}').hexdigest()},
    ]
    row = verify_task(f.store, f.task({'acceptance': checks}))
    assert outcome_summary(row)['acceptance_status'] == 'passed'
    checks[1]['expected'] = {'value': True}
    row = verify_task(f.store, f.task({'acceptance': checks}))
    assert outcome_summary(row)['acceptance_status'] == 'failed'


def test_revalidation_does_not_regrant_private_authority(fixture):
    f = fixture
    (f.project / 'result.txt').write_text('correct')
    task_id = f.task(contract())
    f.profile.enabled = False
    assert outcome_summary(verify_task(f.store, task_id))['external_state_status'] == 'unverified'


def test_operator_ownership_and_incomplete_execution_do_not_verify(fixture, capsys):
    f = fixture
    task_id = f.task(contract())
    assert main(['verify', task_id, '--owner', 'other'], store=f.store) == 1
    assert 'owner mismatch' in capsys.readouterr().out.lower()
    assert f.store.get(task_id)['verification'] is None
    queued = f.store.submit('owner', 's', 'subagent', {})['task_id']
    assert main(['verify', queued, '--owner', 'owner'], store=f.store) == 1
    assert 'not completed' in capsys.readouterr().out


def test_verification_storage_failure_is_visible_without_replay(fixture, monkeypatch):
    f = fixture
    (f.project / 'result.txt').write_text('correct')
    task_id = f.task(contract())
    monkeypatch.setattr(Agent, 'run_stream', lambda *a, **k: pytest.fail('worker replayed'))
    def unavailable(*a, **k):
        raise OSError('fixture journal unavailable')
    monkeypatch.setattr(f.store, 'record_verification', unavailable)
    result = runtime.execute_task(f.store, task_id)
    assert result['execution_status'] == 'completed'
    assert result['acceptance_status'] == result['external_state_status'] == 'unverified'
    assert result['verification_error'] and not result['verified']
    assert f.store.get(task_id)['verification'] is None
    reopened = TaskStore(f.store.path)
    row = verify_task(reopened, task_id)
    assert row['attempt_count'] == 1 and outcome_summary(row)['verified']


def test_native_gateway_read_denial_is_not_lost_in_effect_receipt(fixture):
    from agent.tools.read.read import Read
    f = fixture
    (f.project / 'result.txt').write_text('correct')
    (f.project / 'MEMORY.md').write_text('PRIVATE_FIXTURE')
    child = Agent('fixture', tools=[Read({'cwd': str(f.project)})], workspace_dir=str(f.project),
                  enable_skills=False, skip_context_files=True)
    child.project_dir = str(f.project)
    child._current_agent_id = 'owner'
    child.permission_mode = 'workspace-write'
    child.authority = Authority('workspace-write', frozenset({'fs.read', 'fs.write'}),
                                (str(f.project),), (str(f.project),))
    spec = runtime.snapshot_child(child, 'fixture', owner_id='owner', session_id='s', kind='subagent',
        source_agent_id='owner', target_agent_id='owner', verification=contract())
    task_id = f.store.submit('owner', 's', 'subagent', spec)['task_id']
    def run(*a, **k):
        child.tools[0].context = child
        assert child.tools[0].execute_tool({'path': 'MEMORY.md'}).status == 'error'
        return 'I verified everything'
    child.run_stream = run
    result = runtime.execute_task(f.store, task_id, lambda: child)
    assert result['execution_status'] == 'completed'
    assert result['acceptance_status'] == 'failed'
    assert result['external_state_status'] == 'confirmed' and not result['verified']
    row = f.store.get(task_id)
    effect, = row['attempts'][0]['effects']
    assert not effect['mutating'] and effect['result']['permission_denied']
    assert 'PRIVATE_FIXTURE' not in json.dumps(row['verification'])


@pytest.mark.parametrize('value', [[], {'acceptance': {}},
    {'acceptance': [{'id': 'a', 'type': 'text_equals', 'path': 'x'}]},
    {'acceptance': [{'id': 'a', 'type': 'sha256', 'path': 'x', 'expected': 'bad'}]},
    {'acceptance': [{'id': 'a', 'type': 'file_exists', 'path': 'x', 'expected': False}]}])
def test_invalid_contract_rejected_before_execution(value):
    with pytest.raises(ValueError):
        normalize_contract(value)
