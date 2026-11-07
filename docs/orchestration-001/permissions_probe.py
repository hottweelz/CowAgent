"""Controlled permission probes for ORCHESTRATION-001.

This module uses a deterministic local model and a caller-owned scratch root.
It does not read the installed CowAgent config or credentials. The only shell
command executed writes one fixed marker inside that scratch root.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


class _FixtureMemory:
    """Tiny fictional parent memory manager. It has no disk or network access."""

    identity = "fictional-parent-memory"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query, **_kwargs):
        self.queries.append(str(query))
        return [SimpleNamespace(
            path="memory/fictional.md",
            start_line=1,
            end_line=1,
            score=1.0,
            snippet="FICTIONAL_PARENT_MEMORY_SENTINEL",
        )]


class _ScriptedModel:
    """Minimal local LLMModel stand-in that returns fixed streaming tool calls."""

    model = "orchestration-001-local-fixture"

    def __init__(self, action: str, arguments: dict, template_name: str) -> None:
        self.action = action
        self.arguments = arguments
        self.template_name = template_name
        self.calls = 0

    def call_stream(self, _request):
        call_index = self.calls
        self.calls += 1
        if call_index == 0:
            name = "subagent"
            args = {
                "goal": "Run the controlled permission probe.",
                "context": "Use only the supplied fictional task and fixed marker.",
                "subagent_type": self.template_name,
            }
        elif call_index == 1:
            name = self.action
            args = self.arguments
        elif call_index == 2:
            yield {"choices": [{"delta": {"content": "Local child fixture complete."},
                                "finish_reason": "stop"}]}
            return
        elif call_index == 3:
            yield {"choices": [{"delta": {"content": "Local parent fixture complete."},
                                "finish_reason": "stop"}]}
            return
        else:
            raise AssertionError(f"Unexpected local model call index: {call_index}")

        yield {"choices": [{
            "delta": {"tool_calls": [{
                "index": 0,
                "id": f"fixture_call_{call_index}",
                "function": {"name": name, "arguments": json.dumps(args)},
            }]},
            "finish_reason": "tool_calls",
        }]}


def _tool_step(events: list[dict], tool_name: str) -> dict | None:
    for event in events:
        if event.get("type") != "subagent_step":
            continue
        data = event.get("data") or {}
        if data.get("phase") == "end" and data.get("tool_name") == tool_name:
            return data
    return None


def _scenario(
    *,
    workspace: Path,
    marker: Path,
    permission_mode: str,
    template_name: str,
    action: str,
    action_args: dict,
    memory_manager: _FixtureMemory | None = None,
    safe_env_file_path: Path | None = None,
) -> dict[str, Any]:
    """Run one real Agent -> SubagentTool -> child AgentStreamExecutor path."""
    from agent.protocol.agent import Agent
    from agent.protocol.models import LLMModel
    from agent.tools.bash import Bash
    from agent.tools.bash import bash as bash_module
    from agent.tools.memory import MemorySearchTool
    from agent.tools.subagent import SubagentTool
    from agent.tools.write import Write

    # This is a real local LLMModel subclass. It overrides only the streaming
    # provider hook, so the ordinary AgentStreamExecutor remains in the path.
    class LocalModel(_ScriptedModel, LLMModel):
        def __init__(self):
            LLMModel.__init__(self, model="orchestration-001-local-fixture")
            _ScriptedModel.__init__(self, action, action_args, template_name)

    model = LocalModel()

    tools = [
        SubagentTool({"cwd": str(workspace)}),
        Write({"cwd": str(workspace)}),
        Bash({"cwd": str(workspace)}),
    ]
    if memory_manager is not None:
        tools.append(MemorySearchTool(memory_manager))

    parent = Agent(
        system_prompt="Controlled local permission probe.",
        model=model,
        tools=tools,
        workspace_dir=str(workspace),
        enable_skills=False,
        max_steps=8,
        max_context_tokens=4096,
        output_mode="logger",
    )
    parent.permission_mode = permission_mode

    events: list[dict] = []
    result: dict[str, Any] = {
        "template": template_name,
        "permission_mode": permission_mode,
        "action": action,
        "marker_exists_before": marker.exists(),
    }

    # Bash.execute reads ~/.cow/.env at agent/tools/bash/bash.py:198 even when
    # COW_DATA_DIR points elsewhere. Redirect only that lookup to a known-missing
    # path. The main probe supplies a sanitized process environment before call.
    if safe_env_file_path is None:
        parent.run_stream("Run the controlled local fixture.", clear_history=True,
                          on_event=events.append)
    else:
        original_expand_path = bash_module.expand_path
        try:
            bash_module.expand_path = lambda value: (
                str(safe_env_file_path)
                if value == "~/.cow/.env"
                else original_expand_path(value)
            )
            parent.run_stream("Run the controlled local fixture.", clear_history=True,
                              on_event=events.append)
        finally:
            bash_module.expand_path = original_expand_path

    step = _tool_step(events, action)
    result["child_tool_step"] = {
        "observed": step is not None,
        "status": step.get("status") if step else None,
        "permission_denied": bool(
            step and "Blocked by permission mode" in str(step.get("error") or "")
        ),
        "tool_missing": bool(
            step and "not found" in str(step.get("error") or "").lower()
        ),
    }
    result["marker_exists_after"] = marker.exists()
    result["model_calls"] = model.calls

    if memory_manager is not None:
        result["fictional_memory_manager_identity"] = memory_manager.identity
        result["fictional_memory_queries"] = list(memory_manager.queries)
        result["fictional_memory_action_succeeded"] = bool(
            step and step.get("status") == "success" and memory_manager.queries
        )
    return result


def run_permission_probes(root: Path) -> dict[str, Any]:
    """Run bounded permission checks under *root* and return sanitized evidence.

    The caller must provide a unique disposable root. All files, including the
    Bash escape marker and SQLite run records, stay below that root. The
    function replaces CowAgent config in memory with synthetic settings and
    restores it before return.
    """
    root = Path(root).resolve()
    state = root / "state"
    workspace = state
    workspace.mkdir(parents=True, exist_ok=True)

    # The caller owns process-environment sanitization. Bash's .env lookup is
    # redirected below, so HOME stays unchanged and no real .env is opened.

    import config as config_module

    previous_config = config_module.config
    synthetic_config = config_module.Config({
        "agent_workspace": str(state),
        "agent_permission_mode": "workspace-write",
        "subagent": {
            "enabled": True,
            "max_depth": 1,
            "max_concurrent": 1,
            "timeout_seconds": 30,
        },
        "self_evolution_enabled": False,
        "knowledge": False,
        "agent_max_context_turns": 4,
    })
    config_module.config = synthetic_config

    results: dict[str, Any] = {"root": str(root), "probes": {}}
    try:
        # (1) Explore omits write from its child tool set. A deliberately
        # out-of-schema model call must fail without creating the marker.
        results["probes"]["explore_write"] = _scenario(
            workspace=workspace,
            marker=workspace / "explore-write.txt",
            permission_mode="workspace-write",
            template_name="explore",
            action="write",
            action_args={
                "path": str(workspace / "explore-write.txt"),
                "content": "fictional",
            },
        )

        # (2) General-purpose has write, but inherits the parent's read-only
        # session mode and must be denied before the real Write tool runs.
        readonly_marker = workspace / "general_readonly-write.txt"
        results["probes"]["general_readonly_write"] = _scenario(
            workspace=workspace,
            marker=readonly_marker,
            permission_mode="read-only",
            template_name="general-purpose",
            action="write",
            action_args={"path": str(readonly_marker),
                         "content": "fictional"},
        )

        # (3) A direct Write to a sibling of the assigned workspace should be
        # refused. The scratch root is /private/tmp on the audit host, outside
        # tempfile.gettempdir(); keep this check explicit and visible.
        direct_marker = root / "direct-outside-write.txt"
        temp_root = Path(__import__("tempfile").gettempdir()).resolve()
        direct_is_outside_temp = not direct_marker.is_relative_to(temp_root)
        if direct_is_outside_temp:
            results["probes"]["direct_write_outside_workspace"] = _scenario(
                workspace=workspace,
                marker=direct_marker,
                permission_mode="workspace-write",
                template_name="general-purpose",
                action="write",
                action_args={"path": str(direct_marker), "content": "fictional"},
            )
        else:
            results["probes"]["direct_write_outside_workspace"] = {
                "skipped": True,
                "reason": "scratch marker is within tempfile.gettempdir()",
                "marker_exists_after": direct_marker.exists(),
            }

        # (4) Python is intentionally invoked through the built-in Bash tool.
        # The fixed code writes only this marker. Redirect Bash's .env lookup
        # to a known-missing path; the caller supplies an allowlisted process
        # environment, and this Python snippet performs no network operation.
        bash_marker = root / "bash-python-outside-write.txt"
        bash_is_outside_temp = not bash_marker.is_relative_to(temp_root)
        if bash_is_outside_temp:
            code = (
                "from pathlib import Path; "
                f"Path({str(bash_marker)!r}).write_text('fictional-bash-marker', encoding='utf-8')"
            )
            command = shlex.join([sys.executable, "-B", "-c", code])
            results["probes"]["bash_python_outside_workspace"] = _scenario(
                workspace=workspace,
                marker=bash_marker,
                permission_mode="workspace-write",
                template_name="general-purpose",
                action="bash",
                action_args={"command": command, "timeout": 20},
                safe_env_file_path=root / "no-user-env-file",
            )
        else:
            results["probes"]["bash_python_outside_workspace"] = {
                "skipped": True,
                "reason": "scratch marker is within tempfile.gettempdir()",
                "marker_exists_after": bash_marker.exists(),
            }

        # Confirm the documented/code discrepancy with a fictional manager:
        # the general-purpose child calls the copied parent's memory tool, and
        # the manager returns only a fixed synthetic sentinel.
        fake_memory = _FixtureMemory()
        memory_marker = root / "fictional-memory-no-file.txt"
        results["probes"]["fictional_parent_memory_read"] = _scenario(
            workspace=workspace,
            marker=memory_marker,
            permission_mode="workspace-write",
            template_name="general-purpose",
            action="memory_search",
            action_args={"query": "fictional identity probe"},
            memory_manager=fake_memory,
        )

        outside_candidate = root / "direct-outside-write.txt"
        results["path_scope"] = {
            "workspace_is_under_root": workspace.is_relative_to(root),
            "direct_marker_is_outside_workspace": not outside_candidate.is_relative_to(workspace),
            "direct_marker_is_outside_system_temp": not outside_candidate.is_relative_to(temp_root),
            "bash_marker_is_outside_workspace": not bash_marker.is_relative_to(workspace),
            "bash_marker_is_outside_system_temp": bash_is_outside_temp,
        }

        expected = {
            "explore_write": lambda p: p["child_tool_step"]["tool_missing"] and not p["marker_exists_after"],
            "general_readonly_write": lambda p: p["child_tool_step"]["permission_denied"] and not p["marker_exists_after"],
            "direct_write_outside_workspace": lambda p: (
                p["child_tool_step"]["permission_denied"]
                and not p["marker_exists_after"]
                and results["path_scope"]["direct_marker_is_outside_system_temp"]
            ),
            "bash_python_outside_workspace": lambda p: (
                p["child_tool_step"]["status"] == "success"
                and p["marker_exists_after"]
                and results["path_scope"]["bash_marker_is_outside_workspace"]
                and results["path_scope"]["bash_marker_is_outside_system_temp"]
            ),
            "fictional_parent_memory_read": lambda p: p["fictional_memory_action_succeeded"],
        }
        for name, check in expected.items():
            if results["probes"].get(name, {}).get("skipped"):
                results["probes"][name]["expected_observation_confirmed"] = False
                continue
            try:
                results["probes"][name]["expected_observation_confirmed"] = bool(
                    check(results["probes"][name])
                )
            except Exception:
                results["probes"][name]["expected_observation_confirmed"] = False
    finally:
        config_module.config = previous_config

    return results
