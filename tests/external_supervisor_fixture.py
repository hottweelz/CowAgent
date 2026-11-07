"""Owned process for killing the supervisor at actual transport boundaries."""
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
root, socket_path, mode = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
os.environ['HOME'] = str(root / 'host-home')
os.environ['COW_DATA_DIR'] = str(root / 'host-data')
from agent.external.contract import Credential
from agent.external.transport import ExternalTransport
from agent.external.journal import ExternalJournal
from agent.external.supervisor import ExternalSupervisor
from agent.recovery.store import TaskStore

cfg = json.loads((root / 'config.json').read_text())
credential = Credential(cfg['supervisor_id'], cfg['runtime_id'], cfg['key_id'],
                        bytes.fromhex(cfg['secret_hex']), cfg['expires_at'], tuple(cfg['operations']))
transport = ExternalTransport(socket_path, credential)
journal = ExternalJournal(TaskStore(root / 'host-journal/tasks.db'))
supervisor = ExternalSupervisor(journal, transport, owner_id='owner', source_id='source', conversation_id='conversation')
spec = json.loads((root / 'host-spec.json').read_text())
original = transport.submit


def paused_submit(*args, **kwargs):
    result = original(*args, **kwargs) if mode == 'after_send' else None
    (root / 'host-reached').write_text(mode)
    while not (root / 'host-release').exists():
        time.sleep(.02)
    return result


transport.submit = paused_submit
supervisor.prepare(spec)
if spec['task']['operation'] == 'record_effect':
    supervisor.approve(spec['task_id'], approved_by='fixture-operator', expires_at=spec['authority']['expires_at'])
supervisor.submit(spec['task_id'])
