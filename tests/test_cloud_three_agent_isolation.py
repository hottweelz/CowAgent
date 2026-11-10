"""Disposable three-identity routing receipts for the cloud failure boundary."""
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent.registry import AgentRegistry, set_agent_registry
if "linkai" not in sys.modules:
    stub = types.ModuleType("linkai")
    stub.LinkAIClient = type("LinkAIClient", (), {})
    stub.PushMsg = type("PushMsg", (), {})
    sys.modules["linkai"] = stub

from common.cloud_client import CloudClient  # noqa: E402

IDS = ('default', 'testpilot', 'testpilot2')
SERVICES = (
    ('memory', 'agent.memory.service', 'MemoryService'),
    ('knowledge', 'agent.knowledge.service', 'KnowledgeService'),
    ('workspace', 'agent.workspace.service', 'WorkspaceService'),
)


@pytest.fixture
def identities(tmp_path):
    roots = {name: tmp_path / name for name in IDS}
    for name, root in roots.items():
        root.mkdir()
        (root / 'sentinel.txt').write_text(name)
    registry = AgentRegistry.from_config({
        'agent_workspace': str(tmp_path), 'default_agent_id': 'default',
        'agents': [{'id': name, 'name': name, 'workspace': str(root), 'enabled': True}
                   for name, root in roots.items()],
    })
    set_agent_registry(registry)
    try:
        yield roots
    finally:
        set_agent_registry(None)


@pytest.mark.parametrize('identity', IDS)
@pytest.mark.parametrize('service,module_name,class_name', SERVICES)
@pytest.mark.parametrize('failure', ('build', 'registry', 'none'))
def test_named_reads_and_writes_never_cross_identity(
    identities, monkeypatch, identity, service, module_name, class_name, failure
):
    calls = []

    class FileService:
        def __init__(self, workspace):
            self.root = Path(workspace)

        def dispatch(self, action, payload):
            calls.append(self.root.name)
            path = self.root / 'sentinel.txt'
            if action == 'write':
                path.write_text(payload['content'])
            return {'code': 200, 'payload': path.read_text()}

    client = CloudClient.__new__(CloudClient)
    setattr(client, '_' + service + '_service', FileService(identities['default']))
    constructor = FileService if failure != 'build' else Mock(side_effect=RuntimeError('broken index'))
    monkeypatch.setattr(importlib.import_module(module_name), class_name, constructor)
    if failure == 'registry':
        monkeypatch.setattr('agent.registry.get_agent_registry', Mock(side_effect=RuntimeError('unavailable')))
    callback = getattr(client, 'on_' + service)
    for operation in ('read', 'write'):
        response = callback({'action': operation, 'payload': {
            'agent_id': identity, 'content': identity + ':changed'}})
        assert response['code'] == (200 if failure == 'none' else 500)
        if failure == 'none':
            assert response['payload'] == identity + (':changed' if operation == 'write' else '')
    assert calls == ([identity, identity] if failure == 'none' else [])
    for name, root in identities.items():
        suffix = ':changed' if failure == 'none' and name == identity else ''
        assert (root / 'sentinel.txt').read_text() == name + suffix


@pytest.mark.parametrize('identity', IDS)
@pytest.mark.parametrize('failure', (False, True))
def test_history_resolution_never_opens_another_identity(identities, monkeypatch, identity, failure):
    opened = []

    class History:
        def __init__(self, workspace):
            opened.append(Path(workspace).name)
            self.workspace = Path(workspace)

        def load_history_page(self, **kwargs):
            return {'messages': [{'content': (self.workspace / 'sentinel.txt').read_text()}], 'total': 1}

    monkeypatch.setattr('agent.memory.conversation_store.get_conversation_store', History)
    if failure:
        monkeypatch.setattr('agent.registry.get_agent_registry', Mock(side_effect=RuntimeError('unavailable')))
    client = CloudClient.__new__(CloudClient)
    response = client.on_history({'action': 'query', 'payload': {'session_id': 'fictional', 'agent_id': identity}})
    assert response['payload']['status'] == ('error' if failure else 'success')
    assert opened == ([] if failure else [identity])
    for name, root in identities.items():
        assert (root / 'sentinel.txt').read_text() == name
