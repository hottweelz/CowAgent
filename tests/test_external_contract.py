"""Authentication and strict identity checks without a provider or live service."""
from dataclasses import replace
import time
import uuid

import pytest

from agent.external import contract
from tests.test_external_runtime import fixture as runtime_fixture

fixture = runtime_fixture


def test_signed_response_is_bound_to_request_runtime_action_and_expiry():
    credential = contract.Credential('bullgod', 'synthetic', 'fixture-key', b'x' * 32, time.time() + 60)
    request = contract.envelope(credential, 'status', {'task_id': str(uuid.uuid4())})
    response = contract.envelope(credential, 'status', {'ok': True, 'data': {}},
                                 request_id=request['request_id'], kind='response')
    assert contract.authenticate(response, credential, kind='response', request_id=request['request_id'], action='status')['ok']
    for kwargs in ({'request_id': str(uuid.uuid4())}, {'action': 'cancel'}, {'now': time.time() + 61}):
        with pytest.raises(contract.ProtocolError): contract.authenticate(response, credential, kind='response', **kwargs)
    for field, value in [('runtime_id', 'other'), ('payload', {'ok': True, 'data': {'state': 'completed'}})]:
        with pytest.raises(contract.ProtocolError): contract.authenticate(dict(response, **{field: value}), credential, kind='response')
    with pytest.raises(contract.ProtocolError):
        contract.authenticate(response, replace(credential, secret=b'z' * 32), kind='response')


def test_runtime_rejects_forged_and_expired_wire_requests(fixture):
    root, start, call, make_spec, transport = fixture; start()
    spec = make_spec()
    request = contract.envelope(transport.credential, 'submit', {'spec': spec, 'approval': None})
    request['mac'] = '0' * 64
    with pytest.raises(EOFError): call('submit', {}, request=request)
    expired = contract.envelope(transport.credential, 'discover', {}, now=time.time() - 40)
    with pytest.raises(EOFError): call('discover', {}, request=expired)
    assert not (root / 'exports' / spec['task_id']).exists()


@pytest.mark.parametrize('field,value', [('model', 'foreign-model'), ('session_id', 'borrowed-session'),
                                       ('credentials', {'token': 'fictional'}), ('tools', ['bash'])])
def test_task_cannot_override_runtime_owned_configuration(fixture, field, value):
    spec = fixture[3]('write_artifact')
    with pytest.raises(contract.ProtocolError): contract.normalize_spec(dict(spec, **{field: value}))


def test_scope_and_private_socket_access_fail_closed(fixture):
    root, start, _, make_spec, transport = fixture; start()
    spec = make_spec('write_artifact')
    spec['task']['artifact'] = '../private-memory.txt'
    with pytest.raises(contract.ProtocolError): contract.normalize_spec(spec)
    transport.socket_path.chmod(0o666)
    with pytest.raises(contract.ProtocolError, match='private'): transport.discover()
