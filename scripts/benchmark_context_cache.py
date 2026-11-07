#!/usr/bin/env python3
"""EFFICIENCY-001: isolated, count-only baseline; no production optimization.

Requires a private workspace snapshot (including a consistent SQLite backup).
The config is read, never rewritten. Only the snapshot is opened by CowAgent.
Live requests are opt-in and use the configured OpenRouter credential in memory.
No raw prompts, responses, tool arguments, credentials, or DB rows are emitted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import copy
from datetime import date, timedelta
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def safe_usage(value):
    """Keep numeric usage data only, including nested provider cache counters."""
    if not isinstance(value, dict):
        return {}
    return {
        key: safe_usage(item) if isinstance(item, dict) else item
        for key, item in value.items()
        if isinstance(item, (int, float, bool, dict)) or item is None
    }


def validate_snapshot(snapshot, active_root):
    """Reject active paths and symlinks before CowAgent can open any database."""
    snapshot, active_root = snapshot.resolve(), active_root.resolve()
    if snapshot == active_root or snapshot in active_root.parents or active_root in snapshot.parents:
        raise ValueError("Snapshot must be separate from active workspace")
    if not snapshot.is_dir() or any(path.is_symlink() for path in snapshot.rglob('*')):
        raise ValueError("Snapshot must be a private directory without symlinks")
    if any(snapshot.rglob('mcp.json')):
        raise ValueError("This audit runner does not start configured MCP subprocesses")
    return snapshot


def historical_case(snapshot):
    db = sqlite3.connect(snapshot / "memory/long-term/index.db")
    db.row_factory = sqlite3.Row
    try:
        selected = None
        for row in db.execute("SELECT * FROM messages WHERE role='assistant' ORDER BY id DESC"):
            usage = json.loads(row["extras"] or "{}").get("usage", {})
            if usage.get("prompt_tokens") == 20208 and usage.get("completion_tokens") == 160:
                selected = row
                break
        if selected is None:
            raise ValueError("The requested baseline is absent from this snapshot")
        rows = db.execute(
            "SELECT role,content FROM messages WHERE agent_id=? AND session_id=? AND seq<=? ORDER BY seq",
            (selected["agent_id"], selected["session_id"], selected["seq"]),
        ).fetchall()
        messages = [{"role": r[0], "content": json.loads(r[1])} for r in rows]
        context = db.execute(
            "SELECT context_usage FROM sessions WHERE agent_id=? AND session_id=?",
            (selected["agent_id"], selected["session_id"]),
        ).fetchone()
        stored_context = json.loads(context[0] or "{}")
        usage = json.loads(selected["extras"])["usage"]
        return messages, {
            "persisted_provider_run_usage": safe_usage(usage),
            "persisted_context_display": stored_context,
            "first_request_input_inferred": usage["prompt_tokens"] - stored_context["used"],
            "second_request_input_from_last_context": stored_context["used"],
            "per_call_raw_provider_payloads_retained": False,
        }
    finally:
        db.close()


def construct(args):
    # Imports happen after private logging configuration; disable all application
    # logging before constructing anything that might log a prompt or response.
    logging.disable(logging.CRITICAL)
    import config
    from agent.protocol.agent import Agent
    from agent.protocol.agent_stream import AgentStreamExecutor, build_tools_schema
    from agent.protocol.accounting import request_snapshot
    from agent.memory.manager import MemoryManager
    from agent.memory.config import MemoryConfig
    from agent.tools import MemoryGetTool, MemorySearchTool
    from agent.registry import set_agent_registry
    from agent.skills import build_skill_manager
    from common.runtime_identity import identity_scope
    from bridge.agent_initializer import AgentInitializer
    from models.chatgpt.chat_gpt_bot import ChatGPTBot
    from scripts.efficiency_metrics import capture_sections, text_metrics as base_metrics, prefix_metrics
    native_tokenizer = None
    if args.tokenizer_json:
        from tokenizers import Tokenizer
        native_tokenizer = Tokenizer.from_file(str(args.tokenizer_json))
    def text_metrics(text):
        metrics = base_metrics(text)
        if native_tokenizer is not None:
            metrics['model_family_tokenizer_proxy_tokens'] = len(
                native_tokenizer.encode(text, add_special_tokens=False).ids
            )
        return metrics

    original = json.loads(args.config.read_text())
    active_root = Path(original["agent_workspace"]).resolve()
    snapshot = validate_snapshot(args.snapshot, active_root)
    settings = copy.deepcopy(original)
    settings["agent_workspace"] = str(snapshot)
    settings["web_file_serve_root"] = str(snapshot)
    config.config = config.Config(settings)
    from common import i18n
    i18n.set_language(settings.get('cow_lang', 'auto'))
    set_agent_registry(None)
    workspace = snapshot / "agents" / args.agent
    manager = MemoryManager(MemoryConfig(workspace_root=str(workspace)), embedding_provider=None)
    from agent.memory import storage as storage_module
    deadline = time.monotonic() + 20
    while str(manager.storage.db_path) in storage_module._maintenance_running:
        if time.monotonic() > deadline:
            raise TimeoutError("Snapshot maintenance did not finish")
        time.sleep(.02)
    initializer = AgentInitializer(None, SimpleNamespace())
    with identity_scope(agent_id=args.agent):
        tools = initializer._load_tools(str(workspace), manager,
                                        [MemorySearchTool(manager), MemoryGetTool(manager)],
                                        session_id="efficiency-audit", host_agent_id=args.agent)
        skills = build_skill_manager(workspace_dir=str(workspace))
        runtime = initializer._get_runtime_info(str(workspace))
        from agent.registry import get_agent_registry
        runtime.update(agent_id=args.agent, agent_name=get_agent_registry().get(args.agent).name,
                       _get_teammates=lambda: [])
        agent = Agent(system_prompt="", tools=tools, model=SimpleNamespace(model=settings["model"]),
                      workspace_dir=str(workspace), skill_manager=skills, memory_manager=manager,
                      runtime_info=runtime, output_mode="logger")
        with capture_sections() as sections:
            system = agent.get_full_system_prompt()
        normalize = lambda text: text.replace(str(snapshot), str(active_root))
        system = normalize(system)
        section_rows = []
        assembled = []
        for section in sections:
            parts = [normalize(part) for part in section["parts"]]
            assembled.extend(parts)
            section_rows.append({"name": section["name"], **text_metrics("\n".join(parts))})
        assert "\n".join(assembled) == system, "Section accounting does not reconstruct final prompt"
        from agent.prompt import PromptBuilder, load_context_files
        initial_prompt = normalize(PromptBuilder(str(workspace), language='zh').build(
            tools=tools, context_files=load_context_files(str(workspace)),
            skill_manager=skills, memory_manager=manager, runtime_info=runtime,
        ))
        agent.system_prompt = initial_prompt
        messages, historical = historical_case(snapshot)
        agent.messages = copy.deepcopy(messages)
        executor = AgentStreamExecutor(agent, agent.model, system, tools, messages=messages[:1])
        selected_tools = executor._select_tools_for_injection()
        schemas = build_tools_schema(selected_tools)
        bot = ChatGPTBot(bot_type=settings["bot_type"])

        def payload(turn_messages, model, prompt=system, stream=True):
            captured = {}
            def capture(params, *_):
                captured.update(copy.deepcopy(params))
                return iter(()) if stream else {}
            with patch.object(bot, '_handle_stream_response', side_effect=capture), \
                 patch.object(bot, '_handle_sync_response', side_effect=capture):
                bot.call_with_tools(turn_messages, tools=schemas, stream=stream,
                                    model=model, system=prompt, temperature=0,
                                    max_tokens=executor._catalog_max_output_tokens())
            if not captured:
                raise ValueError("No Chat Completions payload was constructed")
            return json.loads(json.dumps(captured).replace(str(snapshot), str(active_root)))

        first = payload(messages[:1], settings['model'])
        second = payload(messages[:3], settings['model'])
        again = normalize(agent.get_full_system_prompt())
        files = __import__('agent.prompt', fromlist=['load_context_files']).load_context_files(str(workspace))
        context_rows = [{"name": f.path, **text_metrics(f.content)} for f in files]
        tool_rows = []
        for tool in first.get('tools', []):
            func = tool['function']
            tool_rows.append({"name": func['name'], **text_metrics(canonical(tool))})
        history_rows = [{"index": i, "role": m['role'], **text_metrics(canonical(m))}
                        for i, m in enumerate(first['messages'] + second['messages'][2:])]
        # Field-level tokenization is a transparent proxy, not a provider chat template.
        index_queries = []
        manager.storage.conn.set_trace_callback(
            lambda sql: index_queries.append("fts_match") if " MATCH " in sql.upper() else None
        )
        historical_tool = next(b for m in messages for b in m['content']
                               if b.get('type') == 'tool_use' and b.get('name') == 'memory_search')
        indexed_result = MemorySearchTool(manager).execute(historical_tool['input'])
        manager.storage.conn.set_trace_callback(None)
        assert indexed_result.status == 'success' and index_queries
        accounting = {}
        for name, request, internal in [('first',first,messages[:1]),('second',second,messages[:3])]:
            snapshot = request_snapshot(agent, system, internal, schemas, settings['model'])
            accounting[name] = {
                "wire_json": text_metrics(canonical(request)),
                "system": text_metrics(system),
                "messages_without_system": text_metrics(canonical(request['messages'][1:])),
                "tools": text_metrics(canonical(request['tools'])),
                "diagnostic_estimate": snapshot['estimated_input_tokens'],
                "request_accounting": snapshot,
                "cowagent_history_estimate": sum(agent._estimate_message_tokens(m) for m in internal),
                "payload_sha256": digest(request),
            }
        if args.chat_template:
            if not args.tokenizer_json:
                raise ValueError('A tokenizer JSON is required with a chat template')
            from scripts.efficiency_metrics import model_template_metrics
            for name, body in [('first', first), ('second', second)]:
                accounting[name]['model_family_chat_template'] = model_template_metrics(
                    body, args.tokenizer_json, args.chat_template)
        skill_prompt = normalize(agent.get_skills_prompt())
        date_today = date.today().isoformat()
        date_tomorrow = (date.today() + timedelta(days=1)).isoformat()
        # A simulated date change uses the same material, not a second live run.
        date_rollover = system.replace(date_today, date_tomorrow)
        result = {
            "schema_version": 1,
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "historical_lookup_replay": {"fts_match_executed": bool(index_queries),
                                         "result_success": indexed_result.status == 'success'},
            "source_revision": args.revision,
            "models": args.models,
            "method": {
                "local_tokenizer": "cl100k_base proxy; not the native Nemotron/Gemma tokenizer",
                "provider_component_counts_available": False,
                "optional_model_family_tokenizer": {
                    'label': args.tokenizer_label,
                    'sha256': hashlib.sha256(args.tokenizer_json.read_bytes()).hexdigest(),
                    'add_special_tokens': False,
                    'exact_upstream_chat_template_verified': False,
                } if args.tokenizer_json else None,
                "snapshot_paths_normalized_to_active_paths_in_memory": True,
                "application_logs_disabled": True,
                "database_write_scope": "isolated snapshot only",
                "full_tool_inventory_preserved": True,
                "baseline_reconstruction_limit": "original complete wire payload was not retained; current source and retained conversation used",
                "title_measurement": "application title prompt with plain-chat request args; separate non-streaming request",
                "request_policy": "unmodified adapter tool inventory, two identical first requests per model, at most one memory_search continuation, no retries",
            },
            "historical": historical,
            "cached_initial_prompt": text_metrics(initial_prompt),
            "cached_initial_differs_from_sent_prompt": initial_prompt != system,
            "chart_estimate_with_cached_initial_prompt": agent.get_context_usage(),
            "prompt_sections": section_rows,
            "context_file_bodies": context_rows,
            "skill_catalog": text_metrics(skill_prompt),
            "tool_definitions": tool_rows,
            "message_components": history_rows,
            "requests": accounting,
            "prefix_checks": {
                "rebuilt_system_same_inputs": prefix_metrics(system, again),
                "date_literal_rollover_simulation": prefix_metrics(system, date_rollover),
                "model_switch_simulations": {
                    model: prefix_metrics(system, system.replace(settings['model'], model))
                    for model in args.models
                },
                "first_vs_second_system_identical": first['messages'][0] == second['messages'][0],
                "first_vs_second_tools_identical": first['tools'] == second['tools'],
                "first_messages_are_prefix_of_second": first['messages'] == second['messages'][:len(first['messages'])],
                "system_then_tools_proxy_tokens": text_metrics(system+canonical(first['tools']))['tiktoken_cl100k_base_proxy_tokens'],
            },
            "live": [],
        }
        return result, bot, payload, messages, manager, system


def request_live(config_path, body, limit_seconds=180):
    """One exact body, no automatic retry; raw contents live only in memory."""
    import requests
    cfg = json.loads(config_path.read_text())
    base = cfg.get('custom_api_base','').rstrip('/')
    if base != 'https://openrouter.ai/api/v1':
        raise ValueError('This benchmark only permits the configured OpenRouter endpoint')
    key = cfg.get('custom_api_key')
    if not key:
        raise ValueError('Configured OpenRouter key is missing')
    start = time.monotonic()
    requested_at = datetime.now(timezone.utc).isoformat()
    response = requests.post(base+'/chat/completions',json=body,
                             headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},
                             stream=body.get('stream',False),timeout=(15,limit_seconds))
    receipt = {'request_sha256':digest(body),'http_status':response.status_code,'requested_model':body['model'],
               'requested_at_utc':requested_at,
               'stream':body.get('stream',False),'cache_status_header':response.headers.get('X-OpenRouter-Cache-Status'),
               'usage_raw_numeric':{},'first_delta_seconds':None,
               'retry_after':response.headers.get('Retry-After')}
    content = ''
    calls = {}
    if response.status_code != 200:
        receipt['elapsed_seconds']=round(time.monotonic()-start,3)
        # Deliberately omit untrusted error bodies (may echo prompt/credentials).
        response.close()
        return receipt,None
    try:
        if not body.get('stream'):
            obj=response.json()
            receipt['usage_raw_numeric']=safe_usage(obj.get('usage',{}))
            receipt['response_model']=obj.get('model')
            receipt['provider']=obj.get('provider')
            answer=obj.get('choices',[{}])[0].get('message',{})
            receipt['elapsed_seconds']=round(time.monotonic()-start,3)
            return receipt,answer
        for line in response.iter_lines():
            if time.monotonic()-start>limit_seconds:
                raise TimeoutError('Response deadline exceeded')
            if not line.startswith(b'data:'):continue
            data=line[5:].strip()
            if data==b'[DONE]':break
            obj=json.loads(data)
            if obj.get('error'):
                receipt['stream_error']=True
                break
            if obj.get('usage'):receipt['usage_raw_numeric']=safe_usage(obj['usage'])
            if obj.get('model'):receipt['response_model']=obj['model']
            if obj.get('provider'):receipt['provider']=obj['provider']
            for choice in obj.get('choices',[]):
                delta=choice.get('delta',{})
                if delta and receipt['first_delta_seconds'] is None:
                    receipt['first_delta_seconds']=round(time.monotonic()-start,3)
                content+=delta.get('content') or ''
                for tc in delta.get('tool_calls') or []:
                    item=calls.setdefault(tc['index'],{'id':'','type':'function','function':{'name':'','arguments':''}})
                    if tc.get('id'):item['id']=tc['id']
                    for field in ('name','arguments'):
                        item['function'][field]+=tc.get('function',{}).get(field) or ''
                if choice.get('finish_reason'):receipt['finish_reason']=choice['finish_reason']
        answer={'role':'assistant','content':content}
        if calls:answer['tool_calls']=[calls[k] for k in sorted(calls)]
        receipt['tool_names']=[c['function']['name'] for c in calls.values()]
        receipt['elapsed_seconds']=round(time.monotonic()-start,3)
        return receipt,answer
    finally:
        response.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--agent',default='testpilot')
    parser.add_argument('--revision',default='unknown')
    parser.add_argument('--models',nargs='+',default=['nvidia/nemotron-3.5-super-vl:free','google/gemma-4-26b-a4b-it:free','openrouter/free'])
    parser.add_argument('--tokenizer-json',type=Path)
    parser.add_argument('--chat-template',type=Path)
    parser.add_argument('--tokenizer-label',default='unspecified model-family proxy')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    os.environ['COW_DATA_DIR']=str(args.snapshot.parent/'audit-logs')
    result,bot,build,messages,manager,system=construct(args)
    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    print(json.dumps({'event':'offline_complete','tools':len(result['tool_definitions']),'output':str(args.output)}),flush=True)
    try:
        if args.live:
            from agent.tools import MemorySearchTool
            for model in args.models:
                model_system=system.replace(result['historical']['persisted_context_display']['model'],model)
                body=build(messages[:1],model,prompt=model_system)
                for repetition in range(2):
                    receipt,answer=request_live(args.config,body)
                    receipt.update(kind='memory_first',repeat=repetition)
                    result['live'].append(receipt);save()
                    print(json.dumps({'event':'live_request','model':model,'kind':receipt['kind'],'repeat':repetition,'status':receipt['http_status'],'usage':receipt['usage_raw_numeric'],'seconds':receipt['elapsed_seconds']}),flush=True)
                    if repetition==0 and answer and answer.get('tool_calls'):
                        calls=answer['tool_calls']
                        if len(calls)==1 and calls[0]['function']['name']=='memory_search':
                            tool_args=json.loads(calls[0]['function']['arguments'])
                            tool_result=MemorySearchTool(manager).execute(tool_args)
                            receipt['indexed_memory_search_success']=tool_result.status=='success' and 'Found ' in str(tool_result.result)
                            continuation=copy.deepcopy(body)
                            continuation['messages'] += [answer,{'role':'tool','tool_call_id':calls[0]['id'],'content':str(tool_result.result)}]
                            second,final=request_live(args.config,continuation)
                            second.update(kind='memory_second',repeat=0)
                            result['live'].append(second);save()
                            print(json.dumps({'event':'live_request','model':model,'kind':'memory_second','status':second['http_status'],'usage':second['usage_raw_numeric'],'seconds':second['elapsed_seconds']}),flush=True)
                        else:
                            receipt['non_memory_tools_not_executed']=True;save()
                # Use the application's exact title prompt builder but intercept
                # the bot call; then send the captured title-only body separately.
                from agent.chat import session_service
                title_prompt={}
                def capture_title(prompt,*_):title_prompt['text']=prompt;return 'audit title'
                user_text='\n'.join(b.get('text','') for b in messages[0]['content'] if b.get('type')=='text')
                with patch.object(session_service,'_title_from_primary',side_effect=capture_title):
                    session_service.generate_session_title(user_text)
                title_body={k:v for k,v in bot.args.items() if k not in ['timeout','request_timeout'] and v is not None}
                title_body.update(model=model,messages=[{'role':'user','content':title_prompt['text']}],stream=False)
                title,answer=request_live(args.config,title_body)
                title.update(kind='session_title',repeat=0)
                result['live'].append(title);save()
                print(json.dumps({'event':'live_request','model':model,'kind':'session_title','status':title['http_status'],'usage':title['usage_raw_numeric'],'seconds':title['elapsed_seconds']}),flush=True)
    finally:
        manager.close()
        save()


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Exception messages can contain upstream response text. Do not print them.
        print(json.dumps({'event':'audit_failed','error_type':type(exc).__name__}),file=sys.stderr)
        raise SystemExit(1)
