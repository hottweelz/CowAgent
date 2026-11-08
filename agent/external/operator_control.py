"""Local account decisions only: no dispatch, credential access or runtime calls.

The private directory's owning POSIX account is the operator. Same-account code
is trusted; this does not establish human presence or provide an OS sandbox.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import stat
import time

from .contract import MAX_MESSAGE_BYTES, ProtocolError, canonical, digest, finite, identifier, task_id
from .operator_review import _enrollment_packet, build_task_review

VERSION = 'cow.external.operator-command/1'
_SCOPE = frozenset({'supervisor_id', 'owner_id', 'source_id', 'conversation_id', 'runtime_id'})
_PAYLOADS = {
    'enroll': {'review', 'expires_at'},
    'approve_task': {'spec', 'enrollment_revision', 'task_review_id', 'reviewed_at', 'expires_at'},
    'revoke_enrollment': set(),
    'revoke_task': {'task_id'},
}


def _scope(value):
    if not isinstance(value, dict) or set(value) != _SCOPE or not all(identifier(v) for v in value.values()):
        raise ProtocolError('Invalid operator scope')
    return dict(value)


def _now(value):
    value = time.time() if value is None else value
    try:
        valid = finite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ProtocolError('Invalid decision time')
    return value


def _revision(value):
    return type(value) is int and value >= 0


def _disabled(value):
    return dict(value, execution_enabled=False, external_actions_enabled=False)


class OperatorControl:
    """Explicit private local journal; construction never enables an adapter."""

    def __init__(self, state_dir, *, initialize=False):
        if not hasattr(os, 'geteuid') or os.getuid() != os.geteuid():
            raise ProtocolError('Operator control requires an ordinary POSIX account')
        self.uid = os.getuid()
        self.directory = Path(state_dir)
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise ProtocolError('Operator state path must be canonical and absolute')
        self._ancestors()
        if initialize:
            self.directory.mkdir(mode=0o700, exist_ok=True)
        self.path = self.directory / 'operator.db'
        self._guard(allow_missing=initialize)
        if initialize:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(fd)
        with self._connect() as db:
            if initialize:
                mode = db.execute('PRAGMA journal_mode=WAL').fetchone()[0]
                if mode.lower() != 'wal':
                    raise ProtocolError('Operator journal requires WAL')
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS operator_metadata (
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                        version INTEGER NOT NULL, owner_uid INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS operator_state (
                        target_id TEXT PRIMARY KEY, scope_hash TEXT NOT NULL,
                        revision INTEGER NOT NULL, body TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS operator_decisions (
                        sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                        request_hash TEXT NOT NULL, scope_hash TEXT NOT NULL,
                        receipt TEXT NOT NULL
                    );
                ''')
                db.execute('INSERT OR IGNORE INTO operator_metadata VALUES (1,1,?)', (self.uid,))
            metadata = db.execute('SELECT version,owner_uid FROM operator_metadata WHERE singleton=1').fetchone()
            if metadata is None or tuple(metadata) != (1, self.uid):
                raise ProtocolError('Operator journal identity or version differs')
            if db.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'wal':
                raise ProtocolError('Operator journal requires WAL')

    def _ancestors(self):
        # A private leaf is insufficient if another account can replace it.
        # Root/account-owned sticky shared ancestors (such as /private/tmp)
        # protect the next root/account-owned path component from other users.
        for parent in self.directory.parents:
            value = parent.lstat()
            if (not stat.S_ISDIR(value.st_mode) or value.st_uid not in (0, self.uid)
                    or value.st_mode & 0o022 and not value.st_mode & stat.S_ISVTX):
                raise ProtocolError('Operator state ancestors are not trusted')

    def _guard(self, *, allow_missing=False):
        if os.getuid() != self.uid or os.geteuid() != self.uid:
            raise ProtocolError('Operator account changed')
        self._ancestors()
        try:
            directory = self.directory.lstat()
        except FileNotFoundError as exc:
            raise ProtocolError('Operator state directory is not initialized') from exc
        if (self.directory.resolve() != self.directory or not stat.S_ISDIR(directory.st_mode)
                or directory.st_uid != self.uid or directory.st_mode & 0o077):
            raise ProtocolError('Operator state directory is not private and owned')
        for path in (self.path, *(Path(str(self.path) + suffix) for suffix in ('-wal', '-shm', '-journal'))):
            # SQLite removes WAL/SHM when its last connection closes. Some
            # filesystems can report an already-unlinked inode during lstat.
            # Recheck only that transient sidecar case; every extant result is
            # still subject to all ownership, mode, type and link checks.
            for attempt in range(4):
                try:
                    value = path.lstat()
                except FileNotFoundError:
                    if path == self.path and not allow_missing:
                        raise ProtocolError('Operator journal is not initialized')
                    break
                if (not stat.S_ISREG(value.st_mode) or value.st_uid != self.uid
                        or value.st_mode & 0o077):
                    raise ProtocolError('Operator journal files are not private and owned')
                if value.st_nlink == 1:
                    break
                if path == self.path or value.st_nlink != 0 or attempt == 3:
                    raise ProtocolError('Operator journal files are not private and owned')

    @contextmanager
    def _connect(self):
        self._guard()
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
    def _row(db, target, scope):
        row = db.execute('SELECT * FROM operator_state WHERE target_id=?', (target,)).fetchone()
        if row is None:
            return None
        if row['scope_hash'] != digest(scope):
            raise ProtocolError('Decision belongs to another caller scope')
        return json.loads(row['body'])

    def _current(self, db, target, scope, now):
        row = self._row(db, target, scope)
        if row is None:
            return _disabled({'target_id': target, 'revision': 0, 'approval_status': 'missing',
                              'approval_current': False})
        status = row['decision']
        if status == 'approved' and row['expires_at'] <= now:
            status = 'expired'
        if status == 'approved' and row['kind'] == 'task':
            enrollment = self._row(db, 'enrollment-' + digest(scope), scope)
            if (enrollment is None or enrollment['decision'] != 'approved'
                    or enrollment['revision'] != row['enrollment_revision']
                    or enrollment['review_id'] != row['enrollment_review_id']):
                status = 'enrollment_changed'
            elif enrollment['expires_at'] <= now:
                status = 'enrollment_expired'
        return _disabled(dict(row, approval_status=status, approval_current=status == 'approved'))

    @staticmethod
    def _command(request):
        if (not isinstance(request, dict) or set(request) != {
                'protocol', 'request_id', 'action', 'scope', 'expected_revision', 'payload'}
                or request['protocol'] != VERSION or not task_id(request['request_id'])
                or not isinstance(request['action'], str) or request['action'] not in _PAYLOADS
                or not _revision(request['expected_revision'])):
            raise ProtocolError('Invalid operator command')
        _scope(request['scope'])
        payload = request['payload']
        if not isinstance(payload, dict) or set(payload) != _PAYLOADS[request['action']]:
            raise ProtocolError('Invalid operator command payload')
        raw = canonical(request)
        if len(raw.encode()) > MAX_MESSAGE_BYTES:
            raise ProtocolError('Operator command exceeds protocol limit')
        return json.loads(raw)

    def apply(self, request, *, now=None):
        """Record an explicit decision; repeated requests never reapply a grant."""
        try:
            return self._apply(request, now=now)
        except ProtocolError:
            raise
        except (TypeError, KeyError, ValueError, OverflowError) as exc:
            raise ProtocolError('Invalid operator command payload') from exc

    def _apply(self, request, *, now=None):
        request = self._command(request)
        scope, action, payload = request['scope'], request['action'], request['payload']
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            # A writer can wait for another process. Check expiry after ownership.
            now = _now(now)
            old = db.execute('SELECT * FROM operator_decisions WHERE request_id=?', (request['request_id'],)).fetchone()
            if old:
                if old['request_hash'] != digest(request):
                    raise ProtocolError('Operator request ID conflicts')
                receipt = json.loads(old['receipt'])
                return {'receipt': receipt, 'duplicate': True,
                        'current': self._current(db, receipt['target_id'], scope, now)}
            if action in ('enroll', 'revoke_enrollment'):
                target = 'enrollment-' + digest(scope)
            elif action == 'revoke_task':
                if not task_id(payload['task_id']):
                    raise ProtocolError('Invalid task ID')
                target = 'task-' + payload['task_id']
            else:
                spec = payload['spec']
                if not isinstance(spec, dict) or not task_id(spec.get('task_id')):
                    raise ProtocolError('Invalid task ID')
                target = 'task-' + spec['task_id']
            current = self._row(db, target, scope)
            revision = current['revision'] if current else 0
            if request['expected_revision'] != revision:
                raise ProtocolError('Stale operator decision revision')
            if action.startswith('revoke_'):
                if current is None:
                    raise ProtocolError('No decision to revoke')
                body = dict(current, decision='revoked')
            elif action == 'enroll':
                review = _enrollment_packet(payload['review'])
                if review['status'] != 'review_required':
                    raise ProtocolError('Enrollment review is blocked')
                body = {'kind': 'enrollment', 'decision': 'approved', 'review': review,
                        'review_id': review['review_id'], 'expires_at': payload['expires_at']}
            else:
                enrollment = self._current(db, 'enrollment-' + digest(scope), scope, now)
                if (not enrollment['approval_current'] or not _revision(payload['enrollment_revision'])
                        or payload['enrollment_revision'] != enrollment['revision']):
                    raise ProtocolError('Current enrollment approval is required')
                if (not finite(payload['reviewed_at']) or payload['reviewed_at'] > now
                        or any(spec.get(key) != scope[key] for key in _SCOPE - {'supervisor_id'})):
                    raise ProtocolError('Task review identity or time differs')
                review = build_task_review(spec, enrollment['review'], now=payload['reviewed_at'])
                if review['status'] != 'review_required' or review['review_id'] != payload['task_review_id']:
                    raise ProtocolError('Task review differs or is blocked')
                if current and current['task_hash'] != review['task_hash']:
                    raise ProtocolError('Task identity is bound to another specification')
                if (not finite(payload['expires_at']) or payload['expires_at'] > enrollment['expires_at']
                        or payload['expires_at'] > review['authority']['expires_at']):
                    raise ProtocolError('Task approval exceeds authority expiry')
                body = {'kind': 'task', 'decision': 'approved', 'review': review,
                        'review_id': review['review_id'], 'task_hash': review['task_hash'],
                        'enrollment_review_id': enrollment['review_id'],
                        'enrollment_revision': enrollment['revision'], 'expires_at': payload['expires_at']}
            if not action.startswith('revoke_') and (not finite(body['expires_at']) or body['expires_at'] <= now):
                raise ProtocolError('Approval expiry must be in the future')
            body.update(target_id=target, scope=scope, revision=revision + 1,
                        operator_uid=self.uid, decided_at=now)
            body = _disabled(body)
            receipt = _disabled({'request_id': request['request_id'], 'action': action,
                                 'target_id': target, 'revision': revision + 1, 'operator_uid': self.uid,
                                 'recorded_at': now, 'decision': body['decision'],
                                 'review_id': body['review_id'], 'historical': True,
                                 'snapshot': body})
            db.execute('INSERT INTO operator_state VALUES (?,?,?,?) '
                       'ON CONFLICT(target_id) DO UPDATE SET revision=excluded.revision,body=excluded.body',
                       (target, digest(scope), revision + 1, canonical(body)))
            # Fence bound work atomically with the changed decision.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='external_approval_bindings'").fetchone():
                if action in ('enroll', 'revoke_enrollment'):
                    bound = db.execute('SELECT task_id FROM external_approval_bindings WHERE scope_hash=?', (digest(scope),)).fetchall()
                else:
                    bound = db.execute('SELECT task_id FROM external_approval_bindings WHERE scope_hash=? AND task_id=?', (digest(scope), target[5:])).fetchall()
                for item in bound:
                    tid = item['task_id']
                    db.execute('UPDATE external_tasks SET cancel_requested=1 WHERE task_id=?', (tid,))
                    db.execute("UPDATE external_approval_bindings SET cancel_status=CASE WHEN cancel_status='none' THEN 'pending' ELSE cancel_status END WHERE task_id=?", (tid,))
                    db.execute('INSERT INTO external_events(task_id,kind,body) VALUES (?,?,?)', (tid, 'cancel_requested', canonical({'reason': 'operator_decision_changed'})))
            db.execute('INSERT INTO operator_decisions(request_id,request_hash,scope_hash,receipt) VALUES (?,?,?,?)',
                       (request['request_id'], digest(request), digest(scope), canonical(receipt)))
            return {'receipt': receipt, 'duplicate': False, 'current': self._current(db, target, scope, now)}

    def status(self, scope, *, task_id=None, now=None):
        scope = _scope(scope)
        if task_id is not None:
            from .contract import task_id as valid_task_id
            if not valid_task_id(task_id):
                raise ProtocolError('Invalid task ID')
        target = 'task-' + task_id if task_id is not None else 'enrollment-' + digest(scope)
        with self._connect() as db:
            # One snapshot covers the task approval and its enrollment revision.
            db.execute('BEGIN')
            return self._current(db, target, scope, _now(now))

    def audit(self, scope):
        scope = _scope(scope)
        with self._connect() as db:
            return [dict(json.loads(row['receipt']), sequence=row['sequence']) for row in db.execute(
                'SELECT sequence,receipt FROM operator_decisions WHERE scope_hash=? ORDER BY sequence', (digest(scope),)
            )]
