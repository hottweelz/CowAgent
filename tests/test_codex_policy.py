"""Focused tests for the fail-closed Codex enrollment policy."""
import hashlib
from types import SimpleNamespace

import pytest

from agent.external.codex_policy import (
    DISABLED_FEATURES,
    PROFILE,
    VERSION,
    CodexPolicy,
    SafetyGateError,
)


FAKE_CREDENTIAL = "fake-codex-provider-canary-do-not-leak"
PROVIDER_ENV = "CODEX_TEST_PROVIDER_TOKEN"
MODEL = "codex-test-model"
PROVIDER = "test-provider"


def enrolled_policy(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    config = codex_home / "config.toml"
    # This fixture is deliberately small and writes only under tmp_path.
    config.write_text(
        f'model = "{MODEL}"\n'
        f'model_provider = "{PROVIDER}"\n'
        'model_reasoning_effort = "high"\n'
        '\n[mcp_servers.fixture_mcp]\nurl = "https://example.invalid/mcp"\n'
        '\n[shell_environment_policy]\ninherit = "all"\n'
        '\n[shell_environment_policy.set]\nCODEX_TEST_INJECTED = "must-be-cleared"\n'
        '\n[model_providers.test-provider]\n'
        f'env_key = "{PROVIDER_ENV}"\n',
        encoding="utf-8",
    )
    auth = codex_home / "auth.json"
    auth.write_text('{"access_token":"' + FAKE_CREDENTIAL + '"}\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    monkeypatch.setenv("PATH", "/fake/bin")
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv(PROVIDER_ENV, FAKE_CREDENTIAL)
    monkeypatch.setenv("UNRELATED_SECRET", "unrelated-secret-canary")
    monkeypatch.setenv("CODEX_TEST_INJECTED", "parent-value-must-not-pass")
    monkeypatch.setattr("agent.external.codex_policy.sys.platform", "darwin")
    return CodexPolicy(tmp_path / "fake-bin" / "codex"), config, auth


def mock_codex_version(monkeypatch, stdout=None, *, error=None):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if error:
            raise error
        return SimpleNamespace(stdout=stdout or f"codex-cli {VERSION}\n")

    monkeypatch.setattr("agent.external.codex_policy.subprocess.run", run)
    return calls


def test_launch_keeps_model_provider_auth_owned_and_does_not_write_config(tmp_path, monkeypatch):
    policy, config, auth = enrolled_policy(tmp_path, monkeypatch)
    config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
    auth_hash = hashlib.sha256(auth.read_bytes()).hexdigest()
    calls = mock_codex_version(monkeypatch)

    argv, env, expected = policy.launch()

    assert calls[0][0] == [str(policy.executable), "--version"]
    assert argv[:3] == [str(policy.executable), "app-server", "--stdio"]
    assert "--model" not in argv and "--provider" not in argv
    assert "--auth" not in argv and "auth.json" not in argv
    assert expected == {
        "model": MODEL,
        "modelProvider": PROVIDER,
        "reasoningEffort": "high",
        "mcp_servers": ("fixture_mcp",),
    }
    assert FAKE_CREDENTIAL not in " ".join(argv)
    assert FAKE_CREDENTIAL not in repr(expected)
    assert env[PROVIDER_ENV] == FAKE_CREDENTIAL
    assert hashlib.sha256(config.read_bytes()).hexdigest() == config_hash
    assert hashlib.sha256(auth.read_bytes()).hexdigest() == auth_hash


def test_launch_narrows_capabilities_environment_and_clears_configured_shell_set(tmp_path, monkeypatch):
    policy, _, _ = enrolled_policy(tmp_path, monkeypatch)
    mock_codex_version(monkeypatch)

    argv, env, _ = policy.launch()

    assert all(argv.count(feature) == 1 for feature in DISABLED_FEATURES)
    assert all(argv[argv.index(feature) - 1] == "--disable" for feature in DISABLED_FEATURES)
    assert "-c" in argv and 'mcp_servers.fixture_mcp.enabled=false' in argv
    assert 'shell_environment_policy.inherit="none"' in argv
    assert 'shell_environment_policy.set.CODEX_TEST_INJECTED=""' in argv
    assert set(env).issubset({"HOME", "PATH", "LANG", "LC_ALL", "TMPDIR", "CODEX_HOME", PROVIDER_ENV})
    assert env[PROVIDER_ENV] == FAKE_CREDENTIAL
    assert "UNRELATED_SECRET" not in env
    assert "CODEX_TEST_INJECTED" not in env


def test_launch_fails_closed_when_codex_is_missing_or_version_is_unvalidated(tmp_path, monkeypatch):
    home = tmp_path / "empty-codex-home"
    home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setattr("agent.external.codex_policy.sys.platform", "darwin")
    mock_codex_version(monkeypatch, error=FileNotFoundError("fake Codex is absent"))
    policy = CodexPolicy(tmp_path / "fake-bin" / "codex")

    with pytest.raises(SafetyGateError, match="unavailable"):
        policy.launch()

    (home / "config.toml").write_text(
        f'model = "{MODEL}"\nmodel_provider = "{PROVIDER}"\n'
        '[model_providers.test-provider]\n'
        f'env_key = "{PROVIDER_ENV}"\n', encoding="utf-8"
    )
    mock_codex_version(monkeypatch, "codex-cli 999.0.0\n")

    with pytest.raises(SafetyGateError, match="Unvalidated Codex version"):
        policy.launch()


class StubClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def request(self, method, params, timeout):
        self.calls.append((method, params, timeout))
        response = self.responses[method]
        return response(params) if callable(response) else response


def start_thread_responses(cwd, **overrides):
    result = {
        "activePermissionProfile": {"id": PROFILE},
        "approvalPolicy": "on-request",
        "approvalsReviewer": "user",
        "cwd": str(cwd),
        "sandbox": {
            "type": "workspaceWrite",
            "networkAccess": False,
            "excludeSlashTmp": True,
            "excludeTmpdirEnvVar": True,
            "writableRoots": [],
        },
        "thread": {"id": "fake-thread"},
    }
    result.update(overrides)
    return {
        "permissionProfile/list": {"data": [{"id": PROFILE, "allowed": True}]},
        "thread/start": result,
    }


def test_start_thread_accepts_active_profile_with_restricted_sandbox(tmp_path):
    cwd = tmp_path / "workspace"
    client = StubClient(start_thread_responses(cwd))

    result = CodexPolicy(tmp_path / "codex").start_thread(client, cwd)

    assert result["activePermissionProfile"]["id"] == PROFILE
    assert client.calls[1][1] == {
        "cwd": str(cwd),
        "permissions": PROFILE,
        "approvalPolicy": "on-request",
        "approvalsReviewer": "user",
        "allowProviderModelFallback": False,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"activePermissionProfile": {"id": "other"}, "approvalPolicy": "never",
         "approvalsReviewer": "auto"},
        {"sandbox": {"type": "workspaceWrite", "networkAccess": True,
                     "excludeSlashTmp": True, "excludeTmpdirEnvVar": True, "writableRoots": []}},
        {"sandbox": {"type": "workspaceWrite", "networkAccess": False,
                     "excludeSlashTmp": False, "excludeTmpdirEnvVar": False, "writableRoots": []}},
    ],
)
def test_start_thread_rejects_unsafe_effective_policy(tmp_path, changes):
    cwd = tmp_path / "workspace"
    client = StubClient(start_thread_responses(cwd, **changes))

    with pytest.raises(SafetyGateError, match="Effective Codex permission policy"):
        CodexPolicy(tmp_path / "codex").start_thread(client, cwd)


