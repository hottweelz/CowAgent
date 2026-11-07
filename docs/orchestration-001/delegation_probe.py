"""Controlled local probe of persistent peer-Agent delegation.

The caller must set COW_DATA_DIR to a disposable directory and load a synthetic
configuration before calling :func:`run_delegation_probes`. This probe creates
only fictional profiles and files below ``root``. It uses the real registry,
router, AgentBridge methods, Agent stream executor, permission gate, Write tool,
and SQLite conversation store. It replaces bridge initialization with a small
per-profile Agent factory and replaces only model responses with local scripted
streams. It does not contact a model provider or another service.
"""

from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any

from agent.protocol import Agent, LLMModel
from agent.registry import AgentProfile, AgentRegistry
from agent.routing import AgentRouter
from agent.tools.agent_delegate.agent_delegate import (
    AgentDelegateTool,
    attach_agent_delegate_to_tool,
)
from agent.tools.write.write import Write
from bridge.agent_bridge import AgentBridge
from bridge.context import Context, ContextType


class _ScriptedLocalModel(LLMModel):
    """Emit one real Write tool call and then a short synthetic answer."""

    def __init__(self, agent_id: str):
        super().__init__(f"orchestration-probe-{agent_id}")
        self.agent_id = agent_id
        self._awaiting_answer = False
        self.turns = 0
        self.request_count = 0
        self._lock = threading.Lock()

    def call_stream(self, request):
        with self._lock:
            self.request_count += 1
            if not self._awaiting_answer:
                self.turns += 1
                self._awaiting_answer = True
                turn = self.turns
                action = "write"
            else:
                self._awaiting_answer = False
                turn = self.turns
                action = "answer"

        if action == "write":
            path = f"probe-output/{self.agent_id}-{turn}.txt"
            arguments = json.dumps(
                {
                    "path": path,
                    "content": f"artifact-owner={self.agent_id}\nturn={turn}\n",
                },
                ensure_ascii=False,
            )
            yield {
                "choices": [{
                    "delta": {
                        "tool_calls": [{
                            "index": 0,
                            "id": f"probe-{self.agent_id}-{turn}",
                            "type": "function",
                            "function": {"name": "write", "arguments": arguments},
                        }]
                    },
                    "finish_reason": None,
                }]
            }
            yield {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        else:
            yield {
                "choices": [{
                    "delta": {"content": f"{self.agent_id} completed synthetic turn {turn}."},
                    "finish_reason": None,
                }]
            }
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}


