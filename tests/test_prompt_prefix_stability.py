"""Date rollover changes the prompt suffix without dropping its instructions."""

from collections import Counter
import datetime
from types import SimpleNamespace

import pytest

from agent.prompt import builder
from agent.protocol.accounting import request_snapshot
from agent.protocol.agent import Agent
from agent.protocol.agent_stream import build_tools_schema


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime.datetime):
        day = 6

        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, cls.day, 12, 34, 56, tzinfo=tz)

        @classmethod
        def info(cls):
            return {"date": cls.now().strftime("%Y-%m-%d"),
                    "weekday": cls.now().strftime("%A"), "timezone": "UTC-05",
                    "time": "12:34:56"}

    monkeypatch.setattr(datetime, "datetime", Clock)
    return Clock


@pytest.fixture
def prompt_args(tmp_path, clock, monkeypatch):
    monkeypatch.setattr(builder, "conf", lambda: {"knowledge": False})
    tools = [SimpleNamespace(name=name, description=name,
                             params={"type": "object", "properties": {}})
             for name in ("read", "write", "edit", "bash", "ls", "send",
                          "search_files", "env_config", "scheduler", "web_search",
                          "web_fetch", "vision", "browser", "time", "memory_search", "memory_get")]
    return dict(
        workspace_dir=str(tmp_path), tools=tools, memory_manager=object(),
        context_files=[builder.ContextFile("USER.md", "Keep this historical date: 2026-11-06.")],
        runtime_info={"model": "test-model", "workspace": str(tmp_path),
                      "_get_current_time": clock.info, "agent_id": "test",
                      "agent_name": "Test", "teammates": [{"id": "peer", "name": "Peer"}]},
        permission_mode="workspace-write",
    )


@pytest.mark.parametrize("language", ["en", "zh", "zh-Hant"])
@pytest.mark.parametrize("project_mode", [False, True])
def test_date_rollover_changes_only_final_suffix(prompt_args, clock, language, project_mode):
    args = {**prompt_args, "language": language}
    if project_mode:
        args["project_dir"] = args["workspace_dir"] + "/project"
    first = builder.build_agent_system_prompt(**args)
    assert builder.build_agent_system_prompt(**args) == first
    marker = "Current date:" if language == "en" else "当前日期:"
    stable, dated = first.split(marker, 1)
    assert "Runtime:" in stable if language == "en" else "运行时:" in stable
    assert "2026-11-06.md" not in stable
    assert "Keep this historical date: 2026-11-06." in stable
    assert dated.count("2026-11-06.md") == 2
    if project_mode:
        assert dated.count(args["workspace_dir"] + "/memory/2026-11-06.md") == 2
    assert "12:34:56" not in first

    # Both dated lines still exist exactly once; every other memory instruction
    # remains verbatim. Standalone helper callers retain the complete section.
    memory = builder._build_memory_section(args["memory_manager"], args["tools"],
                                           language, args["workspace_dir"], args.get("project_dir"))
    expected = Counter(line for line in memory if line)
    actual = Counter(first.splitlines())
    assert all(actual[line] >= count for line, count in expected.items())

    schemas = build_tools_schema(args["tools"])
    clock.day = 7
    second = builder.build_agent_system_prompt(**args)
    assert second.split(marker, 1)[0] == stable
    assert "2026-11-07.md" in second and "2026-11-06.md" not in second
    assert "Keep this historical date: 2026-11-06." in second
    assert build_tools_schema(args["tools"]) == schemas


def test_daily_guidance_without_runtime_and_without_memory_tools(prompt_args, clock):
    args = {**prompt_args, "language": "en", "runtime_info": None}
    first = builder.build_agent_system_prompt(**args)
    assert first.endswith("- Today's events/progress → `memory/2026-11-06.md`")
    clock.day = 7
    assert "2026-11-07.md" in builder.build_agent_system_prompt(**args)
    args["tools"] = [t for t in args["tools"] if not t.name.startswith("memory_")]
    assert "2026-11-07.md" not in builder.build_agent_system_prompt(**args)


def test_rollover_invalidates_actual_usage_and_rebuilds_fresh_date(prompt_args, clock, monkeypatch):
    monkeypatch.setattr("common.i18n.get_language", lambda: "en")
    agent = Agent("cached", tools=prompt_args["tools"], model=SimpleNamespace(model="test-model"),
                  workspace_dir=prompt_args["workspace_dir"], enable_skills=False,
                  memory_manager=prompt_args["memory_manager"], runtime_info=prompt_args["runtime_info"],
                  output_mode="logger", max_context_tokens=10000)
    agent.messages = [{"role": "user", "content": "Synthetic request"}]
    first = agent.get_full_system_prompt()
    schemas = build_tools_schema(agent.tools)
    sent = request_snapshot(agent, first, agent.messages, schemas, "test-model")
    agent.record_request_accounting(sent, schemas)
    agent.last_usage = {"prompt_tokens": 4321, "prompt_tokens_reported_calls": 1,
                        "request_fingerprint": sent["request_fingerprint"]}
    assert agent.get_context_usage()["estimated"] is False
    clock.day = 7
    usage = agent.get_context_usage()
    assert usage["estimated"] is True and usage["context_state_changed"] is True
    fresh = agent.get_full_system_prompt()
    assert "2026-11-07.md" in fresh and "2026-11-06.md" not in fresh
    assert fresh.split("Current date:")[0] == first.split("Current date:")[0]
    assert request_snapshot(agent, fresh, agent.messages, schemas, "test-model")["request_fingerprint"] != sent["request_fingerprint"]
