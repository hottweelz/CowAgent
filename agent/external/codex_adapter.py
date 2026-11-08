"""Trusted-host Codex runtime. Native dispatch is never replayed automatically."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import stat
import threading
import time
import uuid

from agent.external import contract
from agent.external.codex_client import CodexClient
from agent.external.synthetic_runtime import Handler, Rejection, Server, _private_directory, _safe_file


class CodexRuntime:
    """One durable runtime for an enrolled supervisor; credentials stay in memory.

    policy and client_factory are trusted host dependencies, never task input.
    `serve` uses the EXTERNAL-001 authenticated private Unix transport.
    """

    def __init__(self, root, socket_path, credential, policy, *, client_factory=CodexClient,
                 turn_timeout=180):
        from agent.external import analysis
        self.analysis = analysis
        self.root = _private_directory(root)
        self.socket_path = Path(socket_path)
        _private_directory(self.socket_path.parent)
        self.credential = credential
        if set(credential.operations) != {'analyze_records'}:
            raise ValueError('Codex runtime requires analyze_records enrollment')
        self.policy = policy
        self.client_factory = client_factory
        self.turn_timeout = turn_timeout
        self.epoch = str(uuid.uuid4())
        self.mutex = threading.RLock()
        self.clients = {}
        self.workers = set()
        self.reconciling = set()
        self.reconciled = set()
        self.closed = False
        self.resources_closed = False
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
                    cancel_requested INTEGER NOT NULL DEFAULT 0, intent INTEGER NOT NULL DEFAULT 0,
                    native_thread TEXT, native_session TEXT, native_turn TEXT, publication_intent INTEGER NOT NULL DEFAULT 0, progress TEXT NOT NULL DEFAULT '{}',
                    result TEXT, reason TEXT NOT NULL DEFAULT '',
                    UNIQUE(supervisor_id,idempotency_key));
            ''')
            if 'native_session' not in {row[1] for row in self.db.execute('PRAGMA table_info(tasks)')}:
                self.db.execute('ALTER TABLE tasks ADD COLUMN native_session TEXT')
            if 'publication_intent' not in {row[1] for row in self.db.execute('PRAGMA table_info(tasks)')}:
                self.db.execute('ALTER TABLE tasks ADD COLUMN publication_intent INTEGER NOT NULL DEFAULT 0')
            _private_directory(self.root / 'exports')
            _private_directory(self.root / 'workspaces')
            # No dispatch is resumed after restart, even if it was only queued.
            self.db.execute("UPDATE tasks SET state='running', reason='runtime_restarted', revision=revision+1 WHERE state IN ('queued','running')")
        except BaseException:
            os.close(self.lock_fd)
            raise

    def _row(self, task_id):
        return self.db.execute('SELECT * FROM tasks WHERE task_id=? AND supervisor_id=?',
                               (task_id, self.credential.supervisor_id)).fetchone()

    def _observation(self, row):
        result = json.loads(row['result']) if row['result'] else json.loads(row['progress']) or None
        value = {'task_id': row['task_id'], 'task_hash': row['task_hash'],
                 'runtime_id': self.credential.runtime_id, 'session_id': row['session_id'],
                 'revision': row['revision'], 'state': row['state'],
                 'cancel_requested': bool(row['cancel_requested']),
                 'termination_confirmed': row['state'] in contract.TERMINAL,
                 'result': result, 'reason': row['reason']}
        return contract.validate_observation(value, json.loads(row['spec']))

    def handle(self, request):
        payload = contract.authenticate(request, self.credential, kind='request')
        action = request['action']
        with self.mutex:
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
                    cwd = _private_directory(self.root / 'workspaces' / 'discovery')
                    native = self.policy.discover(cwd)
                    model = native['model']
                    if not isinstance(model, str) or not model:
                        raise ValueError('Native model unavailable')
                    # Reject non-JSON metadata rather than leaking an arbitrary object.
                    native = json.loads(contract.canonical(native))
                except Exception:
                    raise Rejection('unavailable') from None
                return {'protocol': contract.VERSION, 'runtime_id': self.credential.runtime_id,
                        'name': 'Codex app-server', 'model': model, 'native_capabilities': native,
                        'operations': ['analyze_records'], 'approval_operations': [],
                        'session_ownership': 'runtime', 'cancellation': 'cooperative', 'epoch': self.epoch}
            if action == 'submit':
                if set(payload) != {'spec', 'approval'}:
                    raise Rejection('invalid_request')
                try:
                    spec = contract.normalize_spec(payload['spec'])
                    if spec['task']['operation'] != 'analyze_records':
                        raise contract.ProtocolError('Unsupported operation')
                    self.analysis.normalize_payload(spec['task']['content'])
                except (contract.ProtocolError, TypeError, ValueError):
                    raise Rejection('unauthorized') from None
                task_hash = contract.digest(spec)
                self.db.execute('BEGIN IMMEDIATE')
                try:
                    row = self.db.execute('SELECT * FROM tasks WHERE supervisor_id=? AND idempotency_key=?',
                                          (self.credential.supervisor_id, spec['idempotency_key'])).fetchone()
                    if row:
                        if row['task_hash'] != task_hash:
                            raise Rejection('conflict')
                        self.db.execute('COMMIT')
                        return self._observation(row)
                    if self._row(spec['task_id']):
                        raise Rejection('conflict')
                    try:
                        contract.authorize(spec, self.credential, payload['approval'])
                    except (contract.ProtocolError, TypeError, ValueError):
                        raise Rejection('unauthorized') from None
                    self.db.execute('INSERT INTO tasks (task_id,supervisor_id,task_hash,idempotency_key,spec,approval,session_id,state,revision) VALUES (?,?,?,?,?,?,?,?,?)',
                                    (spec['task_id'], self.credential.supervisor_id, task_hash,
                                     spec['idempotency_key'], contract.canonical(spec), contract.canonical(payload['approval']),
                                     str(uuid.uuid4()), 'queued', 1))
                    row = self._row(spec['task_id'])
                    self.db.execute('COMMIT')
                except BaseException:
                    self.db.execute('ROLLBACK')
                    raise
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
                    # This durable bit is also the publication fence.
                    self.db.execute('UPDATE tasks SET cancel_requested=1,revision=revision+1 WHERE task_id=?', (row['task_id'],))
                    row = self._row(row['task_id'])
                # An explicit repeat can recover a lost native interrupt.
                # Status polling never retries the cancellation request.
                active = self.clients.get(row['task_id'])
                if active and row['native_thread'] and row['native_turn']:
                    threading.Thread(target=self._interrupt, args=(active, row['native_thread'], row['native_turn']), daemon=True).start()
            if action in ('status', 'result') and row['reason'] in ('runtime_restarted', 'reconciliation_unavailable', 'reconciled_uncertain') and row['native_thread'] and row['task_id'] not in self.reconciling and row['task_id'] not in self.reconciled:
                self.reconciling.add(row['task_id'])
                self.reconciled.add(row['task_id'])
                worker = threading.Thread(target=self._reconcile, args=(row['task_id'],), daemon=True)
                self.workers.add(worker)
                worker.start()
            return self._observation(row)

    @staticmethod
    def _interrupt(client, thread_id, turn_id):
        try:
            client.request('turn/interrupt', {'threadId': thread_id, 'turnId': turn_id}, timeout=10)
        except Exception:
            pass  # Cancellation is a request, not proof of termination.

    def _update(self, task_id, **values):
        values['revision'] = self._row(task_id)['revision'] + 1
        self.db.execute('UPDATE tasks SET ' + ','.join(k + '=?' for k in values) + ' WHERE task_id=?', (*values.values(), task_id))

    def _progress(self, row, **extra):
        value = {'adapter_version': 'cow.codex/1', 'native_session_id': row['native_session'],
                 'native_thread_id': row['native_thread'], 'native_turn_id': row['native_turn'],
                 'native_status': 'unknown', 'publication_status': 'not_published',
                 'termination_scope': 'unconfirmed', 'descendants_terminated': False,
                 'child_threads': [], 'model_activity_observed': False,
                 'model_activity_counts': {}}
        if row['progress']:
            previous = json.loads(row['progress'])
            for key in ('model_activity_observed', 'model_activity_counts'):
                if key in previous:
                    value[key] = previous[key]
        value.update(extra)
        return value

    @staticmethod
    def _native_id(value):
        if not contract.identifier(value):
            raise ValueError('Invalid native identifier')
        return value

    def _artifact(self, task_id, name, data):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(self.root, flags)
        try:
            exports_fd = os.open('exports', flags, dir_fd=root_fd)
            try:
                try:
                    os.mkdir(task_id, 0o700, dir_fd=exports_fd)
                except FileExistsError:
                    pass
                task_fd = os.open(task_id, flags, dir_fd=exports_fd)
                try:
                    info = os.fstat(task_fd)
                    if info.st_uid != os.getuid() or info.st_mode & 0o077:
                        raise ValueError('Unsafe export directory')
                    temp = '.tmp-' + uuid.uuid4().hex
                    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=task_fd)
                    try:
                        with os.fdopen(fd, 'wb') as stream:
                            stream.write(data)
                            stream.flush()
                            os.fsync(stream.fileno())
                        try:
                            info = os.stat(name, dir_fd=task_fd, follow_symlinks=False)
                            if not stat.S_ISREG(info.st_mode):
                                raise ValueError('Unsafe artifact target')
                        except FileNotFoundError:
                            pass
                        os.replace(temp, name, src_dir_fd=task_fd, dst_dir_fd=task_fd)
                        os.fsync(task_fd)
                    finally:
                        try:
                            os.unlink(temp, dir_fd=task_fd)
                        except FileNotFoundError:
                            pass
                finally:
                    os.close(task_fd)
            finally:
                os.close(exports_fd)
        finally:
            os.close(root_fd)

    def _observe_item(self, item, child_states):
        if item.get('type') == 'subAgentActivity':
            child = item.get('agentThreadId')
            kind = item.get('kind')
            if contract.identifier(child):
                child_states[child] = {'started': 'running', 'interacted': 'running',
                                       'interrupted': 'interrupted', 'completed': 'completed'}.get(kind, 'unknown')
                return [child]
        if item.get('type') == 'collabAgentToolCall':
            found = []
            states = item.get('agentsStates') or {}
            for child in item.get('receiverThreadIds') or []:
                if contract.identifier(child):
                    state = states.get(child) or {}
                    status = state.get('status') if isinstance(state, dict) else None
                    child_states[child] = status if status in ('pendingInit', 'running', 'interrupted', 'completed', 'errored', 'shutdown', 'notFound') else 'unknown'
                    found.append(child)
            return found
        return []

    def _history(self, client, root_thread, turn_id, child_states, final_text):
        """Read available public history; unknown or truncated trees stay explicit."""
        pending = [(root_thread, None)]
        seen = set()
        complete = True
        deadline = time.monotonic() + min(15, self.turn_timeout)
        while pending and len(seen) < 64 and time.monotonic() < deadline:
            current, parent = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            try:
                response = client.request('thread/read', {'threadId': current, 'includeTurns': True}, timeout=min(5, max(.001, deadline - time.monotonic())))
                thread = response['thread']
                if parent is not None:
                    source = thread.get('source')
                    subagent = source.get('subAgent', {}) if isinstance(source, dict) else {}
                    spawn = subagent.get('thread_spawn', {}) if isinstance(subagent, dict) else {}
                    if thread.get('parentThreadId') != parent or not isinstance(spawn, dict) or spawn.get('parent_thread_id') != parent:
                        raise ValueError('Unconfirmed child lineage')
                turns = thread['turns']
                if not isinstance(turns, list):
                    raise ValueError('History unavailable')
                for turn in turns:
                    if turn.get('itemsView') != 'full':
                        complete = False
                    for item in turn.get('items', []):
                        if current == root_thread and turn.get('id') == turn_id and item.get('type') == 'agentMessage' and item.get('phase') in (None, 'final_answer') and isinstance(item.get('text'), str):
                            final_text = item['text']
                        for child in self._observe_item(item, child_states):
                            if child not in seen:
                                pending.append((child, current))
            except Exception:
                complete = False
        if pending:
            complete = False
        return final_text, child_states, 'available' if complete else 'partial_or_unavailable'

    def _reconcile(self, task_id):
        """Read persisted native identity only; never dispatch or publish on recovery."""
        client = None
        try:
            with self.mutex:
                row = self._row(task_id)
                thread_id, turn_id = row['native_thread'], row['native_turn']
            workspace = self.root / 'workspaces' / task_id
            argv, env, _ = self.policy.launch(workspace)
            client = self.client_factory(argv, str(workspace), env)
            self.policy.initialize(client)
            response = client.request('thread/read', {'threadId': thread_id, 'includeTurns': True}, timeout=15)
            thread = response['thread']
            if thread.get('id') != thread_id or thread.get('sessionId') != row['native_session']:
                raise ValueError('Native identity mismatch')
            turns = thread.get('turns')
            if not isinstance(turns, list):
                raise ValueError('Native history unavailable')
            native_status = 'unknown'
            for turn in turns:
                if turn.get('id') == turn_id and turn.get('status') in ('completed', 'failed', 'interrupted', 'inProgress'):
                    native_status = turn['status']
            with self.mutex:
                if not self.closed:
                    row = self._row(task_id)
                    progress = json.loads(row['progress']) if row['progress'] else self._progress(row)
                    progress.update({'native_status': native_status, 'reconciliation': 'read_only_history',
                                     'termination_scope': 'unconfirmed', 'descendants_terminated': False})
                    self._update(task_id, progress=contract.canonical(progress), reason='reconciled_uncertain')
        except Exception:
            with self.mutex:
                if not self.closed:
                    self._update(task_id, reason='reconciliation_unavailable')
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            with self.mutex:
                self.reconciling.discard(task_id)
                self.workers.discard(threading.current_thread())

    def _work(self, task_id):
        client = None
        intent = False
        try:
            with self.mutex:
                row = self._row(task_id)
                if row['cancel_requested']:
                    self._update(task_id, state='cancelled', reason='cancelled_before_dispatch')
                    return
                spec = contract.authorize(json.loads(row['spec']), self.credential, json.loads(row['approval']))
                self._update(task_id, state='running', reason='starting')
            workspace = _private_directory(self.root / 'workspaces' / task_id)
            argv, env, expected = self.policy.launch(workspace)
            client = self.client_factory(argv, str(workspace), env)
            with self.mutex:
                if self.closed:
                    return
                self.clients[task_id] = client
            self.policy.initialize(client)
            thread = self.policy.start_thread(client, workspace)
            native_thread = self._native_id(thread['thread']['id'])
            native_session = self._native_id(thread['thread']['sessionId'])
            self.policy.attest_configuration(client, workspace, thread, expected)
            with self.mutex:
                row = self._row(task_id)
                self._update(task_id, native_thread=native_thread, native_session=native_session,
                             progress=contract.canonical(self._progress(row, native_thread_id=native_thread, native_session_id=native_session)), reason='thread_created')
                row = self._row(task_id)
                if row['cancel_requested'] or self.closed:
                    self._update(task_id, state='cancelled', reason='cancelled_before_dispatch')
                    return
                contract.authorize(spec, self.credential, json.loads(row['approval']))
                # Commit intent before issuing turn/start. Any ambiguity prevents replay.
                self._update(task_id, intent=1, reason='dispatch_intent')
                intent = True
            response = client.request('turn/start', {
                'threadId': native_thread,
                'input': [{'type': 'text', 'text': self.analysis.build_prompt(spec), 'text_elements': []}],
                'outputSchema': self.analysis.output_schema(spec),
            }, timeout=min(30, self.turn_timeout))
            native_turn = self._native_id(response['turn']['id'])
            with self.mutex:
                row = self._row(task_id)
                progress = self._progress(row, native_turn_id=native_turn, native_status='inProgress')
                self._update(task_id, native_turn=native_turn, progress=contract.canonical(progress), reason='turn_started')
                if self._row(task_id)['cancel_requested']:
                    threading.Thread(target=self._interrupt, args=(client, native_thread, native_turn), daemon=True).start()
            deadline = time.monotonic() + self.turn_timeout
            final_text = None
            child_states = {}
            denied_requests = 0
            root_status = None
            deadline_interrupted = False
            while True:
                if time.monotonic() >= deadline:
                    if deadline_interrupted:
                        break
                    # Deadline is a cooperative cancellation request, not a hard budget.
                    with self.mutex:
                        row = self._row(task_id)
                        if not row['cancel_requested']:
                            self._update(task_id, cancel_requested=1, reason='deadline_cancel_requested')
                    self._interrupt(client, native_thread, native_turn)
                    deadline_interrupted = True
                    deadline = time.monotonic() + min(5, self.turn_timeout)
                try:
                    event = client.next_event(timeout=min(1, max(.001, deadline - time.monotonic())))
                except queue.Empty:
                    continue
                if event.get('type') == 'transport_error':
                    break
                if event.get('type') == 'server_request_denied':
                    denied_requests += 1
                    with self.mutex:
                        row = self._row(task_id)
                        progress = self._progress(row, native_status='inProgress', denied_requests=denied_requests, child_threads=[{'id': k, 'status': v} for k, v in sorted(child_states.items())])
                        self._update(task_id, progress=contract.canonical(progress))
                    continue
                params = event.get('params', {})
                if not isinstance(params, dict):
                    continue
                item = params.get('item', {})
                if (event.get('method') == 'item/started' and params.get('threadId') == native_thread
                        and params.get('turnId') == native_turn and isinstance(item, dict)
                        and item.get('type') in ('reasoning', 'agentMessage', 'collabAgentToolCall', 'subAgentActivity')):
                    with self.mutex:
                        row = self._row(task_id)
                        progress = self._progress(row, native_status='inProgress', denied_requests=denied_requests,
                                                  child_threads=[{'id': k, 'status': v} for k, v in sorted(child_states.items())])
                        counts = dict(progress['model_activity_counts'])
                        item_type = item['type']
                        counts[item_type] = min(1000, counts.get(item_type, 0) + 1)
                        progress.update(model_activity_observed=True, model_activity_counts=counts)
                        self._update(task_id, progress=contract.canonical(progress))
                if isinstance(item, dict) and item.get('type') in ('collabAgentToolCall', 'subAgentActivity'):
                    self._observe_item(item, child_states)
                    with self.mutex:
                        row = self._row(task_id)
                        progress = self._progress(row, native_status='inProgress', denied_requests=denied_requests, child_threads=[{'id': k, 'status': v} for k, v in sorted(child_states.items())])
                        self._update(task_id, progress=contract.canonical(progress))
                if (event.get('method') == 'item/completed' and params.get('threadId') == native_thread
                        and params.get('turnId') == native_turn and isinstance(item, dict)
                        and item.get('type') == 'agentMessage' and isinstance(item.get('text'), str)):
                    if item.get('phase') in (None, 'final_answer'):
                        final_text = item['text']
                if event.get('method') == 'turn/completed' and params.get('threadId') == native_thread:
                    turn = params.get('turn') or {}
                    if turn.get('id') == native_turn:
                        root_status = turn.get('status')
                        break
            history_status = 'not_read'
            if root_status == 'completed':
                final_text, child_states, history_status = self._history(client, native_thread, native_turn, child_states, final_text)
            with self.mutex:
                row = self._row(task_id)
                progress = self._progress(row, native_status=root_status or 'unknown', history_observation=history_status, denied_requests=denied_requests,
                                          child_threads=[{'id': k, 'status': v} for k, v in sorted(child_states.items())])
                if root_status not in ('completed', 'interrupted'):
                    self._update(task_id, progress=contract.canonical(progress), reason='native_outcome_unconfirmed')
                    return
                if root_status == 'interrupted' and not row['cancel_requested']:
                    self._update(task_id, progress=contract.canonical(progress), reason='native_outcome_unconfirmed')
                    return
                if getattr(self.policy, 'task_effects_confined', False) is not True:
                    self._update(task_id, progress=contract.canonical(progress), reason='authority_inheritance_unconfirmed')
                    return
                progress['termination_scope'] = 'task_effects'
                if row['cancel_requested']:
                    progress['publication_status'] = 'fenced'
                    self._update(task_id, state='cancelled', progress=contract.canonical(progress), reason='publication_fenced')
                    return
                if final_text is None or len(final_text.encode('utf-8')) > contract.MAX_MESSAGE_BYTES:
                    self._update(task_id, state='failed', progress=contract.canonical(progress), reason='missing_or_oversized_output')
                    return
                contract.authorize(spec, self.credential, json.loads(row['approval']))
                data = final_text.encode('utf-8')
                # Persist the irreversible seal before publication. Recovery never republishes.
                self._update(task_id, publication_intent=1, reason='publication_intent')
                # The mutex serializes cancellation and the atomic publication.
                self._artifact(task_id, spec['task']['artifact'], data)
                progress.update({'publication_status': 'published', 'artifact': spec['task']['artifact'],
                                 'sha256': hashlib.sha256(data).hexdigest()})
                self._update(task_id, state='completed', result=contract.canonical(progress), reason='')
        except Exception:
            with self.mutex:
                if not self.closed:
                    row = self._row(task_id)
                    if row and row['state'] not in contract.TERMINAL:
                        self._update(task_id, state='running' if intent else 'failed',
                                     reason='dispatch_uncertain' if intent else 'startup_failed')
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            with self.mutex:
                self.clients.pop(task_id, None)
                self.workers.discard(threading.current_thread())

    def serve(self):
        """Run the authenticated private socket server until externally shut down."""
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
            # Fence publication durably before interrupting or closing any client.
            self.db.execute("UPDATE tasks SET cancel_requested=1,revision=revision+1,reason='runtime_shutdown' WHERE state IN ('queued','running') AND cancel_requested=0")
            clients = [(task_id, client, self._row(task_id)) for task_id, client in self.clients.items()]
            workers = list(self.workers)
        server = getattr(self, 'server', None)
        if server:
            server.shutdown()
        for _, client, row in clients:
            if row and row['native_thread'] and row['native_turn']:
                self._interrupt(client, row['native_thread'], row['native_turn'])
            try:
                client.close()
            except Exception:
                pass
        for worker in workers:
            worker.join(timeout=5)
        # An active worker may still hold a database reference; do not close it.
        with self.mutex:
            if not self.resources_closed and not any(worker.is_alive() for worker in workers):
                self.db.close()
                os.close(self.lock_fd)
                self.resources_closed = True
