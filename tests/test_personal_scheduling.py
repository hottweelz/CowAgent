"""Personal commitments use typed pointers in CowAgent's existing scheduler."""

import sys
import threading
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from agent.personal.scheduling import (
    execute_scheduled_commitment,
    reconcile_commitments,
    scheduling_status,
    sync_commitment,
)
from agent.tools.scheduler import integration
from agent.tools.scheduler.scheduler_service import SchedulerService
from agent.tools.scheduler.task_store import TaskStore


def _profile(agent_id="bullgod"):
    return SimpleNamespace(id=agent_id, workspace="/tmp/bullgod")


def _commitment(**overrides):
    result = {
        "commitment_id": "commit-1",
        "agent_id": "bullgod",
        "source_session_id": "owner-session",
        "revision": 3,
        "status": "active",
        "read_authorized": True,
        "objective": "Fetch approved news and prepare a briefing",
        "schedule": {"cron": "0 8 * * *", "timezone": "America/New_York"},
    }
    result.update(overrides)
    return result


def test_sync_creates_typed_pointer_without_owner_prompt(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))

    assert sync_commitment(_profile(), _commitment(), store)

    task = store.get_task("personal_commit-1")
    assert task["agent_id"] == "bullgod"
    assert task["schedule"] == {
        "type": "cron",
        "expression": "0 8 * * *",
        "timezone": "America/New_York",
    }
    assert task["next_run_at"]
    assert task["action"] == {
        "type": "personal_commitment",
        "commitment_id": "commit-1",
        "revision": 3,
        "channel_type": "web",
        "receiver": "owner-session",
        "notify_session_id": "owner-session",
    }
    assert "objective" not in task["action"]
    assert "task_description" not in task["action"]


def test_sync_updates_pointer_and_disables_inactive_or_unauthorized_commitment(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))
    sync_commitment(_profile(), _commitment(), store)

    updated = _commitment(revision=4, schedule={"cron": "30 9 * * *", "timezone": "America/New_York"})
    sync_commitment(_profile(), updated, store)
    task = store.get_task("personal_commit-1")
    assert task["action"]["revision"] == 4
    assert task["schedule"]["expression"] == "30 9 * * *"
    assert task["enabled"] is True

    sync_commitment(_profile(), _commitment(revision=5, status="paused"), store)
    assert store.get_task("personal_commit-1")["enabled"] is False

    sync_commitment(_profile(), _commitment(revision=6, read_authorized=False), store)
    assert store.get_task("personal_commit-1")["enabled"] is False


def test_sync_leaves_unscheduled_commitment_without_pointer(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))

    sync_commitment(_profile(), _commitment(schedule=None), store)

    assert store.get_task("personal_commit-1") is None


def test_sync_preserves_existing_due_slot_for_catchup(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))
    sync_commitment(_profile(), _commitment(), store)
    overdue = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    store.update_task("personal_commit-1", {"next_run_at": overdue})

    sync_commitment(_profile(), _commitment(), store)

    assert store.get_task("personal_commit-1")["next_run_at"] == overdue


def test_sync_rejects_pointer_collision_owned_by_another_agent(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))
    store.add_task({"id": "personal_commit-1", "agent_id": "another-agent", "enabled": True})

    try:
        sync_commitment(_profile(), _commitment(), store)
    except ValueError as exc:
        assert "identity collision" in str(exc)
    else:
        raise AssertionError("expected owner collision to be rejected")


def test_delayed_stale_sync_cannot_replace_newer_active_pointer(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))

    assert sync_commitment(_profile(), _commitment(revision=3), store)
    assert sync_commitment(_profile(), _commitment(revision=2), store) is False

    pointer = store.get_task("personal_commit-1")
    assert pointer["action"]["revision"] == 3
    assert pointer["enabled"] is True


def test_delayed_stale_active_sync_cannot_reenable_newer_paused_pointer(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))

    assert sync_commitment(_profile(), _commitment(revision=2), store)
    assert sync_commitment(_profile(), _commitment(revision=4, status="paused"), store)
    assert sync_commitment(_profile(), _commitment(revision=3, status="active"), store) is False

    pointer = store.get_task("personal_commit-1")
    assert pointer["action"]["revision"] == 4
    assert pointer["enabled"] is False


def test_concurrent_old_projection_waits_then_cannot_replace_new_revision(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))
    older_waiting = threading.Event()
    newer_written = threading.Event()
    errors = []

    class OrderedStore:
        def get_task(self, task_id):
            return store.get_task(task_id)

        def sync_personal_pointer(self, pointer, revision):
            if revision == 2:
                older_waiting.set()
                assert newer_written.wait(3)
            applied = store.sync_personal_pointer(pointer, revision)
            if revision == 3:
                newer_written.set()
            return applied

    adapter = OrderedStore()

    def old_sync():
        try:
            sync_commitment(_profile(), _commitment(revision=2), adapter)
        except Exception as exc:  # surfaced in the test thread
            errors.append(exc)

    worker = threading.Thread(target=old_sync)
    worker.start()
    assert older_waiting.wait(3)
    assert sync_commitment(_profile(), _commitment(revision=3), adapter)
    worker.join(3)

    assert not worker.is_alive()
    assert not errors
    assert store.get_task("personal_commit-1")["action"]["revision"] == 3


