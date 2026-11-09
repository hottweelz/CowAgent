import importlib.util
import sqlite3
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "bootstrap_002_recovery_fixture",
    Path(__file__).parents[1] / "docs/first-bootstrap-002/recovery_fixture.py",
)
recovery_fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery_fixture)


def _tables(path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    finally:
        db.close()


def test_native_four_database_snapshot_and_real_migration_fallback(tmp_path):
    result = recovery_fixture.run_fixture(tmp_path)

    assert result["status"] == "passed"
    assert result["database_count"] == 4
    assert result["native_schemas"] is True
    assert result["candidate_migration"] == "real migrate_conversations_to_global"
    assert result["fallback_migration"] == "real migrate_conversations_to_global"
    assert result["candidate_and_fallback_state_match"] is True
    assert result["migration_markers"] == ["merged_agent:testpilot", "merged_agent:testpilot2"]
    assert result["migrated_testpilot2_messages"] == 1
    assert result["recovery_rows"] == {
        "recovery_tasks": 1, "recovery_attempts": 1,
        "recovery_effects": 1, "recovery_verifications": 1,
    }
    assert "no effect executor" in result["effect_history"]
    assert result["existing_candidate_restore"].startswith("refused")
    assert result["later_user_file_and_memory_row"].startswith("created before restore")


def test_native_database_schema_matches_cowagent_storage_classes(tmp_path):
    root = recovery_fixture.create_fictional_root(tmp_path)
    source = root / "source"
    recovery_fixture.seed_fixture(source)
    global_tables = _tables(source / recovery_fixture.DATABASES[0])
    memory_tables = _tables(source / recovery_fixture.DATABASES[1])
    recovery_tables = _tables(source / recovery_fixture.DATABASES[3])

    assert {"sessions", "messages", "runs", "artifacts", "chunks", "files"} <= global_tables
    assert {"chunks", "files", "chunks_fts", "chunks_fts_trigram"} <= memory_tables
    assert {"recovery_tasks", "recovery_attempts", "recovery_effects",
            "recovery_verifications"} <= recovery_tables
    for rel in recovery_fixture.DATABASES:
        db = sqlite3.connect(f"file:{source / rel}?mode=ro", uri=True)
        try:
            assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        finally:
            db.close()


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_manifest_rejects_missing_or_corrupt_entry(tmp_path, damage):
    root = recovery_fixture.create_fictional_root(tmp_path)
    source = root / "source"
    recovery_fixture.seed_fixture(source)
    snapshot = root / "snapshot"
    manifest = recovery_fixture.create_snapshot(source, snapshot)
    target = snapshot / "unknown-extra.bin"
    if damage == "missing":
        target.unlink()
    else:
        target.write_bytes(b"tampered fictional bytes")

    with pytest.raises(recovery_fixture.RecoveryError, match="do not match manifest"):
        recovery_fixture.verify_snapshot(snapshot, manifest)


def test_snapshot_api_rejects_path_without_private_fictional_marker(tmp_path):
    source = tmp_path / "unmarked-source"
    source.mkdir()

    with pytest.raises(recovery_fixture.RecoveryError, match="marker is missing"):
        recovery_fixture.create_snapshot(source, tmp_path / "backup")


def test_fictional_root_must_be_canonical_temp_and_private(tmp_path):
    with pytest.raises(recovery_fixture.RecoveryError, match="outside canonical temp root"):
        recovery_fixture.create_fictional_root(Path("/var/tmp"))
