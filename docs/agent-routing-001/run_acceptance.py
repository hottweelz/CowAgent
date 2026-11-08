"""Opt-in one-task native experiment. Caller never opens the private workspace."""
import argparse
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

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def write(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, sort_keys=True, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--private-workspace', required=True)
    parser.add_argument('--probe-receipt', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('The live experiment requires --execute')
    config = Path(args.config).absolute()
    private_workspace = Path(args.private_workspace).absolute()
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix='cowagent-routing-', dir='/private/tmp'))
    os.environ['COW_DATA_DIR'] = str(root / 'caller-data')
    (root / 'caller-data').mkdir()
    blocked = []
    denied = (config.parent, private_workspace, Path.home() / '.cow')

    def audit(event, values):
        if event != 'open' or not values or not isinstance(values[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(values[0])).resolve()
        if any(path == p or p in path.parents for p in denied):
            blocked.append('private_open_denied')
            raise PermissionError('Caller cannot open native private state')
    sys.addaudithook(audit)

    from agent.external import contract
    from agent.external.analysis import AnalysisVerifier
    from agent.external.approved_dispatch import ApprovalJournal
    from agent.external.operator_control import OperatorControl, VERSION
    from agent.external.operator_review import build_enrollment_review, build_task_review
    from agent.external.supervisor import ExternalSupervisor
    from agent.external.transport import ExternalTransport

    command = [sys.executable, '-m', 'agent.external.cowagent_cli', '--config', str(config)]
    with (root / 'inspect.log').open('w') as log:
        inspected = subprocess.run(command + ['inspect', '--output', str(root / 'snapshot.json')],
                                   cwd=REPO, stdout=log, stderr=log, timeout=30)
    if inspected.returncode:
        raise RuntimeError('Native preflight failed; inspect its private log locally')
    snapshot = json.loads((root / 'snapshot.json').read_text())['snapshot']
    enrollment = dict(snapshot, probe_sha256=hashlib.sha256(Path(args.probe_receipt).read_bytes()).hexdigest())
    review = build_enrollment_review(enrollment, current=snapshot, observed_probe_sha256=enrollment['probe_sha256'])
    expiry = time.time() + 300
    credential = contract.Credential('codex', 'cowagent.testpilot', 'routing-001', secrets.token_bytes(32),
                                     expiry, ('analyze_records',))
    operator = OperatorControl(root / 'operator', initialize=True)
    journal = ApprovalJournal(operator)
    scope = {'supervisor_id': 'codex', 'owner_id': 'maintainer', 'source_id': 'codex',
             'conversation_id': 'agent-routing-001', 'runtime_id': credential.runtime_id}
    def decision(action, payload, revision):
        return operator.apply({'protocol': VERSION, 'request_id': str(uuid.uuid4()), 'action': action,
                               'scope': scope, 'expected_revision': revision, 'payload': payload})
    decision('enroll', {'review': review, 'expires_at': expiry}, 0)
    tid = str(uuid.uuid4())
    payload = {'schema_version': 1, 'currency': 'USD', 'records': [
        {'id': 'fictional-a', 'amount_cents': 12500, 'status': 'paid'},
        {'id': 'fictional-b', 'amount_cents': 7500, 'status': 'paid'},
        {'id': 'fictional-c', 'amount_cents': -2000, 'status': 'refund'},
        {'id': 'fictional-d', 'amount_cents': 3000, 'status': 'pending'},
        {'id': 'fictional-a', 'amount_cents': 900, 'status': 'paid'},
        {'id': 'fictional-e', 'amount_cents': 100, 'status': 'void'},
        {'id': 'fictional-f', 'amount_cents': 400, 'status': 'refund'},
    ]}
    spec = contract.normalize_spec({
        'task_id': tid, 'idempotency_key': 'one-native-analysis',
        **{k: scope[k] for k in ('owner_id', 'source_id', 'conversation_id', 'runtime_id')},
        'task': {'operation': 'analyze_records', 'artifact': 'report.json', 'content': json.dumps(payload)},
        'authority': {'operations': ['analyze_records'], 'resource': tid, 'expires_at': expiry},
        'verification': {'acceptance': [], 'external_state': []},
    })
    transport = ExternalTransport(root / 'ipc' / 'runtime.sock', credential)
    supervisor = ExternalSupervisor(journal, transport, owner_id=scope['owner_id'], source_id='codex',
                                    conversation_id=scope['conversation_id'],
                                    verifier=AnalysisVerifier(root / 'runtime' / 'exports'))
    supervisor.prepare(spec)
    try:
        supervisor.submit(tid)
    except contract.ProtocolError:
        denied_without_approval = True
    else:
        raise AssertionError('Unapproved task admitted')
    task_review = build_task_review(spec, review)
    decision('approve_task', {'spec': spec, 'enrollment_revision': 1,
                             'task_review_id': task_review['review_id'],
                             'reviewed_at': task_review['reviewed_at'], 'expires_at': expiry}, 0)
    (root / 'ipc').mkdir()
    launch = {'credential': {'supervisor_id': credential.supervisor_id, 'runtime_id': credential.runtime_id,
                             'key_id': credential.key_id, 'secret_hex': credential.secret.hex(),
                             'expires_at': expiry, 'operations': list(credential.operations)},
              'enrollment': enrollment, 'operator_dir': str(root / 'operator'),
              'runtime_dir': str(root / 'runtime'), 'socket': str(transport.socket_path)}
    write(root / 'launch.json', launch)
    write(root / 'task.json', spec)
    print(json.dumps({'phase': 'starting_native', 'fixture': str(root), 'task_id': tid}), flush=True)
    with (root / 'native.log').open('w') as log:
        process = subprocess.Popen(command + ['serve', '--launch', str(root / 'launch.json')],
                                   cwd=REPO, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 25
            while not transport.socket_path.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Native endpoint did not start')
                time.sleep(.1)
            discovery = supervisor.discover()
            status = supervisor.submit(tid)
            print(json.dumps({'phase': 'submitted', 'status': status}), flush=True)
            deadline = time.monotonic() + 220
            while status['execution_status'] not in contract.TERMINAL and time.monotonic() < deadline:
                time.sleep(.5)
                status = supervisor.status(tid)
                if status.get('runtime_result') is None and journal.get(tid)['observation']['reason'] == 'dispatch_uncertain':
                    break
            if status['execution_status'] == 'completed':
                status = supervisor.verify(tid)
                duplicate = supervisor.submit(tid)
                assert duplicate['session_id'] == status['session_id']
                artifact = root / 'runtime' / 'exports' / tid / 'report.json'
                report = json.loads(artifact.read_text())
                # A second check deliberately does not call expected_report.
                assert report['totals'] == {'paid_cents': 20000, 'refund_cents': -2000,
                                           'pending_cents': 3000, 'net_cents': 18000}
                assert report['accepted_count'] == 4 and len(report['exceptions']) == 3
            with operator._connect() as db:
                intent_counts = {name: db.execute('SELECT count(*) FROM external_events WHERE task_id=? AND kind=?',
                                                  (tid, name)).fetchone()[0]
                                 for name in ('submit_intent', 'native_intent', 'publication_intent')}
            receipt = {'schema': 'cow.agent-routing.acceptance/1', 'fixture': str(root),
                       'enrollment': enrollment, 'discovery': discovery, 'task': spec,
                       'status': status, 'intent_counts': intent_counts,
                       'unapproved_denied': denied_without_approval,
                       'caller_private_open_attempts': len(blocked),
                       'caller_audit_guard': 'denied native workspace, data directory and ~/.cow opens',
                       'native_process_pid': process.pid}
            write(root / 'receipt.json', receipt)
            print(json.dumps({'phase': 'finished', 'receipt': str(root / 'receipt.json'), 'status': status}), flush=True)
            if not status['verified']:
                raise RuntimeError('Native experiment not verified; no retry was attempted')
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
