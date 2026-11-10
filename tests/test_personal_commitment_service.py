"""Owner API, native composition and continued intent across read failures."""
import json
from types import SimpleNamespace

import pytest
import web

from agent.memory.conversation_store import ConversationStore
from agent.memory.personal import PersonalStore
from agent.personal import commitments, service, scheduling, collaboration
from agent.registry import AgentProfile
from agent.tools.base_tool import ToolResult
from channel.web.api import commitments as api, personal

ENDPOINT = 'https://news.example/api/news'


@pytest.fixture
def owner(tmp_path, monkeypatch):
    profile = AgentProfile('owner', 'Owner', str(tmp_path))
    registry = SimpleNamespace(get_addressed=lambda aid: profile if aid == 'owner' else
                               (_ for _ in ()).throw(KeyError(aid)),
                               list=lambda **kwargs: [profile])
    native = ConversationStore(tmp_path / 'memory.db')
    native.append_messages('session', [{'role': 'user', 'content': 'Please track Bitcoin each morning'}], channel_type='web')
    monkeypatch.setattr(service, 'get_agent_registry', lambda: registry)
    monkeypatch.setattr(collaboration, 'get_agent_registry', lambda: registry)
    monkeypatch.setattr(service, 'get_conversation_store', lambda root: native)
    monkeypatch.setattr(commitments, 'conf', lambda: {'personal_http_endpoints': {ENDPOINT: ['93.184.216.34']}})
    monkeypatch.setattr(scheduling, 'sync_commitment', lambda *a: True)
    monkeypatch.setattr(scheduling, 'scheduling_status', lambda *a: {'next_run_at': None})
    svc = commitments.CommitmentService('owner', 'session')
    return svc, native


def create(svc, **extra):
    fields = dict(objective='Track Bitcoin news', preferences=['Bitcoin'], endpoint=ENDPOINT,
                  read_authorized=True, **extra)
    return svc.mutate({'operation': 'create', 'fields': fields, 'source_seq': 0})['commitments'][0]


def article(content='A regulated institution launched a Bitcoin custody service.'):
    return {'id': 1, 'title': 'Bitcoin custody service launches', 'provider': 'Fixture Publisher',
            'link': 'https://publisher.example/bitcoin-custody', 'description': content,
            'pubDate': '2026-11-10T12:00:00Z'}


def test_owner_api_no_password_no_guest_and_cross_origin(owner, monkeypatch):
    svc, _ = owner
    monkeypatch.setattr(personal, '_is_password_enabled', lambda: True)
    monkeypatch.setattr(personal, '_verify_auth_token', lambda token: token == 'owner-token')
    app = web.application(('/api/commitments/(.*)', 'CommitmentsHandler'),
                          {'CommitmentsHandler': api.CommitmentsHandler}, autoreload=False)
    path = '/api/commitments/session?agent_id=owner'
    assert app.request(path).status.startswith('401')
    headers = {'Authorization': 'Bearer owner-token', 'Content-Type': 'application/json'}
    assert app.request(path.replace('owner', 'unknown'), headers=headers).status.startswith('404')
    assert app.request(path.replace('/session', '/other'), headers=headers).status.startswith('404')
    assert app.request(path, method='POST', headers={**headers, 'Origin': 'https://evil.example'}, data='{}').status.startswith('403')
    payload = {'operation': 'create', 'source_seq': 0,
               'fields': {'objective': 'Follow Bitcoin', 'preferences': ['Bitcoin'], 'endpoint': ENDPOINT}}
    response = app.request(path, method='POST', headers=headers, data=json.dumps(payload))
    assert response.status.startswith('200')
    assert json.loads(response.data)['source_seq'] == 0
    assert svc.snapshot()['commitments'][0]['read_authorized'] is False
    monkeypatch.setattr(personal, '_is_password_enabled', lambda: False)
    assert app.request(path, headers=headers).status.startswith('401')


