#!/usr/bin/env python3
"""Fictional native-schema snapshot and restore checks for FIRST-BOOTSTRAP-002."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import uuid
from pathlib import Path

DATABASES = (
    "memory/long-term/index.db",
    "agents/testpilot/memory/long-term/index.db",
    "agents/testpilot2/memory/long-term/index.db",
    "memory/recovery/tasks.db",
)
SIDECARS = tuple(f"{name}{suffix}" for name in DATABASES for suffix in ("-wal", "-shm", "-journal"))
ROOT_MARKER = ".cow-first-bootstrap-fictional-root"
MARKER_VALUE = "cow.first-bootstrap.fictional-root/1\n"


class RecoveryError(RuntimeError):
    """A fixture snapshot is incomplete or has changed."""


def create_fictional_root(parent: Path) -> Path:
    parent = parent.resolve(strict=True)
    temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    try:
        parent.relative_to(temp_root)
    except ValueError as exc:
        raise RecoveryError("fixture parent is outside canonical temp root") from exc
    root = parent / f"cow-first-bootstrap-fixture-{uuid.uuid4().hex}"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    marker = root / ROOT_MARKER
    marker.write_text(MARKER_VALUE, encoding="utf-8")
    os.chmod(marker, 0o600)
    return root


def _owned_root(path: Path) -> Path:
    path = path.resolve(strict=True)
    temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    try:
        path.relative_to(temp_root)
    except ValueError as exc:
        raise RecoveryError("fixture path is outside canonical temp root") from exc
    for candidate in (path, *path.parents):
        marker = candidate / ROOT_MARKER
        if marker.is_file():
            root_stat = candidate.stat()
            marker_stat = marker.lstat()
            if root_stat.st_uid != os.getuid() or stat.S_IMODE(root_stat.st_mode) != 0o700:
                raise RecoveryError("fictional root owner or mode is unsafe")
            if marker.is_symlink() or marker_stat.st_uid != os.getuid() or stat.S_IMODE(marker_stat.st_mode) != 0o600:
                raise RecoveryError("fictional root marker owner or mode is unsafe")
            if marker.read_text(encoding="utf-8") != MARKER_VALUE:
                raise RecoveryError("fictional root marker is invalid")
            return candidate
    raise RecoveryError("fictional root marker is missing")


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(root: Path) -> list[dict[str, object]]:
    entries = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if rel in SIDECARS:
            continue
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            entries.append({"path": rel, "kind": "symlink", "mode": mode, "target": os.readlink(path)})
        elif path.is_dir():
            entries.append({"path": rel, "kind": "directory", "mode": mode})
        elif path.is_file():
            entries.append({"path": rel, "kind": "file", "mode": mode,
                            "size": path.stat().st_size, "sha256": _digest(path)})
        else:
            raise RecoveryError(f"unsupported fixture entry: {rel}")
    return entries


def _sqlite_snapshot(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=0)
    dst = sqlite3.connect(destination)
    try:
        src.execute("PRAGMA query_only=ON")
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    os.chmod(destination, stat.S_IMODE(source.stat().st_mode))


def create_snapshot(source: Path, destination: Path) -> dict[str, object]:
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=False)
    root = _owned_root(source)
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise RecoveryError("snapshot destination is outside fictional root") from exc
    if source == destination or source in destination.parents or destination in source.parents:
        raise RecoveryError("source and snapshot must be separate trees")
    if destination.exists():
        raise RecoveryError("snapshot destination already exists")
    for rel in DATABASES:
        if not (source / rel).is_file():
            raise RecoveryError(f"required database missing: {rel}")
    ignored = {Path(name).name + suffix for name in DATABASES for suffix in ("-wal", "-shm", "-journal")}
    shutil.copytree(source, destination, symlinks=True,
                    ignore=lambda _directory, names: [name for name in names if name in ignored])
    for rel in DATABASES:
        _sqlite_snapshot(source / rel, destination / rel)
    manifest = {"schema": "cow.first-bootstrap.recovery-manifest/2",
                "databases": list(DATABASES), "entries": _inventory(destination)}
    (destination / "recovery-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_snapshot(snapshot: Path, manifest: dict[str, object]) -> None:
    _owned_root(snapshot)
    if manifest.get("schema") != "cow.first-bootstrap.recovery-manifest/2":
        raise RecoveryError("unsupported manifest")
    expected = manifest.get("entries")
    if not isinstance(expected, list):
        raise RecoveryError("invalid manifest entries")
    actual = [entry for entry in _inventory(snapshot) if entry["path"] != "recovery-manifest.json"]
    if actual != expected:
        raise RecoveryError("snapshot entries do not match manifest")
    for rel in DATABASES:
        db = sqlite3.connect(f"file:{snapshot / rel}?mode=ro", uri=True, timeout=0)
        try:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RecoveryError(f"SQLite integrity failed: {rel}")
        finally:
            db.close()


def restore_snapshot(snapshot: Path, target: Path, manifest: dict[str, object]) -> None:
    root = _owned_root(snapshot)
    target = target.resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RecoveryError("restore target is outside fictional root") from exc
    if target.exists():
        raise RecoveryError("restore target already exists")
    verify_snapshot(snapshot, manifest)
    shutil.copytree(snapshot, target, symlinks=True)
    (target / "recovery-manifest.json").unlink()
    if _inventory(target) != manifest["entries"]:
        raise RecoveryError("restored tree does not match snapshot manifest")
    for rel in DATABASES:
        db = sqlite3.connect(f"file:{target / rel}?mode=ro", uri=True, timeout=0)
        try:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise RecoveryError(f"restored SQLite integrity failed: {rel}")
        finally:
            db.close()


def _seed_legacy_conversations(path: Path, session_id: str, message: str) -> None:
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY, channel_type TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '', context_start_seq INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL, last_active INTEGER NOT NULL,
                msg_count INTEGER NOT NULL DEFAULT 0, pinned INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                seq INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
                created_at INTEGER NOT NULL, extras TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '', UNIQUE(session_id, seq)
            );
        """)
        db.execute("INSERT INTO sessions(session_id,channel_type,created_at,last_active,msg_count) VALUES(?, 'web', 1, 1, 1)", (session_id,))
        db.execute("INSERT INTO messages(session_id,seq,role,content,created_at) VALUES(?,0,'user',?,1)",
                   (session_id, json.dumps(message)))


