"""Disposable process fixture for actual runtime/service crash boundaries."""
import json
import os
from pathlib import Path
import socket
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
root, mode = Path(sys.argv[1]).resolve(), sys.argv[2]
root.mkdir(parents=True, exist_ok=True)
workspace = root / 'workspace'
workspace.mkdir(exist_ok=True)
case_file = root / 'release-case.json'
case = json.loads(case_file.read_text()) if case_file.exists() else {}
os.environ['HOME'] = str(root / 'home')
os.environ['COW_DATA_DIR'] = str(root / 'data')
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError('network prohibited'))

import config
config.config = config.Config({'agent_workspace': str(workspace), 'default_agent_id': 'owner',
    **({'agents': case['agents']} if 'agents' in case else {}),
    'agent_permission_mode': case.get('permission', 'workspace-write'), 'model': 'fixture-model', 'bot_type': 'fixture',
    'knowledge': False, 'self_evolution_enabled': False})
from agent.protocol import Agent, LLMModel
from agent.permission.authority import Authority
from agent.tools.write.write import Write
from agent.tools.read.read import Read
from agent.recovery.runtime import snapshot_child, execute_task
from agent.recovery.store import TaskStore
from agent.recovery.service import RecoveryService
from agent.registry import AgentRegistry

if 'agents' in case:
    profiles = AgentRegistry.from_config(config.config).list(include_disabled=True)
    (root / f'profile-snapshot-{mode}.json').write_text(json.dumps([
        {'id': p.id, 'name': p.name, 'workspace': p.workspace, 'enabled': p.enabled}
        for p in profiles]))

store = TaskStore(root / 'private-journal/tasks.db')


def ready():
    (root / 'ready').write_text(mode)
    while True:
        time.sleep(.05)


class Model(LLMModel):
    def __init__(self, *_):
        super().__init__('fixture-model')
        self.calls = 0
    def set_agent_default(self, *_):
        pass
    def set_session_override(self, *_):
        pass
    def call_stream(self, request):
        self.calls += 1
        if case.get('capture_requests'):
            with (root / 'model-requests.jsonl').open('a') as requests:
                requests.write(json.dumps(vars(request), default=str) + '\n')
        if case.get('sibling_probe') and self.calls == 1:
            yield {'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'fixture-read',
                'function': {'name': 'read', 'arguments': json.dumps({'path': str(root / 'sibling/secret.txt')})}}]}, 'finish_reason': 'tool_calls'}]}
            return
        if self.calls == (2 if case.get('sibling_probe') else 1):
            if mode == 'before_effect':
                ready()
            if case.get('skip_output'):
                yield {'choices': [{'delta': {'content': 'fixture completed'}, 'finish_reason': 'stop'}]}
                return
            yield {'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'fixture-write',
                'function': {'name': 'write', 'arguments': json.dumps({'path': 'result.txt',
                'content': case.get('content', 'durable fixture result')})}}]}, 'finish_reason': 'tool_calls'}]}
        else:
            yield {'choices': [{'delta': {'content': 'fixture completed'}, 'finish_reason': 'stop'}]}


from agent.permission.filesystem import FileBroker
original_write = FileBroker.write


def counted_write(self, path, content):
    result = original_write(self, path, content)
    with (root / 'effect-count').open('a') as receipt:
        receipt.write('write\n')
    return result


FileBroker.write = counted_write
original_before = store.before_tool
original_after = store.after_tool
original_finish = store.finish


def before(*args, **kwargs):
    effect = original_before(*args, **kwargs)
    if mode == 'after_intent':
        ready()
    return effect


def after(*args, **kwargs):
    if mode == 'after_effect':
        ready()
    return original_after(*args, **kwargs)


def finish(*args, **kwargs):
    result = original_finish(*args, **kwargs)
    if mode == 'after_completion':
        ready()
    return result


store.before_tool, store.after_tool = before, after
store.finish = finish
if mode in ('before_dispatch', 'before_effect', 'after_intent', 'after_effect', 'after_completion'):
    child = Agent('fictional task', model=Model(), tools=[Read({'cwd': str(workspace)}), Write({'cwd': str(workspace)})] if case.get('sibling_probe') else [Write({'cwd': str(workspace)})],
                  workspace_dir=str(workspace), enable_skills=False, skip_context_files=True,
                  max_steps=3, output_mode='logger')
    child._current_agent_id = 'owner'
    child.permission_mode = 'workspace-write'
    child.authority = Authority('workspace-write', frozenset({'fs.read', 'fs.write'}),
                                (str(workspace),), (str(workspace),))
    verification = {group: [{'id': group, 'type': 'text_equals', 'path': 'result.txt',
                             'expected': 'durable fixture result'}]
                    for group in ('acceptance', 'external_state')} if mode == 'after_completion' or case.get('verification') else None
    spec = snapshot_child(child, 'Write the fixture result once', owner_id='owner', session_id='s',
                          kind='subagent', source_agent_id='owner', target_agent_id='owner', timeout_seconds=case.get('timeout', 30),
                          verification=verification)
    task = store.submit('owner', 's', 'subagent', spec, idempotency_key='fixture')
    (root / 'task-id').write_text(task['task_id'])
    if mode == 'before_dispatch':
        ready()
    execute_task(store, task['task_id'], lambda: child)
else:
    import bridge.agent_bridge
    bridge.agent_bridge.AgentLLMModel = Model
    service = RecoveryService(object(), store, max_workers=1)
    if mode != 'service-scan':
        service.start()
    task_id = (root / 'task-id').read_text()
    try:
        if mode == 'service-scan':
            service.scan_once()
            (root / 'service-scan.json').write_text(json.dumps(store.get(task_id)))
        else:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                row = store.get(task_id)
                if row['state'] in ('needs_review', 'failed') or row['state'] == 'completed' and row['verification']:
                    (root / 'service-result.json').write_text(json.dumps(row))
                    break
                time.sleep(.02)
            else:
                raise AssertionError('recovery service did not settle')
    finally:
        service.close(wait=True)
