"""Source releases with a separate data directory must stay read-only."""
from pathlib import Path

from plugins import plugin_manager


def test_explicit_data_root_contains_mutable_plugin_store(tmp_path, monkeypatch):
    monkeypatch.setenv("COW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(plugin_manager.sys, "frozen", False, raising=False)
    result = Path(plugin_manager._plugins_data_dir())
    assert result == tmp_path / "data/plugins"
    assert result.is_dir()


def test_source_without_data_override_retains_plugin_path(monkeypatch):
    monkeypatch.delenv("COW_DATA_DIR", raising=False)
    monkeypatch.setattr(plugin_manager.sys, "frozen", False, raising=False)
    assert plugin_manager._plugins_data_dir() == "./plugins"
