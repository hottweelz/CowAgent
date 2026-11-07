"""Independent, read-only artifact checks. Worker claims never certify results."""
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import re

GROUPS = ('acceptance', 'external_state')
TYPES = ('file_exists', 'text_equals', 'json_equals', 'sha256')


class VerificationBusy(RuntimeError):
    pass


CHECK_SCHEMA = {'type': 'object', 'properties': {
    'id': {'type': 'string'}, 'type': {'type': 'string', 'description': ', '.join(TYPES)},
    'path': {'type': 'string'}, 'expected': {}}, 'required': ['id', 'type']}
CONTRACT_SCHEMA = {'type': 'object', 'description':
    'Frozen independent checks. Relative paths use the worker task directory. '
    'Acceptance checks validate output; external_state checks independently read filesystem state. '
    'Missing or unsupported checks remain unverified; remote services are unsupported.',
    'properties': {group: {'type': 'array', 'items': CHECK_SCHEMA} for group in GROUPS}}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def normalize_contract(value):
    """Validate known checks before dispatch; retain unsupported checks as such."""
    value = {} if value is None else value
    if not isinstance(value, dict) or set(value) - set(GROUPS):
        raise ValueError('Invalid verification contract')
    result = {}
    for group in GROUPS:
        checks = value.get(group, [])
        if not isinstance(checks, list):
            raise ValueError('Verification checks must be a list')
        ids = set()
        for check in checks:
            if (not isinstance(check, dict) or not isinstance(check.get('id'), str)
                    or not check['id'] or check['id'] in ids
                    or not isinstance(check.get('type'), str) or not check['type']):
                raise ValueError('Invalid verification check identity')
            ids.add(check['id'])
            if check['type'] not in TYPES:
                continue  # No plug-in dispatch, URL fetch, command or evaluation.
            if (set(check) - {'id', 'type', 'path', 'expected'}
                    or not isinstance(check.get('path'), str) or not check['path'] or '\0' in check['path']):
                raise ValueError('Invalid artifact check')
            kind = check['type']
            if kind == 'file_exists':
                if 'expected' in check and check['expected'] is not True:
                    raise ValueError('file_exists requires a present artifact')
            elif 'expected' not in check:
                raise ValueError('Artifact check requires expected value')
            elif kind == 'text_equals' and not isinstance(check['expected'], str):
                raise ValueError('text_equals requires text')
            elif kind == 'sha256' and (not isinstance(check['expected'], str)
                    or not re.fullmatch('[0-9a-fA-F]{64}', check['expected'])):
                raise ValueError('Invalid SHA-256 expectation')
        result[group] = checks
    return json.loads(_json(result))  # Immutable JSON copy, including finite values.


def outcome_summary(task):
    record = task.get('verification') or {}
    acceptance = record.get('acceptance') or {'status': 'unverified', 'reason': 'no_independent_check'}
    external = record.get('external_state') or {'status': 'unverified', 'reason': 'no_independent_check'}
    return {
        'execution_status': task['state'], 'acceptance_status': acceptance['status'],
        'external_state_status': external['status'],
        'verified': task['state'] == 'completed' and acceptance['status'] == 'passed'
                    and external['status'] == 'confirmed',
        'verification_id': record.get('verification_id'), 'checked_at': record.get('checked_at'),
        'verification_reasons': {'acceptance': acceptance.get('reason', ''),
                                 'external_state': external.get('reason', '')},
    }


def task_result(task):
    result = dict(task.get('result') or {})
    result.update(task_id=task['task_id'], attempt_id=task['attempt_id'], status=task['state'])
    if task.get('error'):
        result['error'] = task['error']
    result.update(outcome_summary(task))
    return result


def format_outcomes(result):
    return ('Execution: ' + result.get('execution_status', result.get('status', 'unknown'))
            + ' · Acceptance: ' + result.get('acceptance_status', 'unverified')
            + ' · External state: ' + result.get('external_state_status', 'unverified'))


def reported_outcomes(result):
    return {key: result[key] for key in ('execution_status', 'acceptance_status', 'external_state_status',
            'verified', 'verification_id', 'checked_at', 'verification_reasons', 'verification_error')
            if key in result}


def checks_failed(result):
    return result.get('acceptance_status') == 'failed' or result.get('external_state_status') == 'failed'


