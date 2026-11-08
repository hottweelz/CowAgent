#!/usr/bin/env python3
"""Opt-in EXTERNAL-003B acceptance with private, retained fictional fixtures.

Runs two bounded model turns and two native empty-thread cases. No OAuth files,
configuration, profile, or model selection are changed. Cancellation is scoped;
this does not prove descendant termination or a hard cost ceiling.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import secrets
import signal
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import uuid

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
old = runpy.run_path(str(PROJECT / 'docs/external-002b/run_native_acceptance.py'))
write_json, say, wait_for = (old[k] for k in ('write_json', 'say', 'wait_for'))
credential, make_spec, fixture_repository = (old[k] for k in ('credential', 'make_spec', 'fixture_repository'))
observe_until, native_turns, assert_preflight = (old[k] for k in ('observe_until', 'native_turns', 'assert_preflight'))

SCOPE = {'supervisor_id': 'acceptance-supervisor', 'owner_id': 'acceptance-owner',
         'source_id': 'fixture', 'conversation_id': 'fixture', 'runtime_id': 'acceptance-runtime'}


def make_host(root):
    from agent.external.analysis import AnalysisVerifier
    from agent.external.approved_dispatch import ApprovalJournal
    from agent.external.operator_control import OperatorControl
    from agent.external.supervisor import ExternalSupervisor
    from agent.external.transport import ExternalTransport
    root = Path(root)
    control = OperatorControl(root / 'operator')
    journal = ApprovalJournal(control)
    host = ExternalSupervisor(journal, ExternalTransport(root / 'ipc/runtime.sock', credential(root), timeout=30),
                              owner_id=SCOPE['owner_id'], source_id=SCOPE['source_id'],
                              conversation_id=SCOPE['conversation_id'],
                              verifier=AnalysisVerifier(root / 'runtime/exports'))
    return control, host


def decision(control, action, payload, expected_revision):
    from agent.external.operator_control import VERSION
    return control.apply({'protocol': VERSION, 'request_id': str(uuid.uuid4()), 'action': action,
                          'scope': SCOPE, 'expected_revision': expected_revision, 'payload': payload})


def enroll(control, enrollment, expiry):
    from agent.external.operator_review import build_enrollment_review
    current = {k: v for k, v in enrollment.items() if k != 'probe_sha256'}
    review = build_enrollment_review(enrollment, current=current, observed_probe_sha256=enrollment['probe_sha256'])
    decision(control, 'enroll', {'review': review, 'expires_at': expiry}, 0)
    return review


def approve(control, spec, review, expiry):
    from agent.external.operator_review import build_task_review
    now = time.time()
    draft = build_task_review(spec, review, now=now)
    return decision(control, 'approve_task', {'spec': spec, 'enrollment_revision': 1,
                    'task_review_id': draft['review_id'], 'reviewed_at': now, 'expires_at': expiry}, 0)


def revoke(control, spec):
    return decision(control, 'revoke_task', {'task_id': spec['task_id']}, 1)


def hook_enabled(root, name, task):
    path = root / (name + '.json')
    return path.exists() and json.loads(path.read_text())['task_id'] == task


def runtime_main(root, executable, enrollment_path):
    from agent.external.approved_dispatch import ApprovalJournal
    from agent.external.codex_adapter import CodexRuntime
    from agent.external.codex_client import CodexClient
    from agent.external.codex_policy import CodexAnalysisPolicy
    from agent.external.operator_control import OperatorControl
    root = Path(root)
    enrollment = json.loads(Path(enrollment_path).read_text())
    class PausingPolicy(CodexAnalysisPolicy):
        def attest_configuration(self, client, cwd, thread, expected):
            result = super().attest_configuration(client, cwd, thread, expected)
            task = Path(cwd).name
            if hook_enabled(root, 'pause-attestation', task):
                write_json(root / ('attestation-paused-' + task + '.json'), {'task_id': task,
                           'native_thread': thread['thread']['id'], 'native_session': thread['thread']['sessionId']})
                wait_for('attestation release', lambda: (root / ('attestation-release-' + task)).exists(), timeout=180)
            return result
    class Client(CodexClient):
        def __init__(self, argv, cwd, env):
            super().__init__(argv, cwd, env)
            self.fixture_task = Path(cwd).name
            try:
                task = str(uuid.UUID(self.fixture_task))
            except ValueError:
                task = None
            if task == self.fixture_task:
                path = root / ('rpc-' + task + '.jsonl')
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'a', encoding='utf-8') as stream:
                    stream.write(json.dumps({'task_id': task, 'method': 'fixture/client_created', 'timestamp': time.time()}) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
        def request(self, method, params, **kwargs):
            if method == 'turn/start' and hook_enabled(root, 'pause-turn', self.fixture_task):
                write_json(root / ('turn-paused-' + self.fixture_task + '.json'), {'task_id': self.fixture_task})
                wait_for('turn release', lambda: (root / ('turn-release-' + self.fixture_task)).exists(), timeout=180)
            if method in ('turn/start', 'turn/interrupt'):
                event = {'task_id': self.fixture_task, 'method': method,
                         'thread_id': params.get('threadId'), 'timestamp': time.time()}
                if 'turnId' in params:
                    event['turn_id'] = params['turnId']
                path = root / ('rpc-' + self.fixture_task + '.jsonl')
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'a', encoding='utf-8') as stream:
                    stream.write(json.dumps(event, sort_keys=True) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            return super().request(method, params, **kwargs)
    runtime = CodexRuntime(root / 'runtime', root / 'ipc/runtime.sock', credential(root),
                           PausingPolicy(executable, enrollment=enrollment), client_factory=Client,
                           approval_gate=ApprovalJournal(OperatorControl(root / 'operator')))
    def stop(_sig, _frame):
        if getattr(runtime, 'server', None):
            threading.Thread(target=runtime.server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    try:
        runtime.serve()
    finally:
        runtime.close()


def pause_host(root, spec_path):
    _, host = make_host(root)
    spec = json.loads(Path(spec_path).read_text())
    original = host.transport.submit
    def pause(specification, approval):
        response = original(specification, approval)
        write_json(Path(root) / 'host-accepted.json', {'task_id': specification['task_id'],
                   'session_id': response['session_id']})
        wait_for('host process termination', lambda: False, timeout=180)
    host.transport.submit = pause
    host.submit(spec['task_id'])


def spawn(args, env, root, label):
    log = open(Path(root) / (label + '.log'), 'ab', buffering=0)
    try:
        return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *args], cwd=PROJECT,
                                env=env, start_new_session=True, stdout=log, stderr=log)
    finally:
        log.close()


def stop(process, forced=False):
    if process is None or process.poll() is not None:
        return
    groups = old['owned_groups'](process.pid)
    process.send_signal(signal.SIGKILL if forced else signal.SIGTERM)
    try:
        process.wait(timeout=5 if forced else 15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    # Groups were captured while the parent was alive; cleanup must not skip them.
    for group in groups:
        try:
            os.killpg(group, signal.SIGKILL)
        except ProcessLookupError:
            pass
    def groups_gone():
        for group in groups:
            try:
                os.killpg(group, 0)
            except ProcessLookupError:
                continue
            return False
        return True
    wait_for('owned process group cleanup', groups_gone, timeout=10)


def db_row(path, sql, args=()):
    with sqlite3.connect(path, timeout=30) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(sql, args).fetchone()
        return dict(row) if row else None


def denied(call):
    from agent.external.contract import ProtocolError
    try:
        call()
    except ProtocolError:
        return
    raise AssertionError('Operation unexpectedly accepted')


def empty_history(policy, workspace, thread_id):
    from agent.external.codex_client import RemoteError
    try:
        turns = native_turns(policy, workspace, thread_id)
    except RemoteError as exc:
        error = exc.error if isinstance(exc.error, dict) else {}
        code = error.get('code')
        if not isinstance(code, (int, str)):
            code = None
        reason = 'thread_not_loaded' if 'thread not loaded' in str(error.get('message', '')).lower() else 'rpc_error'
        return {'status': 'unavailable', 'error_type': 'RemoteError', 'error_code': code, 'reason': reason}
    if turns:
        raise AssertionError('Expected zero native public turns')
    return {'status': 'available', 'turns': turns}


def no_turn_start_trace(root, task):
    path = root / ('rpc-' + task + '.jsonl')
    if not path.exists():
        raise AssertionError('Fixture RPC trace missing')
    events = [json.loads(line) for line in path.read_text().splitlines()]
    if not any(event.get('method') == 'fixture/client_created' and event.get('task_id') == task for event in events):
        raise AssertionError('Fixture RPC instrumentation was not observed')
    if any(event.get('method') == 'turn/start' for event in events):
        raise AssertionError('Fixture attempted a native turn/start')
    return {'evidence': 'fixture_client_outbound_rpc_attempts', 'task_id': task,
            'turn_start_attempts': 0, 'events': events}


def execute(executable, root_arg=None, *, resume=False):
    import tempfile
    from agent.external import contract
    from agent.external.codex_policy import CodexAnalysisPolicy
    from agent.external.operator_control import OperatorControl
    root = Path(root_arg) if root_arg else Path(tempfile.mkdtemp(prefix='cowagent-003b-', dir='/private/tmp')).resolve()
    if not root.is_absolute() or root.resolve() != root or root.parent != Path('/private/tmp'):
        raise ValueError('Fixture root must be canonical and under /private/tmp')
    if root.exists():
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or (not resume and any(root.iterdir())):
            raise ValueError('Existing fixture root must be private, owned and empty')
    else:
        if resume:
            raise ValueError('Resume requires an existing fixture root')
        root.mkdir(mode=0o700)
    if resume and not root_arg:
        raise ValueError('Resume requires a retained fixture root')
    if not resume:
        for name in ('ipc', 'cow-data', 'preflight', 'receipts'):
            (root / name).mkdir(mode=0o700)
    os.environ['COW_DATA_DIR'] = str(root / 'cow-data')
    say('Retained fixture: ' + str(root))
    runtime = host_process = None
    config_path = before = None
    status = 'incomplete'
    previous = None
    if resume:
        final_path = root / 'receipts/final.json'
        previous = json.loads(final_path.read_text())
        denials = json.loads((root / 'receipts/denials.json').read_text())
        success = json.loads((root / 'receipts/success.json').read_text())
        if (previous['status'] != 'incomplete' or not previous['native_config_unchanged']
                or not previous['owned_group_cleanup_confirmed']
                or not all(denials.get(k) is True for k in ('unapproved_denied', 'raw_legacy_denied', 'revoked_denied', 'unsupported_effect_denied', 'runtime_row_absent'))
                or not success['verification']['verified'] or len(success['native_turns']) != 1):
            raise ValueError('Required prior acceptance receipts are invalid')
        for name, expected in previous['source_sha256'].items():
            if name != 'docs/external-003b/run_native_acceptance.py' and old['digest_file'](PROJECT / name) != expected:
                raise ValueError('Product source changed since accepted evidence: ' + name)
        archive = root / 'receipts/attempt-1-final.json'
        if archive.exists():
            raise ValueError('Prior final receipt already archived')
    try:
        enrollment, config_path, before = assert_preflight(executable, root / 'preflight')
        _, native_env, _ = CodexAnalysisPolicy(executable).launch(root / 'preflight')
        env = dict(native_env, COW_DATA_DIR=str(root / 'cow-data'))
        if resume:
            saved_enrollment = json.loads((root / 'enrollment.json').read_text())
            if enrollment != saved_enrollment or before != previous['config_sha_after']:
                raise ValueError('Retained enrollment or native configuration differs')
            control = OperatorControl(root / 'operator')
            current = control.status(SCOPE)
            expiry = credential(root).expires_at
            grant_expiry = current['expires_at']
            if not current['approval_current'] or min(expiry, grant_expiry) <= time.time():
                raise ValueError('Retained credential or enrollment approval expired')
            review = current['review']
            if review['enrollment'] != enrollment:
                raise ValueError('Retained operator enrollment differs')
            # Preserve the prior final only after every preflight check succeeds.
            write_json(archive, previous)
        else:
            expiry = time.time() + 1800
            grant_expiry = expiry - 60
            write_json(root / 'ipc-key.json', {'secret': secrets.token_hex(32), 'expires_at': expiry})
            write_json(root / 'enrollment.json', enrollment)
            control = OperatorControl(root / 'operator', initialize=True)
            review = enroll(control, enrollment, grant_expiry)
        runtime_args = ['--runtime', '--root', str(root), '--executable', executable, '--enrollment', str(root / 'enrollment.json')]
        runtime = spawn(runtime_args, env, root, 'runtime')
        control, host = make_host(root)
        wait_for('runtime socket', lambda: (root / 'ipc/runtime.sock').exists(), timeout=30, process=runtime)
        def discover_when_ready():
            from agent.external.transport import RemoteRejected, TransportUnavailable
            try:
                return host.discover()
            except (RemoteRejected, TransportUnavailable):
                return None
        discovery = wait_for('runtime discovery', discover_when_ready, timeout=90, process=runtime)
        if discovery['model'] != enrollment['model'] or discovery['native_capabilities']['modelProvider'] != enrollment['modelProvider']:
            raise AssertionError('Discovery does not match enrollment')
        say('Private runtime and enrolled operator are ready')
        records = [{'id': 'sale1', 'amount_cents': 12500, 'status': 'paid'},
                   {'id': 'refund1', 'amount_cents': -2500, 'status': 'refund'},
                   {'id': 'pending1', 'amount_cents': 8000, 'status': 'pending'},
                   {'id': 'sale2', 'amount_cents': 3000, 'status': 'paid'},
                   {'id': 'invalid1', 'amount_cents': -100, 'status': 'paid'},
                   {'id': 'void1', 'amount_cents': 4400, 'status': 'void'},
                   {'id': 'sale1', 'amount_cents': 12500, 'status': 'paid'}]
        policy = CodexAnalysisPolicy(executable, enrollment=enrollment)
        if not resume:
            bad = make_spec(records, expiry)
            host.prepare(bad)
            denied(lambda: host.submit(bad['task_id']))
            legacy = {'task_hash': contract.digest(bad), 'approved_by': 'fixture', 'expires_at': grant_expiry}
            denied(lambda: host.transport.submit(bad, legacy))
            assert db_row(root / 'runtime/runtime.db', 'SELECT task_id FROM tasks WHERE task_id=?', (bad['task_id'],)) is None
            approve(control, bad, review, grant_expiry)
            revoke(control, bad)
            denied(lambda: host.submit(bad['task_id']))
            assert not host.journal.get(bad['task_id'])['submission_started']
            effect = dict(bad, task=dict(bad['task'], operation='record_effect', content='fictional'),
                          authority=dict(bad['authority'], operations=['record_effect']))
            denied(lambda: host.transport.submit(effect, legacy))
            assert db_row(root / 'runtime/runtime.db', 'SELECT task_id FROM tasks WHERE task_id=?', (bad['task_id'],)) is None
            write_json(root / 'receipts/denials.json', {'task_id': bad['task_id'], 'unapproved_denied': True,
                       'raw_legacy_denied': True, 'revoked_denied': True, 'unsupported_effect_denied': True,
                       'runtime_row_absent': True})
            say('Unapproved, revoked, legacy and unsupported requests rejected')

            spec = make_spec(records, expiry)
            fixture_repository(root, spec, env)
            host.prepare(spec)
            approve(control, spec, review, grant_expiry)
            write_json(root / 'success-spec.json', spec)
            host_process = spawn(['--pause-host', '--root', str(root), '--spec', str(root / 'success-spec.json')], env, root, 'host')
            marker = wait_for('accepted submission before host observation', lambda: json.loads((root / 'host-accepted.json').read_text()) if (root / 'host-accepted.json').exists() else None, timeout=90, process=host_process)
            stop(host_process, forced=True)
            host_process = None
            control, host = make_host(root)
            reconciled = host.reconcile()
            duplicate = host.submit(spec['task_id'])
            done = observe_until(host, spec['task_id'], 'completed analysis', lambda v: v['termination_confirmed'], timeout=180)
            if done['execution_status'] != 'completed' or done['session_id'] != marker['session_id']:
                raise AssertionError('Original task did not complete under original session')
            verified = host.verify(spec['task_id'])
            artifact = root / 'runtime/exports' / spec['task_id'] / 'report.json'
            report = json.loads(artifact.read_text())
            totals = {'paid_cents': 15500, 'refund_cents': -2500, 'pending_cents': 8000, 'net_cents': 13000}
            if not verified['verified'] or report['totals'] != totals or report['accepted_count'] != 4 or len(report['exceptions']) != 3:
                raise AssertionError('Analysis verification or expected totals failed')
            policy = CodexAnalysisPolicy(executable, enrollment=enrollment)
            result = done['runtime_result']
            turns = native_turns(policy, root / 'runtime/workspaces' / spec['task_id'], result['native_thread_id'])
            if len(turns) != 1 or turns[0]['id'] != result['native_turn_id']:
                raise AssertionError('Success must have one original native turn')
            write_json(root / 'receipts/success.json', {'task_id': spec['task_id'], 'ack': marker, 'reconciled': reconciled,
                       'duplicate': duplicate, 'outcome': done, 'verification': verified, 'report': report, 'native_turns': turns})
            say('Host crash recovered; analysis verified with one native turn')

        queued = make_spec(records, expiry)
        fixture_repository(root, queued, env)
        host.prepare(queued)
        approve(control, queued, review, grant_expiry)
        write_json(root / 'pause-attestation.json', {'task_id': queued['task_id']})
        host.submit(queued['task_id'])
        paused = wait_for('native configuration attestation', lambda: json.loads((root / ('attestation-paused-' + queued['task_id'] + '.json')).read_text()) if (root / ('attestation-paused-' + queued['task_id'] + '.json')).exists() else None, timeout=90, process=runtime)
        revoke(control, queued)
        (root / ('attestation-release-' + queued['task_id'])).touch(mode=0o600)
        outcome = observe_until(host, queued['task_id'], 'revoked queued task', lambda v: v['termination_confirmed'], timeout=90)
        binding = db_row(root / 'operator/operator.db', 'SELECT native_intent FROM external_approval_bindings WHERE task_id=?', (queued['task_id'],))
        history = empty_history(policy, root / 'runtime/workspaces' / queued['task_id'], paused['native_thread'])
        trace = no_turn_start_trace(root, queued['task_id'])
        observation = host.journal.get(queued['task_id'])['observation']
        if (outcome['execution_status'] != 'failed' or observation['reason'] != 'approval_unavailable'
                or binding['native_intent'] is not None):
            raise AssertionError('Revoked task admitted a native turn')
        write_json(root / 'receipts/queued-revocation.json', {'pause': paused, 'outcome': outcome, 'binding': binding, 'native_history': history, 'outbound_rpc_trace': trace})
        say('Revocation after fresh attestation blocked native admission')

        large = [{'id': f'r{i:03}', 'amount_cents': i * 137 + 1, 'status': 'paid'} for i in range(100)]
        cancel = make_spec(large, expiry)
        fixture_repository(root, cancel, env)
        host.prepare(cancel)
        approve(control, cancel, review, grant_expiry)
        host.submit(cancel['task_id'])
        active = observe_until(host, cancel['task_id'], 'model activity', lambda v: bool((v.get('runtime_result') or {}).get('model_activity_observed')) or v['termination_confirmed'])
        if active['execution_status'] != 'running' or not active['runtime_result']['model_activity_observed']:
            raise AssertionError('Model task ended before cancellation')
        revoke(control, cancel)
        fenced = host.journal.get(cancel['task_id'])
        if not fenced['cancel_requested'] or not fenced['observation'] or fenced['observation']['termination_confirmed']:
            raise AssertionError('Expected durable unconfirmed cancellation fence')
        flushed = host.flush_pending_cancellations()
        cancelled = observe_until(host, cancel['task_id'], 'cancellation confirmation', lambda v: v['termination_confirmed'])
        native = cancelled.get('runtime_result') or {}
        if cancelled['execution_status'] != 'cancelled' or native.get('termination_scope') != 'task_effects' or native.get('descendants_terminated') is not False or (root / 'runtime/exports' / cancel['task_id'] / 'report.json').exists():
            raise AssertionError('Scoped cancellation or publication fence not confirmed')
        write_json(root / 'receipts/cancellation.json', {'active': active, 'durable_host_cancel': bool(fenced['cancel_requested']), 'last_observation': fenced['observation'], 'flush': flushed, 'outcome': cancelled, 'artifact_exists': False})
        say('Running task revoked; scoped cancellation observed')

        crash = make_spec(records, expiry)
        fixture_repository(root, crash, env)
        host.prepare(crash)
        approve(control, crash, review, grant_expiry)
        write_json(root / 'pause-turn.json', {'task_id': crash['task_id']})
        host.submit(crash['task_id'])
        wait_for('native intent before turn/start', lambda: (root / ('turn-paused-' + crash['task_id'] + '.json')).exists(), timeout=90, process=runtime)
        runtime_row = db_row(root / 'runtime/runtime.db', 'SELECT * FROM tasks WHERE task_id=?', (crash['task_id'],))
        binding = db_row(root / 'operator/operator.db', 'SELECT native_intent FROM external_approval_bindings WHERE task_id=?', (crash['task_id'],))
        if not runtime_row['intent'] or not binding['native_intent']:
            raise AssertionError('Native intents were not committed before pause')
        stop(runtime, forced=True)
        runtime = None
        (root / 'pause-turn.json').unlink()
        runtime = spawn(runtime_args, env, root, 'runtime-restart')
        wait_for('restarted runtime', lambda: host.status(crash['task_id'])['observation_current'], timeout=60, process=runtime)
        reconciled = host.reconcile()
        duplicate = host.submit(crash['task_id'])
        after = host.status(crash['task_id'])
        history = empty_history(policy, root / 'runtime/workspaces' / crash['task_id'], runtime_row['native_thread'])
        trace = no_turn_start_trace(root, crash['task_id'])
        resumed_row = db_row(root / 'runtime/runtime.db', 'SELECT session_id,native_thread,native_session,intent FROM tasks WHERE task_id=?', (crash['task_id'],))
        if (any(resumed_row[k] != runtime_row[k] for k in ('session_id', 'native_thread', 'native_session', 'intent'))
                or (root / 'runtime/exports' / crash['task_id'] / 'report.json').exists()):
            raise AssertionError('Runtime crash replayed or published task')
        write_json(root / 'receipts/native-intent-crash.json', {'task_id': crash['task_id'], 'runtime_session_id': runtime_row['session_id'], 'native_thread': runtime_row['native_thread'], 'native_session': runtime_row['native_session'], 'intent': True, 'binding': binding, 'reconcile': reconciled, 'duplicate': duplicate, 'after': after, 'native_history': history, 'outbound_rpc_trace': trace, 'artifact_exists': False})
        write_json(root / 'receipts/operator-audit.json', control.audit(SCOPE))
        status = 'passed'
        say('Native-intent crash recovered without a turn replay')
    finally:
        errors = []
        for process in (host_process, runtime):
            try:
                stop(process)
            except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
                errors.append(type(exc).__name__)
        if config_path is not None and (not resume or archive.exists()):
            after_hash = old['digest_file'](config_path)
            sources = ['agent/external/' + name + '.py' for name in (
                'approved_dispatch', 'operator_control', 'operator_review', 'supervisor',
                'codex_adapter', 'codex_client', 'codex_policy', 'contract', 'journal', 'transport',
                'synthetic_runtime', 'analysis')]
            sources += ['docs/external-003b/run_native_acceptance.py', 'docs/external-002b/run_native_acceptance.py']
            write_json(root / 'receipts/final.json', {'status': status, 'config_sha_before': before, 'config_sha_after': after_hash,
                       'native_config_unchanged': before == after_hash, 'source_sha256': {p: old['digest_file'](PROJECT / p) for p in sources},
                       'owned_process_cleanup_errors': errors, 'owned_group_cleanup_confirmed': not errors,
                       'all_descendants_terminated_proven': False,
                       'hard_cost_ceiling': False, 'fixture_retained': str(root),
                       'previous_accepted_evidence': {'final': 'attempt-1-final.json', 'denials': 'denials.json', 'success': 'success.json'} if resume else None})
            if before != after_hash or errors:
                raise RuntimeError('Configuration integrity or fixture cleanup failed')
    say('Native acceptance: ' + status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', action='store_true', help='continue retained accepted evidence without replay')
    parser.add_argument('--execute', action='store_true', help='run real bounded Codex acceptance')
    parser.add_argument('--executable', help='absolute enrolled Codex CLI executable')
    parser.add_argument('--root', help='private fixture directory under /private/tmp')
    parser.add_argument('--runtime', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--pause-host', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--enrollment', help=argparse.SUPPRESS)
    parser.add_argument('--spec', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.runtime:
        runtime_main(args.root, args.executable, args.enrollment)
    elif args.pause_host:
        pause_host(args.root, args.spec)
    elif args.execute or args.resume:
        if not args.executable or not Path(args.executable).is_absolute():
            parser.error('--execute requires an absolute --executable')
        if args.resume and (args.execute or not args.root):
            parser.error('--resume requires --root and cannot be combined with --execute')
        execute(args.executable, args.root, resume=args.resume)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
