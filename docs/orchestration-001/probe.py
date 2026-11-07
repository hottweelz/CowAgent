#!/usr/bin/env python3
"""Reproduce the audit with real CowAgent orchestration and local scripted models.

No implementation patch, network, credentials or production configuration.
All fixtures, databases and child processes belong to a fresh temporary directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

TASK_REQUIREMENTS = {
    "worker-a": "Add the fictional shipment counts 1, 2, 3, 4 and 5.",
    "worker-b": "Multiply the fictional crate count 6 by 7 items per crate.",
    "worker-c": "Multiply the fictional box count 3 by 14 items per box.",
    "worker-d": "Multiply the fictional pack count 2 by 21 items per pack.",
}


def worker_goal(key):
    return (f"{key}: {TASK_REQUIREMENTS[key]} "
            f"Save the calculated integer as a JSON object with key answer in {key}.json "
            "inside your workspace, then report completion.")


def source_evidence():
    """Permit docs-only audit commits, but refuse a different implementation."""
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    changed = subprocess.check_output([
        "git", "diff", "--name-only", "c2c39a2e", "--", ".",
        ":(exclude)docs", ":(exclude)CHANGELOG_AI.md",
    ], cwd=REPO, text=True).splitlines()
    assert not changed, f"Implementation differs from audited baseline: {changed}"
    untracked_runtime = subprocess.check_output([
        "git", "ls-files", "--others", "--exclude-standard", "--",
        "agent", "bridge", "channel", "common", "models", "plugins",
    ], cwd=REPO, text=True).splitlines()
    assert not untracked_runtime, f"Untracked runtime source: {untracked_runtime}"
    return {"actual_head": revision, "implementation_matches_baseline": True,
            "comparison_excludes": ["docs/", "CHANGELOG_AI.md"]}


def setup(root):
    # Preserve HOME; drop inherited provider credentials from this probe process.
    keep = {k: v for k, v in os.environ.items()
            if k in {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT"}}
    os.environ.clear()
    os.environ.update(keep)
    os.environ["COW_DATA_DIR"] = str(root / "data")
    logging.disable(logging.CRITICAL)
    import config
    config.config = config.Config({
        "agent_workspace": str(root / "state"), "cow_lang": "en",
        "self_evolution_enabled": False, "agent_permission_mode": "workspace-write",
        "subagent": {"enabled": True, "max_concurrent": 2, "timeout_seconds": 10},
    })
    from agent.registry import AgentProfile, AgentRegistry, set_agent_registry
    set_agent_registry(AgentRegistry([
        AgentProfile("parent", "Fictional parent", str(root / "state")),
    ], "parent"))


def text_chunk(text):
    return {"choices": [{"delta": {"content": text}, "finish_reason": "stop"}]}


def tool_chunk(name, arguments, suffix="1"):
    return {"choices": [{"delta": {"tool_calls": [{
        "index": 0, "id": "audit_" + suffix, "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]}, "finish_reason": "tool_calls"}]}


def goal_of(request):
    for message in request.messages:
        if message["role"] == "user":
            content = message["content"]
            if isinstance(content, str):
                return content
            return "".join(b.get("text", "") for b in content if b.get("type") == "text")
    raise AssertionError("Missing synthetic task")


class ScriptModel:
    model = "local-fictional-audit-model"

    def __init__(self, workspace, goals, *, barrier=False, wrong=False, fail=False, retry=False,
                 split_batches=False):
        self.workspace, self.goals = workspace, goals
        self.barrier = threading.Barrier(len(goals)) if barrier else None
        self.wrong, self.fail, self.retry = wrong, fail, retry
        self.split_batches = split_batches
        self.calls, self.intervals = {}, {}
        self.lock = threading.Lock()

    def call_stream(self, request):
        goal = goal_of(request).split(": ", 1)[0]
        with self.lock:
            call = self.calls.get(goal, 0)
            self.calls[goal] = call + 1
        if goal == "parent-task":
            if call == 0:
                if self.split_batches:
                    calls = []
                    for i, group in enumerate((self.goals[:2], self.goals[2:])):
                        item = tool_chunk("subagent", {"tasks": [{"goal": worker_goal(g)} for g in group]}, str(i))
                        tc = item["choices"][0]["delta"]["tool_calls"][0]
                        tc["index"] = i
                        calls.append(tc)
                    yield {"choices": [{"delta": {"tool_calls": calls}, "finish_reason": "tool_calls"}]}
                else:
                    yield tool_chunk("subagent", {"tasks": [{"goal": worker_goal(g)} for g in self.goals]})
            else:
                yield text_chunk("Parent received the worker reports.")
            return
        if self.fail and goal == "worker-b":
            raise RuntimeError("401 fictional provider rejection")
        if self.retry and call == 0:
            raise RuntimeError("503 fictional service unavailable")
        first = call == (1 if self.retry else 0)
        if first:
            self.intervals[goal] = {"start": time.monotonic(), "thread": threading.get_ident()}
            if self.barrier:
                self.barrier.wait(timeout=5)
            time.sleep(0.08)
            answer = 15 if goal == "worker-a" else 42
            if self.wrong:
                answer = -1
            yield tool_chunk("write", {"path": str(self.workspace / (goal + ".json")),
                                       "content": json.dumps({"answer": answer})}, goal)
        else:
            self.intervals[goal]["end"] = time.monotonic()
            yield text_chunk("Task complete; artifact written.")


def parent_agent(workspace, model, case):
    from agent.protocol.agent import Agent
    from agent.tools.subagent import SubagentTool
    from agent.tools.write.write import Write
    workspace.mkdir(parents=True, exist_ok=True)
    parent = Agent("Fictional audit coordinator", model=model,
                   tools=[SubagentTool({"cwd": str(workspace)}), Write({"cwd": str(workspace)})],
                   workspace_dir=str(workspace), enable_skills=False, skip_context_files=True,
                   max_steps=8, max_context_tokens=12000, output_mode="logger")
    parent.permission_mode = "workspace-write"
    parent._current_agent_id = "parent"
    parent._current_session_id = case
    return parent


def run_parent(parent, case):
    from common.runtime_identity import identity_scope
    with identity_scope(agent_id="parent", session_id=case, run_id="parent-" + case):
        parent.run_stream("parent-task: Delegate the independent fictional arithmetic tasks and collect reports.",
                          clear_history=True)
    results = []
    for message in parent.messages:
        for block in message.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                content = block.get("content", "")
                try:
                    parsed = json.loads(content)
                except (TypeError, ValueError):
                    continue
                if isinstance(parsed, dict) and "results" in parsed:
                    results.extend(parsed["results"])
    assert results, "Parent did not receive native subagent results"
    return results


def batch_case(root, case, **options):
    workspace = root / case
    goals = ["worker-a", "worker-b", "worker-c", "worker-d"] if options.get("split_batches") else ["worker-a", "worker-b"]
    model = ScriptModel(workspace, goals, **options)
    parent = parent_agent(workspace, model, case)
    results = run_parent(parent, case)
    # Independent verifier: expected values come from separate arithmetic.
    expected_values = {"worker-a": sum(range(1, 6)), "worker-b": 6 * 7,
                       "worker-c": 3 * 14, "worker-d": 2 * 21}
    expected = {g: expected_values[g] for g in goals}
    verification = {g: ((workspace / (g + ".json")).exists() and
                        json.loads((workspace / (g + ".json")).read_text())["answer"] == v)
                    for g, v in expected.items()}
    from agent.memory import get_conversation_store
    rows = get_conversation_store(str(workspace)).list_runs(session_id=case)
    receipt = {"native_statuses": [r["status"] for r in results],
               "independent_artifacts_valid": verification,
               "model_calls": model.calls, "database_statuses": sorted(r["status"] for r in rows),
               "same_parent_agent_identity": all(r["agent_id"] == "parent" for r in rows),
               "same_parent_run": all(r["parent_run_id"] == "parent-" + case for r in rows)}
    if options.get("barrier"):
        intervals = list(model.intervals.values())
        overlap = min(a["end"] for a in intervals) - max(a["start"] for a in intervals)
        assert overlap > 0 and len({a["thread"] for a in intervals}) == len(goals)
        receipt.update(overlap_seconds=round(overlap, 4), distinct_worker_threads=True,
                       simultaneous_workers=len(goals), configured_limit_per_call=2,
                       same_process=True, shared_workspace=True)
    return receipt


class BlockingModel:
    model = "local-blocking-audit-model"

    def __init__(self, ready=None):
        self.entered, self.release, self.closed = threading.Event(), threading.Event(), threading.Event()
        self.ready = ready

    def call_stream(self, request):
        self.entered.set()
        if self.ready:
            self.ready.write_text("native worker entered model call")
        try:
            if not self.release.wait(20):
                raise RuntimeError("Audit rescue timeout")
            yield text_chunk("Released fixture")
        finally:
            self.closed.set()


def stopped_case(root, *, timeout):
    from agent.subagent import SubagentSettings, SubagentTask, load_templates, run_tasks
    from agent.memory import get_conversation_store
    case = "timeout" if timeout else "cancel"
    workspace = root / case
    model = BlockingModel()
    parent = parent_agent(workspace, model, case)
    stop = threading.Event()
    results = []
    settings = SubagentSettings(timeout_seconds=0.3 if timeout else 5)
    thread = threading.Thread(target=lambda: results.extend(run_tasks(
        parent, [SubagentTask("pending")], load_templates(str(workspace)), settings,
        cancel_event=stop)))
    thread.start()
    try:
        assert model.entered.wait(3)
        start = time.monotonic()
        if not timeout:
            stop.set()
        thread.join(3)
        assert not thread.is_alive() and results
        expected = "timeout" if timeout else "cancelled"
        assert results[0]["status"] == expected
        still_inside = not model.closed.is_set()
        store = get_conversation_store(str(workspace))
        before = [r["status"] for r in store.list_runs(session_id=case)]
    finally:
        model.release.set()
        thread.join(3)
    assert model.closed.wait(3)
    deadline = time.monotonic() + 3
    while any(r["status"] == "running" for r in store.list_runs(session_id=case)):
        assert time.monotonic() < deadline
        time.sleep(.01)
    return {"returned_status": expected, "return_wait_seconds": round(time.monotonic() - start, 3),
            "model_still_blocked_when_runner_returned": still_inside,
            "database_status_at_return": before,
            "database_status_after_worker_exits": [r["status"] for r in store.list_runs(session_id=case)],
            "budget_note": "timeout uses a direct runner setting of 0.3s; public config minimum is 10s"}


def restart_child(root, inspect=False):
    from agent.memory import get_conversation_store
    from agent.subagent import SubagentSettings, SubagentTask, load_templates, run_tasks
    workspace = root / "restart"
    model = BlockingModel(root / "pending.ready")
    parent = parent_agent(workspace, model, "restart")
    store = get_conversation_store(str(workspace))
    if not inspect:
        run_tasks(parent, [SubagentTask("pending-fictional-task")], load_templates(str(workspace)),
                  SubagentSettings(timeout_seconds=30))
        return
    rows = store.list_runs(session_id="restart")
    assert len(rows) == 1 and rows[0]["status"] == "running"
    conn = store._connect()
    try:
        displayed = store._unfinished_runs(conn, "restart")
    finally:
        conn.close()
    assert set(displayed.values()) == {"interrupted"}
    before = len(rows)
    assert not model.entered.is_set()
    # Explicit resubmission creates a new execution; it is not checkpoint resume.
    model.release.set()
    rerun = run_tasks(parent, [SubagentTask("pending-fictional-task")], load_templates(str(workspace)),
                      SubagentSettings(timeout_seconds=3))
    after = store.list_runs(session_id="restart")
    assert len(after) == before + 1 and rerun[0]["status"] == "completed"
    print(json.dumps({"raw_status_after_restart": rows[0]["status"],
                      "history_interpretation": list(displayed.values()),
                      "automatic_execution_observed": False, "explicit_resubmission_added_run": True,
                      "old_run_still_running_in_ledger": store.get_run(rows[0]["run_id"])["status"] == "running",
                      "old_run_extras_keys": sorted(rows[0]["extras"]),
                      "new_run_count": len(after)}))


def restart_case(root):
    command = [sys.executable, str(Path(__file__).resolve()), "--child-root", str(root)]
    proc = subprocess.Popen(command + ["--pending"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not (root / "pending.ready").exists():
            if proc.poll() is not None:
                raise AssertionError(proc.communicate()[1].decode())
            assert time.monotonic() < deadline
            time.sleep(.02)
        assert proc.poll() is None
        proc.terminate()  # Only the task-owned process observed alive above.
        proc.communicate(timeout=5)
        assert proc.returncode != 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=5)
    inspect = subprocess.run(command + ["--inspect"], text=True, capture_output=True, timeout=10)
    assert inspect.returncode == 0, inspect.stderr
    result = json.loads(inspect.stdout)
    result.update(terminated_pid=proc.pid, terminated_returncode=proc.returncode,
                  restart_scope="new backend probe process, not full web server startup")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--child-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--pending", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--inspect", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.child_root or Path(tempfile.mkdtemp(prefix="cowagent-orchestration-", dir="/private/tmp"))
    setup(root)
    # No model/transport can silently make a real network call in this process.
    with patch.object(socket.socket, "connect", side_effect=AssertionError("Audit network disabled")):
        if args.child_root:
            restart_child(root, args.inspect)
            return
        report = {"baseline": "c2c39a2e", "workspace": str(root), "live_provider_calls": 0,
                  "source_evidence": source_evidence(), "fictional_task_requirements": TASK_REQUIREMENTS,
                  "recorded_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
                  "environment": {"python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
                                  "platform": sys.platform},
                  "model_boundary": "deterministic local streaming responses; real Agent/tool/runner/store"}
        report["parallel"] = batch_case(root, "parallel", barrier=True)
        assert report["parallel"]["native_statuses"] == ["completed", "completed"]
        assert all(report["parallel"]["independent_artifacts_valid"].values())
        report["multiple_batches"] = batch_case(root, "multiple-batches", barrier=True, split_batches=True)
        assert report["multiple_batches"]["native_statuses"] == ["completed"] * 4
        assert all(report["multiple_batches"]["independent_artifacts_valid"].values())
        report["wrong_output"] = batch_case(root, "wrong-output", wrong=True)
        assert report["wrong_output"]["native_statuses"] == ["completed", "completed"]
        assert not any(report["wrong_output"]["independent_artifacts_valid"].values())
        report["worker_failure"] = batch_case(root, "failure", fail=True)
        assert report["worker_failure"]["native_statuses"] == ["completed", "failed"]
        report["transient_provider_failure"] = batch_case(root, "retry", retry=True)
        assert all(report["transient_provider_failure"]["independent_artifacts_valid"].values())
        report["cancellation"] = stopped_case(root, timeout=False)
        report["timeout"] = stopped_case(root, timeout=True)
        report["restart"] = restart_case(root)
        (root / "core-results.json").write_text(json.dumps(report, indent=2) + "\n")
        from permissions_probe import run_permission_probes
        from delegation_probe import run_delegation_probes
        report["permissions"] = run_permission_probes(root / "permissions")
        skips = []
        for name, observation in report["permissions"]["probes"].items():
            if observation.get("skipped"):
                skips.append(name)
            else:
                assert observation.get("expected_observation_confirmed") is True, name
        report["permission_probe_skips"] = skips
        report["persistent_delegation"] = run_delegation_probes(root / "delegation")
    report["self_evolution_enabled"] = False
    output = args.output or root / "results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    status = "audit observations verified with explicit skips" if skips else "audit observations verified"
    print(json.dumps({"result": status, "output": str(output),
                      "workspace": str(root), "receipt_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
