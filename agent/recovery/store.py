"""Durable task journal with process-lifetime ownership and attempt fencing."""
import hashlib
import json
from contextlib import contextmanager
import os
import sqlite3
import uuid
from pathlib import Path

try:
    import fcntl
except ImportError:  # No unsafe lock emulation on unsupported platforms.
    fcntl = None


class LeaseLost(RuntimeError):
    """The attempt no longer has authority to start or record work."""


class Claim:
    def __init__(self, task_id, attempt_id, task, fd, resource_fd=None):
        self.task_id, self.attempt_id, self.task, self._fd = task_id, attempt_id, task, fd
        self._resource_fd = resource_fd

    def close(self):
        try:
            if self._resource_fd is not None:
                TaskStore._unlock(self._resource_fd)
                self._resource_fd = None
        finally:
            if self._fd is not None:
                TaskStore._unlock(self._fd)
                self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class TaskStore:
    def __init__(self, path):
        if fcntl is None:
            raise RuntimeError("Task recovery requires POSIX flock")
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        self.lock_dir = self.path.parent / (self.path.name + '.locks')
        self.lock_dir.mkdir(mode=0o700, exist_ok=True)
        with self._connect() as db:
            mode = db.execute('PRAGMA journal_mode=WAL').fetchone()[0]
            if mode.lower() != 'wal':
                raise RuntimeError('Task journal requires SQLite WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS recovery_tasks (
                    task_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, session_id TEXT NOT NULL,
                    kind TEXT NOT NULL, spec TEXT NOT NULL, idempotency_key TEXT,
                    state TEXT NOT NULL, attempt_id TEXT, attempt_count INTEGER NOT NULL DEFAULT 0,
                    generation INTEGER NOT NULL DEFAULT 0,
                    result TEXT, error TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    UNIQUE(owner_id, session_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS recovery_attempts (
                    attempt_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES recovery_tasks(task_id),
                    number INTEGER NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    ended_at TEXT
                );
                CREATE TABLE IF NOT EXISTS recovery_effects (
                    effect_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES recovery_attempts(attempt_id),
                    name TEXT NOT NULL, mutating INTEGER NOT NULL, call_id TEXT,
                    result TEXT, recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS recovery_verifications (
                    verification_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES recovery_tasks(task_id),
                    attempt_id TEXT NOT NULL REFERENCES recovery_attempts(attempt_id),
                    contract_hash TEXT NOT NULL, report TEXT NOT NULL,
                    observed_at TEXT,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE INDEX IF NOT EXISTS recovery_attempt_task ON recovery_attempts(task_id, number);
                CREATE INDEX IF NOT EXISTS recovery_effect_attempt ON recovery_effects(attempt_id);
                CREATE INDEX IF NOT EXISTS recovery_verification_attempt ON recovery_verifications(task_id, attempt_id);
            ''')
            # Serialize migration across independently starting services.
            db.execute('BEGIN IMMEDIATE')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(recovery_tasks)')}
            if 'generation' not in columns:
                db.execute('ALTER TABLE recovery_tasks ADD COLUMN generation INTEGER NOT NULL DEFAULT 0')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=30)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _json(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

    def _lock(self, task_id):
        # IDs are generated internally; reject paths and aliases on public methods.
        if str(uuid.UUID(task_id)) != task_id:
            raise ValueError('invalid task id')
        return self._lock_name(task_id)

    def _lock_name(self, name):
        fd = os.open(self.lock_dir / name, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return None
        except BaseException:
            os.close(fd)
            raise
        return fd

    @staticmethod
    def _unlock(fd):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    @classmethod
    def _resource_name(cls, spec):
        if not isinstance(spec, dict) or any(
            not isinstance(spec.get(key), str) or not spec[key]
            for key in ('target_agent_id', 'target_session_id')
        ):
            raise ValueError('delegate requires target agent and session strings')
        encoded = cls._json([spec['target_agent_id'], spec['target_session_id']])
        return 'resource-' + hashlib.sha256(encoded.encode('utf-8')).hexdigest()

    def _get(self, db, task_id):
        row = db.execute('SELECT * FROM recovery_tasks WHERE task_id=?', (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        task = dict(row)
        task['spec'] = json.loads(task['spec'])
        task['result'] = json.loads(task['result']) if task['result'] is not None else None
        task['verification'] = None
        task['attempts'] = []
        for attempt in db.execute('SELECT * FROM recovery_attempts WHERE task_id=? ORDER BY number', (task_id,)):
            item = dict(attempt)
            item['effects'] = []
            for effect in db.execute('SELECT * FROM recovery_effects WHERE attempt_id=? ORDER BY rowid', (item['attempt_id'],)):
                entry = dict(effect)
                entry['mutating'] = bool(entry['mutating'])
                entry['result'] = json.loads(entry['result']) if entry['result'] is not None else None
                item['effects'].append(entry)
            item['verifications'] = []
            for verification in db.execute('SELECT * FROM recovery_verifications WHERE task_id=? AND attempt_id=? ORDER BY rowid', (task_id, item['attempt_id'])):
                record = dict(verification)
                report = json.loads(record.pop('report'))
                report.update(record)
                item['verifications'].append(report)
                if item['attempt_id'] == task['attempt_id']:
                    task['verification'] = report
            task['attempts'].append(item)
        return task

    def get(self, task_id):
        with self._connect() as db:
            return self._get(db, task_id)

    def record_verification(self, task_id, attempt_id, contract_hash, report):
        if not isinstance(report, dict):
            raise ValueError('verification report must be an object')
        for key, statuses in (('acceptance', ('passed', 'failed', 'unverified')),
                              ('external_state', ('confirmed', 'failed', 'unverified'))):
            value = report.get(key)
            if not isinstance(value, dict) or value.get('status') not in statuses:
                raise ValueError('invalid verification status for ' + key)
        encoded = self._json(report)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state,attempt_id,spec FROM recovery_tasks WHERE task_id=?', (task_id,)).fetchone()
            if row is None or row['state'] != 'completed' or row['attempt_id'] != attempt_id:
                return False
            spec = json.loads(row['spec'])
            if not isinstance(spec, dict):
                return False
            expected = hashlib.sha256(self._json(spec.get('verification', {})).encode('utf-8')).hexdigest()
            if contract_hash != expected:
                return False
            db.execute('INSERT INTO recovery_verifications(verification_id,task_id,attempt_id,contract_hash,report,observed_at) VALUES (?,?,?,?,?,?)',
                       (str(uuid.uuid4()), task_id, attempt_id, contract_hash, encoded, report.get('checked_at')))
            return True

    def list_unverified_completed(self, limit=100):
        with self._connect() as db:
            rows = db.execute("""SELECT t.task_id FROM recovery_tasks t
                WHERE t.state='completed' AND NOT EXISTS (
                    SELECT 1 FROM recovery_verifications v
                    WHERE v.task_id=t.task_id AND v.attempt_id=t.attempt_id
                ) ORDER BY t.created_at ASC, t.rowid ASC LIMIT ?""", (limit,)).fetchall()
            return [self._get(db, row['task_id']) for row in rows]

    @contextmanager
    def verification_lock(self, task_id):
        fd = self._lock(task_id)
        if fd is None:
            yield None
            return
        try:
            task = self.get(task_id)
            if task['state'] != 'completed':
                raise ValueError('task execution not completed')
            yield task
        finally:
            self._unlock(fd)

    def submit(self, owner_id, session_id, kind, spec, *, idempotency_key=None):
        if kind == 'delegate':
            self._resource_name(spec)
        encoded = self._json(spec)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if idempotency_key is not None:
                row = db.execute('SELECT * FROM recovery_tasks WHERE owner_id=? AND session_id=? AND idempotency_key=?',
                                 (owner_id, session_id, idempotency_key)).fetchone()
                if row:
                    if row['kind'] != kind or row['spec'] != encoded:
                        raise ValueError('idempotency key conflicts with existing task')
                    return self._get(db, row['task_id'])
            task_id = str(uuid.uuid4())
            db.execute('INSERT INTO recovery_tasks(task_id,owner_id,session_id,kind,spec,idempotency_key,state) VALUES (?,?,?,?,?,?,?)',
                       (task_id, owner_id, session_id, kind, encoded, idempotency_key, 'queued'))
            return self._get(db, task_id)

    def list_tasks(self, owner_id=None, states=None, limit=100, oldest_first=False):
        clauses, args = [], []
        if owner_id is not None:
            clauses.append('owner_id=?'); args.append(owner_id)
        if states is not None:
            states = list(states)
            if not states:
                return []
            clauses.append('state IN (' + ','.join('?' for _ in states) + ')'); args.extend(states)
        args.append(limit)
        with self._connect() as db:
            order = 'ASC' if oldest_first else 'DESC'
            rows = db.execute('SELECT task_id FROM recovery_tasks' + (' WHERE ' + ' AND '.join(clauses) if clauses else '') + f' ORDER BY created_at {order}, rowid {order} LIMIT ?', args).fetchall()
            return [self._get(db, row['task_id']) for row in rows]

    def claim(self, task_id, *, expected_generation=None):
        fd = self._lock(task_id)
        if fd is None:
            return None
        resource_fd = None
        transferred = False
        try:
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute("SELECT kind,spec,generation FROM recovery_tasks WHERE task_id=? AND state='queued'", (task_id,)).fetchone()
                if row is None or (expected_generation is not None and row['generation'] != expected_generation):
                    return None
                if row['kind'] == 'delegate':
                    resource_fd = self._lock_name(self._resource_name(json.loads(row['spec'])))
                    if resource_fd is None:
                        return None
                attempt_id = str(uuid.uuid4())
                cur = db.execute("UPDATE recovery_tasks SET state='running', attempt_id=?, attempt_count=attempt_count+1, reason='', updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE task_id=? AND state='queued'", (attempt_id, task_id))
                if not cur.rowcount:
                    return None
                db.execute("INSERT INTO recovery_attempts(attempt_id,task_id,number,state) SELECT ?,task_id,attempt_count,'running' FROM recovery_tasks WHERE task_id=?", (attempt_id, task_id))
                task = self._get(db, task_id)
            claim = Claim(task_id, attempt_id, task, fd, resource_fd)
            transferred = True
            return claim
        finally:
            if not transferred:
                try:
                    if resource_fd is not None:
                        self._unlock(resource_fd)
                finally:
                    self._unlock(fd)

    def finish(self, claim, status, result=None, error=''):
        if status not in ('completed', 'failed', 'cancelled', 'timed_out', 'needs_review'):
            raise ValueError('invalid terminal status')
        if claim._fd is None:
            return False
        encoded = self._json(result) if result is not None else None
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cur = db.execute("UPDATE recovery_tasks SET state=?,result=?,error=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE task_id=? AND state='running' AND attempt_id=?", (status, encoded, error, claim.task_id, claim.attempt_id))
            if cur.rowcount:
                db.execute("UPDATE recovery_attempts SET state=?,ended_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE attempt_id=?", (status, claim.attempt_id))
            return bool(cur.rowcount)

    def request_stop(self, task_id, status='cancelled', *, attempt_id=None, expected_generation=None, expected_state=None, return_snapshot=False):
        if status not in ('cancelled', 'timed_out'):
            raise ValueError('invalid stop status')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state,attempt_id,generation FROM recovery_tasks WHERE task_id=?', (task_id,)).fetchone()
            if row is None or row['state'] not in ('queued', 'running'):
                return False
            if expected_state is not None and row['state'] != expected_state:
                return False
            if expected_generation is not None and row['generation'] != expected_generation:
                return False
            if attempt_id is not None and (row['state'] != 'running' or row['attempt_id'] != attempt_id):
                return False
            db.execute("UPDATE recovery_tasks SET state=?,reason=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE task_id=?", (status, status, task_id))
            if row['state'] == 'running':
                db.execute("UPDATE recovery_attempts SET state=?,reason=?,ended_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE attempt_id=?", (status, status, row['attempt_id']))
            return self._get(db, task_id) if return_snapshot else True

    def before_tool(self, claim, name, *, mutating, call_id=None):
        effect_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT 1 FROM recovery_tasks WHERE task_id=? AND state='running' AND attempt_id=?", (claim.task_id, claim.attempt_id)).fetchone()
            if not row or claim._fd is None:
                raise LeaseLost('attempt no longer running')
            db.execute('INSERT INTO recovery_effects(effect_id,attempt_id,name,mutating,call_id) VALUES (?,?,?,?,?)', (effect_id, claim.attempt_id, name, int(mutating), call_id))
        return effect_id

    def after_tool(self, claim, effect_id, result):
        encoded = self._json(result)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cur = db.execute("UPDATE recovery_effects SET result=?,completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE effect_id=? AND attempt_id=? AND completed_at IS NULL AND EXISTS (SELECT 1 FROM recovery_tasks WHERE task_id=? AND state='running' AND attempt_id=?)", (encoded, effect_id, claim.attempt_id, claim.task_id, claim.attempt_id)) if claim._fd is not None else None
            return bool(cur and cur.rowcount)

    def reconcile(self):
        with self._connect() as db:
            ids = [row[0] for row in db.execute("SELECT task_id FROM recovery_tasks WHERE state='running'")]
        changed = []
        for task_id in ids:
            fd = self._lock(task_id)
            if fd is None:
                continue
            try:
                with self._connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute("SELECT attempt_id FROM recovery_tasks WHERE task_id=? AND state='running'", (task_id,)).fetchone()
                    if not row:
                        continue
                    attempt_id = row['attempt_id']
                    effects = db.execute('SELECT 1 FROM recovery_effects WHERE attempt_id=? AND mutating=1 LIMIT 1', (attempt_id,)).fetchone()
                    state = 'needs_review' if effects else 'queued'
                    db.execute("UPDATE recovery_attempts SET state='interrupted',reason='process_interrupted',ended_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE attempt_id=?", (attempt_id,))
                    db.execute("UPDATE recovery_tasks SET state=?,reason='process_interrupted',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE task_id=?", (state, task_id))
                    changed.append(task_id)
            finally:
                self._unlock(fd)
        return changed

    def retry(self, task_id, *, acknowledge_effects=False):
        fd = self._lock(task_id)
        if fd is None:
            raise RuntimeError('task still owned by a live execution')
        try:
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                task = self._get(db, task_id)
                if task['state'] not in ('failed', 'cancelled', 'timed_out', 'needs_review'):
                    raise ValueError('task cannot be retried in its current state')
                effects = db.execute('SELECT 1 FROM recovery_effects e JOIN recovery_attempts a ON a.attempt_id=e.attempt_id WHERE a.task_id=? AND e.mutating=1 LIMIT 1', (task_id,)).fetchone()
                if effects and not acknowledge_effects:
                    raise ValueError('retry requires acknowledgement of prior effects')
                db.execute("UPDATE recovery_tasks SET state='queued',attempt_id=NULL,result=NULL,error='',reason='explicit_retry',generation=generation+1,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE task_id=?", (task_id,))
                return self._get(db, task_id)
        finally:
            self._unlock(fd)