def inspection_responses(*, mcp_enabled=False, feature_enabled=False, shell_inherit="none"):
    config = {
        "model": MODEL,
        "model_provider": PROVIDER,
        "model_reasoning_effort": "high",
        "mcp_servers": {"fixture_mcp": {"enabled": mcp_enabled}},
        "shell_environment_policy": {"inherit": shell_inherit, "set": {}},
        "notify": [],
        "web_search": "disabled",
    }
    return {
        "config/read": {"config": config},
        "mcpServerStatus/list": {"data": [{"name": "fixture_mcp", "runtimeStatus": "disabled",
                                               "tools": [], "resources": []}]},
        "experimentalFeature/list": {"data": [{"name": name, "enabled": feature_enabled}
                                                 for name in DISABLED_FEATURES]},
    }


EXPECTED = {
    "model": MODEL,
    "modelProvider": PROVIDER,
    "reasoningEffort": "high",
    "mcp_servers": ("fixture_mcp",),
}


def test_attest_configuration_accepts_matching_settings(tmp_path):
    thread = {"model": MODEL, "modelProvider": PROVIDER,
              "thread": {"id": "fake-thread", "reasoningEffort": "high"}}
    client = StubClient(inspection_responses())

    result = CodexPolicy(tmp_path / "codex").attest_configuration(
        client, tmp_path, thread, EXPECTED
    )

    assert result["shell_inherit"] == "none"
    assert result["features"] == {name: False for name in DISABLED_FEATURES}


@pytest.mark.parametrize(
    "thread,inspection",
    [
        ({"model": "different-model", "modelProvider": PROVIDER,
          "thread": {"id": "fake-thread", "reasoningEffort": "high"}}, inspection_responses()),
        ({"model": MODEL, "modelProvider": PROVIDER,
          "thread": {"id": "fake-thread", "reasoningEffort": "high"}},
         inspection_responses(mcp_enabled=True, feature_enabled=True, shell_inherit="all")),
    ],
)
def test_attest_configuration_rejects_model_or_unsafe_capability_config(tmp_path, thread, inspection):
    client = StubClient(inspection)

    with pytest.raises(SafetyGateError):
        CodexPolicy(tmp_path / "codex").attest_configuration(
            client, tmp_path, thread, EXPECTED
        )
