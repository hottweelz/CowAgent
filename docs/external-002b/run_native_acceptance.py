#!/usr/bin/env python3
"""Opt-in disposable real Codex acceptance. Does not alter native config or auth.

No task is replayed after uncertain submission. Native deadline/cancellation are
cooperative, not hard process, descendant or cost ceilings. Retains fixtures.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
PROBE_SHA256 = '6586f6dc7a28de6ad2ab6b48788d6901952c00c3bc73117051c3d6f7c255f452'


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path = Path(path)
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def say(message):
    print(message, flush=True)


def wait_for(label, check, timeout=180, process=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(label + ': owned process exited')
        value = check()
        if value:
            return value
        time.sleep(.2)
    raise TimeoutError(label + ': timed out without confirmation')


def credential(root):
    from agent.external.contract import Credential
    data = json.loads((Path(root) / 'ipc-key.json').read_text())
    return Credential('acceptance-supervisor', 'acceptance-runtime', 'acceptance-key',
                      bytes.fromhex(data['secret']), data['expires_at'], ('analyze_records',))


def make_supervisor(root):
    from agent.external.analysis import AnalysisVerifier
    from agent.external.journal import ExternalJournal
    from agent.external.supervisor import ExternalSupervisor
    from agent.external.transport import ExternalTransport
    from agent.recovery.store import TaskStore
    root = Path(root)
    journal = ExternalJournal(TaskStore(root / 'host' / 'tasks.db'))
    transport = ExternalTransport(root / 'ipc' / 'runtime.sock', credential(root), timeout=30)
    return ExternalSupervisor(journal, transport, owner_id='acceptance-owner', source_id='fixture',
                              conversation_id='fixture', verifier=AnalysisVerifier(root / 'runtime' / 'exports'))


def make_spec(records, expiry):
    from agent.external import contract
    task_id = str(uuid.uuid4())
    content = json.dumps({'schema_version': 1, 'currency': 'USD', 'records': records}, separators=(',', ':'))
    return contract.normalize_spec({
        'task_id': task_id, 'idempotency_key': 'fixture-' + task_id,
        'owner_id': 'acceptance-owner', 'source_id': 'fixture', 'conversation_id': 'fixture',
        'runtime_id': 'acceptance-runtime',
        'task': {'operation': 'analyze_records', 'artifact': 'report.json', 'content': content},
        'authority': {'operations': ['analyze_records'], 'resource': task_id, 'expires_at': expiry},
        'verification': {},
    })


def fixture_repository(root, spec, env):
    workspace = Path(root) / 'runtime' / 'workspaces' / spec['task_id']
    workspace.mkdir(mode=0o700, parents=True, exist_ok=True)
    git_env = dict(env, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null')
    subprocess.run(['git', '-c', 'init.templateDir=', 'init', '-q', str(workspace)],
                   env=git_env, check=True, timeout=10)


def runtime_main(root, executable, enrollment_path):
    from agent.external.codex_adapter import CodexRuntime
    from agent.external.codex_policy import CodexAnalysisPolicy
    root = Path(root)
    enrollment = json.loads(Path(enrollment_path).read_text())
    policy = CodexAnalysisPolicy(executable, enrollment=enrollment)
    runtime = CodexRuntime(root / 'runtime', root / 'ipc' / 'runtime.sock', credential(root), policy)
    def stop(_signum, _frame):
        server = getattr(runtime, 'server', None)
        if server:
            threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    try:
        runtime.serve()
    finally:
        runtime.close()


def pause_host(root, spec_path):
    supervisor = make_supervisor(root)
    spec = json.loads(Path(spec_path).read_text())
    original = supervisor.transport.submit
    def pause_after_acceptance(specification, approval):
        response = original(specification, approval)
        write_json(Path(root) / 'host-accepted.json', {'task_id': specification['task_id'],
                   'session_id': response['session_id'], 'native_dispatch_acknowledged_to_host': False})
        while True:
            time.sleep(1)
    supervisor.transport.submit = pause_after_acceptance
    supervisor.delegate(spec)


def spawn(args, env):
    return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *args], cwd=PROJECT,
                            env=env, start_new_session=True, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def owned_groups(leader):
    """Snapshot only descendants of an owned fixture process before forced cleanup."""
    output = subprocess.run(['ps', '-axo', 'pid=,ppid=,pgid='], capture_output=True,
                            text=True, timeout=5, check=True).stdout
    rows = [tuple(map(int, line.split())) for line in output.splitlines() if len(line.split()) == 3]
    descendants = {leader}
    while True:
        added = {pid for pid, parent, _ in rows if parent in descendants} - descendants
        if not added:
            break
        descendants.update(added)
    # Only signal a group whose leader is itself a fixture descendant.
    return {pgid for pid, _, pgid in rows if pid in descendants and pid == pgid and pgid != os.getpgrp()}


def stop_owned(process, *, cooperative=True):
    if process is None or process.poll() is not None:
        return
    groups = owned_groups(process.pid)
    process.send_signal(signal.SIGTERM if cooperative else signal.SIGKILL)
    try:
        process.wait(timeout=15 if cooperative else 5)
    except subprocess.TimeoutExpired:
        for group in groups:
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=5)


def observe_until(supervisor, task_id, label, predicate, *, timeout=180):
    def check():
        outcome = supervisor.status(task_id)
        return outcome if predicate(outcome) else None
    return wait_for(label, check, timeout=timeout)


def native_turns(policy, workspace, thread_id):
    """Read native public history; no resume, turn, or arbitrary RPC."""
    from agent.external.codex_client import CodexClient
    argv, env, _ = policy.launch(workspace)
    client = CodexClient(argv, str(workspace), env)
    try:
        policy.initialize(client)
        turns, cursor = [], None
        while True:
            response = client.request('thread/turns/list', {'threadId': thread_id, 'limit': 100, 'cursor': cursor}, timeout=20)
            turns.extend({'id': t['id'], 'status': t['status']} for t in response['data'])
            cursor = response.get('nextCursor')
            if not cursor:
                return turns
            if len(turns) >= 100:
                raise RuntimeError('History exceeds fixture bound')
    finally:
        client.close()


def assert_preflight(executable, workspace):
    from agent.external.codex_policy import CodexAnalysisPolicy, ANALYSIS_POLICY_REVISION, VERSION
    path = PROJECT / 'docs/external-002b/authority-probes.json'
    if digest_file(path) != PROBE_SHA256:
        raise RuntimeError('Retained authority probe checksum mismatch')
    proof = json.loads(path.read_text())
    preflight = proof['preflight']
    policy = CodexAnalysisPolicy(executable)
    config_path = policy.codex_home / 'config.toml'
    before = digest_file(config_path)
    if (proof['cli_version'] != VERSION or VERSION != '0.165.0'
            or proof['policy_revision'] != ANALYSIS_POLICY_REVISION
            or before != preflight['config_sha_before'] or before != preflight['config_sha_after']
            or not all(proof['assertions'][key] is True for key in ('native_child_mapping', 'inside_and_outside_write_approval_declined', 'markers_absent', 'root_model_provider_effort_unchanged', 'global_config_unchanged'))):
        raise RuntimeError('Retained authority preflight does not match current configuration')
    # launch checks installed binary/version without starting a model turn.
    _, _, expected = policy.launch(workspace)
    native = preflight['thread']
    if (expected['model'] != native['model'] or expected['modelProvider'] != native['modelProvider']
            or expected['reasoningEffort'] != native['reasoningEffort']):
        raise RuntimeError('Selected model/provider/effort differs from retained preflight')
    enrollment = {'cli_version': VERSION, 'model': native['model'], 'modelProvider': native['modelProvider'],
                  'policy_revision': ANALYSIS_POLICY_REVISION, 'probe_sha256': PROBE_SHA256,
                  'provider_config_sha256': policy._provider_digest(), 'config_sha256': before}
    return enrollment, config_path, before


def execute(executable):
    from agent.external import contract
    from agent.external.codex_policy import CodexAnalysisPolicy
    from agent.external.transport import RemoteRejected
    root = Path(tempfile.mkdtemp(prefix='cowagent-external-002b-', dir='/private/tmp')).resolve()
    root.chmod(0o700)
    for name in ('ipc', 'host', 'cow-data', 'preflight', 'receipts'):
        (root / name).mkdir(mode=0o700)
    os.environ['COW_DATA_DIR'] = str(root / 'cow-data')
    env = None
    say('Owned fixture root: ' + str(root))
    runtime = host = missing_runtime = None
    config_path, before = None, None
    status = 'incomplete'
    try:
        enrollment, config_path, before = assert_preflight(executable, root / 'preflight')
        # Pass only the native runtime's enrolled environment, never unrelated
        # credentials inherited by the acceptance harness.
        _, native_env, _ = CodexAnalysisPolicy(executable).launch(root / 'preflight')
        env = dict(native_env, COW_DATA_DIR=str(root / 'cow-data'))
        expiry = time.time() + 1800
        write_json(root / 'ipc-key.json', {'secret': secrets.token_hex(32), 'expires_at': expiry})
        write_json(root / 'enrollment.json', enrollment)
        write_json(root / 'receipts' / 'preflight.json', {'probe_sha256': PROBE_SHA256,
                   'config_sha_before': before, 'enrollment': enrollment,
                   'evidence_type': 'retained_authority_plus_current_preflight'})
        say('Preflight matched retained authority evidence')
        runtime_args = ['--runtime', '--root', str(root), '--executable', executable,
                        '--enrollment', str(root / 'enrollment.json')]
        runtime = spawn(runtime_args, env)
        supervisor = make_supervisor(root)
        wait_for('private runtime socket', lambda: (root / 'ipc' / 'runtime.sock').exists(), timeout=15, process=runtime)
        discovery = wait_for('discovery', lambda: supervisor.discover(), timeout=90, process=runtime)
        cap = discovery['native_capabilities']
        if (discovery['model'] != enrollment['model'] or cap['modelProvider'] != enrollment['modelProvider']
                or cap['authority_enrollment'] != 'matched_tested_configuration' or not cap['profile_available']):
            raise RuntimeError('Effective discovery did not match the enrolled runtime')
        write_json(root / 'receipts' / 'discovery.json', {'case': 'real_runtime_discovery', 'discovery': discovery})
        say('Authenticated native discovery completed')

        # An unsupported effect receives no runtime authority, even with a claimed approval.
        bad_id = str(uuid.uuid4())
        bad = {'task_id': bad_id, 'idempotency_key': 'bad-' + bad_id, 'owner_id': 'acceptance-owner',
               'source_id': 'fixture', 'conversation_id': 'fixture', 'runtime_id': 'acceptance-runtime',
               'task': {'operation': 'record_effect', 'artifact': 'effect.json', 'content': 'fictional'},
               'authority': {'operations': ['record_effect'], 'resource': bad_id, 'expires_at': expiry}, 'verification': {}}
        try:
            supervisor.transport.submit(bad, {'task_hash': contract.digest(bad), 'approved_by': 'fixture', 'expires_at': expiry - 1})
        except RemoteRejected:
            write_json(root / 'receipts' / 'unsupported-effect.json', {'case': 'unauthorized_record_effect', 'rejected': True})
        else:
            raise AssertionError('Unsupported effect unexpectedly accepted')

        records = [
            {'id': 'sale1', 'amount_cents': 12500, 'status': 'paid'},
            {'id': 'refund1', 'amount_cents': -2500, 'status': 'refund'},
            {'id': 'pending1', 'amount_cents': 8000, 'status': 'pending'},
            {'id': 'sale2', 'amount_cents': 3000, 'status': 'paid'},
            {'id': 'invalid1', 'amount_cents': -100, 'status': 'paid'},
            {'id': 'void1', 'amount_cents': 4400, 'status': 'void'},
            {'id': 'sale1', 'amount_cents': 12500, 'status': 'paid'},
        ]
        spec = make_spec(records, expiry)
        fixture_repository(root, spec, env)
        write_json(root / 'success-spec.json', spec)
        host = spawn(['--pause-host', '--root', str(root), '--spec', str(root / 'success-spec.json')], env)
        marker = wait_for('runtime acceptance before supervisor observation',
                          lambda: json.loads((root / 'host-accepted.json').read_text())
                          if (root / 'host-accepted.json').exists() else None,
                          timeout=60, process=host)
        os.kill(host.pid, signal.SIGKILL)
        host.wait(timeout=5)
        host = None
        # Reopen the same durable journal in a new supervisor; reconcile never resubmits.
        supervisor = make_supervisor(root)
        initial = supervisor.reconcile()
        duplicate = supervisor.submit(spec['task_id'])
        if duplicate['session_id'] not in (None, marker['session_id']):
            raise AssertionError('Duplicate changed runtime session')
        write_json(root / 'receipts' / 'host-restart.json', {'case': 'real_submit_host_crash',
                   'task_id': spec['task_id'], 'runtime_session_id': marker['session_id'],
                   'host_killed_after_runtime_accepted_before_observation': True,
                   'reconciliation': initial, 'duplicate_result': duplicate})
        say('Killed owned supervisor after acceptance; reconciled existing task ID')
        done = observe_until(supervisor, spec['task_id'], 'analysis completion',
                             lambda o: o['execution_status'] in ('completed', 'failed', 'cancelled'), timeout=180)
        if done['execution_status'] != 'completed' or done['session_id'] != marker['session_id']:
            raise AssertionError('Native analysis did not complete under the original session')
        verified = supervisor.verify(spec['task_id'])
        if not verified['verified']:
            raise AssertionError('Independent artifact verification failed')
        artifact = root / 'runtime' / 'exports' / spec['task_id'] / 'report.json'
        report = json.loads(artifact.read_text())
        write_json(root / 'receipts' / 'verified-report.json', report)
        expected_totals = {'paid_cents': 15500, 'refund_cents': -2500, 'pending_cents': 8000, 'net_cents': 13000}
        if report.get('totals') != expected_totals or report.get('accepted_count') != 4 or len(report.get('exceptions', [])) != 3:
            raise AssertionError('Independent expected totals or exceptions differ')
        policy = CodexAnalysisPolicy(executable, enrollment=enrollment)
        result = done['runtime_result']
        turns = native_turns(policy, root / 'runtime' / 'workspaces' / spec['task_id'], result['native_thread_id'])
        if len(turns) != 1 or turns[0]['id'] != result['native_turn_id']:
            raise AssertionError('Native history does not show exactly one original turn')
        write_json(root / 'receipts' / 'successful-analysis.json', {'case': 'real_codex_analysis',
                   'task_id': spec['task_id'], 'execution': done, 'verification': verified,
                   'expected_totals': expected_totals, 'expected_accepted_count': 4,
                   'expected_exception_count': 3, 'native_history_turns': turns})
        say('Real analysis completed; independent artifact and single native turn verified')

        # Only fixture output is changed; verification must detect it without replay.
        report['totals']['net_cents'] += 1
        write_json(artifact, report)
        tampered = supervisor.verify(spec['task_id'])
        if tampered['acceptance_status'] != 'failed' or tampered['verified']:
            raise AssertionError('Verifier accepted modified artifact')
        after_tamper = supervisor.submit(spec['task_id'])
        turns_after = native_turns(policy, root / 'runtime' / 'workspaces' / spec['task_id'], result['native_thread_id'])
        if turns_after != turns:
            raise AssertionError('Verification failure changed native turn history')
        write_json(root / 'receipts' / 'wrong-output.json', {'case': 'owned_artifact_tamper',
                   'verification': tampered, 'repeat_submit': after_tamper, 'native_history_turns': turns_after})
        say('Tampered fixture artifact rejected; no native rerun')

        large = [{'id': f'r{i:03}', 'amount_cents': i * 137 + 1, 'status': 'paid'} for i in range(100)]
        cancel_spec = make_spec(large, expiry)
        fixture_repository(root, cancel_spec, env)
        supervisor.delegate(cancel_spec)
        active = observe_until(supervisor, cancel_spec['task_id'], 'model activity before cancellation',
                               lambda o: bool((o.get('runtime_result') or {}).get('model_activity_observed'))
                               or o['execution_status'] in ('completed', 'failed', 'cancelled'))
        if active['execution_status'] != 'running' or not active['runtime_result']['model_activity_observed']:
            raise AssertionError('Task ended before model activity could be cancelled')
        requested = supervisor.cancel(cancel_spec['task_id'])
        write_json(root / 'receipts' / 'cancel-request.json', {'case': 'real_cancel_after_model_activity',
                   'activity': active, 'request': requested})
        if not requested['cancel_requested'] or requested['termination_confirmed']:
            raise AssertionError('Cancellation acknowledgement did not show requested but unconfirmed')
        cancelled = observe_until(supervisor, cancel_spec['task_id'], 'native cancellation acknowledgement',
                                  lambda o: o['termination_confirmed'] or o['execution_status'] == 'failed')
        cancel_result = cancelled.get('runtime_result') or {}
        if (cancelled['execution_status'] != 'cancelled' or cancel_result.get('native_status') != 'interrupted'
                or cancel_result.get('termination_scope') != 'task_effects' or cancel_result.get('descendants_terminated') is not False
                or (root / 'runtime' / 'exports' / cancel_spec['task_id'] / 'report.json').exists()):
            raise AssertionError('Cancellation did not establish the required scoped outcome')
        write_json(root / 'receipts' / 'cancel-result.json', {'case': 'real_native_interrupt', 'outcome': cancelled,
                   'artifact_exists': False, 'descendant_exit_proven': False})
        say('Native cancellation observed with publication fenced')

        interrupted_spec = make_spec(large, expiry)
        fixture_repository(root, interrupted_spec, env)
        supervisor.delegate(interrupted_spec)
        active = observe_until(supervisor, interrupted_spec['task_id'], 'model activity before runtime shutdown',
                               lambda o: bool((o.get('runtime_result') or {}).get('model_activity_observed'))
                               or o['execution_status'] in ('completed', 'failed', 'cancelled'))
        if active['execution_status'] != 'running' or not active['runtime_result']['model_activity_observed']:
            raise AssertionError('Task ended before runtime interruption could be tested')
        original_native = active['runtime_result']
        say('Stopping owned runtime cooperatively after model activity')
        stop_owned(runtime)
        runtime = None
        runtime = spawn(runtime_args, env)
        wait_for('restarted runtime socket', lambda: supervisor.status(interrupted_spec['task_id'])['observation_current'], timeout=30, process=runtime)
        resumed = observe_until(supervisor, interrupted_spec['task_id'], 'read-only restart reconciliation',
                                lambda o: (o.get('runtime_result') or {}).get('reconciliation') == 'read_only_history'
                                or o['execution_status'] in ('cancelled', 'failed', 'completed'), timeout=60)
        observed_native = resumed['runtime_result']
        if (observed_native['native_thread_id'] != original_native['native_thread_id']
                or observed_native['native_turn_id'] != original_native['native_turn_id']):
            raise AssertionError('Restart changed native identity')
        resumed_turns = native_turns(policy, root / 'runtime' / 'workspaces' / interrupted_spec['task_id'], original_native['native_thread_id'])
        if len(resumed_turns) != 1 or resumed_turns[0]['id'] != original_native['native_turn_id']:
            raise AssertionError('Restart caused a new native turn')
        no_artifact = not (root / 'runtime' / 'exports' / interrupted_spec['task_id'] / 'report.json').exists()
        if not no_artifact:
            raise AssertionError('Runtime interruption published an artifact')
        write_json(root / 'receipts' / 'runtime-restart.json', {'case': 'cooperative_runtime_sigterm_and_restart',
                   'before': active, 'after': resumed, 'native_history_turns': resumed_turns,
                   'artifact_exists': False, 'restart_replayed': False})
        say('Runtime restart reconciled existing native identity without replay')

        # Separate owned fixture; deliberately absent executable, never modify installed Codex.
        missing = root / 'missing-case'
        for path in (missing, missing / 'ipc', missing / 'host', missing / 'cow-data'):
            path.mkdir(mode=0o700)
        write_json(missing / 'ipc-key.json', json.loads((root / 'ipc-key.json').read_text()))
        write_json(missing / 'enrollment.json', enrollment)
        missing_path = str(missing / 'not-installed-codex')
        missing_runtime = spawn(['--runtime', '--root', str(missing), '--executable', missing_path,
                                 '--enrollment', str(missing / 'enrollment.json')], env)
        missing_host = make_supervisor(missing)
        wait_for('missing executable runtime', lambda: (missing / 'ipc' / 'runtime.sock').exists(), timeout=15, process=missing_runtime)
        try:
            missing_host.discover()
        except RemoteRejected:
            pass
        else:
            raise AssertionError('Missing executable discovery unexpectedly succeeded')
        missing_spec = make_spec(records, expiry)
        missing_host.delegate(missing_spec)
        failed = observe_until(missing_host, missing_spec['task_id'], 'missing executable startup failure',
                               lambda o: o['execution_status'] == 'failed', timeout=30)
        write_json(root / 'receipts' / 'missing-executable.json', {'case': 'owned_missing_executable_fixture',
                   'discovery_unavailable': True, 'outcome': failed})
        say('Missing executable failure verified without changing the installation')
        status = 'passed'
    finally:
        cleanup_errors = []
        for process in (host, missing_runtime, runtime):
            try:
                stop_owned(process)
            except (OSError, subprocess.SubprocessError):
                cleanup_errors.append('owned_process_cleanup_unconfirmed')
        if config_path is not None:
            after = digest_file(config_path)
            write_json(root / 'receipts' / 'final.json', {'status': status, 'native_config_sha_before': before,
                       'native_config_sha_after': after, 'native_config_unchanged': before == after,
                       'fixture_retained': str(root), 'cleanup_errors': cleanup_errors, 'hard_cost_ceiling': False,
                       'all_descendants_terminated_proven': False})
            say('Native config unchanged: ' + str(before == after))
            if before != after:
                raise RuntimeError('Native configuration changed during fixture run')
        if cleanup_errors:
            raise RuntimeError('Owned process cleanup could not be confirmed')
    say('Native acceptance status: ' + status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='run real bounded Codex acceptance')
    parser.add_argument('--executable', help='absolute enrolled Codex CLI path')
    parser.add_argument('--runtime', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--pause-host', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--root', help=argparse.SUPPRESS)
    parser.add_argument('--enrollment', help=argparse.SUPPRESS)
    parser.add_argument('--spec', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.runtime:
        runtime_main(args.root, args.executable, args.enrollment)
    elif args.pause_host:
        pause_host(args.root, args.spec)
    elif args.execute:
        if not args.executable or not Path(args.executable).is_absolute():
            parser.error('--execute requires an absolute --executable')
        execute(args.executable)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
