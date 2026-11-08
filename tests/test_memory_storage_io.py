"""SQLite I/O failures during memory storage startup must remain visible."""

import os
import sqlite3
from pathlib import Path

import pytest

from agent.memory.conversation_store import ConversationStore
from agent.memory.storage import MemoryChunk, MemoryStorage


class TrackingConnection(sqlite3.Connection):
    """Connection subclass that records deterministic closure in fault tests."""

    def close(self):
        self.was_closed = True
        return super().close()


def _tracked_connect(real_connect, connections, db_path, fail_at=None, failure=None):
    target_path = Path(db_path).resolve()

    def connect(*args, **kwargs):
        database = args[0] if args else kwargs.get("database")
        try:
            is_target = Path(os.fsdecode(os.fspath(database))).resolve() == target_path
        except (TypeError, ValueError):
            is_target = False
        if not is_target:
            return real_connect(*args, **kwargs)
        if fail_at == "connect":
            raise failure
        kwargs["factory"] = TrackingConnection
        conn = real_connect(*args, **kwargs)
        conn.was_closed = False
        original_execute = conn.execute
        original_commit = conn.commit

        def execute(sql, *params):
            statement = " ".join(sql.split())
            if fail_at == "fts_create" and statement.startswith(
                "CREATE VIRTUAL TABLE IF NOT EXISTS fts5_test"
            ):
                raise failure
            if fail_at == "fts_drop" and statement.startswith("DROP TABLE IF EXISTS fts5_test"):
                raise failure
            if fail_at == "schema" and statement.startswith("CREATE TABLE IF NOT EXISTS chunks"):
                raise failure
            if fail_at == "trigram_detach" and statement.startswith("DROP TRIGGER IF EXISTS chunks_trigram_"):
                raise failure
            return original_execute(sql, *params)

        def commit():
            if fail_at == "commit":
                raise failure
            return original_commit()

        conn.execute = execute
        conn.commit = commit
        connections.append(conn)
        return conn

    return connect


@pytest.mark.parametrize("fail_at", ["connect", "fts_create", "fts_drop", "schema", "commit"])
def test_initialization_propagates_sqlite_error_and_closes_open_connection(
    tmp_path, monkeypatch, fail_at
):
    db_path = tmp_path / "index.db"
    failure = sqlite3.OperationalError(f"injected SQLite I/O failure at {fail_at}")
    connections = []
    real_connect = sqlite3.connect
    monkeypatch.setattr(
        sqlite3,
        "connect",
        _tracked_connect(real_connect, connections, db_path, fail_at, failure),
    )

    with pytest.raises(sqlite3.OperationalError) as caught:
        MemoryStorage(db_path)

    assert caught.value is failure
    if fail_at == "connect":
        assert connections == []
    else:
        assert len(connections) == 1
        assert connections[0].was_closed


@pytest.mark.parametrize("fail_at", ["fts_create", "fts_drop", "schema", "commit"])
def test_initialization_error_log_has_operation_path_and_traceback(
    tmp_path, monkeypatch, fail_at
):
    from common.log import logger

    records = []
    monkeypatch.setattr(logger, "error", lambda *args, **kwargs: records.append((args, kwargs)))
    failure = sqlite3.OperationalError(f"injected failure {fail_at}")
    connections = []
    real_connect = sqlite3.connect
    db_path = tmp_path / "index.db"
    monkeypatch.setattr(
        sqlite3,
        "connect",
        _tracked_connect(real_connect, connections, db_path, fail_at, failure),
    )

    with pytest.raises(sqlite3.OperationalError) as caught:
        MemoryStorage(db_path)

    assert caught.value is failure
    assert records
    diagnostics = [(args[0] % args[1:], kwargs) for args, kwargs in records]
    expected_operation = {
        "fts_create": "CREATE VIRTUAL TABLE fts5_test",
        "fts_drop": "DROP TABLE fts5_test",
        "schema": "CREATE TABLE chunks",
        "commit": "commit initialization",
    }[fail_at]
    assert any(
        f"operation={expected_operation}" in message
        and str(db_path) in message
        and "sqlite_errorcode=" in message
        and "sqlite_errorname=" in message
        and kwargs.get("exc_info") is True
        for message, kwargs in diagnostics
    )