def seed_fixture(root: Path) -> dict[str, str]:
    """Seed current native schemas and one supported legacy transcript."""
    root = root.resolve(strict=False)
    owner = _owned_root(root.parent)
    root.mkdir(mode=0o700)
    from agent.memory.conversation_store import ConversationStore
    from agent.memory.storage import MemoryChunk, MemoryStorage
    from agent.recovery.store import TaskStore

    ids = {name: str(uuid.uuid4()) for name in (
        "default_session", "testpilot2_session", "default_chunk", "testpilot_chunk",
        "testpilot2_chunk", "recovery_task", "recovery_effect", "later_chunk")}
    (root / "agents").mkdir(mode=0o700)
    team = {"default_agent_id": "default", "agents": [
        {"id": agent, "name": f"Fictional {agent}"}
        for agent in ("default", "testpilot", "testpilot2")
    ]}
    (root / "agents/team.json").write_text(json.dumps(team), encoding="utf-8")
    (root / "identity.json").write_text(json.dumps(team), encoding="utf-8")
    os.chmod(root / "identity.json", 0o600)

    global_db = root / DATABASES[0]
    global_db.parent.mkdir(parents=True, exist_ok=True)
    default = ConversationStore(global_db, agent_id="")
    assert default.append_messages(ids["default_session"],
        [{"role": "user", "content": "fictional default conversation"}], channel_type="web")
    shared = MemoryStorage(global_db)
    shared.save_chunk(MemoryChunk(ids["default_chunk"], None, "shared", "memory", "MEMORY.md",
        1, 1, "Fictional shared memory.", None, "fictional-default-hash"))
    shared.update_file_metadata("MEMORY.md", "memory", "fictional-default-hash", 1, 26)
    shared.close()

    for agent in ("testpilot", "testpilot2"):
        path = root / f"agents/{agent}/memory/long-term/index.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        storage = MemoryStorage(path)
        storage.save_chunk(MemoryChunk(ids[f"{agent}_chunk"], None, "shared", "memory", "MEMORY.md",
            1, 1, f"Fictional memory for {agent}.", None, f"fictional-{agent}-hash"))
        storage.update_file_metadata("MEMORY.md", "memory", f"fictional-{agent}-hash", 1, 30)
        storage.close()
    _seed_legacy_conversations(root / DATABASES[2], ids["testpilot2_session"],
                               "fictional testpilot2 transcript")

    task_store = TaskStore(root / DATABASES[3])
    verification = {"checks": ["fictional-state-continuity"]}
    task = task_store.submit("default", ids["default_session"], "fixture",
                             {"verification": verification})
    claim = task_store.claim(task["task_id"])
    assert claim is not None
    effect = task_store.before_tool(claim, "fictional-noop", mutating=False)
    assert task_store.after_tool(claim, effect, {"fixture": "complete"})
    assert task_store.finish(claim, "completed", result={"fixture": "complete"})
    attempt_id = claim.attempt_id
    claim.close()
    contract_hash = hashlib.sha256(TaskStore._json(verification).encode("utf-8")).hexdigest()
    assert task_store.record_verification(task["task_id"], attempt_id, contract_hash,
        {"acceptance": {"status": "passed"}, "external_state": {"status": "unverified"},
         "checked_at": "fictional"})
    (root / "unknown-extra.bin").write_bytes(b"fictional-extra")
    (root / "private-link").symlink_to("unknown-extra.bin")
    assert owner == _owned_root(root)
    return ids


