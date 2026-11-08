import _socket
import json
from pathlib import Path
import queue
import socket
import tempfile
import threading
import time
import uuid

import pytest

from agent.external import contract
from agent.external.codex_adapter import CodexRuntime
from agent.external.synthetic_runtime import Rejection
from agent.external.transport import ExternalTransport


class FakePolicy:
    task_effects_confined = True
    def launch(self, cwd): return ['fake'], {}, {}
    def initialize(self, client): pass
    def start_thread(self, client, cwd): return {'thread': {'id': 'native-thread', 'sessionId': 'native-session'}}
    def discover(self, cwd): return {'model': 'fake-model', 'modelProvider': 'fake-provider'}
    def attest_configuration(self, client, cwd, thread, expected): pass


class FakeClient:
    def __init__(self, output='{"wrong":true}', hold=False, fail=False):
        self.output = output
        self.hold = hold
        self.fail = fail
        self.released = threading.Event()
        self.events = queue.Queue()
        self.starts = 0
        self.interrupts = 0

    def request(self, method, params, timeout):
        if method == 'thread/read':
            return {'thread': {'id': 'native-thread', 'sessionId': 'native-session', 'turns': [{'id': 'native-turn', 'status': 'completed', 'itemsView': 'full', 'items': []}]}}
        if method == 'turn/interrupt':
            self.interrupts += 1
            return {}
        assert method == 'turn/start'
        self.starts += 1
        if self.fail:
            raise TimeoutError('unknown dispatch')
        if not self.hold:
            self.finish()
        return {'turn': {'id': 'native-turn'}}

    def finish(self):
        self.events.put({'method': 'item/completed', 'params': {'threadId': 'native-thread', 'turnId': 'native-turn', 'item': {'type': 'agentMessage', 'phase': 'final_answer', 'text': self.output}}})
        self.events.put({'method': 'turn/completed', 'params': {'threadId': 'native-thread', 'turn': {'id': 'native-turn', 'status': 'completed'}}})

    def next_event(self, timeout): return self.events.get(timeout=timeout)
    def close(self): self.released.set()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    cred = contract.Credential('supervisor', 'runtime', 'key', b'x' * 32, time.time() + 300, ('analyze_records',))
    root = tmp_path / 'runtime'
    holder = tempfile.TemporaryDirectory(prefix='cow-adapter-', dir='/tmp')
    socket_path = (Path(holder.name) / 's').resolve()
    previous_connect = socket.socket.connect
    def guarded_connect(client, address):
        if client.family == socket.AF_UNIX and address == str(socket_path):
            return _socket.socket.connect(client, address)
        if previous_connect is _socket.socket.connect:
            raise RuntimeError('Network access outside owned fixture denied')
        return previous_connect(client, address)
    monkeypatch.setattr(socket.socket, 'connect', guarded_connect)
    runtimes = []
    def start(fake_client, policy=None, turn_timeout=2):
        rt = CodexRuntime(root, socket_path, cred, policy or FakePolicy(), client_factory=lambda *a: fake_client, turn_timeout=turn_timeout)
        runtimes.append(rt)
        return rt
    def spec():
        task = str(uuid.uuid4())
        return contract.normalize_spec({'task_id': task, 'idempotency_key': 'key-' + task,
            'owner_id': 'owner', 'source_id': 'source', 'conversation_id': 'conversation',
            'runtime_id': 'runtime', 'task': {'operation': 'analyze_records', 'artifact': 'report.json', 'content': json.dumps({'schema_version': 1, 'currency': 'USD', 'records': [{'id': 'a', 'amount_cents': 100, 'status': 'paid'}]})},
            'authority': {'operations': ['analyze_records'], 'resource': task, 'expires_at': time.time() + 200}, 'verification': {}})
    yield root, socket_path, cred, start, spec
    for rt in runtimes: rt.close()
    holder.cleanup()


def call(rt, credential, action, payload):
    return rt.handle(contract.envelope(credential, action, payload))


