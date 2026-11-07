"""External supervisor records share the native journal, never its dispatch queue."""
import json
from contextlib import contextmanager
from .contract import ProtocolError, canonical, digest, normalize_spec, validate_observation


class ExternalBusy(RuntimeError):
    pass


class ExternalJournal:
    def __init__(self, task_store):
        self.store = task_store
        with self.store._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS external_tasks (
                    task_id TEXT PRIMARY KEY, supervisor_id TEXT NOT NULL,
                    runtime_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                    spec TEXT NOT NULL, spec_hash TEXT NOT NULL,
                    transport_status TEXT NOT NULL DEFAULT 'not_sent',
                    submission_started INTEGER NOT NULL DEFAULT 0,
                    approval TEXT, observation TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    UNIQUE(supervisor_id,runtime_id,idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS external_events (
                    event_id INTEGER PRIMARY KEY, task_id TEXT NOT NULL REFERENCES external_tasks(task_id),
                    kind TEXT NOT NULL, body TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE TABLE IF NOT EXISTS external_verifications (
                    verification_id INTEGER PRIMARY KEY, task_id TEXT NOT NULL REFERENCES external_tasks(task_id),
                    spec_hash TEXT NOT NULL, remote_revision INTEGER NOT NULL, report TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
            ''')

    def _get(self, db, task_id):
        row = db.execute('SELECT * FROM external_tasks WHERE task_id=?', (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        value = dict(row)
        for key in ('spec', 'approval', 'observation'):
            value[key] = json.loads(value[key]) if value[key] else None
        value['verification'] = None
        latest = db.execute('SELECT report,remote_revision FROM external_verifications WHERE task_id=? ORDER BY verification_id DESC LIMIT 1', (task_id,)).fetchone()
        if latest and value['observation'] and latest['remote_revision'] == value['observation']['revision']:
            value['verification'] = json.loads(latest['report'])
        return value

    def get(self, task_id):
        with self.store._connect() as db:
            return self._get(db, task_id)

    def create(self, supervisor_id, spec):
        spec = normalize_spec(spec)
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT task_id,spec_hash FROM external_tasks WHERE supervisor_id=? AND runtime_id=? AND idempotency_key=?',
                             (supervisor_id, spec['runtime_id'], spec['idempotency_key'])).fetchone()
            if old:
                if old['spec_hash'] != digest(spec):
                    raise ProtocolError('Idempotency key conflicts with immutable task')
                return self._get(db, old['task_id'])
            db.execute('INSERT INTO external_tasks(task_id,supervisor_id,runtime_id,idempotency_key,spec,spec_hash) VALUES (?,?,?,?,?,?)',
                       (spec['task_id'], supervisor_id, spec['runtime_id'], spec['idempotency_key'], canonical(spec), digest(spec)))
            return self._get(db, spec['task_id'])

    @contextmanager
    def lock(self, task_id):
        from .contract import task_id as valid_id
        if not valid_id(task_id):
            raise ProtocolError('Invalid task ID')
        fd = self.store._lock_name('external-' + task_id)
        if fd is None:
            raise ExternalBusy('External task is supervised by another caller')
        try:
            yield self.get(task_id)
        finally:
            self.store._unlock(fd)

    def event(self, task_id, kind, body, *, transport_status=None):
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (task_id, kind, canonical(body)))
            if transport_status:
                db.execute('UPDATE external_tasks SET transport_status=?,last_error=? WHERE task_id=?',
                           (transport_status, body.get('error', ''), task_id))
            if kind == 'cancel_requested':
                db.execute('UPDATE external_tasks SET cancel_requested=1 WHERE task_id=?', (task_id,))
            if kind == 'submit_intent':
                db.execute('UPDATE external_tasks SET submission_started=1 WHERE task_id=?', (task_id,))

    def approve(self, task_id, approval):
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._get(db, task_id)
            if row['submission_started'] or row['cancel_requested']:
                raise ProtocolError('Cannot approve work after submission intent')
            db.execute('UPDATE external_tasks SET approval=? WHERE task_id=?', (canonical(approval), task_id))
            db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (task_id, 'approved', canonical(approval)))

    def observe(self, task_id, observation):
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._get(db, task_id)
            value = validate_observation(observation, row['spec'])
            old = row['observation']
            if old and (value['session_id'] != old['session_id'] or value['revision'] < old['revision']
                        or value['revision'] == old['revision'] and canonical(value) != canonical(old)):
                raise ProtocolError('Stale or inconsistent runtime observation')
            from .contract import TERMINAL
            if old and old['state'] in TERMINAL and value != old:
                raise ProtocolError('Runtime changed a terminal task')
            db.execute('UPDATE external_tasks SET observation=?,transport_status=?,last_error=? WHERE task_id=?',
                       (canonical(value), 'acknowledged', '', task_id))
            db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (task_id, 'observed', canonical(value)))
            return self._get(db, task_id)

    def verify(self, task_id, revision, report):
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._get(db, task_id)
            if not row['observation'] or row['observation']['revision'] != revision:
                raise ProtocolError('Verification observation changed')
            db.execute('INSERT INTO external_verifications(task_id,spec_hash,remote_revision,report) VALUES (?,?,?,?)',
                       (task_id, row['spec_hash'], revision, canonical(report)))
            return self._get(db, task_id)

    def pending(self, supervisor_id, runtime_id):
        with self.store._connect() as db:
            ids = [row['task_id'] for row in db.execute('SELECT task_id FROM external_tasks WHERE supervisor_id=? AND runtime_id=?', (supervisor_id, runtime_id))]
            return [self._get(db, value) for value in ids]
