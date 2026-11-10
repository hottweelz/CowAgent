"""Owner authentication and request boundary for personal state."""
import json
from types import SimpleNamespace

import pytest
import web

from agent.memory.conversation_store import ConversationStore
from agent.personal import service
from agent.registry import AgentProfile
from channel.web.api import personal


@pytest.fixture
def app(tmp_path, monkeypatch):
    profile = AgentProfile('owner', 'Owner', str(tmp_path))
    registry = SimpleNamespace(get_addressed=lambda aid: profile if aid == 'owner' else (_ for _ in ()).throw(KeyError(aid)))
    store = ConversationStore(tmp_path / 'conversation.db')
    store.append_messages('owned', [{'role': 'user', 'content': 'My goal'}], channel_type='web')
    monkeypatch.setattr(service, 'get_agent_registry', lambda: registry)
    monkeypatch.setattr(service, 'get_conversation_store', lambda root: store)
    monkeypatch.setattr(personal, '_is_password_enabled', lambda: True)
    monkeypatch.setattr(personal, '_verify_auth_token', lambda token: token == 'owner-token')
    return web.application(('/api/personal/(.*)', 'PersonalHandler'),
                           {'PersonalHandler': personal.PersonalHandler}, autoreload=False)


def test_owner_auth_exact_identity_and_owned_session(app):
    assert app.request('/api/personal/owned?agent_id=owner').status.startswith('401')
    headers = {'Authorization': 'Bearer owner-token'}
    assert app.request('/api/personal/owned?agent_id=unknown', headers=headers).status.startswith('404')
    assert app.request('/api/personal/other?agent_id=owner', headers=headers).status.startswith('404')
    assert app.request('/api/personal/owned', headers=headers).status.startswith('404')
    response = app.request('/api/personal/owned?agent_id=owner', headers=headers)
    assert response.status.startswith('200')
    assert json.loads(response.data)['identity']['agent_id'] == 'owner'


def test_cross_origin_state_change_denied(app):
    response = app.request('/api/personal/owned?agent_id=owner', method='POST',
                           headers={'Authorization': 'Bearer owner-token', 'Content-Type': 'application/json',
                                    'Origin': 'https://evil.example'}, data='{}')
    assert response.status.startswith('403')


def test_owner_can_save_goal_from_visible_turn(app):
    headers = {'Authorization': 'Bearer owner-token', 'Content-Type': 'application/json'}
    payload = {'operation': 'save_goal', 'fields': {'goal': 'Build a checklist'},
               'source_seq': 0, 'revision': 0}
    response = app.request('/api/personal/owned?agent_id=owner', method='POST',
                           headers=headers, data=json.dumps(payload))
    assert response.status.startswith('200')
    assert json.loads(response.data)['continuity']['goal'] == 'Build a checklist'
