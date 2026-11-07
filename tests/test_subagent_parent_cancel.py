"""A user Stop must reach running sub agents; timeouts stay per task."""

import json
import threading
from types import SimpleNamespace

import pytest

from agent.subagent import SubagentSettings, SubagentTask, runner
from agent.subagent.templates import GENERAL_PURPOSE
from agent.tools.subagent import SubagentTool

TEMPLATES = {GENERAL_PURPOSE.name: GENERAL_PURPOSE}


@pytest.fixture
def parent(tmp_path, monkeypatch):
    from agent.protocol.agent import Agent
    from agent.registry import AgentProfile, AgentRegistry, set_agent_registry
    from agent.tools.read.read import Read
    from agent.tools.write.write import Write
    from agent.tools.ls.ls import Ls
    from agent.tools.search_files.search_files import SearchFiles
    from agent.workspace import project_store, session_prefs
    from agent import team
    from config import conf

    tmp_path.mkdir(parents=True, exist_ok=True)
    owner, session = "cancel-test-owner", "cancel-test-session"
    profile = AgentProfile(owner, owner, str(tmp_path), model="fixture-model", bot_type="fixture")
    set_agent_registry(AgentRegistry([profile], owner))
    monkeypatch.setattr("agent.permission.authority._registry_profiles", lambda: [profile])
    monkeypatch.setattr("agent.recovery.runtime._registry_profiles", lambda: [profile])
    monkeypatch.setattr(team, "team_file", lambda _settings: tmp_path / "team.json")
    conf()["agent_workspace"] = str(tmp_path)
    project_store.set_project_dir(session, str(tmp_path), owner)
    session_prefs.set_prefs(session, owner, permission="workspace-write")
    tools = [Read({"cwd": str(tmp_path)}), Write({"cwd": str(tmp_path)}),
             Ls({"cwd": str(tmp_path)}), SearchFiles({"cwd": str(tmp_path)})]
    result = Agent("fixture parent", model=object(), tools=tools, workspace_dir=str(tmp_path),
                   enable_skills=False, skip_context_files=True)
    result._current_agent_id = owner
    result._current_session_id = session
    result.permission_mode = "workspace-write"
    result.project_dir = str(tmp_path)
    return result


@pytest.fixture
def children(monkeypatch):
    """Stub children: goals starting with "slow" block until cancelled or released."""
    state = SimpleNamespace(started=[], events={}, entered=threading.Event(),
                            release=threading.Event(), attempts={})

    class Child:
        def run_stream(self, goal, clear_history, cancel_event, on_event, steer_inbox=None):
            state.started.append(goal)
            state.events[goal] = cancel_event
            if not goal.startswith("slow"):
                return f"{goal} done"
            state.entered.set()
            while not state.release.wait(0.01):
                if cancel_event.is_set():
                    return "stopped"
            return "released"

    original = runner._build_child
    def build(parent, template, task):
        child = original(parent, template, task)
        run = Child().run_stream
        def run_stream(goal, clear_history, cancel_event, on_event, steer_inbox=None):
            state.attempts[goal] = child.recovery_attempt
            return run(goal, clear_history, cancel_event, on_event, steer_inbox)
        child.run_stream = run_stream
        return child
    monkeypatch.setattr(runner, "_build_child", build)
    yield state
    state.release.set()


def _run_in_thread(parent, *goals, cancel_event, **settings):
    results = []
    thread = threading.Thread(target=lambda: results.extend(runner.run_tasks(
        parent, [SubagentTask(g) for g in goals], TEMPLATES,
        SubagentSettings(**settings), cancel_event=cancel_event)))
    thread.start()
    return thread, results


def test_stop_reaches_running_child_and_cancels_queued_ones(children, parent):
    stop = threading.Event()
    thread, results = _run_in_thread(parent, "slow", "queued", cancel_event=stop,
                                     max_concurrent=1, timeout_seconds=5)
    assert children.entered.wait(2)
    stop.set()
    thread.join(2)
    assert not thread.is_alive()
    assert children.events["slow"].is_set()
    assert children.started == ["slow"]
    assert [r["status"] for r in results] == ["cancelled", "cancelled"]


def test_stop_keeps_an_already_completed_sibling(children, parent):
    stop = threading.Event()
    thread, results = _run_in_thread(parent, "slow", "sibling", cancel_event=stop, timeout_seconds=5)
    assert children.entered.wait(2)
    while "sibling" not in children.started:
        threading.Event().wait(0.01)
    threading.Event().wait(0.2)
    stop.set()
    thread.join(2)
    assert [r["status"] for r in results] == ["cancelled", "completed"]
    assert results[1]["summary"] == "sibling done"


def test_timeout_cancels_only_the_slow_child(children, parent):
    stop = threading.Event()
    results = runner.run_tasks(parent, [SubagentTask("slow"), SubagentTask("sibling")],
                               TEMPLATES, SubagentSettings(timeout_seconds=0.2),
                               cancel_event=stop)
    assert [r["status"] for r in results] == ["timed_out", "completed"]
    assert children.events["slow"].is_set()
    assert children.attempts["slow"].store.get(children.attempts["slow"].claim.task_id)["state"] == "timed_out"
    assert children.attempts["sibling"].store.get(children.attempts["sibling"].claim.task_id)["state"] == "completed"
    assert not stop.is_set()


def test_tool_passes_its_cancel_event_and_skips_children_once_stopped(children, monkeypatch, tmp_path):
    (tmp_path / "subagents").mkdir()
    monkeypatch.setattr(SubagentSettings, "from_config", classmethod(lambda cls: SubagentSettings()))
    tool = SubagentTool({"cwd": str(tmp_path)})
    tool.context = SimpleNamespace(workspace_dir=str(tmp_path))
    tool.cancel_event = threading.Event()
    tool.cancel_event.set()

    result = tool.execute({"goal": "investigate"})

    assert json.loads(result.result)["results"][0]["status"] == "cancelled"
    assert children.started == []
