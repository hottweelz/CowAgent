"""Versioned, authenticated external-runtime wire contract; no provider secrets."""
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import re
import time
import uuid

VERSION = 'cow.external/1'
ACTIONS = ('discover', 'submit', 'status', 'cancel', 'result')
LEGACY_OPERATIONS = ('write_artifact', 'record_effect')
OPERATIONS = LEGACY_OPERATIONS + ('analyze_records',)
STATES = ('queued', 'running', 'completed', 'cancelled', 'failed', 'needs_review')
TERMINAL = frozenset({'completed', 'cancelled', 'failed', 'needs_review'})
MAX_MESSAGE_BYTES = 1024 * 1024


class ProtocolError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def identifier(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value))


def task_id(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class Credential:
    """Explicit out-of-band enrollment. Never serialize this object to a task."""
    supervisor_id: str
    runtime_id: str
    key_id: str
    secret: bytes = field(repr=False)
    expires_at: float = 0
    operations: tuple = LEGACY_OPERATIONS

    def __post_init__(self):
        if (not all(identifier(v) for v in (self.supervisor_id, self.runtime_id, self.key_id))
                or not isinstance(self.secret, bytes) or len(self.secret) < 32
                or not finite(self.expires_at) or not set(self.operations) <= set(OPERATIONS)):
            raise ProtocolError('Invalid enrollment')
        object.__setattr__(self, 'operations', tuple(self.operations))


def envelope(credential, action, payload, *, request_id=None, kind='request', now=None):
    now = time.time() if now is None else now
    if action not in ACTIONS or kind not in ('request', 'response') or now >= credential.expires_at:
        raise ProtocolError('Credential expired or unsupported operation')
    value = {'protocol': VERSION, 'kind': kind, 'request_id': request_id or str(uuid.uuid4()),
             'supervisor_id': credential.supervisor_id, 'runtime_id': credential.runtime_id,
             'key_id': credential.key_id, 'issued_at': now,
             'expires_at': min(now + 30, credential.expires_at), 'action': action, 'payload': payload}
    value['mac'] = hmac.new(credential.secret, canonical(value).encode(), hashlib.sha256).hexdigest()
    return value


def authenticate(value, credential, *, kind, request_id=None, action=None, now=None):
    now = time.time() if now is None else now
    keys = {'protocol', 'kind', 'request_id', 'supervisor_id', 'runtime_id', 'key_id',
            'issued_at', 'expires_at', 'action', 'payload', 'mac'}
    if not isinstance(value, dict) or set(value) != keys or not isinstance(value.get('mac'), str):
        raise ProtocolError('Invalid envelope')
    unsigned = {k: v for k, v in value.items() if k != 'mac'}
    expected = hmac.new(credential.secret, canonical(unsigned).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, value['mac']):
        raise ProtocolError('Authentication failed')
    if (value['protocol'] != VERSION or value['kind'] != kind
            or value['supervisor_id'] != credential.supervisor_id
            or value['runtime_id'] != credential.runtime_id or value['key_id'] != credential.key_id
            or not task_id(value['request_id']) or value['action'] not in ACTIONS
            or request_id is not None and value['request_id'] != request_id
            or action is not None and value['action'] != action):
        raise ProtocolError('Envelope identity mismatch')
    issued, expiry = value['issued_at'], value['expires_at']
    if (not finite(issued) or not finite(expiry) or issued > now + 5 or expiry <= now
            or expiry > issued + 30 or expiry > credential.expires_at or credential.expires_at <= now):
        raise ProtocolError('Expired envelope or credential')
    if not isinstance(value['payload'], dict):
        raise ProtocolError('Invalid payload')
    return value['payload']


def normalize_spec(spec):
    """No arbitrary paths, runtime session choice, model or credential fields."""
    if not isinstance(spec, dict) or set(spec) != {
        'task_id', 'idempotency_key', 'owner_id', 'source_id', 'conversation_id',
        'runtime_id', 'task', 'authority', 'verification',
    }:
        raise ProtocolError('Invalid task specification')
    if (not task_id(spec['task_id']) or not all(identifier(spec[k]) for k in
            ('idempotency_key', 'owner_id', 'source_id', 'conversation_id', 'runtime_id'))):
        raise ProtocolError('Invalid task identity')
    task = spec['task']
    if (not isinstance(task, dict) or set(task) != {'operation', 'artifact', 'content'}
            or task['operation'] not in OPERATIONS or not identifier(task['artifact'])
            or task['artifact'] in ('.', '..') or not isinstance(task['content'], str)
            or len(task['content'].encode('utf-8')) > 65536):
        raise ProtocolError('Unsupported external task')
    auth = spec['authority']
    if (not isinstance(auth, dict) or set(auth) != {'operations', 'resource', 'expires_at'}
            or not isinstance(auth['operations'], list) or not set(auth['operations']) <= set(OPERATIONS)
            or task['operation'] not in auth['operations'] or auth['resource'] != spec['task_id']
            or not finite(auth['expires_at'])):
        raise ProtocolError('Invalid task authority')
    from agent.recovery.verification import normalize_contract
    value = json.loads(canonical(spec))
    if task['operation'] == 'analyze_records':
        from .analysis import normalize_payload
        value['task']['content'] = canonical(normalize_payload(task['content']))
    value['verification'] = normalize_contract(value['verification'])
    return value


def authorize(spec, credential, approval, *, now=None):
    now = time.time() if now is None else now
    spec = normalize_spec(spec)
    if (spec['runtime_id'] != credential.runtime_id or credential.expires_at <= now
            or spec['authority']['expires_at'] <= now
            or not set(spec['authority']['operations']) <= set(credential.operations)):
        raise ProtocolError('Task authority unavailable')
    if spec['task']['operation'] == 'record_effect':
        if (not isinstance(approval, dict) or set(approval) != {'task_hash', 'approved_by', 'expires_at'}
                or approval['task_hash'] != digest(spec) or not identifier(approval['approved_by'])
                or not finite(approval['expires_at']) or approval['expires_at'] <= now
                or approval['expires_at'] > spec['authority']['expires_at']):
            raise ProtocolError('Explicit effect approval required')
    return spec


def validate_observation(value, spec):
    fields = {'task_id', 'task_hash', 'runtime_id', 'session_id', 'revision', 'state',
              'cancel_requested', 'termination_confirmed', 'result', 'reason'}
    if (not isinstance(value, dict) or set(value) != fields or value['task_id'] != spec['task_id']
            or value['task_hash'] != digest(spec) or value['runtime_id'] != spec['runtime_id']
            or not identifier(value['session_id']) or type(value['revision']) is not int
            or value['revision'] < 1 or value['state'] not in STATES
            or type(value['cancel_requested']) is not bool or type(value['termination_confirmed']) is not bool
            or not isinstance(value['reason'], str)
            or value['result'] is not None and not isinstance(value['result'], dict)):
        raise ProtocolError('Invalid task observation')
    if value['termination_confirmed'] != (value['state'] in TERMINAL):
        raise ProtocolError('Termination does not match execution state')
    return json.loads(canonical(value))


def validate_discovery(value, credential):
    if (not isinstance(value, dict) or value.get('protocol') != VERSION
            or value.get('runtime_id') != credential.runtime_id
            or not isinstance(value.get('name'), str) or not isinstance(value.get('model'), str)
            or value.get('session_ownership') != 'runtime' or value.get('cancellation') != 'cooperative'
            or not task_id(value.get('epoch')) or not isinstance(value.get('operations'), list)
            or not set(value['operations']) <= set(OPERATIONS)
            or not isinstance(value.get('approval_operations'), list)
            or not set(value['approval_operations']) <= set(value['operations'])):
        raise ProtocolError('Unsupported runtime capabilities')
    return value
