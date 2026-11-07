import _socket
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import sys
import time
import uuid

import pytest

from agent.external import contract
from agent.external.transport import ExternalTransport


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config, "config", config.Config({
        "agent_workspace": str(tmp_path / "workspace"), "agent_permission_mode": "workspace-write",
        "self_evolution_enabled": False, "knowledge": False, "cow_lang": "en",
    }))
    os.chmod(tmp_path, 0o700)
    config = {'supervisor_id': 'supervisor', 'runtime_id': 'runtime', 'key_id': 'key',
              'secret_hex': 'ab' * 32, 'expires_at': time.time() + 600,
              'operations': ['write_artifact', 'record_effect'], 'name': 'fake', 'model': 'fake-model'}
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    cred = contract.Credential(config['supervisor_id'], config['runtime_id'], config['key_id'],
                               bytes.fromhex(config['secret_hex']), config['expires_at'], tuple(config['operations']))
    socket_dir = tempfile.TemporaryDirectory(prefix='cowext-', dir='/tmp')
    root, sock = tmp_path / 'runtime', (Path(socket_dir.name) / 's').resolve()
    processes = []
    previous_connect = socket.socket.connect

    def guarded_connect(client, address):
        if client.family == socket.AF_UNIX and address == str(sock):
            return _socket.socket.connect(client, address)
        if previous_connect is _socket.socket.connect:
            raise RuntimeError('Network access outside owned fixture denied')
        return previous_connect(client, address)

    monkeypatch.setattr(socket.socket, 'connect', guarded_connect)
    private_env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR') if key in os.environ}
    for key, name in (('HOME', 'home'), ('COW_DATA_DIR', 'data'), ('XDG_CONFIG_HOME', 'xdg')):
        directory = tmp_path / name
        directory.mkdir(mode=0o700)
        private_env[key] = str(directory)

    def start(pause=None):
        args = [sys.executable, '-m', 'agent.external.synthetic_runtime', '--root', str(root),
                '--socket', str(sock), '--config', str(path)]
        if pause:
            args += ['--pause-at', pause]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=private_env)
        processes.append(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(process.stderr.read().decode())
            try:
                call('discover', {})
                return process
            except (OSError, EOFError):
                time.sleep(.02)
        raise AssertionError('Runtime failed to start')

    def call(action, payload, request=None):
        request = request or contract.envelope(cred, action, payload)
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(2)
            client.connect(str(sock))
            client.sendall(contract.canonical(request).encode() + b'\n')
            response = client.makefile('rb').readline()
        if not response:
            raise EOFError()
        response = json.loads(response)
        return contract.authenticate(response, cred, kind='response', request_id=request['request_id'], action=action)

    def spec(operation='record_effect'):
        task_id = str(uuid.uuid4())
        return contract.normalize_spec({'task_id': task_id, 'idempotency_key': 'key-' + task_id,
            'owner_id': 'owner', 'source_id': 'source', 'conversation_id': 'conversation',
            'runtime_id': 'runtime', 'task': {'operation': operation, 'artifact': 'output.txt', 'content': 'fictional'},
            'authority': {'operations': [operation], 'resource': task_id, 'expires_at': time.time() + 300},
            'verification': {}})

    yield root, start, call, spec, ExternalTransport(sock.resolve(), cred)
    for process in processes:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        process.stderr.close()
    socket_dir.cleanup()


def wait_for(check):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(.02)
    raise AssertionError('Timed out')


def test_duplicate_and_replay(fixture):
    root, start, call, make_spec, _transport = fixture
    start()
    spec = make_spec()
    approval = {'task_hash': contract.digest(spec), 'approved_by': 'host', 'expires_at': time.time() + 120}
    first = call('submit', {'spec': spec, 'approval': approval})['data']
    duplicate = call('submit', {'spec': spec, 'approval': approval})['data']
    assert first['session_id'] == duplicate['session_id']
    status_payload = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    done = wait_for(lambda: (v if v['state'] == 'completed' else None)
                    if (v := call('status', status_payload)['data']) else None)
    assert done['termination_confirmed'] and done['revision'] >= first['revision']
    assert (root / 'exports' / spec['task_id'] / 'output.txt').read_text() == 'fictional'
    with sqlite3.connect(root / 'effects.db') as db:
        assert db.execute('SELECT task_id,content FROM effects').fetchall() == [(spec['task_id'], 'fictional')]
    request = contract.envelope(contract.Credential('supervisor', 'runtime', 'key', bytes.fromhex('ab' * 32), time.time() + 100), 'discover', {})
    assert call('discover', {}, request)['ok']
    assert call('discover', {}, request)['error'] == 'replay'


def test_killed_after_effect_is_not_replayed(fixture):
    root, start, call, make_spec, _transport = fixture
    process = start('after_effect')
    spec = make_spec()
    approval = {'task_hash': contract.digest(spec), 'approved_by': 'host', 'expires_at': time.time() + 120}
    call('submit', {'spec': spec, 'approval': approval})
    wait_for(lambda: (root / 'reached').exists())
    process.kill()
    process.wait(timeout=5)
    start()
    obs = call('status', {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)})['data']
    assert obs['state'] == 'needs_review' and obs['termination_confirmed']
    with sqlite3.connect(root / 'effects.db') as db:
        assert db.execute('SELECT count(*) FROM effects').fetchone()[0] == 1


def test_concurrent_duplicate_and_cooperative_cancel(fixture):
    from concurrent.futures import ThreadPoolExecutor

    root, start, call, make_spec, _transport = fixture
    start('before_intent')
    spec = make_spec('write_artifact')
    payload = {'spec': spec, 'approval': None}
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: call('submit', payload), range(8)))
    assert all(response['ok'] for response in responses)
    assert len({response['data']['session_id'] for response in responses}) == 1
    wait_for(lambda: (root / 'reached').exists())
    task = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    cancelling = call('cancel', task)['data']
    assert cancelling['state'] == 'running' and cancelling['cancel_requested']
    assert not cancelling['termination_confirmed']
    (root / 'release').touch()
    done = wait_for(lambda: (v if v['state'] == 'cancelled' else None)
                    if (v := call('status', task)['data']) else None)
    assert done['termination_confirmed'] and done['revision'] > cancelling['revision']
    assert not (root / 'exports' / spec['task_id'] / 'output.txt').exists()
