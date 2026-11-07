"""Disposable, independently owned Unix-socket runtime for EXTERNAL-001."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socketserver
import sqlite3
import stat
import threading
import time
import uuid

from agent.external import contract


class Rejection(Exception):
    pass


def _private_directory(path):
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Directory must be private and owned by the runtime user')
    return path


def _safe_file(path):
    try:
        info = Path(path).lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('Unsafe runtime file')


class Runtime:
    def __init__(self, root, socket_path, config, pause_at=None):
        self.root = _private_directory(root)
        self.socket_path = Path(socket_path)
        _private_directory(self.socket_path.parent)
        self.credential = contract.Credential(config['supervisor_id'], config['runtime_id'],
            config['key_id'], bytes.fromhex(config['secret_hex']), config['expires_at'],
            tuple(config['operations']))
        if not isinstance(config['name'], str) or not isinstance(config['model'], str):
            raise ValueError('Invalid runtime identity')
        self.name, self.model = config['name'], config['model']
        self.pause_at = pause_at
        self.epoch = str(uuid.uuid4())
        self.lock_fd = os.open(self.root / 'runtime.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in ('runtime.db', 'effects.db'):
            _safe_file(self.root / name)
        self.mutex = threading.RLock()
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
                result TEXT, reason TEXT NOT NULL DEFAULT '', UNIQUE(supervisor_id,idempotency_key));
        ''')
        self.effects = sqlite3.connect(self.root / 'effects.db', check_same_thread=False, isolation_level=None)
        self.effects.execute('PRAGMA journal_mode=WAL')
        self.effects.execute('PRAGMA synchronous=FULL')
        self.effects.execute('CREATE TABLE IF NOT EXISTS effects (task_id TEXT PRIMARY KEY, content TEXT NOT NULL)')
        _private_directory(self.root / 'exports')
        with self.mutex:
            self.db.execute("UPDATE tasks SET state='needs_review', revision=revision+1, reason='abandoned_intent' WHERE state='running' AND intent=1")
            self.db.execute("UPDATE tasks SET state='queued', revision=revision+1, reason='' WHERE state='running' AND intent=0")
            pending = [row[0] for row in self.db.execute("SELECT task_id FROM tasks WHERE state='queued'")]
        self.pending = pending

    def start_pending(self):
        for task in self.pending:
            self._start(task)
        self.pending = []

    def _observation(self, row):
        spec = json.loads(row['spec'])
        value = {'task_id': row['task_id'], 'task_hash': row['task_hash'],
            'runtime_id': self.credential.runtime_id, 'session_id': row['session_id'],
            'revision': row['revision'], 'state': row['state'],
            'cancel_requested': bool(row['cancel_requested']),
            'termination_confirmed': row['state'] in contract.TERMINAL,
            'result': json.loads(row['result']) if row['result'] else None, 'reason': row['reason']}
        return contract.validate_observation(value, spec)

    def _row(self, task_id):
        return self.db.execute('SELECT * FROM tasks WHERE task_id=? AND supervisor_id=?',
                               (task_id, self.credential.supervisor_id)).fetchone()

    def handle(self, request):
        payload = contract.authenticate(request, self.credential, kind='request')
        action = request['action']
        with self.mutex:
            try:
                self.db.execute('INSERT INTO requests VALUES (?)', (request['request_id'],))
            except sqlite3.IntegrityError:
                raise Rejection('replay') from None
        if action == 'discover':
            if payload:
                raise Rejection('invalid_request')
            return {'protocol': contract.VERSION, 'runtime_id': self.credential.runtime_id,
                    'name': self.name, 'model': self.model, 'operations': list(self.credential.operations),
                    'approval_operations': [x for x in self.credential.operations if x == 'record_effect'],
                    'session_ownership': 'runtime', 'cancellation': 'cooperative', 'epoch': self.epoch}
        if action == 'submit':
            if set(payload) != {'spec', 'approval'}:
                raise Rejection('invalid_request')
            try:
                spec = contract.normalize_spec(payload['spec'])
                if spec['runtime_id'] != self.credential.runtime_id:
                    raise contract.ProtocolError('Runtime identity mismatch')
            except (contract.ProtocolError, TypeError, ValueError):
                raise Rejection('unauthorized') from None
            task_hash = contract.digest(spec)
            with self.mutex:
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
                        (spec['task_id'], self.credential.supervisor_id, task_hash, spec['idempotency_key'],
                         contract.canonical(spec), contract.canonical(payload['approval']), str(uuid.uuid4()), 'queued', 1))
                    row = self._row(spec['task_id'])
                    self.db.execute('COMMIT')
                except Exception:
                    self.db.execute('ROLLBACK')
                    raise
            self._start(spec['task_id'])
            return self._observation(row)
        if set(payload) != {'task_id', 'task_hash'} or not contract.task_id(payload['task_id']) or not isinstance(payload['task_hash'], str):
            raise Rejection('invalid_request')
        with self.mutex:
            row = self._row(payload['task_id'])
            if not row:
                raise Rejection('not_found')
            if row['task_hash'] != payload['task_hash']:
                raise Rejection('conflict')
            if action == 'cancel' and row['state'] not in contract.TERMINAL and not row['cancel_requested']:
                state = 'cancelled' if row['state'] == 'queued' else row['state']
                self.db.execute('UPDATE tasks SET cancel_requested=1,state=?,revision=revision+1 WHERE task_id=?', (state, row['task_id']))
                row = self._row(row['task_id'])
            return self._observation(row)

    def _start(self, task_id):
        threading.Thread(target=self._work, args=(task_id,), daemon=True).start()

    def _pause(self, boundary):
        if self.pause_at == boundary:
            fd = os.open(self.root / 'reached', os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(boundary)
            while not (self.root / 'release').exists():
                time.sleep(0.02)

    def _finish(self, task_id, state, reason='', result=None):
        with self.mutex:
            self.db.execute('UPDATE tasks SET state=?,reason=?,result=?,revision=revision+1 WHERE task_id=? AND state=?',
                (state, reason, contract.canonical(result) if result is not None else None, task_id, 'running'))

    def _cancelled(self, task_id):
        with self.mutex:
            return bool(self._row(task_id)['cancel_requested'])

    def _write_artifact(self, task_id, name, content):
        # All path components are runtime generated or contract-validated; open
        # each directory without following symlinks, then atomically replace.
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
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    # Reject an existing symlink rather than replacing it.
                    try:
                        existing = os.stat(name, dir_fd=task_fd, follow_symlinks=False)
                        if not stat.S_ISREG(existing.st_mode):
                            raise ValueError('Unsafe artifact target')
                    except FileNotFoundError:
                        pass
                    os.replace(temp, name, src_dir_fd=task_fd, dst_dir_fd=task_fd)
                    os.fsync(task_fd)
                finally:
                    os.close(task_fd)
            finally:
                os.close(exports_fd)
        finally:
            os.close(root_fd)

    def _work(self, task_id):
        with self.mutex:
            row = self._row(task_id)
            if not row or row['state'] != 'queued':
                return
            try:
                spec = contract.authorize(json.loads(row['spec']), self.credential, json.loads(row['approval']))
            except (contract.ProtocolError, ValueError, TypeError):
                self.db.execute("UPDATE tasks SET state='failed',reason='authority_expired',revision=revision+1 WHERE task_id=?", (task_id,))
                return
            self.db.execute("UPDATE tasks SET state='running',revision=revision+1 WHERE task_id=?", (task_id,))
        try:
            self._pause('before_intent')
            if self._cancelled(task_id):
                self._finish(task_id, 'cancelled', 'cancelled_before_intent')
                return
            with self.mutex:
                # Recheck immediately before committing effect intent.
                contract.authorize(spec, self.credential, json.loads(row['approval']))
                self.db.execute('UPDATE tasks SET intent=1 WHERE task_id=?', (task_id,))
            self._pause('after_intent')
            if self._cancelled(task_id):
                self._finish(task_id, 'cancelled', 'cancelled_before_effect')
                return
            contract.authorize(spec, self.credential, json.loads(row['approval']))
            content = spec['task']['content'].encode('utf-8')
            self._write_artifact(task_id, spec['task']['artifact'], content)
            if spec['task']['operation'] == 'record_effect':
                # A grant can expire while the artifact is being written.
                contract.authorize(spec, self.credential, json.loads(row['approval']))
                with self.mutex:
                    self.effects.execute('INSERT OR IGNORE INTO effects VALUES (?,?)', (task_id, spec['task']['content']))
            result = {'artifact': spec['task']['artifact'], 'sha256': hashlib.sha256(content).hexdigest()}
            self._pause('after_effect')
            if self._cancelled(task_id):
                self._finish(task_id, 'needs_review', 'cancelled_after_effect', result)
                return
            self._finish(task_id, 'completed', result=result)
            self._pause('after_completion')
        except Exception:
            # Intent means that a partial write cannot be ruled out.
            with self.mutex:
                current = self._row(task_id)
                intent = current and current['intent']
            self._finish(task_id, 'needs_review' if intent else 'failed', 'execution_interrupted')


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(3)
        try:
            raw = self.rfile.readline(contract.MAX_MESSAGE_BYTES + 1)
            if not raw.endswith(b'\n') or len(raw) > contract.MAX_MESSAGE_BYTES:
                return
            request = json.loads(raw)
            # Authentication precedes any response or durable request record.
            contract.authenticate(request, self.server.runtime.credential, kind='request')
            try:
                data = self.server.runtime.handle(request)
                payload = {'ok': True, 'data': data}
            except Rejection as exc:
                payload = {'ok': False, 'error': str(exc)}
            except Exception:
                payload = {'ok': False, 'error': 'internal_error'}
            response = contract.envelope(self.server.runtime.credential, request['action'], payload,
                                         request_id=request['request_id'], kind='response')
            self.wfile.write(contract.canonical(response).encode() + b'\n')
        except (ValueError, TypeError, OSError, contract.ProtocolError):
            return


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(*args)

    def process_request(self, request, client_address):
        self.slots.acquire()
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--socket', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--pause-at', choices=('before_intent', 'after_intent', 'after_effect', 'after_completion'))
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as stream:
        config = json.load(stream)
    runtime = Runtime(args.root, args.socket, config, args.pause_at)
    try:
        try:
            info = runtime.socket_path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError('Unsafe socket target')
            runtime.socket_path.unlink()
        except FileNotFoundError:
            pass
        old_umask = os.umask(0o077)
        try:
            server = Server(str(runtime.socket_path), Handler)
        finally:
            os.umask(old_umask)
        server.runtime = runtime
        runtime.start_pending()
        with server:
            server.serve_forever()
    finally:
        os.close(runtime.lock_fd)


if __name__ == '__main__':
    main()
