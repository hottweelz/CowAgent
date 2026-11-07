"""Retained profiles, history and indexed memory across a real worker restart."""
import asyncio
import hashlib
import json
import os
import sqlite3

import pytest

from agent.memory.config import MemoryConfig
from agent.memory.conversation_store import ConversationStore
from agent.memory.manager import MemoryManager
from agent.protocol import Agent
from agent.recovery.store import TaskStore
from agent.recovery.verification import outcome_summary
from agent.registry import AgentRegistry
from agent.tools.memory.memory_search import MemorySearchTool
from tests.test_recovery_process import launch, wait_file


def history_rows(path):
    with sqlite3.connect(path) as db:
        return {table: db.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
                for table in ('sessions', 'messages', 'runs')}


@pytest.mark.skipif(os.name != 'posix', reason='POSIX process ownership backend')
def test_restart_preserves_teammate_identity_history_and_fts(tmp_path, monkeypatch):
    import config
    import agent.registry as registry_module

    profiles = [
        {'id': 'owner', 'name': 'Fixture Owner', 'workspace': str(tmp_path / 'workspace')},
        {'id': 'teammate', 'name': 'Persistent Teammate', 'workspace': str(tmp_path / 'sibling'),
         'model': 'fixture-model', 'bot_type': 'fixture'},
    ]
    settings = {'agent_workspace': profiles[0]['workspace'], 'agents': profiles,
                'default_agent_id': 'owner', 'agent_permission_mode': 'workspace-write',
                'model': 'fixture-model', 'bot_type': 'fixture',
                'knowledge': False, 'self_evolution_enabled': False}
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('COW_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr(config, 'config', config.Config(settings))
    registry = AgentRegistry.from_config(settings)
    monkeypatch.setattr(registry_module, '_registry_instance', registry)
    monkeypatch.setattr(registry_module, '_registry_pinned', True)
    monkeypatch.setattr('socket.socket.connect', lambda *a, **k: pytest.fail('network access'))
    case = tmp_path / 'release-case.json'
    case.write_text(json.dumps({'verification': True, 'agents': profiles, 'capture_requests': True}))
    retained = [case]
    configs = []
    for profile in registry.list():
        workspace = profile.workspace_path
        (workspace / 'memory').mkdir(parents=True)
        for name, text in {
            'AGENT.md': f'PRIVATE_IDENTITY_{profile.id}',
            'MEMORY.md': f'PRIVATE_CORE_{profile.id}',
            'memory/retained.md': f'QUARTZPERSIST{profile.id.upper()} retained indexed fact',
        }.items():
            path = workspace / name
            path.write_text(text)
            retained.append(path)
        memory_config = MemoryConfig(workspace_root=str(workspace))
        configs.append((profile, memory_config))
        manager = MemoryManager(memory_config, embedding_provider=None)
        try:
            asyncio.run(manager.sync())
            assert manager.storage.fts5_available
        finally:
            manager.close()

    shared_db = configs[0][1].get_db_path()
    for profile in registry.list():
        history = ConversationStore(shared_db, agent_id=profile.id)
        history.append_messages('retained', [
            {'role': 'user', 'content': f'PRIVATE_HISTORY_{profile.id}'},
            {'role': 'assistant', 'content': f'retained reply for {profile.id}'},
        ], channel_type='web')
        assert history.create_run(f'retained-{profile.id}', agent_id=profile.id, session_id='retained')
        assert history.finish_run(f'retained-{profile.id}')
    before_rows = history_rows(shared_db)
    before_files = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in retained}
    before_profiles = [profile.to_dict() for profile in registry.list()]

    worker = launch(tmp_path, 'after_intent')
    try:
        wait_file(worker, tmp_path / 'ready')
        worker.kill()
        worker.wait(timeout=5)
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=5)
    task_id = (tmp_path / 'task-id').read_text()
    journal = TaskStore(tmp_path / 'private-journal/tasks.db')
    frozen_spec = journal.get(task_id)['spec']
    for mode in ('service-hold', 'service-retry', 'service-repeat'):
        if mode == 'service-retry':
            assert journal.get(task_id)['state'] == 'needs_review'
            journal.retry(task_id, acknowledge_effects=True)
        service = launch(tmp_path, mode)
        try:
            assert service.wait(timeout=12) == 0, (tmp_path / f'{mode}.log').read_text()
        finally:
            if service.poll() is None:
                service.kill()
                service.wait(timeout=5)
    task = journal.get(task_id)
    assert task['spec'] == frozen_spec
    assert task['attempt_count'] == 2 and outcome_summary(task)['verified']
    assert (tmp_path / 'workspace/result.txt').read_text() == 'durable fixture result'
    assert (tmp_path / 'effect-count').read_text().splitlines() == ['write']
    assert history_rows(shared_db) == before_rows
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in retained} == before_files
    assert [p.to_dict() for p in AgentRegistry.from_config(settings).list()] == before_profiles
    expected_profiles = [{key: value for key, value in p.items()
                          if key in ('id', 'name', 'workspace', 'enabled')} for p in before_profiles]
    for mode in ('after_intent', 'service-hold', 'service-retry', 'service-repeat'):
        assert json.loads((tmp_path / f'profile-snapshot-{mode}.json').read_text()) == expected_profiles
    requests = (tmp_path / 'model-requests.jsonl').read_text()
    assert 'Write the fixture result once' in requests
    for prefix in ('PRIVATE_IDENTITY_', 'PRIVATE_CORE_', 'PRIVATE_HISTORY_'):
        assert prefix not in requests

    for profile, memory_config in configs:
        manager = MemoryManager(memory_config, embedding_provider=None)
        try:
            # Read the existing index without re-syncing or rebuilding it.
            manager.config.sync_on_search = False
            statements = []
            manager.storage.conn.set_trace_callback(statements.append)
            owner = Agent('fixture', tools=[], workspace_dir=profile.workspace,
                          enable_skills=False, skip_context_files=True)
            owner._current_agent_id = profile.id
            owner.permission_mode = 'full-access'
            search = MemorySearchTool(manager)
            search.context = owner
            result = search.execute_tool({'query': f'QUARTZPERSIST{profile.id.upper()}', 'min_score': 0})
            assert result.status == 'success' and 'retained indexed fact' in str(result.result)
            assert any(' MATCH ' in sql.upper() for sql in statements)
            assert not any(' LIKE ' in sql.upper() for sql in statements)
            assert manager.storage.conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
            assert manager.storage.conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert manager.storage.conn.execute('PRAGMA foreign_key_check').fetchall() == []
        finally:
            manager.close()
        messages = ConversationStore(shared_db, agent_id=profile.id).load_messages('retained')
        assert messages[0]['content'] == f'PRIVATE_HISTORY_{profile.id}'
        assert all(f'PRIVATE_HISTORY_{other.id}' not in str(messages)
                   for other in registry.list() if other.id != profile.id)
    assert history_rows(shared_db) == before_rows
    with journal._connect() as db:
        assert db.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        assert db.execute('PRAGMA synchronous').fetchone()[0] == 2
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
