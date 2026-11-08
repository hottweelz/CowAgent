import json
import os
import threading
import time
import uuid

import pytest

from agent.external import analysis, contract
from agent.external.cowagent_adapter import CowAgentRuntime
from agent.external.synthetic_runtime import Rejection


class Gate:
    def __init__(self):
        self.denied = False
        self.native_count = self.publications = 0
        self.cancelled = False
        self.claimed = False

    def validate_submission(self, *args, **kwargs):
        if self.denied:
            raise contract.ProtocolError('denied')

    def authorize_native(self, *args, **kwargs):
        self.validate_submission()
        self.native_count += 1
        if self.native_count > 1:
            raise contract.ProtocolError('duplicate intent')

    def authorize_publication(self, *args, **kwargs):
        self.validate_submission()
        if self.cancelled:
            raise contract.ProtocolError('cancelled')
        self.publications += 1

    def should_cancel(self, *args, **kwargs):
        return self.cancelled

    def claim_cancel(self, task_id):
        if self.claimed:
            return False
        self.claimed = True
        return True


class Native:
    enrollment = {'runtime_kind': 'cowagent-registered/1', 'agent_id': 'testpilot', 'model': 'fixture',
                  'provider': 'provider', 'config_sha256': 'a' * 64, 'profile_sha256': 'b' * 64,
                  'source_sha256': 'c' * 64, 'probe_sha256': 'd' * 64}

    def __init__(self, hold=False):
        self.hold = hold
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self.drift = False
        self.receipt_binding = {'agent_id': self.enrollment['agent_id'], 'agent_name': 'Fixture',
                                'model': self.enrollment['model'], 'provider': self.enrollment['provider'],
                                'profile_sha256': self.enrollment['profile_sha256'], 'memory_scope_sha256': 'e' * 64}

    def discover(self):
        value = {k: v for k, v in self.enrollment.items() if k != 'probe_sha256'}
        if self.drift:
            value['model'] = 'changed'
        return value

    def prepare(self, session_id):
        self.session_id = session_id
        return self

    def run(self, spec, cancel_event):
        self.calls += 1
        self.started.set()
        if self.hold:
            while not self.release.wait(.01):
                if cancel_event.is_set():
                    break
        return {'report': analysis.expected_report(spec), 'receipt': {
            **self.receipt_binding, 'native_pid': os.getpid(),
            'native_started_at': time.time(), 'native_finished_at': time.time(),
            'session_id': self.session_id, 'source': 'codex', 'prompt_source': 'native',
            'memory_owner': 'runtime', 'permission_mode': 'read-only', 'native_run_id': 'run-1', 'tool_event_count': 0}}


def setup_runtime(tmp_path, native=None, gate=None):
    credential = contract.Credential('supervisor', 'cowagent.testpilot', 'key', b'x' * 32, time.time() + 300, ('analyze_records',))
    native, gate = native or Native(), gate or Gate()
    runtime = CowAgentRuntime(tmp_path / 'runtime', tmp_path / 'socket', credential, native, approval_gate=gate, turn_timeout=2)
    task = str(uuid.uuid4())
    spec = contract.normalize_spec({'task_id': task, 'idempotency_key': 'k-' + task,
        'owner_id': 'owner', 'source_id': 'source', 'conversation_id': 'conversation', 'runtime_id': 'cowagent.testpilot',
        'task': {'operation': 'analyze_records', 'artifact': 'report.json', 'content': json.dumps({
            'schema_version': 1, 'currency': 'USD', 'records': [{'id': 'a', 'amount_cents': 100, 'status': 'paid'}]})},
        'authority': {'operations': ['analyze_records'], 'resource': task, 'expires_at': time.time() + 200}, 'verification': {}})
    return runtime, credential, native, gate, spec


def call(rt, cred, action, payload):
    return rt.handle(contract.envelope(cred, action, payload))


def wait_for(fn):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(.01)
    raise AssertionError('timeout')


def test_success_and_duplicate(tmp_path):
    rt, cred, native, gate, spec = setup_runtime(tmp_path)
    try:
        payload = {'spec': spec, 'approval': {}}
        first = call(rt, cred, 'submit', payload)
        second = call(rt, cred, 'submit', payload)
        assert first['session_id'] == second['session_id']
        key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
        done = wait_for(lambda: (o if o['state'] == 'completed' else None) if (o := call(rt, cred, 'status', key)) else None)
        assert native.calls == gate.native_count == gate.publications == 1
        assert json.loads((rt.root / 'exports' / spec['task_id'] / 'report.json').read_text()) == analysis.expected_report(spec)
        assert done['result']['publication_status'] == 'published'
    finally:
        rt.close()


