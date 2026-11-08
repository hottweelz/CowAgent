"""Two bounded authenticated native runs; never starts or restarts the webserver.

Expected totals stay in the verifier. Each enrolled runtime gets only its own
fictional dataset. Caller private-open guard is instrumentation, not OS isolation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))


def write(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--private-workspace', required=True)
    parser.add_argument('--probe-receipt', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Live model execution requires --execute')
    config = Path(args.config).resolve()
    private_workspace = Path(args.private_workspace).resolve()
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix='cowagent-routing003-', dir='/private/tmp'))
    os.environ['COW_DATA_DIR'] = str(root / 'caller-data')
    (root / 'caller-data').mkdir()
    blocked = []
    denied = (config.parent, private_workspace, (Path.home() / '.cow').resolve())

    def audit(event, values):
        if event == 'open' and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).resolve()
            if any(path == parent or parent in path.parents for parent in denied):
                blocked.append('private_open_denied')
                raise PermissionError('Caller cannot open native private state')

    sys.addaudithook(audit)
    from agent.external import contract
    from agent.external.analysis import AnalysisVerifier
    from agent.external.approved_dispatch import ApprovalJournal
    from agent.external.operator_control import OperatorControl, VERSION
    from agent.external.operator_review import build_enrollment_review, build_task_review
    from agent.external.supervisor import ExternalSupervisor
    from agent.external.transport import ExternalTransport, RemoteRejected, TransportUnavailable

    tasks = json.loads((HERE / 'tasks.json').read_text())['tasks']
    assert {t['agent_id'] for t in tasks} == {'testpilot', 'testpilot2'} and len(tasks) == 2
    probe_hash = hashlib.sha256(Path(args.probe_receipt).read_bytes()).hexdigest()
    command = [sys.executable, '-m', 'agent.external.cowagent_cli', '--config', str(config)]
    states, processes, logs = [], [], []
    receipt = {'schema': 'cow.agent-routing-003.acceptance/1', 'fixture': str(root),
               'started_at': time.time(), 'workers': [], 'finished': False}
    print(json.dumps({'phase': 'preflight', 'fixture': str(root)}), flush=True)

    def inspect(target, output):
        with output.with_suffix('.log').open('x') as log:
            result = subprocess.run(command + ['inspect', '--agent-id', target, '--output', str(output)],
                                    cwd=REPO, stdout=log, stderr=log, timeout=45)
        if result.returncode:
            raise RuntimeError('Native preflight failed; raw log remains private')
        return json.loads(output.read_text())

    def decision(state, action, payload, revision):
        return state['operator'].apply({'protocol': VERSION, 'request_id': str(uuid.uuid4()),
            'action': action, 'scope': state['scope'], 'expected_revision': revision, 'payload': payload})

    try:
        # Inspect and launch in a fixed order. Native model execution is paired
        # only after both authenticated endpoints are ready and checked.
        for fixture in tasks:
            target = fixture['agent_id']
            folder = root / target
            folder.mkdir()
            before = inspect(target, folder / 'before.json')
            snapshot = before['snapshot']
            assert snapshot['agent_id'] == target
            enrollment = dict(snapshot, probe_sha256=probe_hash)
            review = build_enrollment_review(enrollment, current=snapshot, observed_probe_sha256=probe_hash)
            expiry = time.time() + 300
            credential = contract.Credential('codex', 'cowagent.' + target, 'routing003.' + target,
                                             secrets.token_bytes(32), expiry, ('analyze_records',))
            operator = OperatorControl(folder / 'operator', initialize=True)
            journal = ApprovalJournal(operator)
            scope = {'supervisor_id': 'codex', 'owner_id': 'maintainer', 'source_id': 'codex',
                     'conversation_id': 'agent-routing-003', 'runtime_id': credential.runtime_id}
            state = {'target': target, 'folder': folder, 'fixture': fixture, 'before': before,
                     'enrollment': enrollment, 'credential': credential, 'operator': operator,
                     'journal': journal, 'scope': scope}
            decision(state, 'enroll', {'review': review, 'expires_at': expiry}, 0)
            tid = str(uuid.uuid4())
            spec = contract.normalize_spec({'task_id': tid, 'idempotency_key': fixture['label'],
                **{k: scope[k] for k in ('owner_id', 'source_id', 'conversation_id', 'runtime_id')},
                'task': {'operation': 'analyze_records', 'artifact': 'report.json',
                         'content': json.dumps(fixture['payload'])},
                'authority': {'operations': ['analyze_records'], 'resource': tid, 'expires_at': expiry},
                'verification': {'acceptance': [], 'external_state': []}})
            transport = ExternalTransport(folder / 'ipc' / 'runtime.sock', credential)
            supervisor = ExternalSupervisor(journal, transport, owner_id='maintainer', source_id='codex',
                conversation_id=scope['conversation_id'], verifier=AnalysisVerifier(folder / 'runtime' / 'exports'))
            state.update(spec=spec, transport=transport, supervisor=supervisor)
            supervisor.prepare(spec)
            try:
                supervisor.submit(tid)
            except contract.ProtocolError:
                state['unapproved_denied'] = True
            else:
                raise AssertionError('Unapproved task admitted')
            task_review = build_task_review(spec, review)
            decision(state, 'approve_task', {'spec': spec, 'enrollment_revision': 1,
                'task_review_id': task_review['review_id'], 'reviewed_at': task_review['reviewed_at'],
                'expires_at': expiry}, 0)
            (folder / 'ipc').mkdir()
            launch = {'credential': {'supervisor_id': credential.supervisor_id, 'runtime_id': credential.runtime_id,
                'key_id': credential.key_id, 'secret_hex': credential.secret.hex(), 'expires_at': expiry,
                'operations': list(credential.operations)}, 'enrollment': enrollment,
                'operator_dir': str(folder / 'operator'), 'runtime_dir': str(folder / 'runtime'),
                'socket': str(transport.socket_path)}
            write(folder / 'launch.json', launch)
            write(folder / 'task.json', spec)
            log = (folder / 'native.log').open('x')
            logs.append(log)
            process = subprocess.Popen(command + ['serve', '--launch', str(folder / 'launch.json')],
                                       cwd=REPO, stdout=log, stderr=log)
            processes.append(process)
            state['process'] = process
            states.append(state)
            deadline = time.monotonic() + 30
            while not transport.socket_path.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Native endpoint did not start')
                time.sleep(.1)
            state['discovery'] = supervisor.discover()
            assert state['discovery']['native_capabilities']['agent_id'] == target

        # Wrong credentials are closed without response by the native Handler.
        # Separately test signed target-override and task-routing rejections.
        for index, state in enumerate(states):
            wrong = ExternalTransport(states[1 - index]['transport'].socket_path, state['credential'])
            try:
                wrong.discover()
            except TransportUnavailable:
                state['wrong_credential_no_authenticated_response'] = True
            else:
                raise AssertionError('Cross-target credential was accepted')
            assert states[1 - index]['supervisor'].discover()['native_capabilities']['agent_id'] == states[1 - index]['target']
            try:
                state['transport'].exchange('discover', {'agent_id': states[1 - index]['target']})
            except RemoteRejected as error:
                assert str(error) == 'invalid_request'
                state['authenticated_target_override_denied'] = True
            else:
                raise AssertionError('Request target override was accepted')
            mismatched = dict(state['spec'], runtime_id=states[1 - index]['credential'].runtime_id)
            try:
                state['transport'].submit(mismatched, {})
            except RemoteRejected as error:
                assert str(error) == 'unauthorized'
                state['cross_target_spec_denied'] = True
            else:
                raise AssertionError('Cross-target task was accepted')

        print(json.dumps({'phase': 'submitting_pair', 'targets': [s['target'] for s in states]}), flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            submitted = list(pool.map(lambda s: s['supervisor'].submit(s['spec']['task_id']), states))
        for state, status in zip(states, submitted):
            state['status'] = status
        deadline = time.monotonic() + 220
        while time.monotonic() < deadline:
            for state in states:
                if state['status']['execution_status'] not in contract.TERMINAL:
                    state['status'] = state['supervisor'].status(state['spec']['task_id'])
            if all(s['status']['execution_status'] in contract.TERMINAL for s in states):
                break
            if any(s['journal'].get(s['spec']['task_id'])['observation']['reason'] == 'dispatch_uncertain'
                   for s in states):
                break  # Never replay an uncertain native attempt.
            time.sleep(.5)

        for state in states:
            tid = state['spec']['task_id']
            status = state['status']
            item = {'agent_id': state['target'], 'task_id': tid, 'label': state['fixture']['label'],
                    'enrollment': state['enrollment'], 'discovery': state['discovery'],
                    'preflight': state['before'], 'unapproved_denied': state['unapproved_denied'],
                    'wrong_credential_no_authenticated_response': state['wrong_credential_no_authenticated_response'],
                    'authenticated_target_override_denied': state['authenticated_target_override_denied'],
                    'cross_target_spec_denied': state['cross_target_spec_denied'], 'status': status}
            receipt['workers'].append(item)
            if status['execution_status'] != 'completed':
                continue
            status = state['supervisor'].verify(tid)
            item['status'] = status
            artifact = state['folder'] / 'runtime' / 'exports' / tid / 'report.json'
            report = json.loads(artifact.read_text())
            expected = state['fixture']['expected']
            # Frozen independent expectations do not call analysis.expected_report.
            assert {k: report[k] for k in expected} == expected
            assert report['task_id'] == tid and report['record_count'] == 5
            assert report['dataset_sha256'] == contract.digest(state['fixture']['payload'])
            item['report'] = report
            item['artifact_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            item['independent_result_match'] = True
            binding = status['runtime_result']
            assert all(binding[k] == state['enrollment'][k]
                       for k in ('agent_id', 'model', 'provider', 'profile_sha256'))
            assert binding['memory_scope_sha256'] == state['before']['context_metadata']['memory_scope_sha256']
            assert binding['native_pid'] == state['process'].pid
            assert binding['session_id'] == status['session_id']
            assert binding['sha256'] == item['artifact_sha256']
            item['independent_binding_match'] = True
            duplicate = state['supervisor'].submit(tid)
            assert duplicate['session_id'] == status['session_id']
            item['duplicate_retained_session'] = True
            with state['operator']._connect() as db:
                item['intent_counts'] = {name: db.execute(
                    'SELECT count(*) FROM external_events WHERE task_id=? AND kind=?', (tid, name)).fetchone()[0]
                    for name in ('submit_intent', 'native_intent', 'publication_intent')}
            assert set(item['intent_counts'].values()) == {1}
            assert status['verified']
        assert all(i['status']['verified'] for i in receipt['workers'])
        runs = [i['status']['runtime_result'] for i in receipt['workers']]
        for field in ('agent_id', 'session_id', 'native_run_id', 'memory_scope_sha256', 'native_pid'):
            assert len({r[field] for r in runs}) == 2, field
        receipt['native_run_overlap_seconds'] = max(0, min(r['native_finished_at'] for r in runs)
                                                    - max(r['native_started_at'] for r in runs))
        receipt['parallel_observed'] = receipt['native_run_overlap_seconds'] > 0
        receipt['model_results_verified'] = True
    finally:
        # Owned processes only. The existing webserver is never signalled.
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()
        receipt['owned_processes_exited'] = all(p.poll() is not None for p in processes)
        receipt['caller_private_open_attempts'] = len(blocked)
        receipt['ended_at'] = time.time()
        # Final preservation inspection runs after model work has stopped.
        try:
            for state in states:
                after = inspect(state['target'], state['folder'] / 'after.json')
                matching = [i for i in receipt['workers'] if i['agent_id'] == state['target']]
                if matching:
                    matching[0]['postflight'] = after
                    matching[0]['native_snapshot_unchanged'] = after == state['before']
            receipt['finished'] = bool(receipt.get('model_results_verified') and len(receipt['workers']) == 2
                and all(i.get('native_snapshot_unchanged') for i in receipt['workers'])
                and receipt['owned_processes_exited'] and not blocked)
        finally:
            write(root / 'receipt.json', receipt)
        print(json.dumps({'phase': 'finished', 'receipt': str(root / 'receipt.json'),
                          'finished': receipt['finished'], 'parallel_observed': receipt.get('parallel_observed')}), flush=True)
        if not receipt['finished']:
            raise RuntimeError('Acceptance incomplete; retained receipt is authoritative, do not replay automatically')


if __name__ == '__main__':
    main()