def _check(check, broker, observations, checked_at):
    from agent.permission.filesystem import FileDenied
    evidence = {'id': check['id'], 'type': check['type'], 'observed_at': checked_at,
                'source': 'native_filesystem', 'status': 'unverified'}
    if check['type'] not in TYPES:
        return dict(evidence, reason='unsupported_check', source='unsupported')
    if broker is None:
        return dict(evidence, reason='current_authority_unavailable')
    try:
        # Reuse the same independently read bytes for criteria sharing a file.
        _, _, path = broker.locate(check['path'])
        if path not in observations:
            observations[path] = broker.read(path)
        text = observations[path]
        raw = text.encode('utf-8')
        digest = hashlib.sha256(raw).hexdigest()
        evidence.update(observed_sha256=digest, size_bytes=len(raw))
        kind = check['type']
        if kind == 'file_exists':
            passed = True
        elif kind == 'text_equals':
            passed = text == check['expected']
        elif kind == 'sha256':
            passed = digest == check['expected'].lower()
        else:
            try:
                passed = _json(json.loads(text)) == _json(check['expected'])
            except (ValueError, TypeError, RecursionError):
                return dict(evidence, status='failed', reason='invalid_json_artifact')
        return dict(evidence, status='passed' if passed else 'failed',
                    reason='matched' if passed else 'artifact_mismatch')
    except FileNotFoundError:
        return dict(evidence, status='failed', reason='artifact_missing')
    except FileDenied:
        return dict(evidence, reason='artifact_access_denied')
    except (OSError, UnicodeError):
        return dict(evidence, reason='artifact_unreadable')


def _report(task):
    checked_at = datetime.now(timezone.utc).isoformat()
    report = {'verifier': 'native-file-verifier-v1', 'checked_at': checked_at}
    contract = normalize_contract(task['spec'].get('verification', {}))
    try:
        from agent.permission.filesystem import FileBroker
        from agent.recovery.runtime import _attenuate
        authority, _, _ = _attenuate(task['spec'])
        if 'fs.read' not in authority.capabilities:
            raise ValueError('Artifact read capability unavailable')
        cwd = task['spec'].get('project_dir') or task['spec'].get('workspace_dir')
        broker = FileBroker(authority, cwd)
    except Exception:
        broker = None
    observations = {}
    for group in GROUPS:
        checks = [_check(check, broker, observations, checked_at) for check in contract[group]]
        statuses = {check['status'] for check in checks}
        status = ('failed' if 'failed' in statuses else 'unverified'
                  if not checks or 'unverified' in statuses else 'passed')
        report[group] = {'status': 'confirmed' if group == 'external_state' and status == 'passed' else status,
                         'reason': 'missing_criteria' if not checks else 'checks_' + status,
                         'checks': checks}
    attempt = next(a for a in task['attempts'] if a['attempt_id'] == task['attempt_id'])
    # A claimed successful write is insufficient, and a known denied/failed
    # mutation cannot be hidden by a success summary or a pre-existing artifact.
    failures = [e['effect_id'] for e in attempt['effects'] if isinstance(e.get('result'), dict)
                and e['result'].get('status') == 'error'
                and (e['mutating'] or e['result'].get('permission_denied') or e['result'].get('execution_rejected'))]
    if failures:
        report['acceptance'].update(status='failed', reason='failed_or_denied_tool', effect_ids=failures)
    return report


def verify_task(store, task_id, *, claim=None, force=False):
    """Append independent evidence without changing execution or retrying work."""
    if claim is not None:
        if claim.task_id != task_id or claim._fd is None:
            raise ValueError('Verification execution claim unavailable')
        context = nullcontext(store.get(task_id))
    else:
        context = store.verification_lock(task_id)
    with context as task:
        if task is None:
            raise VerificationBusy('Verification is busy')
        if (task['state'] != 'completed' or claim is not None and task['attempt_id'] != claim.attempt_id):
            raise ValueError('Task execution not completed')
        if task.get('verification') is not None and not force:
            return task
        report = _report(task)
        digest = hashlib.sha256(_json(task['spec'].get('verification', {})).encode('utf-8')).hexdigest()
        if not store.record_verification(task_id, task['attempt_id'], digest, report):
            raise RuntimeError('Verification attempt or contract changed')
        return store.get(task_id)
