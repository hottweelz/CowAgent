"""Focused regressions for the extracted BullGod foundation changes."""
import sqlite3
from types import SimpleNamespace
import uuid

import pytest

from agent.discovery.contracts import provider_id
from agent.discovery.sources import NativeSource
from agent.external import approved_dispatch as approved_dispatch_module
from agent.external import filesystem_trust
from agent.external.approved_dispatch import ApprovalJournal
from agent.external.contract import ProtocolError
from agent.external.operator_control import OperatorControl
from agent.registry import AgentProfile, AgentRegistry


def _registry(tmp_path, *, default=False, model=None, provider=None):
    default_profile = AgentProfile(
        "default", "Default", str(tmp_path / "default"),
    )
    profile = AgentProfile(
        "default" if default else "worker",
        "Default" if default else "Worker",
        str(tmp_path / ("default" if default else "worker")),
        model=model,
        bot_type=provider,
    )
    registry = AgentRegistry(
        [profile] if default else [default_profile, profile],
        profile.id if default else default_profile.id,
    )
    return profile, registry


def test_read_only_approval_journal_borrows_existing_schema_without_mutation(tmp_path):
    state_dir = (tmp_path / "operator-state").resolve()
    writable = OperatorControl(state_dir, initialize=True)
    ApprovalJournal(writable)  # Create the real operator and external schema first.

    def snapshot(control):
        with control._connect() as db:
            schema = [tuple(row) for row in db.execute(
                "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
            )]
            rows = {
                table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                for table in (
                    "operator_metadata", "operator_state", "operator_decisions",
                    "external_tasks", "external_events", "external_verifications",
                    "external_approval_bindings",
                )
            }
        return schema, rows

    before = snapshot(writable)
    read_only = ApprovalJournal.open_read_only(state_dir)
    assert read_only.control.read_only is True
    assert snapshot(read_only.control) == before

    traced = []
    with read_only.control._connect() as db:
        db.set_trace_callback(traced.append)
        with pytest.raises(sqlite3.DatabaseError):
            db.execute(
                "INSERT INTO operator_state(target_id, scope_hash, revision, body) VALUES ('x','x',1,'{}')"
            )
        assert db.total_changes == 0
    assert not any(sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))
                   for sql in traced)
    assert snapshot(writable) == before


def test_read_only_approval_journal_does_not_initialize_missing_external_schema(tmp_path):
    state_dir = (tmp_path / "operator-state").resolve()
    writable = OperatorControl(state_dir, initialize=True)
    with writable._connect() as db:
        before = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    assert "external_approval_bindings" not in before

    with pytest.raises(ProtocolError, match="schema unavailable"):
        ApprovalJournal.open_read_only(state_dir)

    with writable._connect() as db:
        after = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    assert after == before


def test_read_only_approval_journal_lock_rejects_before_file_or_flock(tmp_path, monkeypatch):
    state_dir = (tmp_path / "operator-state").resolve()
    writable = OperatorControl(state_dir, initialize=True)
    ApprovalJournal(writable)
    read_only = ApprovalJournal.open_read_only(state_dir)
    before = {path.name for path in state_dir.iterdir()}

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("read-only journal attempted an execution lock")

    monkeypatch.setattr(approved_dispatch_module.os, "open", unexpected_call)
    monkeypatch.setattr(approved_dispatch_module.fcntl, "flock", unexpected_call)
    with pytest.raises(ProtocolError, match="Read-only journal"):
        with read_only.lock(str(uuid.uuid4())):
            pytest.fail("read-only journal yielded an execution lock")

    assert {path.name for path in state_dir.iterdir()} == before


def test_operator_control_rejects_initialize_with_read_only_before_filesystem_changes(tmp_path):
    state_dir = (tmp_path / "operator-state").resolve()
    with pytest.raises(ProtocolError, match="cannot initialize"):
        OperatorControl(state_dir, initialize=True, read_only=True)
    assert not state_dir.exists()


