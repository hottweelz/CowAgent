import threading

import pytest

from agent.memory.summarizer import MemoryFlushManager
from common import runtime_drain as drain


class _FakeRuntime:
    def validate(self):
        pass


@pytest.fixture
def coordinator(monkeypatch):
    monkeypatch.setattr(drain, "_installed", None)
    monkeypatch.setattr(drain, "_validate_owner", lambda owner: _FakeRuntime())
    coordinator = drain.RuntimeDrain()
    coordinator.bind_owner(object())
    drain.install(coordinator)
    return coordinator


def test_async_memory_flush_remains_tracked_through_file_write(
    tmp_path, coordinator, monkeypatch
):
    manager = MemoryFlushManager(tmp_path, object())
    entered = threading.Event()
    finish = threading.Event()
    write_daily_summary = manager.write_daily_summary

    def summarize(messages, max_messages=0):
        return "- completed memory write"

    def blocked_write(*args, **kwargs):
        entered.set()
        assert finish.wait(2)
        return write_daily_summary(*args, **kwargs)

    monkeypatch.setattr(manager, "_summarize_messages", summarize)
    monkeypatch.setattr(manager, "write_daily_summary", blocked_write)
    assert manager.flush_from_messages([{"role": "user", "content": "remember this"}])
    worker = manager._last_flush_thread
    assert entered.wait(2)

    coordinator.close_admission()
    assert coordinator.wait(0)["active"] == {"memory_flush": 1}
    finish.set()
    worker.join(2)

    assert not worker.is_alive()
    assert "completed memory write" in manager.get_today_memory_file().read_text()
    assert coordinator.wait(1)["active"] == {}


def test_closed_fresh_flush_rejects_before_hash_claim_or_file_write(
    tmp_path, coordinator, monkeypatch
):
    manager = MemoryFlushManager(tmp_path, object())
    monkeypatch.setattr(
        manager, "_summarize_messages", lambda messages, max_messages=0: "- should not write"
    )
    coordinator.close_admission()

    assert manager.flush_from_messages(
        [{"role": "user", "content": "remember this"}]
    ) is False
    assert manager._last_flush_thread is None
    assert manager._trim_inflight_hashes == set()
    assert manager._trim_flushed_hashes == set()
    assert manager._daily_inflight_hashes == set()
    assert not manager.get_today_memory_file().exists()
