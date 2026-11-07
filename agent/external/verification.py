"""Independent enrolled export/fixture-ledger observation; never trust runtime prose."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from agent.permission.authority import Authority
from agent.permission.filesystem import FileBroker
from agent.recovery.verification import _check, TYPES


class ExternalVerifier:
    def __init__(self, export_root, *, synthetic_effect_db=None):
        self.export_root = Path(export_root).resolve()
        self.synthetic_effect_db = Path(synthetic_effect_db).resolve() if synthetic_effect_db else None

    def verify(self, task):
        now = datetime.now(timezone.utc).isoformat()
        spec = task['spec']
        root = self.export_root / spec['task_id']
        authority = Authority('read-only', frozenset({'fs.read'}), (str(root),), ())
        broker = FileBroker(authority, str(root))
        report = {'verifier': 'external-export-v1', 'checked_at': now,
                  'remote_revision': task['observation']['revision'] if task['observation'] else None}
        observed = {}
        for group in ('acceptance', 'external_state'):
            checks = []
            for check in spec['verification'][group]:
                if check['type'] == 'synthetic_effect' and group == 'external_state':
                    result = self._effect(check, spec, now)
                elif check['type'] in TYPES:
                    result = _check(check, broker, observed, now)
                else:
                    result = {'id': check['id'], 'status': 'unverified', 'reason': 'unsupported_check'}
                checks.append(result)
            statuses = {c['status'] for c in checks}
            status = 'failed' if 'failed' in statuses else 'unverified' if not checks or 'unverified' in statuses else 'passed'
            report[group] = {'status': 'confirmed' if group == 'external_state' and status == 'passed' else status,
                             'checks': checks}
        return report

    def _effect(self, check, spec, now):
        result = {'id': check['id'], 'source': 'independent_synthetic_ledger', 'observed_at': now,
                  'status': 'unverified', 'reason': 'verifier_not_enrolled'}
        if self.synthetic_effect_db is None:
            return result
        if set(check) != {'id', 'type', 'expected'} or not isinstance(check['expected'], str):
            return dict(result, reason='unsupported_effect_check')
        try:
            # The path is operator enrolled, never taken from a worker response.
            with sqlite3.connect(self.synthetic_effect_db.as_uri() + '?mode=ro', uri=True) as db:
                row = db.execute('SELECT content FROM effects WHERE task_id=?', (spec['task_id'],)).fetchone()
            passed = row is not None and row[0] == check['expected']
            return dict(result, status='passed' if passed else 'failed', reason='matched' if passed else 'effect_missing_or_mismatched')
        except sqlite3.Error:
            return dict(result, reason='independent_observer_unavailable')