@pytest.mark.parametrize(
    "mount_result",
    [
        filesystem_trust.MNT_IGNORE_OWNERSHIP,
        AttributeError("statfs64 is unavailable"),
    ],
    ids=["ownership-ignored", "missing-darwin-api"],
)
def test_darwin_operator_guard_fails_closed_before_creating_state(tmp_path, monkeypatch, mount_result):
    state_dir = (tmp_path / "operator-state").resolve()
    monkeypatch.setattr(filesystem_trust, "sys", SimpleNamespace(platform="darwin"))

    def mount_flags(*_args, **_kwargs):
        if isinstance(mount_result, Exception):
            raise mount_result
        return mount_result

    monkeypatch.setattr(filesystem_trust, "_darwin_mount_flags", mount_flags)
    with pytest.raises(ProtocolError):
        OperatorControl(state_dir, initialize=True)
    assert not state_dir.exists()


def test_linux_filesystem_ownership_guard_does_not_call_darwin_api(monkeypatch):
    monkeypatch.setattr(filesystem_trust, "sys", SimpleNamespace(platform="linux"))

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("Darwin mount API called on Linux")

    monkeypatch.setattr(filesystem_trust, "_darwin_mount_flags", unexpected_call)
    filesystem_trust.require_filesystem_ownership("/not/consulted")


def test_native_route_uses_supplied_settings_not_global_config(tmp_path, monkeypatch):
    profile, registry = _registry(tmp_path, default=True)
    import config

    monkeypatch.setattr(config, "conf", lambda: (_ for _ in ()).throw(
        AssertionError("route read process-global settings")
    ))
    model, provider = NativeSource._route(profile, registry, {
        "model": "mystery-model",
        "bot_type": "custom:tenant_a",
    })
    assert (model, provider) == ("mystery-model", "custom:tenant_a")


@pytest.mark.parametrize(
    "settings, expected_provider",
    [
        ({"model": "deepseek-chat", "use_linkai": True, "linkai_api_key": "fixture",
          "bot_type": "zhipu"}, "linkai"),
        ({"model": "deepseek-chat", "bot_type": "custom:tenant_b"}, "custom:tenant_b"),
        ({"model": "deepseek-chat"}, "deepseek"),
        ({"model": "unknown-model"}, "openai"),
    ],
    ids=["linkai-precedes-configured-provider", "configured-custom-provider",
         "model-inference", "unknown-model-defaults-to-openai"],
)
def test_native_route_resolves_provider_precedence(tmp_path, settings, expected_provider):
    profile, registry = _registry(tmp_path, default=True)
    model, provider = NativeSource._route(profile, registry, settings)
    assert model == settings["model"]
    assert provider == expected_provider


def test_native_route_uses_agent_model_and_custom_provider_pin(tmp_path):
    profile, registry = _registry(
        tmp_path, model="agent-model", provider="custom:agent_provider"
    )
    model, provider = NativeSource._route(profile, registry, {
        "model": "global-model", "bot_type": "global-provider",
    })
    assert (model, provider) == ("agent-model", "custom:agent_provider")


def test_native_route_reports_unknown_when_fallback_can_change_effective_route(tmp_path):
    profile, registry = _registry(tmp_path, default=True)
    assert NativeSource._route(profile, registry, {
        "model": "deepseek-chat", "bot_type": "deepseek",
        "chat_fallback": {"enabled": True, "chain": [{"provider": "custom:x", "model": "other"}]},
    }) == (None, None)


@pytest.mark.parametrize("value", ["custom:tenant_1", "openai", "deepseek"])
def test_provider_id_accepts_existing_route_ids(value):
    assert provider_id(value)


@pytest.mark.parametrize("value", ["custom:", "custom:bad/path", "custom:bad provider", "https://provider"])
def test_provider_id_rejects_invalid_or_private_route_values(value):
    assert not provider_id(value)
