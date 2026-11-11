"""Focused safety checks for the offline BullGod snapshot helper."""

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/bullgod_backup.py"
spec = importlib.util.spec_from_file_location("bullgod_backup", SCRIPT)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def make_runtime(parent: Path) -> Path:
    root = (parent / "bullgod-runtime").resolve()
    root.mkdir(mode=0o700)
    for name in ("source", "data", "workspace", "config", "home", "tmp"):
        (root / name).mkdir(mode=0o700)
    config = {
        "channel_type": "web", "web_host": "127.0.0.1", "web_port": 29892,
        "web_password": "config-password-canary", "open_ai_api_key": "provider-key-canary",
        "model": "gpt-6-luna", "bot_type": "openai",
        "agent_workspace": str(root / "workspace"), "default_agent_id": "bullgod",
        "default_agent_name": "BullGod", "personal_http_endpoints": {"https://news.example/api": []},
        "unknown_secret": "unknown-secret-canary",
    }
    (root / "config/config.json").write_text(json.dumps(config), encoding="utf-8")
    (root / "data/config.json").symlink_to(root / "config/config.json")
    (root / "instance.json").write_text(json.dumps({"version": 1, "root": str(root)}), encoding="utf-8")
    (root / "service.json").write_text('{"label":"active-service"}', encoding="utf-8")
    (root / "workspace/AGENT.md").write_text("# BullGod\n", encoding="utf-8")
    (root / "workspace/agents").mkdir(mode=0o700)
    team = {
        "default_agent_id": "bullgod",
        "agents": [{"id": "bullgod", "name": "BullGod", "workspace": str(root / "workspace"),
                    "model": "gpt-6-luna", "enabled": True, "provider_api_key": "roster-key-canary"}],
        "channel_instances": [{"instance_id": "web-main", "channel_type": "web",
                               "agent_id": "bullgod", "credentials": {"token": "channel-token-canary"}}],
        "unknown_secret": "roster-secret-canary",
    }
    (root / "workspace/agents/team.json").write_text(json.dumps(team), encoding="utf-8")
    return root


def create_db(path: Path, *, keep_open=False):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
    connection.execute("INSERT INTO records(value) VALUES ('committed-in-wal')")
    connection.commit()
    return connection if keep_open else connection.close()