def test_live_composition_cache_duplicate_restart_and_error_preserve_memory(owner, monkeypatch):
    svc, native = owner
    memory = PersonalStore(native)
    memory.save_goal('session', {'goal': 'Keep this separate goal'}, 0, 0)
    memory.remember('session', 'Owner likes concise reports', 0)
    item = create(svc)
    cid = item['commitment_id']
    monkeypatch.setattr(svc, '_fetch', lambda record, cache: ToolResult.success(
        {'status': 'ok', 'data': [article()], 'etag': '"fixture-v1"'}))
    first = svc.run(cid, 'slot1')
    assert first['status'] == 'delivered' and len(first['selected']) == 1
    assert svc.run(cid, 'slot1')['run_id'] == first['run_id']
    restarted = commitments.CommitmentService('owner', 'session')
    monkeypatch.setattr(restarted, '_fetch', lambda record, cache: ToolResult.success({'status': 'not_modified'}))
    second = restarted.run(cid, 'slot2')
    assert second['status'] == 'delivered' and second['selected'] == []
    restarted.store.followup('session', cid, 'Track custody rollout', [first['selected'][0]['article_id']], 0)
    monkeypatch.setattr(restarted, '_fetch', lambda record, cache: ToolResult.fail('bounded error'))
    failure = restarted.run(cid, 'slot3')
    assert failure['status'] == 'failed'
    snapshot = restarted.snapshot()['commitments'][0]
    assert snapshot['last_success_at'] == first['finished_at']
    assert snapshot['last_error'] == 'network error'
    assert memory.snapshot('session')['continuity']['goal'] == 'Keep this separate goal'
    assert memory.snapshot('session')['memories'][0]['text'] == 'Owner likes concise reports'
    assert snapshot['followups'][0]['text'] == 'Track custody rollout'


def test_error_empty_schema_rate_limit_and_pause_during_fetch(owner, monkeypatch):
    svc, _ = owner
    cid = create(svc)['commitment_id']
    monkeypatch.setattr(svc, '_fetch', lambda *a: ToolResult.success({'status': 'ok', 'data': None}))
    assert svc.run(cid, 'invalid')['error'] == 'invalid response'
    monkeypatch.setattr(svc, '_fetch', lambda *a: ToolResult.success({'status': 'ok', 'data': []}))
    assert svc.run(cid, 'empty')['status'] == 'delivered'
    def pause(*args):
        record = svc.store.get(cid)
        svc.store.update('session', cid, {'status': 'paused'}, 0, record['revision'])
        return ToolResult.success({'status': 'ok', 'data': [article()]})
    monkeypatch.setattr(svc, '_fetch', pause)
    assert svc.run(cid, 'paused')['status'] == 'failed'
    record = svc.store.get(cid)
    svc.store.update('session', cid, {'status': 'active'}, 0, record['revision'])
    calls = []
    def limited(*a):
        calls.append(True)
        return ToolResult.fail('rate limited', {'http_status': 429, 'retry_after': '60'})
    monkeypatch.setattr(svc, '_fetch', limited)
    assert svc.run(cid, 'limited')['error'] == 'rate limited'
    assert svc.run(cid, 'backoff')['error'] == 'rate limited'
    assert len(calls) == 1


def test_instance_endpoint_boundary_and_invalid_schedule(owner):
    svc, _ = owner
    with pytest.raises(ValueError):
        svc.mutate({'operation': 'create', 'source_seq': 0,
                    'fields': {'objective': 'Wrong source', 'endpoint': 'https://other.example/news'}})
    with pytest.raises(ValueError):
        create(svc, schedule={'cron': 'broken', 'timezone': 'America/New_York'})


def test_server_cache_freshness_and_no_store(owner, monkeypatch):
    svc, _ = owner
    cid = create(svc)['commitment_id']
    calls = []
    def fetch(*a):
        calls.append(True)
        return ToolResult.success({'status': 'ok', 'data': [article()], 'cache_control': 'max-age=300'})
    monkeypatch.setattr(svc, '_fetch', fetch)
    assert svc.run(cid, 'first')['status'] == 'delivered'
    assert 'cache' in svc.run(cid, 'cached')['briefing']
    assert len(calls) == 1
    svc.store.save_cache(cid, {})
    monkeypatch.setattr(svc, '_fetch', lambda *a: ToolResult.success(
        {'status': 'ok', 'data': [article()], 'cache_control': 'no-store', 'etag': '"private"'}))
    assert svc.run(cid, 'no-store')['status'] == 'delivered'
    assert 'articles' not in svc.store.get_cache(cid)
    assert 'etag' not in svc.store.get_cache(cid)


def test_commitment_context_model_switch_and_authorization_truth(owner, monkeypatch):
    from agent.memory.personal_context import personal_context
    svc, _ = owner
    item = create(svc, schedule={'cron': '0 8 * * *', 'timezone': 'America/New_York'})
    registry = SimpleNamespace(get_addressed=lambda aid: svc.profile)
    monkeypatch.setattr('agent.registry.get_agent_registry', lambda: registry)
    monkeypatch.setattr('agent.memory.conversation_store.get_conversation_store', lambda root: svc.store._store)
    agent = SimpleNamespace(_personal_session_id='session', _personal_owner_id='owner',
                            _execution_agent_id='owner', workspace_dir=svc.profile.workspace, model='gpt-6-luna')
    first = personal_context(agent)
    svc.store.update('session', item['commitment_id'], {'read_authorized': False}, 0, item['revision'])
    agent.model = 'gpt-5.6-luna'
    monkeypatch.setattr(scheduling, 'scheduling_status', lambda *a: {'next_run_at': None, 'schedule_status': 'inactive'})
    second = personal_context(agent)
    assert 'Track Bitcoin news' in first and 'Track Bitcoin news' in second
    assert '"read_authorized": false' in second and '"schedule_status": "inactive"' in second
    assert '"next_run_at": null' in second
    assert 'untrusted remote DATA' in second


