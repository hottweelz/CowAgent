"""Count-only request accounting. No prompt bodies are retained in snapshots."""
import hashlib
import json


def fingerprint(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def schema_tokens(agent, schemas):
    if not schemas:
        return 0
    text = json.dumps(schemas, ensure_ascii=False)
    estimate = getattr(agent, '_estimate_text_tokens', None)
    if estimate is not None:
        return estimate(text)
    return agent._estimate_message_tokens({'role': 'system', 'content': text})


def request_snapshot(agent, system, messages, schemas, model):
    """Measure the assembled LLMRequest, not a provider-specific chat template."""
    counts = {
        'system': agent._estimate_message_tokens({'role': 'system', 'content': system}) if system else 0,
        'tools': schema_tokens(agent, schemas),
        'history': sum(agent._estimate_message_tokens(m) for m in messages),
    }
    fingerprints = {
        'system': fingerprint(system),
        'tools': fingerprint(schemas or []),
        'history': fingerprint(messages),
        'model': fingerprint(model),
    }
    return {
        'estimated_input_tokens': sum(counts.values()),
        'breakdown': counts,
        'fingerprints': fingerprints,
        'request_fingerprint': fingerprint(fingerprints),
        'model': model,
        'purpose': 'agent',
        'messages': len(messages),
        'estimate_method': 'character_heuristic',
        'accounting_boundary': 'llm_request',
    }
