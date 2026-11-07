"""Pin the historical 16-tool runtime contract and native descriptor registry.

The active request inventory is built through ToolManager, AgentInitializer's
memory attachment, and the stream's availability filter. Optional registry
tools are checked separately from the historical request inventory.
"""

import json
import socket
from pathlib import Path
from types import SimpleNamespace

from agent.permission.policy import _descriptor
from agent.protocol.agent_stream import AgentStreamExecutor, build_tools_schema
from agent.registry import AgentProfile, AgentRegistry
from agent.tools import (
    EvolutionUndoTool,
    MemoryGetTool,
    MemorySearchTool,
    ToolManager,
)
from agent.tools.agent_delegate.agent_delegate import AgentDelegateTool as AgentDelegateClass
from agent.tools.subagent.subagent import SubagentTool


REPO = Path(__file__).resolve().parents[1]
CONTRACTS_PATH = REPO / "docs/orchestration-release-001/native-contracts.json"

HISTORICAL_NAMES = {
    "read", "write", "edit", "bash", "ls", "send", "search_files",
    "env_config", "scheduler", "web_search", "web_fetch", "vision",
    "browser", "time", "memory_search", "memory_get",
}

REGISTRY_CLASSES = {
    "agent_delegate": "agent.tools.agent_delegate.agent_delegate.AgentDelegateTool",
    "bash": "agent.tools.bash.bash.Bash",
    "browser": "agent.tools.browser.browser_tool.BrowserTool",
    "edit": "agent.tools.edit.edit.Edit",
    "env_config": "agent.tools.env_config.env_config.EnvConfig",
    "evolution_undo": "agent.tools.evolution_undo.evolution_undo.EvolutionUndoTool",
    "ls": "agent.tools.ls.ls.Ls",
    "read": "agent.tools.read.read.Read",
    "scheduler": "agent.tools.scheduler.scheduler_tool.SchedulerTool",
    "search_files": "agent.tools.search_files.search_files.SearchFiles",
    "send": "agent.tools.send.send.Send",
    "subagent": "agent.tools.subagent.subagent.SubagentTool",
    "time": "agent.tools.current_time.current_time.TimeTool",
    "vision": "agent.tools.vision.vision.Vision",
    "web_fetch": "agent.tools.web_fetch.web_fetch.WebFetch",
    "web_search": "agent.tools.web_search.web_search.WebSearch",
    "write": "agent.tools.write.write.Write",
    "memory_get": "agent.tools.memory.memory_get.MemoryGetTool",
    "memory_search": "agent.tools.memory.memory_search.MemorySearchTool",
}

DESCRIPTORS = {
    "read": ("read", "fs.read"),
    "write": ("write", "fs.write"),
    "edit": ("edit", "fs.write"),
    "ls": ("ls", "fs.read"),
    "search_files": ("search_files", "fs.read"),
    "time": ("time", "time"),
    "subagent": ("subagent", "subagent.spawn"),
    "agent_delegate": ("agent_delegate", "delegate.local"),
    "bash": ("bash", "privileged"),
    "send": ("send", "privileged"),
    "memory_search": ("memory_search", "privileged"),
    "memory_get": ("memory_get", "privileged"),
    "evolution_undo": ("evolution_undo", "privileged"),
    "env_config": ("env_config", "privileged"),
    "scheduler": ("scheduler", "privileged"),
    "web_search": ("web_search", "privileged"),
    "web_fetch": ("web_fetch", "privileged"),
    "vision": ("vision", "privileged"),
    "browser": ("browser", "privileged"),
}


def _class_path(tool_class):
    return f"{tool_class.__module__}.{tool_class.__name__}"