@pytest.mark.skipif(os.name == "nt", reason="WAL rename reproduction is POSIX-specific")
def test_renamed_wal_reports_io_error_and_leaves_original_files_in_place(tmp_path, monkeypatch):
    from common.log import logger

    db_path = tmp_path / "index.db"
    wal_path = Path(f"{db_path}-wal")
    renamed_wal_path = tmp_path / "index [conflicted].db-wal"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE retained_history (content TEXT NOT NULL)")
    connection.execute("INSERT INTO retained_history VALUES ('conversation survives')")
    connection.commit()
    assert wal_path.exists()
    wal_path.rename(renamed_wal_path)

    records = []
    monkeypatch.setattr(logger, "error", lambda *args, **kwargs: records.append((args, kwargs)))
    try:
        with pytest.raises(sqlite3.DatabaseError) as caught:
            MemoryStorage(db_path)

        assert db_path.exists()
        assert renamed_wal_path.exists()
        assert caught.value.sqlite_errorcode == 522
        assert caught.value.sqlite_errorname == "SQLITE_IOERR_SHORT_READ"
        diagnostics = [(args[0] % args[1:], kwargs) for args, kwargs in records]
        assert any(
            "PRAGMA journal_mode=WAL" in diagnostic
            and str(db_path) in diagnostic
            and str(caught.value.sqlite_errorcode) in diagnostic
            and caught.value.sqlite_errorname in diagnostic
            and kwargs.get("exc_info") is True
            for diagnostic, kwargs in diagnostics
        )
    finally:
        connection.close()


def test_repeated_startup_keeps_wal_fts_retrieval_and_conversation_history(tmp_path):
    db_path = tmp_path / "index.db"
    conversation = ConversationStore(db_path)
    conversation.append_messages(
        "io-regression",
        [{"role": "user", "content": "keep this conversation"}],
        channel_type="web",
    )

    for run in range(2):
        storage = MemoryStorage(db_path)
        try:
            assert storage.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            assert storage.fts5_available
            storage.save_chunk(MemoryChunk(
                id="persisted-note",
                user_id=None,
                scope="shared",
                source="memory",
                path="memory/io-note.md",
                start_line=1,
                end_line=1,
                text="quasarorchid durable indexed note",
                embedding=None,
                hash=f"io-regression-{run}",
            ))
            assert [row.path for row in storage.search_keyword("quasarorchid")] == [
                "memory/io-note.md"
            ]
        finally:
            storage.close()

    reopened = MemoryStorage(db_path)
    try:
        assert reopened.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert [row.path for row in reopened.search_keyword("quasarorchid")] == [
            "memory/io-note.md"
        ]
        assert conversation.load_messages("io-regression")[0]["content"] == "keep this conversation"
    finally:
        reopened.close()


def test_trigram_io_error_propagates_without_removing_existing_triggers(
    tmp_path, monkeypatch
):
    initial = MemoryStorage(tmp_path / "index.db")
    try:
        if not initial.fts5_available or not initial.trigram_fts5_available:
            pytest.skip("SQLite build lacks the FTS5 trigram tokenizer")
        db_path = initial.db_path
        before = {
            row[0]
            for row in initial.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE 'chunks_trigram_%'"
            )
        }
        assert before
    finally:
        initial.close()

    failure = sqlite3.OperationalError("disk I/O error")

    def fail_trigram(_conn):
        raise failure

    monkeypatch.setattr(MemoryStorage, "_create_trigram_objects", staticmethod(fail_trigram))
    with pytest.raises(sqlite3.OperationalError) as caught:
        MemoryStorage(db_path)
    assert caught.value is failure

    check = sqlite3.connect(db_path)
    try:
        after = {
            row[0]
            for row in check.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE 'chunks_trigram_%'"
            )
        }
        assert after == before
    finally:
        check.close()


def test_unsupported_trigram_cleanup_io_error_is_not_suppressed(tmp_path, monkeypatch):
    def unavailable(_conn):
        raise sqlite3.OperationalError("no such tokenizer: trigram")

    failure = sqlite3.OperationalError("disk I/O error")
    connections = []
    monkeypatch.setattr(MemoryStorage, "_create_trigram_objects", staticmethod(unavailable))
    db_path = tmp_path / "index.db"
    monkeypatch.setattr(
        sqlite3, "connect",
        _tracked_connect(sqlite3.connect, connections, db_path,
                         "trigram_detach", failure),
    )
    with pytest.raises(sqlite3.OperationalError) as caught:
        MemoryStorage(db_path)
    assert caught.value is failure
    assert len(connections) == 1 and connections[0].was_closed
