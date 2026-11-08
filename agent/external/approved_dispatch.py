"""Atomic approval and one-shot admission in the private operator journal."""
import fcntl
import json
import os
import time
from contextlib import contextmanager

from .contract import ProtocolError, authorize, canonical, digest, normalize_spec
from .journal import ExternalBusy, ExternalJournal


class ApprovalJournal(ExternalJournal):
    def __init__(self, control):
        self.control = control
        super().__init__(control)
        with control._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS external_approval_bindings (
                    task_id TEXT PRIMARY KEY REFERENCES external_tasks(task_id), scope_hash TEXT NOT NULL,
                    task_revision INTEGER NOT NULL, enrollment_revision INTEGER NOT NULL,
                    receipt TEXT NOT NULL, native_intent TEXT, publication_intent TEXT,
                    cancel_status TEXT NOT NULL DEFAULT 'none'
                );
            ''')

    @contextmanager
    def lock(self, task_id):
        from .contract import task_id as valid_id
        if not valid_id(task_id):
            raise ProtocolError('Invalid task ID')
        self.control._guard()
        path = self.control.directory / ('lock-' + digest(task_id))
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            import stat
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != self.control.uid or info.st_mode & 0o077 or info.st_nlink != 1:
                raise ProtocolError('Unsafe task lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ExternalBusy('External task is supervised by another caller') from exc
            yield self.get(task_id)
        finally:
            os.close(fd)

    @staticmethod
    def _scope(spec, credential):
        return {'supervisor_id': credential.supervisor_id, **{k: spec[k] for k in
                ('owner_id', 'source_id', 'conversation_id', 'runtime_id')}}

    def _check(self, db, spec, credential, now, *, approval=None, enrollment=None, binding=False):
        spec = normalize_spec(spec)
        if spec['task']['operation'] != 'analyze_records' or spec['authority']['operations'] != ['analyze_records']:
            raise ProtocolError('Bounded analysis authority required')
        authorize(spec, credential, None, now=now)
        scope = self._scope(spec, credential)
        row = self._get(db, spec['task_id'])
        if row['spec_hash'] != digest(spec) or row['supervisor_id'] != credential.supervisor_id or row['cancel_requested']:
            raise ProtocolError('Task binding differs or is cancelled')
        task = self.control._current(db, 'task-' + spec['task_id'], scope, now)
        enrolled = self.control._current(db, 'enrollment-' + digest(scope), scope, now)
        if not task['approval_current'] or not enrolled['approval_current'] or task['task_hash'] != digest(spec):
            raise ProtocolError('Current task and enrollment approval required')
        receipt = {'protocol': 'cow.external.approved-dispatch/1', 'task_id': spec['task_id'],
                   'task_hash': digest(spec), 'supervisor_id': credential.supervisor_id,
                   'credential_key_id': credential.key_id, 'credential_expires_at': credential.expires_at,
                   'credential_operations': list(credential.operations), 'task_revision': task['revision'], 'enrollment_revision': enrolled['revision'],
                   'enrollment_review_id': enrolled['review_id']}
        if binding and enrollment != enrolled['review']['enrollment']:
            raise ProtocolError('Runtime enrollment differs from approved enrollment')
        if binding:
            stored = db.execute('SELECT * FROM external_approval_bindings WHERE task_id=?', (spec['task_id'],)).fetchone()
            if (stored is None or approval != receipt or row['approval'] != receipt
                    or json.loads(stored['receipt']) != receipt or not row['submission_started']):
                raise ProtocolError('Submission receipt differs from current approval')
            return receipt, stored
        return receipt, None

    def begin_submit(self, task_id, credential):
        with self.control._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            now = time.time()
            row = self._get(db, task_id)
            if row['submission_started'] or row['cancel_requested']:
                raise ProtocolError('Submission already started or cancelled')
            receipt, _ = self._check(db, row['spec'], credential, now)
            scope = self._scope(row['spec'], credential)
            db.execute('INSERT INTO external_approval_bindings(task_id,scope_hash,task_revision,enrollment_revision,receipt) VALUES (?,?,?,?,?)',
                       (task_id, digest(scope), receipt['task_revision'], receipt['enrollment_revision'], canonical(receipt)))
            db.execute("UPDATE external_tasks SET approval=?,submission_started=1,transport_status='sending' WHERE task_id=?", (canonical(receipt), task_id))
            db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (task_id, 'submit_intent', canonical(receipt)))
            return self._get(db, task_id)

    def validate_submission(self, spec, approval, credential, *, enrollment):
        with self.control._connect() as db:
            db.execute('BEGIN')
            self._check(db, spec, credential, time.time(), approval=approval, enrollment=enrollment, binding=True)

    def _intent(self, spec, approval, credential, enrollment, field, **details):
        with self.control._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            receipt, row = self._check(db, spec, credential, time.time(), approval=approval, enrollment=enrollment, binding=True)
            if row[field] is not None or field == 'publication_intent' and row['native_intent'] is None:
                raise ProtocolError('Intent already recorded or native intent missing')
            intent = {'kind': field, 'task_id': spec['task_id'], 'approval_hash': digest(receipt), **details}
            db.execute('UPDATE external_approval_bindings SET ' + field + '=? WHERE task_id=?', (canonical(intent), spec['task_id']))
            db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (spec['task_id'], field, canonical(intent)))
            return intent

    def authorize_native(self, spec, approval, credential, *, enrollment, native_thread, native_session):
        from .contract import identifier
        if not identifier(native_thread) or not identifier(native_session):
            raise ProtocolError('Invalid native identity')
        return self._intent(spec, approval, credential, enrollment, 'native_intent', native_thread=native_thread, native_session=native_session)

    def authorize_publication(self, spec, approval, credential, *, enrollment):
        return self._intent(spec, approval, credential, enrollment, 'publication_intent')

    def should_cancel(self, spec, approval, credential, *, enrollment):
        with self.control._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                self._check(db, spec, credential, time.time(), approval=approval, enrollment=enrollment, binding=True)
                return False
            except (ProtocolError, KeyError, TypeError, ValueError):
                # Fence only the known bound task; malformed callers cannot select
                # another task or supervisor for cancellation.
                if isinstance(spec, dict) and isinstance(approval, dict):
                    tid = spec.get('task_id')
                    row = db.execute('SELECT t.supervisor_id,t.cancel_requested,b.receipt FROM external_tasks t JOIN external_approval_bindings b ON t.task_id=b.task_id WHERE t.task_id=?', (tid,)).fetchone()
                    if (row and not row['cancel_requested'] and row['supervisor_id'] == credential.supervisor_id
                            and json.loads(row['receipt']) == approval):
                        db.execute('UPDATE external_tasks SET cancel_requested=1 WHERE task_id=?', (tid,))
                        db.execute("UPDATE external_approval_bindings SET cancel_status=CASE WHEN cancel_status='none' THEN 'pending' ELSE cancel_status END WHERE task_id=?", (tid,))
                        db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (tid, 'cancel_requested', canonical({'reason': 'approval_unavailable'})))
                return True

    def claim_cancel(self, task_id):
        with self.control._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            result = db.execute("UPDATE external_approval_bindings SET cancel_status='uncertain' WHERE task_id=? AND cancel_status='pending'", (task_id,))
            return bool(result.rowcount)

    def pending_cancellations(self, supervisor_id, runtime_id):
        with self.control._connect() as db:
            return [self._get(db, r['task_id']) for r in db.execute("SELECT t.task_id FROM external_tasks t JOIN external_approval_bindings b ON t.task_id=b.task_id WHERE t.supervisor_id=? AND t.runtime_id=? AND b.cancel_status='pending'", (supervisor_id, runtime_id))]