def _fixture(tmp_path, monkeypatch):
    """Build the 16 historical names with no credentials or external calls."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("COW_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "home").mkdir()
    (tmp_path / "data").mkdir()
    for key in (
        "DEEPSEEK_API_KEY", "BOCHA_API_KEY", "QIANFAN_API_KEY",
        "ZHIPUAI_API_KEY", "LINKAI_API_KEY", "ANYSEARCH_API_KEY",
        "SERPLY_API_KEY", "TAVILY_API_KEY", "OUTCRAWL_API_KEY",
        "FIRECRAWL_API_KEY", "SEARXNG_URL", "KEENABLE_API_KEY",
        "OPENAI_API_KEY", "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    def no_network(*_args, **_kwargs):
        raise AssertionError("native contract construction attempted network access")

    monkeypatch.setattr(socket.socket, "connect", no_network)

    import config
    settings = {
        "agent_workspace": str(tmp_path / "data"),
        "knowledge": False,
        "self_evolution_enabled": False,
        "subagent": {"enabled": False},
        "agent_delegation": {"enabled": True},
        "mcp_tool_retrieval_enabled": False,
        "tools": {
            "web_search": {
                "anysearch_anonymous": True,
                "strategy": "fixed",
                "provider": "anysearch",
            },
        },
    }
    monkeypatch.setattr(config, "config", config.Config(settings))

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    import agent.registry as registry_module
    monkeypatch.setattr(registry_module, "_registry_instance", AgentRegistry([
        AgentProfile("native-contract-fixture", "Contract Fixture", str(workspace))
    ], "native-contract-fixture"))
    monkeypatch.setattr(registry_module, "_registry_signature", None)
    monkeypatch.setattr(registry_module, "_registry_pinned", True)

    from agent.memory.config import MemoryConfig
    from agent.memory.manager import MemoryManager
    from bridge.agent_initializer import AgentInitializer

    memory = MemoryManager(
        MemoryConfig(workspace_root=str(workspace)), embedding_provider=None
    )
    try:
        initializer = AgentInitializer(None, SimpleNamespace())
        initializer._is_shared_conversation = lambda *_args: False
        tools = initializer._load_tools(
            str(workspace), memory,
            [MemorySearchTool(memory), MemoryGetTool(memory)],
            session_id="native-contract-fixture",
            host_agent_id="native-contract-fixture",
        )
        executor = AgentStreamExecutor.__new__(AgentStreamExecutor)
        executor.tools = {tool.name: tool for tool in tools}
        executor.messages = []
        injected = executor._select_tools_for_injection()
        # Capture the manager while the synthetic registry is still active;
        # ToolManager instances are keyed by their resolved state root.
        manager = ToolManager()
        return tools, injected, manager
    finally:
        memory.close()


def test_historical_16_runtime_schemas_and_registry_descriptors(tmp_path, monkeypatch):
    tools, injected, manager = _fixture(tmp_path, monkeypatch)
    contract_data = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))
    active = contract_data["current_synthetic_runtime"]
    expected = {entry["name"]: entry for entry in active["tools"]}

    assert set(expected) == HISTORICAL_NAMES
    assert len(expected) == 16
    assert {tool.name for tool in injected} == HISTORICAL_NAMES
    actual_schemas = build_tools_schema(injected)
    actual = {schema["name"]: schema["input_schema"] for schema in actual_schemas}
    assert actual == {name: entry["parameters"] for name, entry in expected.items()}

    assert set(manager.tool_classes) == set(REGISTRY_CLASSES) - {
        "memory_get", "memory_search"
    }
    all_tools = {
        name: manager.create_tool(name)
        for name in manager.tool_classes
    }
    memory = next(tool for tool in tools if tool.name == "memory_search").memory_manager
    all_tools["memory_search"] = MemorySearchTool(memory)
    all_tools["memory_get"] = MemoryGetTool(memory)
    assert set(all_tools) == set(REGISTRY_CLASSES)

    for name, tool in all_tools.items():
        assert _class_path(type(tool)) == REGISTRY_CLASSES[name]
        assert _descriptor(tool) == DESCRIPTORS[name]

    # Restricted workers get only these exact built-in classes. This is the
    # worker construction allowlist, not a name-based policy inference.
    from agent.permission import Authority, WORKSPACE_WRITE
    from agent.subagent.runner import _private_tools
    from agent.subagent.templates import GENERAL_PURPOSE
    root = str(tmp_path / "workspace")
    parent = SimpleNamespace(tools=list(all_tools.values()))
    authority = Authority(
        WORKSPACE_WRITE, frozenset({"fs.read", "fs.write", "time"}),
        (root,), (root,),
    )
    worker_tools = _private_tools(parent, GENERAL_PURPOSE, authority=authority)
    assert {_class_path(type(tool)) for tool in worker_tools} == {
        "agent.tools.read.read.Read", "agent.tools.write.write.Write",
        "agent.tools.edit.edit.Edit", "agent.tools.ls.ls.Ls",
        "agent.tools.search_files.search_files.SearchFiles",
        "agent.tools.current_time.current_time.TimeTool",
    }


def test_authorized_root_and_verification_schema_additions_are_explicit():
    contract_data = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))
    additions = contract_data["authorized_schema_additions"]
    subagent = SubagentTool()
    subagent_params = subagent.params
    assert subagent_params == additions["subagent"]
    assert {"read_roots", "write_roots", "verification"} <= set(
        subagent_params["properties"]
    )
    assert {"read_roots", "write_roots", "verification"} <= set(
        subagent_params["properties"]["tasks"]["items"]["properties"]
    )
    assert not ({"read_roots", "write_roots", "verification"} & set(
        subagent_params["required"]
    ))

    peer = AgentDelegateClass()
    assert peer.params == additions["agent_delegate"]
    assert "verification" in peer.params["properties"]
    assert "verification" not in peer.params["required"]
    assert "agent_id" in peer.params["required"]
    assert "task" in peer.params["required"]
    assert EvolutionUndoTool.name == "evolution_undo"
    assert AgentDelegateClass.name == "agent_delegate"
