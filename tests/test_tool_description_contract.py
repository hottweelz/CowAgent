"""Phase 2 may shorten top-level prose, but must retain the argument contract.

These hashes freeze names and complete parameter schemas from 0469a4f3,
including parameter descriptions, types, required fields, enums and defaults.
An intentional future API change must review and update this contract.
"""

import hashlib
import json

import pytest

from agent.tools.bash.bash import Bash
from agent.tools.browser.browser_tool import BrowserTool
from agent.tools.scheduler.scheduler_tool import SchedulerTool
from agent.tools.search_files.search_files import SearchFiles


@pytest.mark.parametrize("tool, expected", [
    (Bash, "fb1df3d9b5a1af153f058fa479c5d9b794329e314c10d69a3f4334f783ecbc87"),
    (BrowserTool, "92460dfbee95e63b0763490107db272ac0f9618dc04fe0cfb603d9e978920ffb"),
    (SchedulerTool, "875c13162c03c7bd9f8c1e5d0180a664da2e8bb076bf4155aa3113a0a9dc0a03"),
    (SearchFiles, "7b8db53bc8f059ab8c78f28dba480421da770b9c8da18f8a640f90de7a95db84"),
])
def test_tool_argument_schema_is_unchanged(tool, expected):
    schema = {"name": tool.name, "parameters": tool.params}
    encoded = json.dumps(schema, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(encoded.encode()).hexdigest() == expected, tool.name


@pytest.mark.parametrize("desktop", [False, True])
def test_bash_description_keeps_safety_when_workspace_changes(tmp_path, monkeypatch, desktop):
    if desktop:
        monkeypatch.setenv("COW_DESKTOP", "1")
    else:
        monkeypatch.delenv("COW_DESKTOP", raising=False)
    first, second = tmp_path / "first", tmp_path / "second"
    tool = Bash({"cwd": str(first)})
    tool.set_cwd(str(second))
    assert str(first) not in tool.description
    assert str(second) in tool.description
    assert "{cwd}" not in tool.description
    assert "destructive" in tool.description and "confirm" in tool.description
    assert ("unless explicitly requested" in tool.description) is desktop