def _set_registry(root: Path, include_testpilot2: bool) -> None:
    from agent.memory import clear_conversation_store_cache
    from agent.registry import AgentProfile, AgentRegistry, set_agent_registry

    profiles = [AgentProfile("default", "Fictional default", str(root)),
                AgentProfile("testpilot", "Fictional testpilot", str(root / "agents/testpilot"))]
    if include_testpilot2:
        profiles.append(AgentProfile("testpilot2", "Fictional testpilot2", str(root / "agents/testpilot2")))
    set_agent_registry(AgentRegistry(profiles, default_agent_id="default"))
    clear_conversation_store_cache()


def _clear_registry() -> None:
    from agent.memory import clear_conversation_store_cache
    from agent.registry import set_agent_registry

    set_agent_registry(None)
    clear_conversation_store_cache()


def _migrate(root: Path, include_testpilot2: bool) -> None:
    from agent.memory import migrate_conversations_to_global

    _set_registry(root, include_testpilot2)
    try:
        migrate_conversations_to_global(kickoff_async=False)
    finally:
        _clear_registry()


def _global_state(root: Path) -> dict[str, object]:
    db = sqlite3.connect(f"file:{root / DATABASES[0]}?mode=ro", uri=True)
    try:
        markers = sorted(row[0] for row in db.execute("SELECT key FROM _migration_meta"))
        sessions = db.execute("SELECT agent_id,session_id FROM sessions ORDER BY agent_id,session_id").fetchall()
        migrated = db.execute("SELECT count(*) FROM messages WHERE agent_id='testpilot2'").fetchone()[0]
        return {"markers": markers, "session_count": len(sessions), "migrated_messages": migrated}
    finally:
        db.close()


def _add_later_memory(root: Path, chunk_id: str) -> None:
    from agent.memory.storage import MemoryChunk, MemoryStorage

    storage = MemoryStorage(root / DATABASES[1])
    try:
        storage.save_chunk(MemoryChunk(chunk_id, None, "shared", "memory", "later.md", 1, 1,
            "Fictional post-checkpoint note.", None, "fictional-later-hash"))
        storage.update_file_metadata("later.md", "memory", "fictional-later-hash", 2, 35)
    finally:
        storage.close()


def _has_later_memory(root: Path, chunk_id: str) -> bool:
    db = sqlite3.connect(f"file:{root / DATABASES[1]}?mode=ro", uri=True)
    try:
        return db.execute("SELECT 1 FROM chunks WHERE id=?", (chunk_id,)).fetchone() is not None
    finally:
        db.close()