def test_reconciliation_reads_enabled_profiles_and_syncs_commitments(monkeypatch, tmp_path):
    profile = _profile()
    fake_store = SimpleNamespace(snapshot=lambda: [_commitment()])
    monkeypatch.setitem(
        sys.modules,
        "agent.memory.commitments",
        types.SimpleNamespace(CommitmentStore=lambda conversation: fake_store),
    )
    monkeypatch.setattr("agent.memory.get_conversation_store", lambda workspace: workspace)
    registry = SimpleNamespace(list=lambda include_disabled: [profile])
    task_store = TaskStore(str(tmp_path / "tasks.json"))

    reconcile_commitments(registry, task_store)

    assert task_store.get_task("personal_commit-1")["action"]["commitment_id"] == "commit-1"


def test_typed_callback_uses_stable_occurrence_and_advances_only_delivery(monkeypatch):
    calls = []

    class Service:
        def __init__(self, agent_id, session_id):
            assert (agent_id, session_id) == ("bullgod", "owner-session")

        def run(self, commitment_id, *, occurrence_key, expected_revision):
            calls.append((commitment_id, occurrence_key, expected_revision))
            # The service reports an already-delivered duplicate for a retry.
            return {"status": "delivered", "duplicate": True}

    registry = SimpleNamespace(get_addressed=lambda agent_id: _profile(agent_id))
    monkeypatch.setattr("agent.registry.get_agent_registry", lambda: registry)
    monkeypatch.setitem(
        sys.modules,
        "agent.personal.commitments",
        types.SimpleNamespace(CommitmentService=Service),
    )
    task = {
        "agent_id": "bullgod",
        "next_run_at": "2026-11-10T13:00:00+00:00",
        "action": {
            "type": "personal_commitment",
            "commitment_id": "commit-1",
            "revision": 3,
            "receiver": "owner-session",
        },
    }

    assert execute_scheduled_commitment(task, "bullgod")["status"] == "delivered"
    assert execute_scheduled_commitment(task, "bullgod")["status"] == "delivered"
    assert calls[0] == calls[1]
    assert calls[0][1] == "commit-1:3:2026-11-10T13:00:00+00:00"


def test_typed_callback_keeps_failed_and_uncertain_runs_retryable(monkeypatch):
    class Service:
        def __init__(self, *_args):
            pass

        def run(self, *_args, **_kwargs):
            return {"status": "uncertain"}

    monkeypatch.setattr(
        "agent.registry.get_agent_registry",
        lambda: SimpleNamespace(get_addressed=lambda agent_id: _profile(agent_id)),
    )
    monkeypatch.setitem(
        sys.modules,
        "agent.personal.commitments",
        types.SimpleNamespace(CommitmentService=Service),
    )
    task = {
        "agent_id": "bullgod",
        "next_run_at": "2026-11-10T13:00:00+00:00",
        "action": {
            "commitment_id": "commit-1",
            "revision": 3,
            "receiver": "owner-session",
        },
    }

    assert execute_scheduled_commitment(task, "bullgod")["status"] == "uncertain"


def test_scheduling_status_reads_existing_pointer_without_claiming_inactive_slot(monkeypatch):
    record = _commitment()
    task = {
        "agent_id": "bullgod",
        "enabled": True,
        "schedule": {"type": "cron", "expression": "0 8 * * *", "timezone": "America/New_York"},
        "next_run_at": "2026-11-10T13:00:00+00:00",
        "action": {
            "type": "personal_commitment",
            "commitment_id": "commit-1",
            "revision": 3,
            "receiver": "owner-session",
        },
    }
    store = SimpleNamespace(get_task=lambda task_id: task)
    monkeypatch.setattr(
        "agent.tools.scheduler.integration.get_task_store",
        lambda agent_id=None: store,
    )

    active = scheduling_status(_profile(), record)
    inactive = scheduling_status(_profile(), _commitment(status="cancelled"))

    assert active["schedule_status"] == "scheduled"
    assert active["next_run_at"] == task["next_run_at"]
    assert "10 minutes" in active["catch_up_policy"]
    assert inactive["next_run_at"] is None
    assert inactive["schedule_status"] == "inactive"


def test_failed_commitment_advances_slot_but_native_run_is_error(monkeypatch):
    finished = []

    class RunStore:
        def finish_run(self, run_id, *, status, error, extras):
            finished.append((run_id, status, error))

    monkeypatch.setattr(
        integration,
        "_record_scheduler_run",
        lambda task, agent_id, trigger: (RunStore(), "native-run-1"),
    )
    monkeypatch.setattr(
        integration,
        "_is_channel_ready",
        lambda *args: True,
    )
    monkeypatch.setattr(
        "agent.personal.scheduling.execute_scheduled_commitment",
        lambda *args, **kwargs: {"status": "failed", "error": "network error"},
    )

    task = {
        "id": "personal_commit-1",
        "action": {
            "type": "personal_commitment",
            "channel_type": "web",
            "receiver": "owner-session",
        },
    }
    handled = integration._run_scheduled_task(task, object(), "bullgod")

    assert handled is True  # SchedulerService advances to the next cron slot.
    assert finished == [("native-run-1", "error", "personal commitment failed")]


def test_daily_eastern_task_catches_up_within_native_ten_minute_window(tmp_path):
    store = TaskStore(str(tmp_path / "tasks.json"))
    now = datetime(2026, 11, 10, 13, 5, tzinfo=timezone.utc)
    next_run = (now - timedelta(minutes=5)).isoformat()
    task = {
        "id": "personal_commit-1",
        "schedule": {"type": "cron", "expression": "0 8 * * *", "timezone": "America/New_York"},
        "next_run_at": next_run,
    }
    service = SchedulerService(store, lambda *_args: True)

    assert service._is_task_due(task, now) is True

    task["next_run_at"] = (now - timedelta(minutes=11)).isoformat()
    assert service._is_task_due(task, now) is False
