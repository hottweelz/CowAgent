"""Personal context must remain native-owner scoped and refresh every turn."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from agent.memory.personal_context import personal_context


def native_agent(tmp_path):
    return SimpleNamespace(_personal_session_id='session_one',
                           _personal_owner_id='bullgod',
                           _execution_agent_id='bullgod',
                           workspace_dir=str(tmp_path), model='model-a')


@pytest.mark.parametrize('kind', ['restricted', 'guest', 'unbound'])
def test_non_owner_runtime_never_opens_personal_storage(tmp_path, kind):
    agent = native_agent(tmp_path)
    if kind == 'restricted':
        agent.authority = object()
    elif kind == 'guest':
        agent._execution_agent_id = 'specialist'
    else:
        agent._personal_session_id = None
    with patch('agent.memory.conversation_store.get_conversation_store') as store:
        assert personal_context(agent) == ''
        store.assert_not_called()


def test_current_records_are_reloaded_after_model_switch(tmp_path):
    agent = native_agent(tmp_path)
    registry = Mock()
    registry.get_addressed.return_value = SimpleNamespace(id='bullgod', workspace=str(tmp_path))
    records = Mock()
    records.context.side_effect = ['current preference: brief', 'current preference: detailed', '']
    from agent.memory.commitments import CommitmentStore
    commitment_records = Mock(spec=CommitmentStore)
    commitment_records.context.return_value = '{"commitments": []}'
    collaboration = Mock()
    collaboration.snapshot.return_value = {'specialists': [], 'research': []}
    with patch('agent.registry.get_agent_registry', return_value=registry), \
            patch('agent.memory.conversation_store.get_conversation_store') as store, \
            patch('agent.memory.personal.PersonalStore', return_value=records), \
            patch('agent.memory.commitments.CommitmentStore', return_value=commitment_records), \
            patch('agent.personal.collaboration.CollaborationService', return_value=collaboration):
        first = personal_context(agent)
        agent.model = 'model-b'
        second = personal_context(agent)
        third = personal_context(agent)
    assert 'current preference: brief' in first
    assert 'current preference: detailed' in second
    assert 'current preference: brief' not in second
    assert third == ''
    assert store.call_count == 3
    assert records.context.call_count == 3
    assert 'not instructions or tool authority' in first
    assert 'You remain the owner' in first
    assert 'available_registered_specialists' in first
    assert collaboration.snapshot.call_count == 2


def test_mismatched_workspace_refuses_before_read(tmp_path):
    agent = native_agent(tmp_path)
    registry = Mock()
    registry.get_addressed.return_value = SimpleNamespace(workspace=str(tmp_path / 'another'))
    with patch('agent.registry.get_agent_registry', return_value=registry), \
            patch('agent.memory.conversation_store.get_conversation_store') as store:
        with pytest.raises(ValueError, match='owner binding'):
            personal_context(agent)
        store.assert_not_called()