def run_fixture(parent: Path) -> dict[str, object]:
    """Run native DB snapshot, real migration, and isolated fallback reconciliation."""
    fictional_root = create_fictional_root(parent.resolve(strict=True))
    source = fictional_root / "checkpoint"
    ids = seed_fixture(source)
    old_data = os.environ.get("COW_DATA_DIR")
    try:
        os.environ["COW_DATA_DIR"] = str(source)
        _migrate(source, include_testpilot2=False)
        baseline = _global_state(source)
        assert baseline["markers"] == ["merged_agent:testpilot"]
        snapshot = fictional_root / "snapshot"
        manifest = create_snapshot(source, snapshot)
        verify_snapshot(snapshot, manifest)

        candidate = fictional_root / "failed-candidate"
        shutil.copytree(snapshot, candidate, symlinks=True)
        (candidate / "recovery-manifest.json").unlink()
        os.environ["COW_DATA_DIR"] = str(candidate)
        _migrate(candidate, include_testpilot2=True)
        candidate_state = _global_state(candidate)
        assert candidate_state["markers"] == ["merged_agent:testpilot", "merged_agent:testpilot2"]
        assert candidate_state["migrated_messages"] == 1
        with sqlite3.connect(candidate / DATABASES[2]) as db:
            source_tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "sessions" not in source_tables
        assert any(name.startswith("sessions_migrated_") for name in source_tables)

        later_file = candidate / "later-user-file.txt"
        later_file.write_text("fictional later user data", encoding="utf-8")
        _add_later_memory(candidate, ids["later_chunk"])
        failed_state_before_restore = _inventory(candidate)
        try:
            restore_snapshot(snapshot, candidate, manifest)
        except RecoveryError as exc:
            assert str(exc) == "restore target already exists"
        else:
            raise AssertionError("restore accepted an existing failed-candidate directory")
        assert _inventory(candidate) == failed_state_before_restore
        assert later_file.read_text(encoding="utf-8") == "fictional later user data"
        assert _has_later_memory(candidate, ids["later_chunk"])

        fallback = fictional_root / "fallback"
        restore_snapshot(snapshot, fallback, manifest)
        os.environ["COW_DATA_DIR"] = str(fallback)
        _migrate(fallback, include_testpilot2=True)
        fallback_state = _global_state(fallback)
        assert fallback_state == candidate_state
        shutil.copy2(later_file, fallback / later_file.name)
        _add_later_memory(fallback, ids["later_chunk"])
        assert (fallback / later_file.name).read_text(encoding="utf-8") == later_file.read_text(encoding="utf-8")
        _migrate(fallback, include_testpilot2=True)
        idempotent_state = _global_state(fallback)
        assert idempotent_state == candidate_state
        assert _has_later_memory(fallback, ids["later_chunk"])

        recovery = sqlite3.connect(f"file:{fallback / DATABASES[3]}?mode=ro", uri=True)
        try:
            recovery_counts = {name: recovery.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                               for name in ("recovery_tasks", "recovery_attempts", "recovery_effects", "recovery_verifications")}
            effect_names = [row[0] for row in recovery.execute("SELECT name FROM recovery_effects")]
        finally:
            recovery.close()
        assert recovery_counts == {"recovery_tasks": 1, "recovery_attempts": 1,
                                   "recovery_effects": 1, "recovery_verifications": 1}
        assert effect_names == ["fictional-noop"]
        assert (fallback / "unknown-extra.bin").read_bytes() == b"fictional-extra"
        assert (fallback / "private-link").is_symlink()
        assert stat.S_IMODE((fallback / "identity.json").stat().st_mode) == 0o600
        return {"status": "passed", "database_count": 4,
                "manifest_entry_count": len(manifest["entries"]), "native_schemas": True,
                "candidate_migration": "real migrate_conversations_to_global",
                "fallback_migration": "real migrate_conversations_to_global",
                "candidate_and_fallback_state_match": True,
                "migration_markers": idempotent_state["markers"],
                "migrated_testpilot2_messages": idempotent_state["migrated_messages"],
                "recovery_rows": recovery_counts,
                "effect_history": "preserved as inert rows; no effect executor/provider/client is invoked",
                "existing_candidate_restore": "refused; failed-candidate tree remained unchanged",
                "later_user_file_and_memory_row": "created before restore and explicitly reconciled into new fallback",
                "unknown_file_preserved": True, "symlink_and_mode_preserved": True,
                "actual_process_startup": False}
    finally:
        _clear_registry()
        if old_data is None:
            os.environ.pop("COW_DATA_DIR", None)
        else:
            os.environ["COW_DATA_DIR"] = old_data
