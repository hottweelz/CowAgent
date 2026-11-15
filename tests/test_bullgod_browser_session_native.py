"""Opt-in native profile storage proof; no HTTP or real authentication claim.

The installed browser visits one task-owned file page. Persistent storage must
survive BrowserService restart and must not leak into a second profile. This
proves profile behavior only, not access to Muse, Grok Bot or an authenticated
HTTP application. All profiles and page data are disposable fixtures.
"""

import os

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("COW_BROWSER_NATIVE_TEST") != "1",
    reason="opt-in installed browser test",
)


def test_profile_storage_survives_restart_without_cross_profile_leakage(tmp_path):
    pytest.importorskip("playwright.sync_api")
    from agent.tools.browser.browser_env import detect_system_chrome
    from agent.tools.browser.browser_tool import BrowserTool

    if detect_system_chrome() is None:
        pytest.skip("no installed system Chrome/Edge")

    page = tmp_path / "fixture.html"
    page.write_text('''<html><body>
<p id="state"></p><input id="input">
<button onclick="localStorage.setItem('fixture-state','FICTIONAL_SESSION');
 document.querySelector('#state').textContent='FICTIONAL_SESSION'">Save fixture state</button>
<script>document.querySelector('#state').textContent =
 localStorage.getItem('fixture-state') || 'EMPTY_PROFILE';</script>
</body></html>''', encoding="utf-8")
    previous = BrowserTool._shared_service
    tools = []

    def open_profile(profile):
        BrowserTool._shared_service = None
        tool = BrowserTool({
            "cwd": str(tmp_path), "user_data_dir": str(profile),
            "screenshot_dir": str(tmp_path / "screenshots"),
            "headless": True, "idle_timeout": 0, "startup_timeout": 20,
            "engine": "system-chrome",
        })
        tools.append(tool)
        result = tool.execute({"action": "navigate", "url": page.as_uri(), "timeout": 15000})
        assert result.status == "success", result.result
        return tool, result.result

    try:
        profile = tmp_path / "persistent-profile"
        first, initial = open_profile(profile)
        assert "EMPTY_PROFILE" in initial and "FICTIONAL_SESSION" not in initial
        result = first.execute({"action": "click", "selector": "button"})
        assert result.status == "success", result.result
        saved = first.execute({"action": "snapshot"})
        assert saved.status == "success" and "FICTIONAL_SESSION" in saved.result
        first.close()

        second, restored = open_profile(profile)
        assert "FICTIONAL_SESSION" in restored and "EMPTY_PROFILE" not in restored
        result = second.execute({"action": "fill", "selector": "#missing",
                                 "text": "unused", "timeout": 250})
        assert result.status == "error", result.result
        second.close()

        _, separate = open_profile(tmp_path / "separate-profile")
        assert "EMPTY_PROFILE" in separate and "FICTIONAL_SESSION" not in separate
    finally:
        try:
            for tool in reversed(tools):
                if tool._service is not None:
                    tool.close()
        finally:
            BrowserTool._shared_service = previous