def wait_until(f):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        value = f()
        if value: return value
        time.sleep(.01)
    raise AssertionError('condition did not occur')


def test_ipc_submit_duplicate_and_wrong_output_preserved(setup):
    root, socket_path, cred, start, make_spec = setup
    fake = FakeClient()
    rt = start(fake)
    server = threading.Thread(target=rt.serve, daemon=True)
    server.start()
    wait_until(socket_path.exists)
    transport = ExternalTransport(socket_path, cred)
    assert transport.discover()['operations'] == ['analyze_records']
    spec = make_spec()
    first = transport.submit(spec)
    duplicate = transport.submit(spec)
    assert first['session_id'] == duplicate['session_id']
    done = wait_until(lambda: (v if v['state'] == 'completed' else None) if (v := transport.status(spec)) else None)
    assert fake.starts == 1 and done['termination_confirmed']
    assert done['result']['termination_scope'] == 'task_effects'
    assert done['result']['native_session_id'] == 'native-session'
    assert done['session_id'] != done['result']['native_session_id']
    assert done['result']['descendants_terminated'] is False
    assert (root / 'exports' / spec['task_id'] / 'report.json').read_text() == '{"wrong":true}'
    from agent.external.analysis import AnalysisVerifier
    verification = AnalysisVerifier(root / 'exports').verify({'spec': spec, 'observation': done})
    assert verification['acceptance']['status'] == 'failed'
    server.join(timeout=.01)