class _SafeProfileInitializer:
    """Build real Agents with only a restricted local Write tool and fake model."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.models: dict[str, _ScriptedLocalModel] = {}

    def initialize_agent(self, session_id=None, agent_id=None, host_agent_id=None):
        profile = self.registry.get(agent_id)
        model = self.models.setdefault(profile.id, _ScriptedLocalModel(profile.id))
        workspace = Path(profile.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        tool = Write({"cwd": str(workspace), "restrict_to_workspace": True})
        agent = Agent(
            system_prompt="Synthetic audit worker. Use the supplied local tool, then report.",
            description=profile.name,
            model=model,
            tools=[tool],
            max_steps=4,
            output_mode="logger",
            workspace_dir=str(workspace),
            enable_skills=False,
        )
        agent.agent_id = profile.id
        agent.agent_profile = profile
        return agent


def _new_bridge(root: Path):
    profiles = [
        AgentProfile("primary", "Synthetic primary", str(root / "workspaces" / "primary")),
        AgentProfile("worker-a", "Synthetic worker A", str(root / "workspaces" / "worker-a")),
        AgentProfile("worker-b", "Synthetic worker B", str(root / "workspaces" / "worker-b")),
    ]
    for profile in profiles:
        Path(profile.workspace).mkdir(parents=True, exist_ok=True)
    registry = AgentRegistry(profiles, "primary")

    # Avoid AgentBridge.__init__: it starts schedulers and the evolution
    # trigger. Keep the actual bridge routing, runtime cache, reply executor,
    # persistence, and cancellation paths exercised.
    bridge = AgentBridge.__new__(AgentBridge)
    bridge.agent_registry = registry
    bridge.agent_router = AgentRouter(registry)
    bridge._agent_instances = {}
    bridge._default_agents = {}
    bridge._agents_lock = threading.RLock()
    bridge.agents = {}
    bridge.default_agent = None
    bridge.initializer = _SafeProfileInitializer(registry)
    bridge._schedule_mcp_hot_reload = lambda agent: None
    return bridge


def _delegation_tool(bridge, source_mode: str, allowlist: dict[str, list[str]],
                     event_log: list[tuple[str, dict]]):
    root_session = "orchestration-001-local-delegation"
    source = bridge.get_agent(session_id=root_session, agent_id="primary")
    source.apply_permission_mode(source_mode)
    context = Context(ContextType.TEXT, "synthetic source turn", kwargs={})
    context["agent_id"] = "primary"
    context["session_id"] = root_session
    context["delegation_members"] = ["worker-a", "worker-b"]
    tool = AgentDelegateTool({
        "timeout_seconds": 30,
        "allowed_targets": allowlist,
    })
    tool.event_callback = lambda event_type, data: event_log.append((event_type, data))
    attach_agent_delegate_to_tool(tool, bridge, context)
    return tool, root_session


def run_delegation_probes(root: Path) -> dict[str, Any]:
    """Run synthetic peer handoffs and return a small sanitized evidence record."""
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("probe root must be an absolute path")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    bridge = _new_bridge(root)
    from agent.registry import get_agent_registry, set_agent_registry

    previous_registry = get_agent_registry()
    set_agent_registry(bridge.agent_registry)
    try:
        return _run_delegation_probes(root, bridge)
    finally:
        set_agent_registry(previous_registry)


def _run_delegation_probes(root: Path, bridge: AgentBridge) -> dict[str, Any]:
    events: list[tuple[str, dict]] = []
    writable, _ = _delegation_tool(
        bridge,
        "workspace-write",
        {"primary": ["worker-a", "worker-b"]},
        events,
    )

    first = writable.execute({"agent_id": "worker-a", "task": "Create one synthetic artifact."})
    assert first.status == "success", first.result
    first_result = first.result
    assert first_result["agent_id"] == "worker-a"
    assert first_result["delegated_by"] == "primary"
    assert first_result["status"] == "done"
    assert "worker-a completed synthetic turn 1" in first_result["content"]

    # Reuse the same source/target/root tuple. Delegation uses the same private
    # peer session, and the real bridge/store should retain both runs and turns.
    second = writable.execute({"agent_id": "worker-a", "task": "Create a second synthetic artifact."})
    assert second.status == "success", second.result
    assert second.result["session_id"] == first_result["session_id"]
    assert "worker-a completed synthetic turn 2" in second.result["content"]

    worker_a = bridge.get_cached_agent(first_result["session_id"], agent_id="worker-a")
    assert worker_a is not None
    assert worker_a.workspace_dir == str(root / "workspaces" / "worker-a")
    assert worker_a.model is bridge.initializer.models["worker-a"]
    for turn in (1, 2):
        artifact = Path(worker_a.workspace_dir) / "probe-output" / f"worker-a-{turn}.txt"
        assert artifact.read_text(encoding="utf-8") == f"artifact-owner=worker-a\nturn={turn}\n"

    store_a = bridge.get_conversation_store("worker-a")
    store_b = bridge.get_conversation_store("worker-b")
    runs = store_a.list_runs(session_id=first_result["session_id"])
    history = store_a.load_messages(first_result["session_id"], max_turns=10)
    other_agent_history = store_b.load_messages(first_result["session_id"], max_turns=10)
    assert len(runs) == 2, runs
    assert all(run["status"] == "done" for run in runs), runs
    assert store_a._db_path == store_b._db_path
    assert store_a._agent_id == "worker-a"
    assert store_b._agent_id == "worker-b"
    assert other_agent_history == []
    visible_turns = [
        message for message in history
        if message.get("role") == "user"
        and isinstance(message.get("content"), list)
        and any(block.get("type") == "text" for block in message["content"]
                if isinstance(block, dict))
    ]
    assert len(visible_turns) == 2

    readonly, _ = _delegation_tool(
        bridge,
        "read-only",
        {"primary": ["worker-a", "worker-b"]},
        events,
    )
    worker_b_result = readonly.execute({"agent_id": "worker-b", "task": "Attempt one synthetic artifact."})
    assert worker_b_result.status == "success", worker_b_result.result
    assert worker_b_result.result["agent_id"] == "worker-b"
    worker_b = bridge.get_cached_agent(worker_b_result.result["session_id"], agent_id="worker-b")
    assert worker_b is not None
    assert worker_b.workspace_dir == str(root / "workspaces" / "worker-b")
    assert worker_b.effective_permission_mode() == "read-only"
    assert not (Path(worker_b.workspace_dir) / "probe-output" / "worker-b-1.txt").exists()
    denied = [
        data for event_type, data in events
        if event_type == "tool_execution_end" and data.get("permission_denied")
    ]
    assert any(item.get("permission_mode") == "read-only" for item in denied), denied

    restricted, _ = _delegation_tool(
        bridge,
        "workspace-write",
        {"primary": ["worker-a"]},
        events,
    )
    denied_target = restricted.execute({"agent_id": "worker-b", "task": "This target is outside the allowed roster."})
    assert denied_target.status == "error"
    assert "not a teammate" in str(denied_target.result)
    assert bridge.initializer.models["worker-b"].turns == 1

    return {
        "status": "passed",
        "boundaries": {
            "real": [
                "AgentRegistry and AgentRouter",
                "AgentBridge local reply, runtime cache, and private peer session",
                "Agent and streaming tool executor",
                "permission gate and Write tool",
                "SQLite run and message persistence",
            ],
            "substituted": [
                "per-profile initializer builds real Agents with safe local tools",
                "LLMModel responses are deterministic local streams",
                "AgentBridge constructor is bypassed to avoid scheduler and evolution startup",
                "MCP hot reload callback is disabled",
            ],
            "not_exercised": [
                "provider or network behavior",
                "cross-process peer transport",
                "production channel routing and credentials",
            ],
        },
        "profiles": {
            profile.id: {
                "workspace": str(Path(profile.workspace).relative_to(root)),
                "registered": True,
            }
            for profile in bridge.agent_registry.list()
        },
        "delegation": {
            "target_ids": [first_result["agent_id"], worker_b_result.result["agent_id"]],
            "source_id": first_result["delegated_by"],
            "worker_a_artifacts": ["worker-a-1.txt", "worker-a-2.txt"],
            "worker_b_read_only_write_denied": True,
            "disallowed_roster_target_denied": True,
            "worker_a_private_session_reused": True,
            "shared_sqlite_path": str(store_a._db_path.relative_to(root)),
            "worker_a_store_scope": store_a._agent_id,
            "worker_b_store_scope": store_b._agent_id,
            "worker_b_sees_worker_a_history": bool(other_agent_history),
            "worker_a_persisted_runs": len(runs),
            "worker_a_persisted_user_turns": len(visible_turns),
        },
    }