def _advice(selection, proposals=True):
    ids = [row['article_id'] for row in selection['selected']]
    return {'selected_ids': ids, 'reasons': {aid: 'A sourced custody development matches your saved Bitcoin interest.' for aid in ids},
            'proposals': [{'action': 'draft_post', 'reason': 'Review a sourced infrastructure post.', 'source_ids': ids[:1]}] if ids and proposals else [],
            'provenance': {'model': 'fixture-model', 'requested_provider': 'fixture', 'usage': {}}}


def test_proactive_meaningful_delivery_then_quiet_check_and_attention_history(owner, monkeypatch):
    svc, native = owner
    item = create(svc, initiative_enabled=True,
                  read_grant={'expires_at': None, 'min_interval_seconds': 0})
    assert item['grant']['agent_id'] == 'owner'
    monkeypatch.setattr(svc, '_fetch', lambda *args: ToolResult.success({'status': 'ok', 'data': [article()]}))
    interpretations = []
    def assess(record, selection):
        interpretations.append(record['grant']['grant_id'])
        return _advice(selection)
    monkeypatch.setattr(svc, '_interpret', assess)
    first = svc.run(item['commitment_id'], 'scheduled-1', trigger='scheduled')
    assert first['status'] == 'delivered' and first['evaluation']['verified']
    assert first['evaluation']['trigger'] == 'scheduled'
    snapshot = svc.snapshot()
    assert {x['kind'] for x in snapshot['attention']} == {'finding', 'decision'}
    assert len(interpretations) == 1
    quiet = svc.run(item['commitment_id'], 'scheduled-2', trigger='scheduled')
    assert quiet['status'] == 'completed' and quiet['message_seq'] is None
    assert quiet['evaluation']['notification'] == 'quiet_check'
    assert len(interpretations) == 1 and len(svc.snapshot()['attention']) == 2
    assert svc.run(item['commitment_id'], 'scheduled-2', trigger='scheduled')['run_id'] == quiet['run_id']
    finding = next(x for x in snapshot['attention'] if x['kind'] == 'finding')
    svc.mutate({'operation': 'decide_attention', 'commitment_id': item['commitment_id'],
                'attention_id': finding['attention_id'], 'decision': 'dismiss', 'source_seq': 0})
    after = svc.snapshot()
    assert len(after['attention']) == 1 and len(after['attention_history']) == 2
    assert len(after['commitments'][0]['runs']) == 2


@pytest.mark.parametrize('code', ['model_timeout', 'model_unavailable', 'model_invalid_response'])
def test_proactive_model_failure_preserves_intent_and_can_resume_fresh_occurrence(owner, monkeypatch, code):
    from agent.personal.interpretation import InterpretationError
    svc, native = owner
    memory = PersonalStore(native)
    memory.save_goal('session', {'goal': 'Keep my separate goal'}, 0, 0)
    memory.remember('session', 'Concise updates please', 0)
    item = create(svc, initiative_enabled=True)
    monkeypatch.setattr(svc, '_fetch', lambda *args: ToolResult.success({'status': 'ok', 'data': [article()]}))
    def fail(*args):
        raise InterpretationError(code)
    monkeypatch.setattr(svc, '_interpret', fail)
    failed = svc.run(item['commitment_id'], 'model-error', trigger='scheduled')
    assert failed['status'] == 'failed' and failed['error'] == code.replace('_', ' ')
    assert not failed['evaluation']['verified'] and failed['message_seq'] is None
    assert svc.store.get_coverage(item['commitment_id']) == []
    assert memory.snapshot('session')['continuity']['goal'] == 'Keep my separate goal'
    assert len(memory.snapshot('session')['memories']) == 1
    monkeypatch.setattr(svc, '_interpret', lambda record, selection: _advice(selection))
    assert svc.run(item['commitment_id'], 'model-error', trigger='scheduled')['run_id'] == failed['run_id']
    resumed = svc.run(item['commitment_id'], 'fresh-slot', trigger='scheduled')
    assert resumed['status'] == 'delivered'
    assert svc.store.get(item['commitment_id'])['grant']['grant_id'] == item['grant']['grant_id']


