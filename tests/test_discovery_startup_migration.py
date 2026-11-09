"""Startup migration recovery checks for the DISCOVERY-002 maintenance gate.

All rows are fictional. The fixtures use the current global schema and the
older per-agent conversation schema that the migration explicitly supports.
"""

import json
import sqlite3
from pathlib import Path

from agent.memory import clear_conversation_store_cache, migrate_conversations_to_global
from agent.memory import conversation_store
from agent.registry import AgentProfile, AgentRegistry, set_agent_registry


def _seed_secondary(workspace: Path, *, with_conversation: bool) -> Path:
    db = workspace / "memory" / "long-term" / "index.db"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as conn:
        # Model the observed secondary memory-index tables, with no
        # conversation tables. No live data or private text is copied here.
        conn.executescript("""
            CREATE TABLE _meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE chunks (
                id TEXT, user_id TEXT, scope TEXT, source TEXT, path TEXT,
                start_line INTEGER, end_line INTEGER, text TEXT, embedding TEXT,
                hash TEXT, metadata TEXT, created_at INTEGER, updated_at INTEGER,
                hit_count INTEGER, last_hit_at INTEGER
            );
            CREATE TABLE chunks_fts (
                text, id, user_id, path, source, scope
            );
            CREATE TABLE chunks_fts_trigram (
                text, id, user_id, path, source, scope
            );
            CREATE TABLE files (
                path TEXT, source TEXT, hash TEXT, mtime INTEGER, size INTEGER,
                updated_at INTEGER
            );
        """)
        if with_conversation:
            conn.executescript("""
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    last_active INTEGER NOT NULL,
                    msg_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(session_id, seq)
                );
            """)
            conn.execute(
                "INSERT INTO sessions VALUES ('fictional-session', 1, 2, 1)"
            )
            conn.execute(
                "INSERT INTO messages(session_id, seq, role, content, created_at) "
                "VALUES ('fictional-session', 0, 'user', ?, 1)",
                (json.dumps("fictional payload"),),
            )
    return db


def _registry(tmp_path: Path, source: Path) -> None:
    set_agent_registry(AgentRegistry([
        AgentProfile("default", "Default", str(tmp_path / "primary")),
        AgentProfile("testpilot2", "TestPilot2", str(source.parent.parent.parent)),
    ], default_agent_id="default"))
    clear_conversation_store_cache()


def _marker_exists(global_db: Path) -> bool:
    with sqlite3.connect(global_db) as conn:
        return conn.execute(
            "SELECT 1 FROM _migration_meta WHERE key = 'merged_agent:testpilot2'"
        ).fetchone() is not None


def test_markerless_existing_secondary_without_conversation_tables_is_safe(tmp_path):
    source = _seed_secondary(tmp_path / "secondary", with_conversation=False)
    _registry(tmp_path, source)
    try:
        # Seed the current global, composite-key schema with fictional rows.
        # The migration must preserve them while it records the empty-source
        # marker for the registered secondary Agent.
        global_store = conversation_store.get_conversation_store()
        global_db = Path(global_store._db_path)
        with sqlite3.connect(global_db) as conn:
            conn.execute(
                "INSERT INTO sessions(agent_id,session_id,created_at,last_active,msg_count) "
                "VALUES ('testpilot2','fictional-session',1,2,1)"
            )
            conn.execute(
                "INSERT INTO messages(agent_id,session_id,seq,role,content,created_at) "
                "VALUES ('testpilot2','fictional-session',0,'user',?,1)",
                (json.dumps("fictional retained row"),),
            )
        migrate_conversations_to_global(kickoff_async=False)
        assert _marker_exists(global_db)
        with sqlite3.connect(global_db) as conn:
            assert conn.execute(
                "SELECT count(*) FROM messages WHERE agent_id='testpilot2' "
                "AND session_id='fictional-session'"
            ).fetchone()[0] == 1
        with sqlite3.connect(source) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert "_meta" in tables
        assert "sessions" not in tables and "messages" not in tables
    finally:
        set_agent_registry(None)
        clear_conversation_store_cache()


def test_copy_committed_without_marker_retries_idempotently(tmp_path, monkeypatch):
    source = _seed_secondary(tmp_path / "secondary", with_conversation=True)
    _registry(tmp_path, source)
    real_mark = conversation_store._mark_migration_done
    first = True

    def fail_marker_once(conn, key, value=""):
        nonlocal first
        if key == "merged_agent:testpilot2" and first:
            first = False
            raise sqlite3.OperationalError("fictional marker write interruption")
        return real_mark(conn, key, value)

    monkeypatch.setattr(conversation_store, "_mark_migration_done", fail_marker_once)
    try:
        migrate_conversations_to_global(kickoff_async=False)
        global_db = tmp_path / "primary" / "memory" / "long-term" / "index.db"
        assert not _marker_exists(global_db)
        with sqlite3.connect(global_db) as conn:
            assert conn.execute(
                "SELECT count(*) FROM messages WHERE agent_id='testpilot2' "
                "AND session_id='fictional-session'"
            ).fetchone()[0] == 1
        with sqlite3.connect(source) as conn:
            source_tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        assert "messages" not in source_tables
        assert any(name.startswith("messages_migrated_") for name in source_tables)

        # Retry sees archived source tables, writes the missing marker, and
        # leaves the already committed destination row unique.
        migrate_conversations_to_global(kickoff_async=False)
        assert _marker_exists(global_db)
        with sqlite3.connect(global_db) as conn:
            assert conn.execute(
                "SELECT count(*) FROM messages WHERE agent_id='testpilot2' "
                "AND session_id='fictional-session'"
            ).fetchone()[0] == 1
        with sqlite3.connect(source) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            assert "messages" not in tables
            assert any(name.startswith("messages_migrated_") for name in tables)
            archived_messages = next(
                name for name in tables if name.startswith("messages_migrated_")
            )
            assert conn.execute(
                f'SELECT count(*) FROM "{archived_messages}"'
            ).fetchone()[0] == 1
    finally:
        set_agent_registry(None)
        clear_conversation_store_cache()
