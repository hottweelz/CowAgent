#!/usr/bin/env python3
"""Count-only Phase 3 comparison on a private workspace copy; live calls opt in.

Uses the existing audit's request capture and indexed-memory case. It never
changes provider routing or writes raw prompts, responses or credentials.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.benchmark_context_cache import construct, digest, request_live  # noqa: E402
from scripts.efficiency_metrics import (  # noqa: E402
    model_template_metrics, model_template_prefix_metrics, prefix_metrics,
)


def baseline_module(revision, relative_path, name):
    """Load the specified local source baseline, not code from the network."""
    source = subprocess.check_output(['git', 'show', f'{revision}:{relative_path}'], cwd=REPO, text=True)
    module = ModuleType(name)
    module.__file__ = str(REPO / relative_path)
    sys.modules[name] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module


def clock_for(day):
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(day.year, day.month, day.day, 12, tzinfo=tz)
    return FixedClock


def prepare(args):
    from agent.prompt import builder
    from agent.skills import formatter, manager as skills_module

    baseline = baseline_module(args.baseline, 'agent/prompt/builder.py', '_prefix_baseline_builder')
    old_formatter = baseline_module(args.baseline, 'agent/skills/formatter.py', '_prefix_baseline_skills')
    captured = []
    original = builder.PromptBuilder.build

    def capture(instance, **kwargs):
        captured.append(dict(kwargs, workspace_dir=instance.workspace_dir, language=instance.language))
        return original(instance, **kwargs)

    with patch.object(builder.PromptBuilder, 'build', capture):
        _, _, payload, messages, manager, _ = construct(args)
    config = json.loads(args.config.read_text())
    assert config['model'] == args.models[0], 'Use the configured Nemotron model unchanged'
    active_root = config['agent_workspace']
    normalize = lambda text: text.replace(str(args.snapshot.resolve()), active_root)
    kwargs = captured[0]
    day = datetime.now().date()
    bodies = {}
    systems = {}
    for label, module in [('before', baseline), ('after', builder)]:
        systems[label] = []
        for offset in (0, 1):
            with patch('datetime.datetime', clock_for(day + timedelta(days=offset))):
                if label == 'before':
                    with patch.object(skills_module, 'format_skill_entries_for_prompt', old_formatter.format_skill_entries_for_prompt), \
                         patch.object(formatter, 'format_unavailable_skills_for_prompt', old_formatter.format_unavailable_skills_for_prompt):
                        system = module.build_agent_system_prompt(**kwargs)
                else:
                    system = module.build_agent_system_prompt(**kwargs)
                    assert system == module.build_agent_system_prompt(**kwargs)
                systems[label].append(normalize(system))
        bodies[label] = [payload(messages[:1], args.models[0], prompt=system) for system in systems[label]]

    for offset in (0, 1):
        assert Counter(systems['before'][offset].split('\n')) == Counter(systems['after'][offset].split('\n'))
        left, right = bodies['before'][offset], bodies['after'][offset]
        assert len(left['tools']) == 16
        assert {k: v for k, v in left.items() if k != 'messages'} == {k: v for k, v in right.items() if k != 'messages'}
        assert left['messages'][1:] == right['messages'][1:]

    result = {
        'schema_version': 1, 'baseline_revision': args.baseline,
        'source_revision': args.revision, 'model': args.models[0],
        'controlled_dates': [day.isoformat(), (day + timedelta(days=1)).isoformat()],
        'same_instruction_lines': True, 'same_16_tool_schemas': True,
        'same_non_system_messages': True, 'same_request_options': True,
        'new_provider_or_cache_fields': False, 'same_input_builds_identical': True,
        'tokenizer_sha256': hashlib.sha256(args.tokenizer_json.read_bytes()).hexdigest(),
        'template_sha256': hashlib.sha256(args.chat_template.read_bytes()).hexdigest(),
        'measurements': {}, 'live': [],
    }
    for label in bodies:
        a, b = bodies[label]
        result['measurements'][label] = {
            'first_request_sha256': digest(a), 'tools_sha256': digest(a['tools']),
            'request_options_sha256': digest({k: v for k, v in a.items() if k not in ('messages', 'tools')}),
            'system_day_rollover': prefix_metrics(*systems[label]),
            'full_template_day_rollover': model_template_prefix_metrics(a, b, args.tokenizer_json, args.chat_template),
            'first_request_template': model_template_metrics(a, args.tokenizer_json, args.chat_template),
        }
    return result, bodies, manager


def measure_live(args, result, bodies, manager, save):
    from agent.tools import MemorySearchTool
    from agent.protocol.usage import normalize_usage

    def call(body, version, kind):
        receipt, answer = request_live(args.config, body, limit_seconds=120)
        receipt.update(version=version, kind=kind, tool_count=len(body['tools']))
        receipt['normalized_usage'] = normalize_usage(receipt['usage_raw_numeric'])
        result['live'].append(receipt)
        save()
        print(json.dumps({'event': 'provider_request', 'version': version, 'kind': kind,
                          'status': receipt['http_status'], 'usage': receipt['usage_raw_numeric']}), flush=True)
        if receipt['http_status'] != 200 or not answer or receipt.get('stream_error'):
            raise RuntimeError('Provider unavailable; no automatic retry')
        assert receipt.get('response_model') == args.models[0]
        raw = receipt['usage_raw_numeric'].get('prompt_tokens_details', {})
        if 'cached_tokens' in raw:
            assert receipt['normalized_usage']['prompt_cache_hit_tokens'] == raw['cached_tokens']
        return receipt, answer

    for version, (body, rollover) in bodies.items():
        receipt, answer = call(body, version, 'first')
        calls = answer.get('tool_calls', [])
        assert len(calls) == 1 and calls[0]['function']['name'] == 'memory_search'
        arguments = json.loads(calls[0]['function']['arguments'])
        trace = []
        fts_rows = []
        original_fts = manager.storage._search_fts5

        def observed_fts(*a, **kw):
            rows = original_fts(*a, **kw)
            fts_rows.append(len(rows))
            return rows

        manager.storage.conn.set_trace_callback(lambda sql: trace.append(True) if ' MATCH ' in sql.upper() else None)
        try:
            with patch.object(manager.storage, '_search_fts5', side_effect=observed_fts), \
                 patch.object(manager.storage, '_search_like', wraps=manager.storage._search_like) as like:
                found = MemorySearchTool(manager).execute(arguments)
                receipt['like_search_calls'] = like.call_count
        finally:
            manager.storage.conn.set_trace_callback(None)
        receipt['fts_result_rows'] = fts_rows
        receipt['indexed_memory_success'] = (found.status == 'success' and 'Found ' in str(found.result)
                                             and bool(trace) and sum(fts_rows) > 0 and like.call_count == 0)
        assert receipt['indexed_memory_success']
        continuation = copy.deepcopy(body)
        continuation['messages'] += [answer, {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': str(found.result)}]
        final_receipt, final = call(continuation, version, 'continuation')
        final_receipt['answered_after_indexed_result'] = bool(final.get('content')) and not final.get('tool_calls')
        assert final_receipt['answered_after_indexed_result']
        for kind, current in [('identical_repeat', body), ('date_rollover', rollover)]:
            item, selected = call(current, version, kind)
            item['selected_memory_search'] = [c['function']['name'] for c in selected.get('tool_calls', [])] == ['memory_search']
            assert item['selected_memory_search']
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tokenizer-json', type=Path, required=True)
    parser.add_argument('--chat-template', type=Path, required=True)
    parser.add_argument('--baseline', default='0ce6dfef')
    parser.add_argument('--revision', default='working-tree')
    parser.add_argument('--agent', default='testpilot')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    args.models = ['nvidia/nemotron-3.5-super-vl:free']
    args.tokenizer_label = 'pinned public NVIDIA template proxy; provider template unconfirmed'
    os.environ['COW_DATA_DIR'] = str(args.snapshot.parent / 'prefix-audit-data')
    logging.disable(logging.CRITICAL)
    result, bodies, manager = prepare(args)

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')

    try:
        save()
        print(json.dumps({'event': 'offline_complete', 'measurements': result['measurements']}), flush=True)
        if args.live:
            measure_live(args, result, bodies, manager, save)
    finally:
        manager.close()
        save()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'event': 'benchmark_failed', 'error_type': type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