def test_revoke_during_semantic_evaluation_prevents_delivery_and_future_reads(owner, monkeypatch):
    svc, _ = owner
    item = create(svc, initiative_enabled=True)
    reads = []
    def fetch(*args):
        reads.append(True)
        return ToolResult.success({'status': 'ok', 'data': [article()]})
    def assess(record, selection):
        svc.mutate({'operation': 'update', 'commitment_id': item['commitment_id'],
                    'fields': {'read_authorized': False}, 'revision': item['revision'], 'source_seq': 0})
        return _advice(selection)
    monkeypatch.setattr(svc, '_fetch', fetch)
    monkeypatch.setattr(svc, '_interpret', assess)
    result = svc.run(item['commitment_id'], 'revoke-race', trigger='scheduled')
    assert result['status'] == 'failed' and result['message_seq'] is None
    with pytest.raises(ValueError):
        svc.run(item['commitment_id'], 'after-revocation', trigger='scheduled')
    assert len(reads) == 1 and svc.store.get_coverage(item['commitment_id']) == []
    assert not svc.snapshot()['commitments'][0]['grant']['authorized']


def test_publication_decision_is_persistent_review_only_and_denial_has_no_effect(owner, monkeypatch):
    svc, native = owner
    item = create(svc, initiative_enabled=True)
    monkeypatch.setattr(svc, '_fetch', lambda *args: ToolResult.success({'status': 'ok', 'data': [article()]}))
    monkeypatch.setattr(svc, '_interpret', lambda record, selection: _advice(selection, proposals=False))
    result = svc.run(item['commitment_id'], 'news', trigger='scheduled')
    source = result['selected'][0]['article_id']
    svc.mutate({'operation': 'save_draft', 'commitment_id': item['commitment_id'],
                'text': 'A sourced draft, not a published post.', 'source_ids': [source],
                'claims': ['The source describes a custody service.'], 'source_seq': 0})
    draft = svc.snapshot()['commitments'][0]['drafts'][0]
    body = {'operation': 'propose_publication', 'commitment_id': item['commitment_id'],
            'draft_id': draft['item_id'], 'source_seq': 0}
    first = svc.mutate(body)
    decision = next(x for x in first['attention'] if x['kind'] == 'decision')
    again = svc.mutate(body)
    assert len([x for x in again['attention'] if x['kind'] == 'decision']) == 1
    assert decision['payload']['execution_status'] == 'blocked'
    restarted = commitments.CommitmentService('owner', 'session')
    monkeypatch.setattr(restarted, '_fetch', lambda *a: pytest.fail('Decision must not trigger an online action'))
    state = restarted.mutate({'operation': 'decide_attention', 'commitment_id': item['commitment_id'],
                              'attention_id': decision['attention_id'], 'decision': 'deny', 'source_seq': 0})
    assert next(x for x in state['attention'] if x['attention_id'] == decision['attention_id'])['status'] == 'denied'
    assert state['commitments'][0]['drafts'][0]['status'] == 'awaiting_publication_approval'


def test_research_api_authentication_and_unavailable_specialist_preserve_commitment(owner, monkeypatch):
    svc, native = owner
    item = create(svc)
    monkeypatch.setattr(svc, '_fetch', lambda *args: ToolResult.success({'status': 'ok', 'data': [article()]}))
    delivered = svc.run(item['commitment_id'], 'research-source')
    source_id = delivered['selected'][0]['article_id']
    before = svc.store.get(item['commitment_id'])
    monkeypatch.setattr(personal, '_is_password_enabled', lambda: True)
    monkeypatch.setattr(personal, '_verify_auth_token', lambda token: token == 'owner-token')
    app = web.application(('/api/commitments/(.*)', 'CommitmentsHandler'),
                          {'CommitmentsHandler': api.CommitmentsHandler}, autoreload=False)
    path = '/api/commitments/session?agent_id=owner'
    body = json.dumps({'operation': 'prepare_research', 'commitment_id': item['commitment_id'],
                       'target_agent_id': 'not-installed', 'source_ids': [source_id],
                       'question': 'Which sourced facts need further investigation?', 'source_seq': 0})
    assert app.request(path, method='POST', data=body).status.startswith('401')
    headers = {'Authorization': 'Bearer owner-token', 'Content-Type': 'application/json'}
    assert app.request(path, method='POST', headers={**headers, 'Origin': 'https://evil.example'},
                       data=body).status.startswith('403')
    response = app.request(path, method='POST', headers=headers, data=body)
    assert response.status.startswith('200')
    snapshot = json.loads(response.data)
    assert snapshot['research_operation']['status'] == 'unavailable'
    assert snapshot['specialists'] == [] and snapshot['research'] == []
    assert svc.store.get(item['commitment_id']) == before
    assert len(svc.snapshot()['commitments'][0]['runs']) == 1
