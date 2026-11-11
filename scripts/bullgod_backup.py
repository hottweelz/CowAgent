#!/usr/bin/env python3
"""Create and inspect private, non-runnable BullGod state snapshots.

This helper does not start CowAgent. A backup contains consistent snapshots of
individual SQLite databases, not a globally atomic view of all runtime files.
Stop the BullGod service before using the CLI for a full recovery point.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import tempfile


VERSION = 1
SQLITE_HEADER = b"SQLite format 3\x00"
SQLITE_EXTENSIONS = {".db", ".sqlite", ".sqlite3"}
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
TREE_NAMES = ("data", "workspace", "home")
CONFIG_KEYS = {
    "model", "bot_type", "language", "agent_workspace", "default_agent_id",
    "default_agent_name", "default_agent_description", "agents", "agent_bindings",
    "agent_max_context_tokens", "agent_max_context_turns", "agent_max_steps",
    "reasoning_effort", "reasoning_effort_by_model", "web_host", "web_port",
    "self_evolution_idle_minutes", "self_evolution_min_turns",
}
PROFILE_KEYS = {
    "id", "name", "workspace", "description", "enabled", "model", "bot_type",
    "avatar", "skills", "knowledge",
}
BINDING_KEYS = {"channel_type", "conversation_id", "agent_id", "instance_id"}
TEAM_KEYS = {"agents", "default_agent_id", "channel_instances"}
SECRET_PARTS = ("credential", "token", "secret", "password", "cookie", "auth", "api_key")
EXCLUDED_CONFIG_NAMES = {"config.json", "mcp.json", "plugins.json", "skills_config.json", "settings.json"}


class BackupError(ValueError):
    """Input or snapshot failed a safety check."""


def _private_dir(path: Path, *, create: bool = False) -> None:
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=False)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise BackupError(f"directory must be owner-private: {path}")


def _runtime_root(value: Path) -> Path:
    root = Path(value).expanduser().resolve(strict=True)
    _private_dir(root)
    marker_path = root / "instance.json"
    if marker_path.is_symlink() or not marker_path.is_file() or marker_path.stat().st_nlink != 1:
        raise BackupError("runtime instance marker must be a private regular file")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError("runtime instance marker is unreadable") from exc
    if marker.get("version") != 1 or marker.get("root") != str(root):
        raise BackupError("runtime instance marker does not match this root")
    for name in ("source", "data", "workspace", "config", "home", "tmp"):
        path = root / name
        if path.is_symlink() or not path.is_dir() or path.resolve() != path:
            raise BackupError(f"runtime path must be a real directory: {name}")
        if path.stat().st_uid != os.getuid():
            raise BackupError(f"runtime path has a different owner: {name}")
    config = root / "config" / "config.json"
    if config.is_symlink() or not config.is_file() or config.stat().st_nlink != 1:
        raise BackupError("runtime config must be a private regular file")
    data_config = root / "data" / "config.json"
    if data_config.is_symlink():
        if data_config.resolve(strict=True) != config.resolve(strict=True):
            raise BackupError("data/config.json symlink must point to config/config.json")
    elif data_config.exists() and (not data_config.is_file() or data_config.stat().st_nlink != 1):
        raise BackupError("data/config.json must be a regular file or the known config symlink")
    return root


def _load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError(f"{label} is not readable JSON") from exc
    if not isinstance(value, dict):
        raise BackupError(f"{label} must contain an object")
    return value


def _filtered_items(value, allowed: set[str]) -> dict:
    return {key: item for key, item in value.items() if key in allowed}


def _safe_config(root: Path) -> dict:
    raw = _load_json(root / "config" / "config.json", "runtime config")
    safe = _filtered_items(raw, CONFIG_KEYS)
    agents = safe.get("agents")
    if isinstance(agents, list):
        safe["agents"] = [_filtered_items(item, PROFILE_KEYS) for item in agents if isinstance(item, dict)]
    bindings = safe.get("agent_bindings")
    if isinstance(bindings, list):
        safe["agent_bindings"] = [_filtered_items(item, BINDING_KEYS) for item in bindings if isinstance(item, dict)]
    # Keep this inspection document from exposing an unauthenticated web console
    # if someone later copies it into an active data directory.
    safe.update({
        "channel_type": "terminal", "web_host": "127.0.0.1", "web_port": 0,
        "web_console": False, "agent": False,
        "external_api_enabled": False, "agent_permission_mode": "read-only",
        "self_evolution_enabled": False,
        "personal_http_endpoints": {}, "personal_http_relays": {},
    })
    return safe


def _safe_team(path: Path) -> dict:
    raw = _load_json(path, "workspace Agent roster")
    safe = {}
    if isinstance(raw.get("agents"), list):
        safe["agents"] = [_filtered_items(item, PROFILE_KEYS) for item in raw["agents"] if isinstance(item, dict)]
    if isinstance(raw.get("default_agent_id"), str):
        safe["default_agent_id"] = raw["default_agent_id"]
    # Keep the roster inspectable, but remove channel instances so restore cannot
    # reopen a network channel from this snapshot.
    if "channel_instances" in raw:
        safe["channel_instances"] = []
    return safe


def _is_sensitive_name(path: Path) -> bool:
    name = path.name.lower()
    return (name == ".env" or name.startswith(".env.") or name in EXCLUDED_CONFIG_NAMES
            or any(part in name for part in SECRET_PARTS))


def _is_sidecar(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(SIDECAR_SUFFIXES)


def _is_log(path: Path) -> bool:
    return re.search(r"\.log(?:\.\d+)?(?:\.gz)?$", path.name, re.IGNORECASE) is not None


def _sqlite_kind(path: Path) -> bool:
    if path.suffix.lower() in SQLITE_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            return handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER
    except OSError as exc:
        raise BackupError(f"cannot inspect file: {path.name}") from exc


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    names = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    result = {}
    for name in names:
        quoted_name = '"' + name.replace('"', '""') + '"'
        result[name] = int(connection.execute(f"SELECT count(*) FROM {quoted_name}").fetchone()[0])
    return result


def sqlite_snapshot(source_path: Path, destination_path: Path) -> dict:
    """Make a consistent SQLite snapshot, including committed WAL content."""
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    if not _sqlite_kind(source_path):
        raise BackupError(f"SQLite database has no recognized header: {source_path.name}")
    uri = source_path.resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=10)) as source:
            with closing(sqlite3.connect(str(destination_path), timeout=10)) as target:
                source.backup(target, pages=256, sleep=0.05)
        os.chmod(destination_path, 0o600)
        with sqlite3.connect(str(destination_path), timeout=10) as check:
            integrity = [row[0] for row in check.execute("PRAGMA integrity_check")]
            if integrity != ["ok"]:
                raise BackupError(f"SQLite integrity check failed: {source_path.name}")
            counts = _table_counts(check)
        return {"integrity": "ok", "tables": counts}
    except (sqlite3.Error, OSError) as exc:
        raise BackupError(f"SQLite snapshot failed: {source_path.name}: {exc}") from exc


def _walk(root: Path, directory: Path):
    """List regular files and every intentionally omitted path."""
    files_out = []
    excluded = []
    root_device = root.stat().st_dev

    def fail_walk(error):
        raise BackupError(f"cannot inspect runtime state: {error.filename}") from error

    for current, dirs, files in os.walk(directory, followlinks=False, onerror=fail_walk):
        current_path = Path(current)
        kept_dirs = []
        for name in sorted(dirs):
            path = current_path / name
            if path.is_symlink():
                raise BackupError(f"unexpected symlink in runtime state: {path.relative_to(root)}")
            info = path.stat()
            if info.st_uid != os.getuid() or info.st_dev != root_device:
                raise BackupError(f"runtime directory owner or filesystem differs: {path.relative_to(root)}")
            if _is_sensitive_name(path) or name.lower() in {"logs", "cache", "caches"}:
                excluded.append({"path": path.relative_to(root).as_posix(), "reason": "sensitive-or-transient-name"})
            else:
                kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in sorted(files):
            path = current_path / name
            rel = path.relative_to(root)
            if path.is_symlink():
                if rel.as_posix() == "data/config.json" and path.resolve(strict=True) == (root / "config/config.json").resolve():
                    excluded.append({"path": rel.as_posix(), "reason": "known-config-symlink"})
                    continue
                raise BackupError(f"unexpected symlink in runtime state: {rel}")
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise BackupError(f"runtime state is not an owner-owned regular file: {rel}")
            if info.st_dev != root_device:
                raise BackupError(f"runtime state crosses a filesystem boundary: {rel}")
            if info.st_nlink != 1:
                raise BackupError(f"hard-linked runtime state is not allowed: {rel}")
            if _is_sensitive_name(path):
                excluded.append({"path": rel.as_posix(), "reason": "sensitive-name"})
                continue
            if rel.as_posix() == "data/config.json":
                continue
            if _is_log(path) or path.suffix.lower() in {".pyc", ".pyo"} or _is_sidecar(path):
                excluded.append({"path": rel.as_posix(), "reason": "log-bytecode-or-sqlite-sidecar"})
                continue
            files_out.append(path)
    return files_out, excluded


def create_snapshot(runtime: Path, destination: Path, *, quiescent: bool = False) -> dict:
    """Create a new private snapshot. Source state is read only."""
    root = _runtime_root(runtime)
    destination = Path(destination).expanduser()
    if not quiescent:
        raise BackupError("a full recovery snapshot requires --quiescent after the service is stopped")
    if destination.exists() or destination.is_symlink():
        raise BackupError("snapshot destination must not already exist")
    parent = destination.parent.resolve(strict=True)
    _private_dir(parent)
    destination = parent / destination.name
    if destination == root or destination.is_relative_to(root):
        raise BackupError("snapshot destination must be outside the runtime root")
    if not destination.name or destination.name in {".", ".."}:
        raise BackupError("invalid snapshot destination")

    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.partial-", dir=parent))
    os.chmod(stage, 0o700)
    exclusions = [
        {"path": "source", "reason": "versioned-release-not-state"},
        {"path": "tmp", "reason": "transient-runtime-data"},
        {"path": "instance.json", "reason": "machine-specific-active-marker"},
        {"path": "service.json", "reason": "active-service-marker"},
        {"path": "sandbox.sb", "reason": "machine-specific-active-policy"},
        {"path": "model_bootstrap.py", "reason": "active-launch-code"},
    ]
    databases = {}
    copied = 0
    try:
        for name in TREE_NAMES:
            source_dir = root / name
            target_dir = stage / name
            target_dir.mkdir(mode=0o700)
            tree_files, tree_exclusions = _walk(root, source_dir)
            exclusions.extend(tree_exclusions)
            for source in tree_files:
                rel = source.relative_to(root)
                target = stage / rel
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if rel.as_posix() == "workspace/agents/team.json":
                    target.write_text(json.dumps(_safe_team(source), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    os.chmod(target, 0o600)
                elif _is_sidecar(source):
                    exclusions.append({"path": rel.as_posix(), "reason": "sqlite-sidecar-included-by-backup-api"})
                elif _sqlite_kind(source):
                    result = sqlite_snapshot(source, target)
                    databases[rel.as_posix()] = result
                else:
                    shutil.copyfile(source, target)
                    os.chmod(target, 0o600)
                copied += 1

        config_dir = stage / "config"
        config_dir.mkdir(mode=0o700)
        safe_config = _safe_config(root)
        (config_dir / "config.json").write_text(json.dumps(safe_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.chmod(config_dir / "config.json", 0o600)
        exclusions.extend([
            {"path": "config/config.json", "reason": "replaced-with-safe-inspection-config"},
            {"path": "service.json", "reason": "not-restorable-or-startable"},
            {"path": "model-credential", "reason": "credential-is-stored-outside-runtime-root"},
        ])
        manifest = {
            "format": "bullgod-state-snapshot", "version": VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_root_id": hashlib.sha256(str(root).encode()).hexdigest()[:16],
            "quiescent_asserted": True, "database_consistency": "per-database SQLite backup API",
            "globally_atomic": False, "complete": True, "runnable": False,
            "copied_files": copied + 1, "databases": databases,
            "excluded": _unique_exclusions(exclusions),
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.chmod(stage / "manifest.json", 0o600)
        _inspect_snapshot(stage)
        os.rename(stage, destination)
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _unique_exclusions(items):
    seen, result = set(), []
    for item in items:
        key = (item["path"], item["reason"])
        if key not in seen:
            seen.add(key)
            result.append({"path": key[0], "reason": key[1]})
    return result


def _inspect_snapshot(snapshot: Path) -> dict:
    snapshot = Path(snapshot).resolve(strict=True)
    _private_dir(snapshot)
    manifest = _load_json(snapshot / "manifest.json", "snapshot manifest")
    if (manifest.get("format") != "bullgod-state-snapshot" or manifest.get("version") != VERSION
            or manifest.get("complete") is not True or manifest.get("runnable") is not False):
        raise BackupError("snapshot is incomplete or may be runnable")
    results = {}
    declared = manifest.get("databases", {})
    if not isinstance(declared, dict):
        raise BackupError("snapshot database list is invalid")
    for relative, expected in declared.items():
        rel = PurePosixPath(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise BackupError("snapshot database path is unsafe")
        path = snapshot.joinpath(*rel.parts)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(snapshot):
            raise BackupError(f"snapshot database is missing or unsafe: {relative}")
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
            integrity = [row[0] for row in db.execute("PRAGMA integrity_check")]
            counts = _table_counts(db)
        if integrity != ["ok"] or expected.get("integrity") != "ok" or counts != expected.get("tables"):
            raise BackupError(f"snapshot database verification failed: {relative}")
        results[relative] = {"integrity": "ok", "tables": counts}
    return {"manifest": manifest, "databases": results}


def inspect_snapshot(snapshot: Path) -> dict:
    """Check a snapshot without starting an application or service."""
    return _inspect_snapshot(Path(snapshot))


def restore_drill(snapshot: Path, destination: Path) -> dict:
    """Copy a snapshot to a new, non-runnable inspection directory."""
    snapshot = Path(snapshot).expanduser().resolve(strict=True)
    _inspect_snapshot(snapshot)
    destination = Path(destination).expanduser()
    if destination.exists() or destination.is_symlink():
        raise BackupError("restore drill destination must be new")
    if not destination.name.startswith("bullgod-restore-"):
        raise BackupError("restore drill destination name must start with bullgod-restore-")
    parent = destination.parent.resolve(strict=True)
    _private_dir(parent)
    destination = parent / destination.name
    if destination == snapshot or destination.is_relative_to(snapshot) or snapshot.is_relative_to(destination):
        raise BackupError("restore drill destination must be isolated from the snapshot")
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.partial-", dir=parent))
    os.chmod(stage, 0o700)
    try:
        for current, dirs, files in os.walk(snapshot, followlinks=False):
            current_path = Path(current)
            rel_dir = current_path.relative_to(snapshot)
            dest_dir = stage / rel_dir
            for name in dirs:
                path = current_path / name
                if path.is_symlink():
                    raise BackupError("snapshot contains an unexpected symlink")
                (dest_dir / name).mkdir(mode=0o700, exist_ok=True)
            for name in files:
                source = current_path / name
                if source.is_symlink() or source.stat().st_nlink != 1:
                    raise BackupError("snapshot contains a symlink or hard-linked file")
                target = dest_dir / name
                shutil.copyfile(source, target)
                os.chmod(target, 0o600)
        _inspect_snapshot(stage)
        os.rename(stage, destination)
        return _inspect_snapshot(destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="create a new private state snapshot")
    backup.add_argument("runtime", type=Path)
    backup.add_argument("destination", type=Path)
    backup.add_argument("--quiescent", action="store_true", required=True,
                        help="assert BullGod has stopped; required for a full recovery point")
    inspect = commands.add_parser("inspect", help="check SQLite integrity and table counts")
    inspect.add_argument("snapshot", type=Path)
    restore = commands.add_parser("restore-drill", help="copy to a new isolated inspection directory")
    restore.add_argument("snapshot", type=Path)
    restore.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            result = create_snapshot(args.runtime, args.destination, quiescent=args.quiescent)
        elif args.command == "inspect":
            result = inspect_snapshot(args.snapshot)
        else:
            result = restore_drill(args.snapshot, args.destination)
    except (BackupError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