class BullGodBackupTests(unittest.TestCase):
    def test_sqlite_online_backup_includes_committed_wal_without_touching_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "index.db"
            target = root / "snapshot/index.db"
            target.parent.mkdir(mode=0o700)
            live = create_db(source, keep_open=True)
            self.addCleanup(live.close)
            self.assertTrue(Path(str(source) + "-wal").exists())
            result = backup.sqlite_snapshot(source, target)

            self.assertEqual(result["integrity"], "ok")
            self.assertEqual(result["tables"]["records"], 1)
            with sqlite3.connect(target) as db:
                self.assertEqual(db.execute("SELECT value FROM records").fetchone()[0], "committed-in-wal")
            self.assertEqual(live.execute("SELECT count(*) FROM records").fetchone()[0], 1)

    def test_snapshot_redacts_configs_secrets_and_active_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = make_runtime(parent)
            create_db(root / "workspace/memory/long-term/index.db")
            (root / "data/run.log").write_text("log-private-canary", encoding="utf-8")
            (root / "data/run.log.1").write_text("rotated-log-private-canary", encoding="utf-8")
            (root / "data/.env").write_text("MODEL_KEY=env-private-canary", encoding="utf-8")
            (root / "workspace/credentials.json").write_text('{"token":"file-token-canary"}', encoding="utf-8")
            (root / "home/session_token_store.json").write_text("home-token-canary", encoding="utf-8")
            target = parent / "backups/snapshot-1"
            target.parent.mkdir(mode=0o700)

            result = backup.create_snapshot(root, target, quiescent=True)

            self.assertFalse((target / "instance.json").exists())
            self.assertFalse((target / "service.json").exists())
            self.assertFalse((target / "data/config.json").exists())
            self.assertFalse((target / "data/run.log").exists())
            self.assertFalse((target / "data/run.log.1").exists())
            self.assertFalse((target / "data/.env").exists())
            self.assertFalse((target / "workspace/credentials.json").exists())
            self.assertFalse((target / "home/session_token_store.json").exists())
            self.assertTrue(result["complete"])
            self.assertFalse(result["runnable"])
            self.assertTrue(result["globally_atomic"] is False)
            safe_config = json.loads((target / "config/config.json").read_text())
            self.assertEqual(safe_config["model"], "gpt-6-luna")
            self.assertFalse(safe_config["agent"])
            self.assertFalse(safe_config["web_console"])
            self.assertEqual(safe_config["channel_type"], "terminal")
            self.assertEqual(safe_config["web_port"], 0)
            self.assertEqual(safe_config["personal_http_endpoints"], {})
            text = "\n".join(path.read_text(errors="ignore") for path in target.rglob("*") if path.is_file())
            for secret in ("config-password-canary", "provider-key-canary", "unknown-secret-canary",
                           "roster-key-canary", "channel-token-canary", "roster-secret-canary",
                           "env-private-canary", "file-token-canary", "home-token-canary",
                           "log-private-canary", "rotated-log-private-canary"):
                self.assertNotIn(secret, text)
            team = json.loads((target / "workspace/agents/team.json").read_text())
            self.assertEqual(team["agents"][0]["id"], "bullgod")
            self.assertNotIn("provider_api_key", team["agents"][0])
            self.assertEqual(team["channel_instances"], [])
            self.assertIn({"path": "data/.env", "reason": "sensitive-name"}, result["excluded"])
            self.assertEqual(backup.inspect_snapshot(target)["databases"]["workspace/memory/long-term/index.db"]["tables"]["records"], 1)

    def test_failed_snapshot_does_not_change_source_or_publish_partial_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = make_runtime(parent)
            bad_db = root / "workspace/bad.db"
            bad_db.write_bytes(b"not a database")
            before = bad_db.read_bytes()
            target = parent / "snapshot"

            with self.assertRaises(backup.BackupError):
                backup.create_snapshot(root, target, quiescent=True)

            self.assertEqual(bad_db.read_bytes(), before)
            self.assertFalse(target.exists())
            self.assertEqual(list(parent.glob(".snapshot.partial-*")), [])

    def test_full_snapshot_requires_explicit_quiescence(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = make_runtime(parent)
            with self.assertRaisesRegex(backup.BackupError, "requires --quiescent"):
                backup.create_snapshot(root, parent / "snapshot", quiescent=False)
            self.assertFalse((parent / "snapshot").exists())

    def test_restore_drill_requires_new_isolated_path_and_checks_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = make_runtime(parent)
            create_db(root / "workspace/memory/recovery/tasks.db")
            snapshot = parent / "snapshot"
            backup.create_snapshot(root, snapshot, quiescent=True)
            existing = parent / "bullgod-restore-existing"
            existing.mkdir()
            with self.assertRaises(backup.BackupError):
                backup.restore_drill(snapshot, existing)
            with self.assertRaises(backup.BackupError):
                backup.restore_drill(snapshot, parent / "unisolated")

            restored = parent / "bullgod-restore-drill-1"
            result = backup.restore_drill(snapshot, restored)

            self.assertEqual(result["databases"]["workspace/memory/recovery/tasks.db"]["integrity"], "ok")
            self.assertFalse((restored / "instance.json").exists())
            self.assertFalse((restored / "service.json").exists())
            self.assertFalse((restored / "source").exists())

    def test_unrecognized_symlink_and_hardlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = make_runtime(parent)
            outside = parent / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (root / "workspace/escape.txt").symlink_to(outside)
            with self.assertRaises(backup.BackupError):
                backup.create_snapshot(root, parent / "snapshot-symlink", quiescent=True)
            (root / "workspace/escape.txt").unlink()
            os.link(outside, root / "workspace/hardlinked.txt")
            with self.assertRaises(backup.BackupError):
                backup.create_snapshot(root, parent / "snapshot-hardlink", quiescent=True)
            self.assertFalse((parent / "snapshot-symlink").exists())
            self.assertFalse((parent / "snapshot-hardlink").exists())


if __name__ == "__main__":
    unittest.main()