def test_denial_and_binding_drift(tmp_path):
    rt, cred, native, gate, spec = setup_runtime(tmp_path)
    try:
        gate.denied = True
        with pytest.raises(Rejection):
            call(rt, cred, 'submit', {'spec': spec, 'approval': {}})
        gate.denied = False
        native.drift = True
        call(rt, cred, 'submit', {'spec': spec, 'approval': {}})
        key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
        wait_for(lambda: call(rt, cred, 'status', key)['state'] == 'failed')
        assert native.calls == gate.native_count == 0
    finally:
        rt.close()


def test_cancel_fences_publication_and_restart_never_replays(tmp_path):
    rt, cred, native, gate, spec = setup_runtime(tmp_path, Native(hold=True))
    payload = {'spec': spec, 'approval': {}}
    key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    call(rt, cred, 'submit', payload)
    assert native.started.wait(2)
    call(rt, cred, 'cancel', key)
    wait_for(lambda: call(rt, cred, 'status', key)['state'] == 'cancelled')
    assert gate.publications == 0
    assert not (rt.root / 'exports' / spec['task_id']).exists()
    rt.close()
    restarted = CowAgentRuntime(tmp_path / 'runtime', tmp_path / 'socket', cred, native, approval_gate=gate)
    try:
        assert call(restarted, cred, 'submit', payload)['state'] == 'cancelled'
        assert native.calls == 1
    finally:
        restarted.close()


def test_restart_running_is_uncertain_and_not_replayed(tmp_path):
    rt, cred, native, gate, spec = setup_runtime(tmp_path)
    key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
    with rt.mutex:
        rt.db.execute('INSERT INTO tasks(task_id,supervisor_id,task_hash,idempotency_key,spec,approval,session_id,state,revision) VALUES (?,?,?,?,?,?,?,?,?)',
                      (spec['task_id'], cred.supervisor_id, contract.digest(spec), spec['idempotency_key'], contract.canonical(spec), '{}', str(uuid.uuid4()), 'running', 1))
    # Simulate a lost process without the graceful shutdown fence.
    rt.db.close()
    import os
    os.close(rt.lock_fd)
    restarted = CowAgentRuntime(tmp_path / 'runtime', tmp_path / 'socket', cred, native, approval_gate=gate)
    try:
        value = call(restarted, cred, 'status', key)
        assert value['state'] == 'running' and not value['termination_confirmed']
        assert call(restarted, cred, 'submit', {'spec': spec, 'approval': {}})['session_id'] == value['session_id']
        assert native.calls == 0
    finally:
        restarted.close()


def test_operator_revocation_claims_cancel_and_fences_publication(tmp_path):
    rt, cred, native, gate, spec = setup_runtime(tmp_path, Native(hold=True))
    try:
        call(rt, cred, 'submit', {'spec': spec, 'approval': {}})
        assert native.started.wait(2)
        gate.cancelled = True
        key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
        wait_for(lambda: call(rt, cred, 'status', key)['state'] == 'cancelled')
        assert gate.claimed and gate.publications == 0
    finally:
        rt.close()


def test_request_replay_is_rejected(tmp_path):
    rt, cred, native, gate, spec = setup_runtime(tmp_path)
    try:
        request = contract.envelope(cred, 'discover', {})
        assert rt.handle(request)['native_capabilities']['agent_id'] == 'testpilot'
        with pytest.raises(Rejection, match='replay'):
            rt.handle(request)
    finally:
        rt.close()


def test_credential_target_mismatch_is_rejected(tmp_path):
    credential = contract.Credential('supervisor', 'cowagent.testpilot2', 'key', b'x' * 32,
                                     time.time() + 300, ('analyze_records',))
    with pytest.raises(ValueError, match='target differ'):
        CowAgentRuntime(tmp_path / 'runtime', tmp_path / 'socket', credential, Native(), approval_gate=Gate())


def test_receipt_mismatch_fences_publication(tmp_path):
    native = Native()
    original = native.run
    def bad_run(*args):
        result = original(*args)
        result['receipt']['agent_id'] = 'testpilot2'
        return result
    native.run = bad_run
    rt, cred, _, gate, spec = setup_runtime(tmp_path, native)
    try:
        call(rt, cred, 'submit', {'spec': spec, 'approval': {}})
        key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
        wait_for(lambda: call(rt, cred, 'status', key)['reason'] == 'dispatch_uncertain')
        assert gate.publications == 0
        assert not (rt.root / 'exports' / spec['task_id']).exists()
    finally:
        rt.close()


