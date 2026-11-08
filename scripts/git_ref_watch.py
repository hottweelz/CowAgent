#!/usr/bin/env python3
"""Poll a repository's Git refs and write safe change summaries as JSONL.

This is a read-only polling monitor. It does not attribute a change to a
process, and it can miss transient changes between samples.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

OID_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
CONFLICT_RE = re.compile(r"conflict", re.IGNORECASE)
MIN_DURATION = 0.1
MAX_DURATION = 3600.0
MIN_INTERVAL = 0.05
MAX_INTERVAL = 60.0


def git(repo: Path, *args: str) -> str:
    env = os.environ.copy()
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def repository_paths(repo: Path) -> tuple[Path, Path, Path]:
    repo = repo.resolve()
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    worktree_git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir")).resolve()
    common_value = Path(git(root, "rev-parse", "--git-common-dir"))
    common_dir = (root / common_value).resolve() if not common_value.is_absolute() else common_value.resolve()
    return root, worktree_git_dir, common_dir


def safe_ref_value(path: Path) -> str:
    """Return only a full object ID or valid symbolic-ref target."""
    try:
        info = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            return f"invalid:size={info.st_size}:mtime_ns={info.st_mtime_ns}"
        raw = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return "unreadable"
    if OID_RE.fullmatch(raw):
        return raw.lower()
    if raw.startswith("ref: ") and "\n" not in raw:
        target = raw[5:]
        checked = subprocess.run(["git", "check-ref-format", target], capture_output=True, check=False)
        if checked.returncode == 0:
            return f"symbolic:{target}"
    return f"invalid:size={info.st_size}:mtime_ns={info.st_mtime_ns}"


def ref_name_is_valid(name: str) -> bool:
    return subprocess.run(["git", "check-ref-format", name], capture_output=True, check=False).returncode == 0


def collect_loose_refs(refs_dir: Path, source: str) -> tuple[dict[str, str], list[str]]:
    refs: dict[str, str] = {}
    invalid_conflicts: list[str] = []
    if not refs_dir.is_dir():
        return refs, invalid_conflicts
    for directory, dirs, files in os.walk(refs_dir, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for filename in sorted(files):
            path = Path(directory) / filename
            relative = path.relative_to(refs_dir).as_posix()
            refname = f"refs/{relative}"
            key = f"{source}:{refname}"
            refs[key] = safe_ref_value(path)
            if CONFLICT_RE.search(relative) and not ref_name_is_valid(refname):
                invalid_conflicts.append(key)
    return refs, invalid_conflicts


def collect_packed_refs(packed_path: Path, source: str) -> tuple[dict[str, str], list[str]]:
    refs: dict[str, str] = {}
    invalid_conflicts: list[str] = []
    try:
        with packed_path.open("r", encoding="ascii", errors="replace") as stream:
            for line_number, line in enumerate(stream, 1):
                fields = line.rstrip("\n").split(" ", 1)
                if len(fields) != 2 or fields[0].startswith("^"):
                    continue
                oid, refname = fields
                if not refname.startswith("refs/"):
                    continue
                key = f"{source}:packed:{refname}"
                conflict_name = bool(CONFLICT_RE.search(refname))
                if OID_RE.fullmatch(oid) and (not conflict_name or ref_name_is_valid(refname)):
                    refs[key] = oid.lower()
                else:
                    # Do not include potentially malformed file contents.
                    refs[key] = f"invalid:line={line_number}"
                    if conflict_name:
                        invalid_conflicts.append(key)
    except FileNotFoundError:
        pass
    except OSError:
        refs[f"{source}:packed-refs"] = "unreadable"
    return refs, invalid_conflicts


def snapshot(worktree_git_dir: Path, common_dir: Path) -> dict[str, Any]:
    refs, invalid_conflicts = collect_loose_refs(common_dir / "refs", "common")
    packed, packed_invalid = collect_packed_refs(common_dir / "packed-refs", "common")
    refs.update(packed)
    invalid_conflicts.extend(packed_invalid)

    if worktree_git_dir != common_dir:
        local_refs, local_invalid = collect_loose_refs(worktree_git_dir / "refs", "worktree")
        local_packed, local_packed_invalid = collect_packed_refs(
            worktree_git_dir / "packed-refs", "worktree"
        )
        refs.update(local_refs)
        refs.update(local_packed)
        invalid_conflicts.extend(local_invalid)
        invalid_conflicts.extend(local_packed_invalid)

    refs["worktree:HEAD"] = safe_ref_value(worktree_git_dir / "HEAD")
    return {"refs": refs, "invalid_conflict_ref_names": sorted(set(invalid_conflicts))}


def parse_expected(values: list[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid --expect-ref {value!r}; expected REF=SHA")
        refname, oid = value.split("=", 1)
        if not ref_name_is_valid(refname) or not OID_RE.fullmatch(oid):
            raise ValueError(f"invalid --expect-ref {value!r}; expected a valid ref and full SHA")
        expected[refname] = oid.lower()
    return expected


def expected_mismatches(repo: Path, expected: dict[str, str]) -> list[dict[str, str]]:
    mismatches = []
    for refname, want in sorted(expected.items()):
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo), "show-ref", "--verify", "--hash", refname],
            capture_output=True, text=True, check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"},
        )
        actual = result.stdout.strip().lower() if result.returncode == 0 else "missing-or-invalid"
        if actual != want:
            mismatches.append({"ref": refname, "expected": want, "actual": actual})
    return mismatches


def diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, str]]:
    old, new = before["refs"], after["refs"]
    changes = []
    for name in sorted(old.keys() | new.keys()):
        prior, current = old.get(name), new.get(name)
        if prior != current:
            changes.append({
                "ref": name,
                "before": prior if prior is not None else "absent",
                "after": current if current is not None else "absent",
            })
    return changes


def emit(stream: Any, record: dict[str, Any]) -> None:
    stream.write(json.dumps(record, sort_keys=True) + "\n")
    stream.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="repository or worktree path")
    parser.add_argument("--duration", required=True, type=float, help="watch duration in seconds (0.1–3600)")
    parser.add_argument("--interval", required=True, type=float, help="poll interval in seconds (0.05–60)")
    parser.add_argument("--output", required=True, type=Path, help="caller-chosen JSONL output path")
    parser.add_argument(
        "--expect-ref", action="append", default=[], metavar="REF=SHA",
        help="require a full object SHA at baseline and end; may be repeated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not MIN_DURATION <= args.duration <= MAX_DURATION:
        parser.error(f"--duration must be between {MIN_DURATION} and {MAX_DURATION} seconds")
    if not MIN_INTERVAL <= args.interval <= MAX_INTERVAL:
        parser.error(f"--interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} seconds")
    try:
        expected = parse_expected(args.expect_ref)
        root, worktree_git_dir, common_dir = repository_paths(args.repo.resolve())
    except (ValueError, subprocess.CalledProcessError, OSError) as exc:
        parser.error(str(exc))

    output = args.output.expanduser().resolve()
    if any(output == path or path in output.parents for path in (root, common_dir, worktree_git_dir)):
        parser.error("--output must be outside the repository and Git metadata")
    if args.output.is_symlink():
        parser.error("--output must not be a symbolic link")
    output.parent.mkdir(parents=True, exist_ok=True)

    deadline = time.monotonic() + args.duration
    previous = snapshot(worktree_git_dir, common_dir)
    with output.open("a", encoding="utf-8") as stream:
        initial_mismatches = expected_mismatches(root, expected)
        problem_seen = bool(initial_mismatches or previous["invalid_conflict_ref_names"])
        emit(stream, {
            "type": "baseline", "time": time.time(), "repo": str(root),
            "common_git_dir": str(common_dir), "worktree_git_dir": str(worktree_git_dir),
            **previous, "expected_ref_mismatches": initial_mismatches,
        })
        while time.monotonic() < deadline:
            time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
            current = snapshot(worktree_git_dir, common_dir)
            changes = diff(previous, current)
            mismatches = expected_mismatches(root, expected)
            problem_seen |= bool(mismatches or current["invalid_conflict_ref_names"])
            if changes or current["invalid_conflict_ref_names"] != previous["invalid_conflict_ref_names"] or mismatches:
                emit(stream, {
                    "type": "change", "time": time.time(), "changes": changes,
                    "invalid_conflict_ref_names": current["invalid_conflict_ref_names"],
                    "expected_ref_mismatches": mismatches,
                })
            previous = current

        final_mismatches = expected_mismatches(root, expected)
        problem_seen |= bool(final_mismatches or previous["invalid_conflict_ref_names"])
        emit(stream, {
            "type": "final", "time": time.time(),
            "invalid_conflict_ref_names": previous["invalid_conflict_ref_names"],
            "expected_ref_mismatches": final_mismatches,
            "result": "problem" if problem_seen else "ok",
        })
    return 2 if problem_seen else 0


if __name__ == "__main__":
    sys.exit(main())
