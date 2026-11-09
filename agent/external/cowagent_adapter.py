"""Authenticated, approval-gated bridge to one enrolled CowAgent target."""
import fcntl
import hashlib
import json
import re
import os
from pathlib import Path
import sqlite3
import stat
import threading
import time
import uuid

from agent.external import analysis, contract
from agent.external.synthetic_runtime import Handler, Rejection, Runtime, Server, _private_directory, _safe_file


class CowAgentRuntime:
    _write_artifact = Runtime._write_artifact

    def __init__(self, root, socket_path, credential, native, *, approval_gate, turn_timeout=180):
        self.root = _private_directory(root)
        self.socket_path = Path(socket_path)
        _private_directory(self.socket_path.parent)
        if set(credential.operations) != {'analyze_records'} or approval_gate is None:
            raise ValueError('Bounded approval required')
        enrollment = native.enrollment
        if (not isinstance(enrollment, dict) or enrollment.get('agent_id') not in ('testpilot', 'testpilot2')
                or credential.runtime_id != 'cowagent.' + enrollment['agent_id']):
            raise ValueError('Credential and native target differ')
        self.credential, self.native, self.approval_gate = credential, native, approval_gate
        self.turn_timeout = turn_timeout
        self.epoch = str(uuid.uuid4())
        self.mutex = threading.RLock()
        self.native_lock = threading.Lock()
        self.workers, self.active = set(), {}
        self.closed = self.resources_closed = False
        self.lock_fd = os.open(self.root / 'runtime.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _safe_file(self.root / 'runtime.db')
            self.db = sqlite3.connect(self.root / 'runtime.db', check_same_thread=False, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS tasks (
                  task_id TEXT PRIMARY KEY, supervisor_id TEXT NOT NULL, task_hash TEXT NOT NULL,
                  idempotency_key TEXT NOT NULL, spec TEXT NOT NULL, approval TEXT NOT NULL,
                  session_id TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
                  cancel_requested INTEGER NOT NULL DEFAULT 0, result TEXT, reason TEXT NOT NULL DEFAULT '',
                  UNIQUE(supervisor_id,idempotency_key));
            ''')
            _private_directory(self.root / 'exports')
            self.db.execute("UPDATE tasks SET state='running',reason='runtime_restarted',revision=revision+1 WHERE state IN ('queued','running')")
        except BaseException:
            os.close(self.lock_fd)
            raise

    def _row(self, task_id):
        return self.db.execute('SELECT * FROM tasks WHERE task_id=? AND supervisor_id=?', (task_id, self.credential.supervisor_id)).fetchone()

    def _update(self, task_id, **values):
        values['revision'] = self._row(task_id)['revision'] + 1
        self.db.execute('UPDATE tasks SET ' + ','.join(k + '=?' for k in values) + ' WHERE task_id=?', (*values.values(), task_id))

    def _observation(self, row):
        return contract.validate_observation({
            'task_id': row['task_id'], 'task_hash': row['task_hash'], 'runtime_id': self.credential.runtime_id,
            'session_id': row['session_id'], 'revision': row['revision'], 'state': row['state'],
            'cancel_requested': bool(row['cancel_requested']), 'termination_confirmed': row['state'] in contract.TERMINAL,
            'result': json.loads(row['result']) if row['result'] else None, 'reason': row['reason'],
        }, json.loads(row['spec']))

    def _discover(self):
        enrollment = self.native.enrollment
        expected = {k: v for k, v in enrollment.items() if k != 'probe_sha256'}
        actual = self.native.discover()
        if actual != expected or actual.get('runtime_kind') != 'cowagent-registered/1' or actual.get('agent_id') != enrollment['agent_id']:
            raise ValueError('Native binding unavailable')
        return json.loads(contract.canonical(actual))

    def handle(self, request):
        payload = contract.authenticate(request, self.credential, kind='request')
        action = request['action']
        with self.mutex:
            if action == 'inspect':
                if payload:
                    raise Rejection('invalid_request')
                from .inspection import inspect_running
                return inspect_running(self, 'persistent_named')
            if self.closed:
                raise Rejection('unavailable')
            try:
                self.db.execute('INSERT INTO requests VALUES (?)', (request['request_id'],))
            except sqlite3.IntegrityError:
                raise Rejection('replay') from None
            if action == 'discover':
                if payload:
                    raise Rejection('invalid_request')
                try:
                    native = self._discover()
                    return {'protocol': contract.VERSION, 'runtime_id': self.credential.runtime_id,
                            'name': 'CowAgent registered agent', 'model': native['model'], 'native_capabilities': native,
                            'operations': ['analyze_records'], 'approval_operations': ['analyze_records'],
                            'session_ownership': 'runtime', 'cancellation': 'cooperative', 'epoch': self.epoch}
                except Exception:
                    raise Rejection('unavailable') from None
            if action == 'submit':
                if set(payload) != {'spec', 'approval'}:
                    raise Rejection('invalid_request')
                try:
                    spec = contract.normalize_spec(payload['spec'])
                    if spec['task']['operation'] != 'analyze_records':
                        raise ValueError('Unsupported operation')
                    contract.authorize(spec, self.credential, payload['approval'])
                    self.approval_gate.validate_submission(spec, payload['approval'], self.credential, enrollment=self.native.enrollment)
                except (contract.ProtocolError, KeyError, TypeError, ValueError):
                    raise Rejection('unauthorized') from None
                task_hash = contract.digest(spec)
                row = self.db.execute('SELECT * FROM tasks WHERE supervisor_id=? AND idempotency_key=?', (self.credential.supervisor_id, spec['idempotency_key'])).fetchone()
                if row:
                    if row['task_hash'] != task_hash:
                        raise Rejection('conflict')
                    return self._observation(row)
                if self._row(spec['task_id']):
                    raise Rejection('conflict')
                self.db.execute('INSERT INTO tasks (task_id,supervisor_id,task_hash,idempotency_key,spec,approval,session_id,state,revision) VALUES (?,?,?,?,?,?,?,?,?)',
                                (spec['task_id'], self.credential.supervisor_id, task_hash, spec['idempotency_key'], contract.canonical(spec), contract.canonical(payload['approval']), str(uuid.uuid4()), 'queued', 1))
                row = self._row(spec['task_id'])
                worker = threading.Thread(target=self._work, args=(spec['task_id'],), daemon=True)
                self.workers.add(worker)
                worker.start()
                return self._observation(row)
            if action not in ('status', 'cancel', 'result') or set(payload) != {'task_id', 'task_hash'} or not contract.task_id(payload['task_id']) or not isinstance(payload['task_hash'], str):
                raise Rejection('invalid_request')
            row = self._row(payload['task_id'])
            if not row:
                raise Rejection('not_found')
            if row['task_hash'] != payload['task_hash']:
                raise Rejection('conflict')
            if action == 'cancel' and row['state'] not in contract.TERMINAL:
                if not row['cancel_requested']:
                    self._update(row['task_id'], cancel_requested=1, reason='cancel_requested')
                event = self.active.get(row['task_id'])
                if event:
                    event.set()  # Supervisor already claimed its durable cancellation.
                row = self._row(row['task_id'])
            return self._observation(row)

    def _watch(self, task_id, spec, approval, event, done):
        deadline = time.monotonic() + self.turn_timeout
        while not done.wait(.1):
            try:
                cancelled = self.approval_gate.should_cancel(spec, approval, self.credential, enrollment=self.native.enrollment)
            except Exception:
                cancelled = True
            if cancelled or time.monotonic() >= deadline:
                with self.mutex:
                    row = self._row(task_id)
                    if row and row['state'] not in contract.TERMINAL and not row['cancel_requested']:
                        self._update(task_id, cancel_requested=1, reason='operator_or_deadline_cancel_requested')
                        if cancelled:
                            try:
                                claimed = self.approval_gate.claim_cancel(task_id)
                            except Exception:
                                claimed = False
                            if not claimed:
                                return
                        event.set()
                return

    def _work(self, task_id):
        # Never hold the status/cancel mutex while waiting for native ownership.
        with self.native_lock:
            self._work_locked(task_id)

    def _work_locked(self, task_id):
        handle, intent = None, False
        done = threading.Event()
        watcher = None
        try:
            with self.mutex:
                row = self._row(task_id)
                if row['cancel_requested'] or self.closed:
                    self._update(task_id, state='cancelled', reason='cancelled_before_dispatch')
                    return
                spec, approval = json.loads(row['spec']), json.loads(row['approval'])
                contract.authorize(spec, self.credential, approval)
                self._update(task_id, state='running', reason='starting')
            self._discover()
            handle = self.native.prepare(row['session_id'])
            self._discover()
            event = threading.Event()
            with self.mutex:
                row = self._row(task_id)
                if row['cancel_requested'] or self.closed:
                    self._update(task_id, state='cancelled', reason='cancelled_before_dispatch')
                    return
                contract.authorize(spec, self.credential, approval)
                self.approval_gate.authorize_native(spec, approval, self.credential, enrollment=self.native.enrollment,
                                                    native_thread=row['session_id'], native_session=row['session_id'])
                intent = True
                self._update(task_id, reason='dispatch_intent')
                self.active[task_id] = event
            watcher = threading.Thread(target=self._watch, args=(task_id, spec, approval, event, done), daemon=True)
            watcher.start()
            outcome = handle.run(spec, event)
            done.set()
            watcher.join()
            with self.mutex:
                row = self._row(task_id)
                if row['cancel_requested'] or self.closed:
                    self._update(task_id, state='cancelled', reason='publication_fenced')
                    return
                if not isinstance(outcome, dict) or set(outcome) != {'report', 'receipt'}:
                    raise ValueError('Invalid output')
                report, receipt = outcome['report'], outcome['receipt']
                if not analysis._valid_report_shape(report, task_id) or report != analysis.expected_report(spec):
                    raise ValueError('Invalid report')
                binding = getattr(handle, 'receipt_binding', None)
                receipt_fields = {'agent_id', 'agent_name', 'model', 'provider', 'profile_sha256',
                                  'memory_scope_sha256', 'session_id', 'native_run_id', 'native_pid',
                                  'native_started_at', 'native_finished_at', 'source', 'prompt_source',
                                  'memory_owner', 'permission_mode', 'tool_event_count'}
                if (not isinstance(receipt, dict) or set(receipt) != receipt_fields
                        or not isinstance(binding, dict) or set(binding) != {
                            'agent_id', 'agent_name', 'model', 'provider', 'profile_sha256', 'memory_scope_sha256'}
                        or any(receipt.get(k) != v for k, v in binding.items())
                        or any(receipt.get(k) != self.native.enrollment.get(k) for k in ('agent_id', 'model', 'provider', 'profile_sha256'))
                        or not isinstance(receipt['agent_name'], str) or not 0 < len(receipt['agent_name']) <= 128
                        or not isinstance(receipt['memory_scope_sha256'], str)
                        or not re.fullmatch(r'[0-9a-f]{64}', receipt['memory_scope_sha256'])
                        or receipt['session_id'] != row['session_id'] or receipt['source'] != 'codex'
                        or receipt['prompt_source'] != 'native' or receipt['memory_owner'] != 'runtime'
                        or receipt['permission_mode'] != 'read-only' or not contract.identifier(receipt['native_run_id'])
                        or type(receipt['native_pid']) is not int or receipt['native_pid'] <= 0
                        or not contract.finite(receipt['native_started_at']) or not contract.finite(receipt['native_finished_at'])
                        or receipt['native_started_at'] <= 0 or receipt['native_finished_at'] < receipt['native_started_at']
                        or type(receipt['tool_event_count']) is not int or receipt['tool_event_count'] < 0):
                    raise ValueError('Invalid receipt')
                contract.authorize(spec, self.credential, approval)
                try:
                    self.approval_gate.authorize_publication(spec, approval, self.credential, enrollment=self.native.enrollment)
                except contract.ProtocolError:
                    self._update(task_id, state='cancelled', cancel_requested=1, reason='operator_publication_fenced')
                    return
                data = contract.canonical(report).encode('utf-8')
                self._update(task_id, reason='publication_intent')
                self._write_artifact(task_id, spec['task']['artifact'], data)
                result = {'adapter_version': 'cow.cowagent/1', 'publication_status': 'published',
                          'artifact': spec['task']['artifact'], 'sha256': hashlib.sha256(data).hexdigest(),
                          **receipt}
                self._update(task_id, state='completed', result=contract.canonical(result), reason='')
        except Exception as exc:
            with self.mutex:
                row = self._row(task_id)
                if row and row['state'] not in contract.TERMINAL:
                    self._update(task_id, state='running' if intent else 'failed',
                                 reason='dispatch_uncertain' if intent else 'approval_unavailable' if isinstance(exc, contract.ProtocolError) else 'startup_failed')
        finally:
            done.set()
            if watcher:
                watcher.join()
            if handle is not None and callable(getattr(handle, 'close', None)):
                try:
                    handle.close()
                except Exception:
                    pass
            with self.mutex:
                self.active.pop(task_id, None)
                self.workers.discard(threading.current_thread())

    def serve(self):
        try:
            info = self.socket_path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError('Unsafe socket target')
            self.socket_path.unlink()
        except FileNotFoundError:
            pass
        old_umask = os.umask(0o077)
        try:
            server = Server(str(self.socket_path), Handler)
        finally:
            os.umask(old_umask)
        server.runtime = self
        self.server = server
        with server:
            server.serve_forever()

    def close(self):
        with self.mutex:
            if self.resources_closed:
                return
            self.closed = True
            self.db.execute("UPDATE tasks SET cancel_requested=1,revision=revision+1,reason='runtime_shutdown' WHERE state IN ('queued','running') AND cancel_requested=0")
            events, workers = list(self.active.values()), list(self.workers)
            for event in events:
                event.set()
        server = getattr(self, 'server', None)
        if server:
            server.shutdown()
        for worker in workers:
            worker.join(timeout=5)
        with self.mutex:
            if not self.resources_closed and not any(worker.is_alive() for worker in workers):
                self.db.close()
                os.close(self.lock_fd)
                self.resources_closed = True
