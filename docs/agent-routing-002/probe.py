"""Audit client for the existing localhost console. Never starts a server.

One submit intent is saved before HTTP POST. Observation reconnects to that
request with its SSE cursor; it never resubmits after a lost response.
Only new experimental session/task metadata and sanitized events are retained.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:9899'
HERE = Path(__file__).resolve().parent


def request(route, data=None):
    req = urllib.request.Request(BASE + route, data=None if data is None else json.dumps(data).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        value = json.load(response)
    if value.get('status') != 'success':
        raise RuntimeError('Console request rejected')
    return value


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.replace(temp, path)


def settings(sid, agent='default'):
    value = request('/api/sessions/' + urllib.parse.quote(sid) + '/settings?agent_id=' + agent)
    return {'model': {k: value['model'].get(k) for k in ('model', 'provider', 'source', 'pin_ignored')},
            'permission': value['permission'], 'team': value['team']}


def submit(path, sid):
    if path.exists():
        raise RuntimeError('Audit state exists; observe it instead of resubmitting')
    registry = request('/api/agents')
    agents = {a['id']: {k: a.get(k) for k in ('id', 'name', 'enabled', 'workspace', 'model', 'bot_type')}
              for a in registry['agents']}
    if any(not agents.get(x, {}).get('enabled') for x in ('default', 'testpilot', 'testpilot2')):
        raise RuntimeError('Required target unavailable')
    before = settings(sid)
    if before['permission']['mode'] != 'workspace-write' or before['team']['members']:
        raise RuntimeError('Unexpected existing permission or session state')
    data = json.loads((HERE / 'tasks.json').read_text())
    targets = [{k: t[k] for k in ('agent_id', 'task_id', 'records')} for t in data['tasks']]
    fields = 'agent_id, task_id, accepted_count, paid_cents, refund_cents, net_cents, excluded'
    prompt = (
        'You are the main CowAgent supervisor for AGENT-ROUTING-002. '
        'Perform exactly two native agent_delegate calls: send Task A to agent_id testpilot '
        'and Task B to agent_id testpilot2. Do not solve or simulate either worker task yourself. '
        'These are independent fictional business tasks; use your native delegation behavior. '
        'Give each worker only its assigned dataset and the complete rules/output requirements. '
        'Each worker must return one JSON object with fields ' + fields + '. '
        'Each excluded entry must contain index, id, reason. Include the assigned task identifier. '
        'Worker identity in output is a claim; the audit will verify runtime identity independently. '
        'Use only the supplied records. Do not read or write files, private memory or history; '
        'do not use shell, browser, network, external services or additional worker tools. '
        'Keep existing model and permissions. After both native calls return, report their results '
        'and any failures without inventing missing results.\nRules: ' + data['rules'] +
        '\nTasks: ' + json.dumps(targets, separators=(',', ':')))
    state = {'session_id': sid, 'created_at': time.time(), 'registry': agents, 'settings_before': before,
             'dataset_sha256': hashlib.sha256((HERE / 'tasks.json').read_bytes()).hexdigest(),
             'cursor': 0, 'events': [], 'submit_intent': False}
    save(path, state)
    # This is the normal session roster setting only: no permission, model,
    # profile, workspace or application configuration fields are sent.
    request('/api/sessions/' + sid + '/settings', {'agent_id': 'default', 'members': ['testpilot', 'testpilot2']})
    state['settings_after_roster'] = settings(sid)
    if state['settings_after_roster']['permission'] != before['permission']:
        raise RuntimeError('Permission changed unexpectedly')
    state['submit_intent'] = True
    save(path, state)
    response = request('/message', {'agent_id': 'default', 'speaker_agent_id': 'default',
                                    'session_id': sid, 'stream': True, 'lang': 'en', 'message': prompt})
    state['request_id'] = response['request_id']
    state['submitted_at'] = time.time()
    save(path, state)
    print(json.dumps({'phase': 'submitted', 'session_id': sid, 'request_id': state['request_id']}), flush=True)
    observe(path)


def sanitize(value):
    event = {k: value[k] for k in ('type', 'seq', 'timestamp', 'card_id', 'agent_id', 'source_id',
                                  'tool_call_id', 'tool', 'status', 'execution_time',
                                  'permission_denied', 'permission_mode', 'reason') if k in value}
    event['observed_at'] = time.time()
    if value.get('type') == 'tool_start' and value.get('tool') == 'agent_delegate':
        arguments = value.get('arguments') or {}
        event['target_agent_id'] = arguments.get('agent_id')
        task = arguments.get('task', '')
        event['task_identifier'] = next((x for x in ('AGENT-ROUTING-002-A', 'AGENT-ROUTING-002-B') if x in task), None)
        event['delegated_task_chars'] = len(task)
    # Deliberately omit arguments, result, display, delta and reasoning text.
    return event


def observe(path):
    state = json.loads(path.read_text())
    if not state.get('request_id'):
        raise RuntimeError('Unknown send outcome; inspect existing session, never resubmit')
    if state.get('stream_ended'):
        print(json.dumps({'phase': 'already_terminal', 'request_id': state['request_id']}), flush=True)
        return
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        route = '/stream?' + urllib.parse.urlencode({'request_id': state['request_id'], 'after_seq': state['cursor']})
        try:
            with urllib.request.urlopen(BASE + route, timeout=30) as response:
                for raw in response:
                    if not raw.startswith(b'data: '):
                        continue
                    value = json.loads(raw[6:])
                    state['cursor'] = max(state['cursor'], value.get('seq', 0))
                    event = sanitize(value)
                    if value.get('type') not in ('delta', 'reasoning', 'tool_progress'):
                        state['events'].append(event)
                        print(json.dumps(event), flush=True)
                    if value.get('type') in ('error', 'resync_required'):
                        state['observation_issue'] = event
                        save(path, state)
                        return
                    if value.get('type') == 'stream_end':
                        state['stream_ended'] = True
                    save(path, state)
                    if state.get('stream_ended'):
                        return
                    if time.monotonic() > deadline:
                        return
        except (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionError):
            # Observe the same live handle after a transport timeout. The
            # application can continue execution without this observer.
            state['observation_reconnects'] = state.get('observation_reconnects', 0) + 1
            save(path, state)
            print(json.dumps({'phase': 'reconnecting_same_request', 'request_id': state['request_id']}), flush=True)
            time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('submit', 'observe'))
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--session')
    args = parser.parse_args()
    if args.action == 'submit':
        if not args.session or not args.session.startswith('audit-routing-002-'):
            parser.error('A fresh audit-routing-002 session is required')
        submit(args.state, args.session)
    else:
        observe(args.state)
