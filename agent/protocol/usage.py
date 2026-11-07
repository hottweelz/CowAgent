"""Count-only provider usage normalization and aggregation."""

import math


def _number(value, integer=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        return None
    return int(value) if integer else value


def _first(data, *paths):
    for path in paths:
        value = data
        for key in path:
            if not isinstance(value, dict) or key not in value:
                break
            value = value[key]
        else:
            if value is not None:
                return value
    return None


def normalize_usage(raw, *, model=None, provider=None, purpose=None):
    """Normalize one actual response; absent optional metadata stays absent."""
    if not isinstance(raw, dict):
        return {}
    result = {}
    for key, aliases in {
        'prompt_tokens': (('prompt_tokens',), ('input_tokens',)),
        'completion_tokens': (('completion_tokens',), ('output_tokens',)),
    }.items():
        value = _number(_first(raw, *aliases))
        result[key] = value if value is not None else 0
        if value is not None:
            result[key + '_reported_calls'] = 1
    total = _number(raw.get('total_tokens'))
    result['total_tokens'] = total if total is not None else result['prompt_tokens'] + result['completion_tokens']
    optional = {
        'prompt_cache_hit_tokens': (('prompt_cache_hit_tokens',), ('prompt_tokens_details', 'cached_tokens'), ('input_tokens_details', 'cached_tokens'), ('cache_read_input_tokens',)),
        'cache_creation_input_tokens': (('cache_creation_input_tokens',), ('cache_write_input_tokens',), ('prompt_tokens_details', 'cache_write_tokens'), ('input_tokens_details', 'cache_write_tokens')),
        'reasoning_tokens': (('reasoning_tokens',), ('completion_tokens_details', 'reasoning_tokens'), ('output_tokens_details', 'reasoning_tokens')),
        'cost': (('cost',), ('total_cost',)),
    }
    for key, paths in optional.items():
        value = _number(_first(raw, *paths), integer=key != 'cost')
        if value is not None:
            result[key] = value
            result[key + '_reported_calls'] = 1
    if 'prompt_cache_hit_tokens' in result and 'prompt_tokens_reported_calls' in result:
        result['prompt_cache_miss_tokens'] = max(0, result['prompt_tokens'] - result['prompt_cache_hit_tokens'])
    result['calls'] = 1
    for key, value in (('model', model), ('provider', provider), ('purpose', purpose)):
        if isinstance(value, str) and value:
            result[key] = value
    return result


_SUM_FIELDS = frozenset({
    'prompt_tokens', 'completion_tokens', 'total_tokens', 'calls',
    'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens',
    'cache_creation_input_tokens', 'reasoning_tokens', 'cost',
    'prompt_tokens_reported_calls', 'completion_tokens_reported_calls',
    'prompt_cache_hit_tokens_reported_calls',
    'cache_creation_input_tokens_reported_calls',
    'reasoning_tokens_reported_calls', 'cost_reported_calls',
})
_METADATA_FIELDS = {'model', 'provider', 'purpose', 'request_fingerprint', 'requested_model'}
_REQUEST_FIELDS = _SUM_FIELDS | _METADATA_FIELDS


def merge_usage(first, second):
    """Sum known counters and retain sanitized per-call snapshots."""
    result = {}
    requests = []
    for item in (first or {}, second or {}):
        for key in _SUM_FIELDS:
            value = item.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                result[key] = result.get(key, 0) + value
        if isinstance(item.get('requests'), list):
            snapshots = item['requests']
        elif item.get('calls') == 1:
            snapshots = [item]
        else:
            snapshots = []
        for snapshot in snapshots:
            if isinstance(snapshot, dict):
                requests.append({key: value for key, value in snapshot.items()
                                 if key in _REQUEST_FIELDS and
                                 ((key in _METADATA_FIELDS and isinstance(value, str))
                                  or (key in _SUM_FIELDS and isinstance(value, (int, float))
                                      and not isinstance(value, bool)))})
    if requests:
        result['requests'] = requests
    return result
