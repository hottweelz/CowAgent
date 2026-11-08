"""Read-only operator drafts. A review packet is neither a grant nor an attestation.

All observations and identity fields are supplied by the caller. Hashes bind the
draft contents; they do not authenticate an operator or authorize execution.
This module performs no runtime, filesystem, network or journal operations.
"""
import json
import re
import time

from .codex_policy import ANALYSIS_POLICY_REVISION, VERSION as CODEX_VERSION
from .contract import ProtocolError, canonical, digest, finite, normalize_spec

VERSION = 'cow.external.operator-review/1'
_CURRENT_FIELDS = frozenset({
    'cli_version', 'model', 'modelProvider', 'policy_revision',
    'provider_config_sha256', 'config_sha256',
})
_COWAGENT_KIND = 'cowagent-registered/1'
_COWAGENT_FIELDS = frozenset({
    'runtime_kind', 'agent_id', 'model', 'provider', 'config_sha256',
    'profile_sha256', 'source_sha256',
})


def _sha256(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _snapshot(value, *, enrollment=False):
    named = isinstance(value, dict) and 'runtime_kind' in value
    fields = (_COWAGENT_FIELDS if named else _CURRENT_FIELDS) | ({'probe_sha256'} if enrollment else set())
    if not isinstance(value, dict) or set(value) != fields:
        raise ProtocolError('Invalid public enrollment snapshot')
    for key, item in value.items():
        if key.endswith('_sha256'):
            valid = _sha256(item)
        elif not named and key in ('model', 'modelProvider') and item is None:
            valid = True  # Unspecified selection stays owned by the native runtime.
        else:
            valid = isinstance(item, str) and 0 < len(item) <= 128
        if not valid:
            raise ProtocolError('Invalid public enrollment field: ' + key)
    if named and (value['runtime_kind'] != _COWAGENT_KIND or value['agent_id'] not in ('testpilot', 'testpilot2')):
        raise ProtocolError('Unsupported registered CowAgent identity')
    return json.loads(canonical(value))


def _packet(body):
    body = json.loads(canonical(dict(
        body, protocol=VERSION, observation_source='caller_supplied',
        approval_status='not_granted', execution_enabled=False,
        external_actions_enabled=False,
    )))
    return dict(body, review_id=digest(body))


def build_enrollment_review(enrollment, *, current, observed_probe_sha256):
    """Compare supplied fingerprints without opening configuration or credentials.

    A matching digest proves only equality to the supplied snapshot. The actual
    probe receipt, its provenance and fresh effective policy checks still need
    independent review before any later enrollment/approval workflow can use it.
    """
    enrollment = _snapshot(enrollment, enrollment=True)
    current = _snapshot(current)
    if not _sha256(observed_probe_sha256):
        raise ProtocolError('Invalid observed probe fingerprint')
    fields = _COWAGENT_FIELDS if 'runtime_kind' in enrollment else _CURRENT_FIELDS
    if set(current) != fields:
        raise ProtocolError('Enrollment runtime kinds differ')
    reasons = [key + '_mismatch' for key in sorted(fields)
               if enrollment[key] != current[key]]
    if enrollment['probe_sha256'] != observed_probe_sha256:
        reasons.append('probe_sha256_mismatch')
    if fields == _CURRENT_FIELDS and enrollment['cli_version'] != CODEX_VERSION:
        reasons.append('unsupported_cli_version')
    if fields == _CURRENT_FIELDS and enrollment['policy_revision'] != ANALYSIS_POLICY_REVISION:
        reasons.append('unsupported_policy_revision')
    return _packet({
        'kind': 'enrollment', 'enrollment': enrollment, 'current': current,
        'observed_probe_sha256': observed_probe_sha256,
        'status': 'blocked' if reasons else 'review_required', 'reasons': reasons,
    })


def _enrollment_packet(value):
    if not isinstance(value, dict):
        raise ProtocolError('Invalid enrollment review packet')
    try:
        expected = build_enrollment_review(
            value['enrollment'], current=value['current'],
            observed_probe_sha256=value['observed_probe_sha256'],
        )
        if canonical(value) != canonical(expected):
            raise ProtocolError('Enrollment review packet differs from its draft')
    except (KeyError, TypeError, ValueError) as exc:
        raise ProtocolError('Invalid enrollment review packet') from exc
    return expected


def build_task_review(spec, enrollment_review, *, now=None):
    """Bind a bounded analysis draft to identity, proposed authority and criteria.

    This does not authenticate identities, grant authority, observe a worker or
    verify an artifact. Even an unblocked draft remains non-executable.
    """
    now = time.time() if now is None else now
    if not finite(now):
        raise ProtocolError('Invalid review time')
    spec = normalize_spec(spec)
    if (spec['task']['operation'] != 'analyze_records'
            or spec['authority']['operations'] != ['analyze_records']):
        raise ProtocolError('Only bounded analysis authority can be reviewed')
    enrollment_review = _enrollment_packet(enrollment_review)
    payload = json.loads(spec['task']['content'])
    reasons = []
    if ('runtime_kind' in enrollment_review['enrollment'] and
            spec['runtime_id'] != 'cowagent.' + enrollment_review['enrollment']['agent_id']):
        reasons.append('runtime_id_mismatch')
    if enrollment_review['status'] == 'blocked':
        reasons.append('enrollment_blocked')
    if spec['authority']['expires_at'] <= now:
        reasons.append('expired_authority')
    return _packet({
        'kind': 'task', 'reviewed_at': now,
        'identity': {key: spec[key] for key in (
            'task_id', 'idempotency_key', 'owner_id', 'source_id',
            'conversation_id', 'runtime_id',
        )},
        'task_hash': digest(spec),
        'enrollment_review_id': enrollment_review['review_id'],
        'authority': spec['authority'],
        'task': {'operation': spec['task']['operation'], 'artifact': spec['task']['artifact'],
                 'dataset_sha256': digest(payload), 'record_count': len(payload['records'])},
        'verification': {
            'required_checks': ['artifact_schema', 'analysis_result', 'published_artifact_sha256'],
            'caller_contract': spec['verification'],
        },
        'status': 'blocked' if reasons else 'review_required', 'reasons': reasons,
        'execution_status': 'unobserved', 'acceptance_status': 'unverified',
        'external_state_status': 'unverified', 'verified': False,
    })
