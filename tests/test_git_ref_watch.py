"""Focused tests for safe Git-ref polling and expected-ref validation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import git_ref_watch


class GitRefWatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="git ref watch test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.template = self.base / "template"
        self.template.mkdir()
        self.env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        }
        self.run_git("init", "--quiet", "--initial-branch=main", f"--template={self.template}", str(self.repo))
        self.run_git("config", "user.name", "Ref Watch Test")
        self.run_git("config", "user.email", "ref-watch@example.invalid")
        self.run_git("config", "core.hooksPath", os.devnull)
        (self.repo / "file.txt").write_text("first\n", encoding="utf-8")
        self.run_git("add", "file.txt")
        self.run_git("commit", "--quiet", "-m", "test commit")
        self.worktree_git_dir = Path(git_ref_watch.git(self.repo, "rev-parse", "--absolute-git-dir"))
        self.common_dir = Path(git_ref_watch.git(self.repo, "rev-parse", "--git-common-dir"))
        if not self.common_dir.is_absolute():
            self.common_dir = (self.repo / self.common_dir).resolve()

    def run_git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "--no-optional-locks", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
            env=self.env,
        ).stdout.strip()

    def test_valid_ref_update_and_conflicted_copy_are_reported(self) -> None:
        first = self.run_git("rev-parse", "HEAD")
        self.run_git("update-ref", "refs/heads/observed", first)
        before = git_ref_watch.snapshot(self.worktree_git_dir, self.common_dir)
        (self.repo / "file.txt").write_text("second\n", encoding="utf-8")
        self.run_git("add", "file.txt")
        self.run_git("commit", "--quiet", "-m", "second commit")
        second = self.run_git("rev-parse", "HEAD")
        self.run_git("update-ref", "refs/heads/observed", second, first)
        self.run_git("update-ref", "refs/heads/created", second)
        conflict = self.common_dir / "refs/heads/main [conflicted]"
        conflict.write_text(f"{second}\n", encoding="ascii")
        after = git_ref_watch.snapshot(self.worktree_git_dir, self.common_dir)

        changes = git_ref_watch.diff(before, after)
        by_ref = {change["ref"]: change for change in changes}
        self.assertEqual(by_ref["common:refs/heads/observed"]["before"], first)
        self.assertEqual(by_ref["common:refs/heads/observed"]["after"], second)
        self.assertEqual(by_ref["common:refs/heads/created"]["before"], "absent")
        self.assertEqual(by_ref["common:refs/heads/created"]["after"], second)
        self.assertIn("common:refs/heads/main [conflicted]", by_ref)
        self.assertEqual(after["invalid_conflict_ref_names"], ["common:refs/heads/main [conflicted]"])

    def test_linked_worktree_uses_shared_common_directory(self) -> None:
        linked = self.base / "linked worktree"
        self.run_git("worktree", "add", "--quiet", "--detach", str(linked))

        root, worktree_git_dir, common_dir = git_ref_watch.repository_paths(linked)
        observed = git_ref_watch.snapshot(worktree_git_dir, common_dir)

        self.assertEqual(root, linked.resolve())
        self.assertEqual(common_dir, self.common_dir)
        self.assertIn("common:refs/heads/main", observed["refs"])
        self.assertIn("worktree:HEAD", observed["refs"])

    def test_conflict_ref_failure_is_latched_after_copy_is_removed(self) -> None:
        output = self.base / "watch-conflict.jsonl"
        conflict = self.common_dir / "refs/heads/main [conflicted]"
        script = Path(git_ref_watch.__file__).resolve()
        process = subprocess.Popen(
            [
                sys.executable, str(script), "--repo", str(self.repo),
                "--duration", "0.6", "--interval", "0.05", "--output", str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
        )
        removed = False
        deadline = time.monotonic() + 4
        try:
            while time.monotonic() < deadline and (not output.exists() or not output.stat().st_size):
                time.sleep(0.01)
            self.assertTrue(output.exists(), "watcher did not write its baseline")
            conflict.write_text(f"{self.run_git('rev-parse', 'HEAD')}\n", encoding="ascii")

            while time.monotonic() < deadline:
                records = [
                    json.loads(line)
                    for line in output.read_text(encoding="utf-8").splitlines()
                ]
                if any(
                    record.get("invalid_conflict_ref_names") == ["common:refs/heads/main [conflicted]"]
                    for record in records
                ):
                    conflict.unlink()
                    removed = True
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.01)

            stdout, stderr = process.communicate(timeout=2)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

        self.assertTrue(removed, f"watcher did not observe the conflict ref: {stdout} {stderr}")
        self.assertEqual(process.returncode, 2)
        records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[-1]["invalid_conflict_ref_names"], [])
        self.assertEqual(records[-1]["result"], "problem")

    def test_expected_ref_mismatch_fails_closed(self) -> None:
        actual = self.run_git("rev-parse", "HEAD")
        wrong = "0" * len(actual)
        output = self.base / "watch.jsonl"

        result = git_ref_watch.main([
            "--repo", str(self.repo), "--duration", "0.1", "--interval", "0.1",
            "--output", str(output), "--expect-ref", f"refs/heads/main={wrong}",
        ])

        self.assertEqual(result, 2)
        records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[0]["expected_ref_mismatches"][0]["actual"], actual)
        self.assertEqual(records[-1]["result"], "problem")


if __name__ == "__main__":
    unittest.main()