def test_cancel_fences_publication(setup):
    root, _, cred, start, make_spec = setup
    fake = FakeClient(hold=True)
    rt = start(fake)
    spec = make_spec()
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: fake.starts)
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    cancel = call(rt, cred, 'cancel', query)
    assert cancel['cancel_requested'] and not cancel['termination_confirmed']
    fake.finish()
    done = wait_until(lambda: (v if v['state'] == 'cancelled' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert done['result']['publication_status'] == 'fenced'
    assert not (root / 'exports' / spec['task_id'] / 'report.json').exists()


def test_explicit_repeat_cancel_recovers_lost_interrupt(setup):
    _, _, cred, start, make_spec = setup
    fake = FakeClient(hold=True)
    original = fake.request
    def request(method, params, timeout):
        if method == 'turn/interrupt':
            fake.interrupts += 1
            if fake.interrupts == 1:
                raise TimeoutError('lost native interrupt')
            fake.events.put({'method': 'turn/completed', 'params': {
                'threadId': 'native-thread', 'turn': {'id': 'native-turn', 'status': 'interrupted'}}})
            return {}
        return original(method, params, timeout)
    fake.request = request
    rt = start(fake)
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: (call(rt, cred, 'status', query).get('result') or {}).get('native_turn_id'))
    first = call(rt, cred, 'cancel', query)
    assert first['cancel_requested'] and not first['termination_confirmed']
    wait_until(lambda: fake.interrupts == 1)
    call(rt, cred, 'status', query)
    assert fake.interrupts == 1
    call(rt, cred, 'cancel', query)
    done = wait_until(lambda: (v if v['state'] == 'cancelled' else None)
                      if (v := call(rt, cred, 'status', query)) else None)
    assert fake.interrupts == 2 and done['termination_confirmed']


def test_uncertain_dispatch_never_replayed_after_restart(setup):
    _, _, cred, start, make_spec = setup
    fake = FakeClient(fail=True)
    rt = start(fake)
    spec = make_spec()
    initial = call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    observed = wait_until(lambda: (v if v['reason'] == 'dispatch_uncertain' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert observed['state'] == 'running' and not observed['termination_confirmed']
    rt.close()
    replacement = FakeClient()
    resumed = start(replacement)
    after = call(resumed, cred, 'submit', {'spec': spec, 'approval': None})
    assert after['session_id'] == initial['session_id'] and after['state'] == 'running'
    assert replacement.starts == 0


def test_no_authority_proof_stays_unconfirmed_and_replay_denied(setup):
    _, _, cred, start, make_spec = setup
    policy = FakePolicy()
    policy.task_effects_confined = False
    rt = start(FakeClient(), policy)
    spec = make_spec()
    request = contract.envelope(cred, 'submit', {'spec': spec, 'approval': None})
    rt.handle(request)
    with pytest.raises(Rejection, match='replay'): rt.handle(request)
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    obs = wait_until(lambda: (v if v['reason'] == 'authority_inheritance_unconfirmed' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert obs['state'] == 'running' and not obs['termination_confirmed']


def test_observed_collaboration_is_sanitized(setup):
    _, _, cred, start, make_spec = setup
    fake = FakeClient(hold=True)
    rt = start(fake)
    spec = make_spec()
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: fake.starts)
    fake.events.put({'method': 'item/completed', 'params': {'item': {
        'type': 'subAgentActivity', 'agentThreadId': 'child-1', 'kind': 'started',
        'agentPath': 'private prompt'}}})
    fake.finish()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    done = wait_until(lambda: (v if v['state'] == 'completed' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert done['result']['child_threads'] == [{'id': 'child-1', 'status': 'running'}]
    assert 'private prompt' not in contract.canonical(done)
    assert done['result']['descendants_terminated'] is False


def test_correct_output_independently_verified(setup):
    from agent.external.analysis import AnalysisVerifier, expected_report
    root, _, cred, start, make_spec = setup
    spec = make_spec()
    fake = FakeClient(output=json.dumps(expected_report(spec)))
    rt = start(fake)
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    done = wait_until(lambda: (v if v['state'] == 'completed' else None) if (v := call(rt, cred, 'status', query)) else None)
    verified = AnalysisVerifier(root / 'exports').verify({'spec': spec, 'observation': done})
    assert verified['acceptance']['status'] == 'passed'
    assert verified['external_state']['status'] == 'confirmed'


def test_restart_reads_native_history_without_dispatch(setup):
    _, _, cred, start, make_spec = setup
    first_client = FakeClient(hold=True)
    rt = start(first_client)
    spec = make_spec()
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    wait_until(lambda: call(rt, cred, 'status', query)['result']['native_turn_id'] if call(rt, cred, 'status', query)['result'] else None)
    rt.close()
    resumed_client = FakeClient()
    resumed = start(resumed_client)
    initial = call(resumed, cred, 'status', query)
    assert initial['state'] == 'running' and not initial['termination_confirmed']
    reconciled = wait_until(lambda: (v if v['reason'] == 'reconciled_uncertain' else None) if (v := call(resumed, cred, 'status', query)) else None)
    assert reconciled['result']['native_status'] == 'completed'
    assert reconciled['result']['reconciliation'] == 'read_only_history'
    assert not reconciled['termination_confirmed'] and resumed_client.starts == 0


def test_publication_crash_is_not_replayed(setup):
    root, _, cred, start, make_spec = setup
    rt = start(FakeClient())
    original = rt._artifact
    def write_then_lose_ack(*args):
        original(*args)
        raise OSError('lost publication acknowledgement')
    rt._artifact = write_then_lose_ack
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: (v if v['reason'] == 'dispatch_uncertain' else None) if (v := call(rt, cred, 'status', query)) else None)
    artifact = root / 'exports' / spec['task_id'] / 'report.json'
    assert artifact.read_text() == '{"wrong":true}'
    rt.close()
    replacement = FakeClient(output='{"replayed":true}')
    resumed = start(replacement)
    obs = call(resumed, cred, 'submit', {'spec': spec, 'approval': None})
    assert obs['state'] == 'running' and not obs['termination_confirmed']
    assert replacement.starts == 0 and artifact.read_text() == '{"wrong":true}'


class InterruptibleClient(FakeClient):
    def request(self, method, params, timeout):
        result = super().request(method, params, timeout)
        if method == 'turn/interrupt':
            self.events.put({'method': 'turn/completed', 'params': {
                'threadId': 'native-thread', 'turn': {'id': 'native-turn', 'status': 'interrupted'}}})
        return result


def test_confirmed_interruption_after_cancel_is_scoped(setup):
    root, _, cred, start, make_spec = setup
    fake = InterruptibleClient(hold=True)
    rt = start(fake)
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: (v['result'] or {}).get('native_turn_id') if (v := call(rt, cred, 'status', query)) else None)
    call(rt, cred, 'cancel', query)
    done = wait_until(lambda: (v if v['state'] == 'cancelled' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert done['termination_confirmed'] and done['result']['termination_scope'] == 'task_effects'
    assert done['result']['native_status'] == 'interrupted'
    assert done['result']['descendants_terminated'] is False
    assert not (root / 'exports' / spec['task_id'] / 'report.json').exists()


def test_deadline_requests_interrupt_and_fences_publication(setup):
    root, _, cred, start, make_spec = setup
    fake = InterruptibleClient(hold=True)
    rt = start(fake, turn_timeout=.2)
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    done = wait_until(lambda: (v if v['state'] == 'cancelled' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert fake.interrupts == 1 and done['cancel_requested']
    assert done['result']['native_status'] == 'interrupted'
    assert not (root / 'exports' / spec['task_id'] / 'report.json').exists()


def test_shutdown_fences_even_if_late_completion_arrives(setup):
    class HistoryHoldClient(FakeClient):
        def __init__(self):
            super().__init__(hold=True)
            self.history_entered = threading.Event()
            self.release_history = threading.Event()
        def request(self, method, params, timeout):
            if method == 'thread/read':
                self.history_entered.set()
                assert self.release_history.wait(2)
            return super().request(method, params, timeout)

    root, _, cred, start, make_spec = setup
    fake = HistoryHoldClient()
    rt = start(fake)
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: (v['result'] or {}).get('native_turn_id') if (v := call(rt, cred, 'status', query)) else None)
    fake.finish()
    assert fake.history_entered.wait(2)
    shutdown = threading.Thread(target=rt.close)
    shutdown.start()
    wait_until(lambda: rt.closed)
    fake.release_history.set()
    shutdown.join(3)
    assert not shutdown.is_alive()
    assert not (root / 'exports' / spec['task_id'] / 'report.json').exists()


def test_deadline_without_native_confirmation_remains_running(setup):
    _, _, cred, start, make_spec = setup
    fake = FakeClient(hold=True)
    rt = start(fake, turn_timeout=.15)
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    observed = wait_until(lambda: (v if v['reason'] == 'native_outcome_unconfirmed' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert fake.interrupts == 1 and observed['cancel_requested']
    assert observed['state'] == 'running' and not observed['termination_confirmed']


def test_model_activity_is_sanitized_and_preserved(setup):
    _, _, cred, start, make_spec = setup
    fake = FakeClient(hold=True)
    rt = start(fake)
    spec = make_spec()
    query = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', {'spec': spec, 'approval': None})
    wait_until(lambda: (v['result'] or {}).get('native_turn_id') if (v := call(rt, cred, 'status', query)) else None)
    fake.events.put({'method': 'item/started', 'params': {
        'threadId': 'native-thread', 'turnId': 'native-turn',
        'item': {'type': 'reasoning', 'summary': ['private model prose']}}})
    activity = wait_until(lambda: (v if (v['result'] or {}).get('model_activity_observed') else None)
                          if (v := call(rt, cred, 'status', query)) else None)
    assert activity['result']['model_activity_counts'] == {'reasoning': 1}
    assert 'private model prose' not in contract.canonical(activity)
    fake.finish()
    done = wait_until(lambda: (v if v['state'] == 'completed' else None) if (v := call(rt, cred, 'status', query)) else None)
    assert done['result']['model_activity_observed'] is True
    assert done['result']['model_activity_counts'] == {'reasoning': 1}
    assert 'private model prose' not in contract.canonical(done)
