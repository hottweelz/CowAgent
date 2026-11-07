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
os.environ['HOME'] = str(root / 'home')
os.environ['COW_DATA_DIR'] = str(root / 'data')
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError('network prohibited'))

import config
config.config = config.Config({'agent_workspace': str(workspace), 'default_agent_id': 'owner',
    'agent_permission_mode': 'workspace-write', 'model': 'fixture-model', 'bot_type': 'fixture',
    'knowledge': False, 'self_evolution_enabled': False})
from agent.protocol import Agent, LLMModel
from agent.permission.authority import Authority
from agent.tools.write.write import Write
from agent.recovery.runtime import snapshot_child, execute_task
from agent.recovery.store import TaskStore
from agent.recovery.service import RecoveryService

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
        if self.calls == 1:
            if mode == 'before_effect':
                ready()
            yield {'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'fixture-write',
                'function': {'name': 'write', 'arguments': json.dumps({'path': 'result.txt',
                'content': 'durable fixture result'})}}]}, 'finish_reason': 'tool_calls'}]}
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


def before(*args, **kwargs):
    effect = original_before(*args, **kwargs)
    if mode == 'after_intent':
        ready()
    return effect


def after(*args, **kwargs):
    if mode == 'after_effect':
        ready()
    return original_after(*args, **kwargs)


store.before_tool, store.after_tool = before, after
if mode in ('before_effect', 'after_intent', 'after_effect'):
    child = Agent('fictional task', model=Model(), tools=[Write({'cwd': str(workspace)})],
                  workspace_dir=str(workspace), enable_skills=False, skip_context_files=True,
                  max_steps=3, output_mode='logger')
    child._current_agent_id = 'owner'
    child.permission_mode = 'workspace-write'
    child.authority = Authority('workspace-write', frozenset({'fs.read', 'fs.write'}),
                                (str(workspace),), (str(workspace),))
    spec = snapshot_child(child, 'Write the fixture result once', owner_id='owner', session_id='s',
                          kind='subagent', source_agent_id='owner', target_agent_id='owner', timeout_seconds=30)
    task = store.submit('owner', 's', 'subagent', spec, idempotency_key='fixture')
    (root / 'task-id').write_text(task['task_id'])
    execute_task(store, task['task_id'], lambda: child)
else:
    import bridge.agent_bridge
    bridge.agent_bridge.AgentLLMModel = Model
    service = RecoveryService(object(), store, max_workers=1).start()
    task_id = (root / 'task-id').read_text()
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            row = store.get(task_id)
            if row['state'] in ('completed', 'needs_review', 'failed'):
                (root / 'service-result.json').write_text(json.dumps(row))
                break
            time.sleep(.02)
        else:
            raise AssertionError('recovery service did not settle')
    finally:
        service.close(wait=True)