def test_same_runtime_serializes_sessions_and_queued_cancel(tmp_path):
    class MultiGate(Gate):
        def authorize_native(self, *args, **kwargs):
            self.validate_submission()
            self.native_count += 1
    native = Native(hold=True)
    rt, cred, _, gate, first = setup_runtime(tmp_path, native, MultiGate())
    second = json.loads(json.dumps(first))
    second['task_id'] = str(uuid.uuid4())
    second['idempotency_key'] = 'k-' + second['task_id']
    second['authority']['resource'] = second['task_id']
    try:
        a = call(rt, cred, 'submit', {'spec': first, 'approval': {}})
        assert native.started.wait(2)
        b = call(rt, cred, 'submit', {'spec': second, 'approval': {}})
        assert a['session_id'] != b['session_id']
        key = {'task_id': second['task_id'], 'task_hash': contract.digest(second)}
        assert call(rt, cred, 'cancel', key)['cancel_requested']
        assert native.calls == 1
        native.release.set()
        wait_for(lambda: call(rt, cred, 'status', key)['state'] == 'cancelled')
        assert native.calls == 1
        assert gate.native_count == 1
    finally:
        rt.close()


def test_separate_runtime_instances_can_overlap(tmp_path):
    barrier = threading.Barrier(2, timeout=2)
    class BarrierNative(Native):
        def run(self, spec, cancel_event):
            barrier.wait()
            return super().run(spec, cancel_event)
    (tmp_path / 'one').mkdir(mode=0o700)
    (tmp_path / 'two').mkdir(mode=0o700)
    one = setup_runtime(tmp_path / 'one', BarrierNative())
    two_native = BarrierNative()
    two_native.enrollment = dict(two_native.enrollment, agent_id='testpilot2', model='fixture-2')
    two_native.receipt_binding = dict(two_native.receipt_binding, agent_id='testpilot2', model='fixture-2')
    cred2 = contract.Credential('supervisor', 'cowagent.testpilot2', 'key', b'x' * 32,
                                time.time() + 300, ('analyze_records',))
    rt2 = CowAgentRuntime(tmp_path / 'two' / 'runtime', tmp_path / 'two' / 'socket', cred2,
                          two_native, approval_gate=Gate())
    rt1, cred1, _, _, spec1 = one
    spec2 = json.loads(json.dumps(spec1))
    spec2['task_id'] = str(uuid.uuid4())
    spec2['idempotency_key'] = 'k-' + spec2['task_id']
    spec2['authority']['resource'] = spec2['task_id']
    spec2['runtime_id'] = 'cowagent.testpilot2'
    try:
        for rt, cred, spec in ((rt1, cred1, spec1), (rt2, cred2, spec2)):
            call(rt, cred, 'submit', {'spec': spec, 'approval': {}})
        for rt, cred, spec in ((rt1, cred1, spec1), (rt2, cred2, spec2)):
            key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
            wait_for(lambda: call(rt, cred, 'status', key)['state'] == 'completed')
    finally:
        rt1.close()
        rt2.close()


def test_same_runtime_runs_two_distinct_sessions_in_order(tmp_path):
    class MultiGate(Gate):
        def authorize_native(self, *args, **kwargs):
            self.validate_submission()
            self.native_count += 1
    native = Native(hold=True)
    rt, cred, _, gate, first = setup_runtime(tmp_path, native, MultiGate())
    second = json.loads(json.dumps(first))
    second['task_id'] = str(uuid.uuid4())
    second['idempotency_key'] = 'k-' + second['task_id']
    second['authority']['resource'] = second['task_id']
    try:
        first_obs = call(rt, cred, 'submit', {'spec': first, 'approval': {}})
        assert native.started.wait(2)
        second_obs = call(rt, cred, 'submit', {'spec': second, 'approval': {}})
        assert first_obs['session_id'] != second_obs['session_id']
        assert native.calls == 1
        native.release.set()
        for spec, observation in ((first, first_obs), (second, second_obs)):
            key = {'task_id': spec['task_id'], 'task_hash': contract.digest(spec)}
            result = wait_for(lambda: (o if o['state'] == 'completed' else None)
                              if (o := call(rt, cred, 'status', key)) else None)
            assert result['result']['session_id'] == observation['session_id']
        assert native.calls == gate.native_count == gate.publications == 2
    finally:
        rt.close()
