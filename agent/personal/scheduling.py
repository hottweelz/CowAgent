"""Bridge owner commitments to CowAgent's existing scheduler."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from common.log import logger


def _task_id(commitment_id: str) -> str:
    return f"personal_{commitment_id}"


def _enabled_schedule(commitment: dict) -> Optional[dict]:
    """Validate and convert the owner schedule to CowAgent's cron shape."""
    schedule = commitment.get("schedule")
    if not isinstance(schedule, dict):
        return None
    expression = schedule.get("cron")
    timezone_name = schedule.get("timezone")
    if not isinstance(expression, str) or not expression.strip():
        return None
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        return None

    # Use the same timezone and cron validation as native scheduler tasks.
    from agent.tools.scheduler.time_utils import resolve_timezone
    from croniter import croniter

    resolve_timezone(timezone_name)
    if not croniter.is_valid(expression):
        raise ValueError("invalid commitment cron expression")
    return {
        "type": "cron",
        "expression": expression.strip(),
        "timezone": timezone_name.strip(),
    }


def sync_commitment(profile: Any, commitment_dict: dict, task_store=None) -> bool:
    """Create, update, or disable one scheduler pointer for a commitment.

    `task_store` is injectable for focused tests. The stored task contains no
    objective or prompt. PersonalStore remains the source of truth.
    """
    if not isinstance(commitment_dict, dict):
        raise TypeError("commitment must be a mapping")
    commitment_id = commitment_dict.get("commitment_id")
    if not isinstance(commitment_id, str) or not commitment_id.strip():
        raise ValueError("commitment id is required")
    if not isinstance(getattr(profile, "id", None), str) or not profile.id:
        raise ValueError("commitment owner profile is required")
    if task_store is None:
        from agent.tools.scheduler.integration import get_task_store
        task_store = get_task_store(agent_id=profile.id)
    if task_store is None:
        raise RuntimeError("scheduler task store is unavailable")

    source_session_id = commitment_dict.get("source_session_id")
    if not isinstance(source_session_id, str) or not source_session_id:
        raise ValueError("scheduled commitment source session is required")
    revision = commitment_dict.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("commitment revision must be a positive integer")
    task_id = _task_id(commitment_id)
    existing = task_store.get_task(task_id)
    native_schedule = _enabled_schedule(commitment_dict)
    enabled = (
        commitment_dict.get("status") == "active"
        and commitment_dict.get("read_authorized") is True
        and native_schedule is not None
    )
    if not enabled and existing is None:
        return True
    task = {
        "id": task_id,
        "name": f"Personal commitment {commitment_id}",
        "agent_id": profile.id,
        "enabled": enabled,
        "created_at": (existing or {}).get("created_at") or datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "schedule": native_schedule,
        "action": {
            "type": "personal_commitment",
            "commitment_id": commitment_id,
            "revision": revision,
            "channel_type": "web",
            "receiver": source_session_id,
            "notify_session_id": source_session_id,
        },
    }
    unchanged_pointer = (
        existing is not None
        and existing.get("schedule") == native_schedule
        and existing.get("action", {}).get("revision") == revision
        and existing.get("action", {}).get("receiver") == source_session_id
    )
    if not enabled:
        if existing and existing.get("next_run_at"):
            task["next_run_at"] = existing["next_run_at"]
    elif unchanged_pointer and existing.get("next_run_at"):
        # Preserve an overdue occurrence for the native catch-up policy. A
        # startup reconciliation must not silently move it to tomorrow.
        task["next_run_at"] = existing["next_run_at"]
    else:
        from agent.tools.scheduler.scheduler_service import SchedulerService
        from agent.tools.scheduler.time_utils import format_scheduled_time

        next_run = SchedulerService.__new__(SchedulerService)._calculate_next_run(
            task, datetime.now()
        )
        if next_run is None:
            raise ValueError("commitment schedule has no next run")
        task["next_run_at"] = format_scheduled_time(next_run)

    task["updated_at"] = datetime.now().isoformat()
    return task_store.sync_personal_pointer(task, revision)


def reconcile_commitments(registry, task_store) -> None:
    """Sync all persisted commitments for enabled Agent profiles.

    Startup calls this after creating the single native scheduler service and
    before starting its polling thread. A per-profile failure is logged and
    does not prevent other Agents from reconciling.
    """
    from agent.memory import get_conversation_store
    from agent.memory.commitments import CommitmentStore

    for profile in registry.list(include_disabled=False):
        try:
            store = CommitmentStore(get_conversation_store(profile.workspace))
            commitments = store.snapshot()
            for commitment in commitments:
                try:
                    sync_commitment(profile, commitment, task_store=task_store)
                except Exception as exc:
                    logger.error(
                        f"[Scheduler] Failed to sync commitment "
                    f"{commitment.get('commitment_id', '<unknown>')} for agent "
                        f"{profile.id}: {exc}"
                    )
        except Exception as exc:
            logger.error(
                f"[Scheduler] Failed to reconcile commitments for agent "
                f"{profile.id}: {exc}"
            )


def scheduling_status(profile: Any, record: dict) -> dict:
    """Read pointer state without starting or initializing SchedulerService."""
    catch_up_policy = (
        "Runs up to 10 minutes late; older missed daily runs are skipped and "
        "rescheduled."
    )
    status = {
        "next_run_at": None,
        "schedule_status": "inactive",
        "catch_up_policy": catch_up_policy,
    }
    if (
        record.get("status") != "active"
        or record.get("read_authorized") is not True
        or not isinstance(record.get("schedule"), dict)
    ):
        return status

    try:
        from agent.tools.scheduler.integration import get_task_store

        task_store = get_task_store(agent_id=profile.id)
        if task_store is None:
            status["schedule_status"] = "unavailable"
            return status
        task = task_store.get_task(_task_id(record.get("commitment_id", "")))
    except Exception:
        status["schedule_status"] = "unavailable"
        return status

    if task is None or not task.get("enabled"):
        status["schedule_status"] = "not_scheduled"
        return status
    action = task.get("action") or {}
    schedule = record["schedule"]
    matches = (
        task.get("agent_id") == profile.id
        and task.get("schedule") == {
            "type": "cron",
            "expression": schedule.get("cron"),
            "timezone": schedule.get("timezone"),
        }
        and action.get("type") == "personal_commitment"
        and action.get("commitment_id") == record.get("commitment_id")
        and action.get("revision") == record.get("revision")
        and action.get("receiver") == record.get("source_session_id")
    )
    if not matches or not task.get("next_run_at"):
        status["schedule_status"] = "out_of_sync"
        return status
    return {
        "next_run_at": task["next_run_at"],
        "schedule_status": "scheduled",
        "catch_up_policy": catch_up_policy,
    }


def execute_scheduled_commitment(task: dict, agent_id: str, trigger: str = "scheduled") -> dict:
    """Execute a bounded commitment callback from its ID and schedule slot."""
    action = task.get("action") if isinstance(task, dict) else None
    if not isinstance(action, dict):
        logger.error("[Scheduler] Personal commitment task has no action")
        return {"status": "skipped", "error": "invalid pointer"}
    commitment_id = action.get("commitment_id")
    expected_revision = action.get("revision")
    if (
        not isinstance(commitment_id, str)
        or not commitment_id
        or isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
    ):
        logger.error("[Scheduler] Personal commitment pointer is invalid")
        return {"status": "skipped", "error": "invalid pointer"}
    if task.get("agent_id") != agent_id:
        logger.error("[Scheduler] Personal commitment owner does not match scheduler identity")
        return {"status": "skipped", "error": "owner mismatch"}

    occurrence = task.get("next_run_at")
    if not isinstance(occurrence, str) or not occurrence:
        logger.error("[Scheduler] Personal commitment has no scheduled occurrence")
        return {"status": "skipped", "error": "missing occurrence"}
    occurrence_key = f"{commitment_id}:{expected_revision}:{occurrence}"
    source_session_id = action.get("receiver")
    if not isinstance(source_session_id, str) or not source_session_id:
        logger.error("[Scheduler] Personal commitment has no owner session")
        return {"status": "skipped", "error": "missing owner session"}

    # Resolve the exact current native profile. No task text or model prompt is
    # accepted at this boundary; the service reloads owner intent by ID.
    try:
        from agent.registry import get_agent_registry
        profile = get_agent_registry().get_addressed(agent_id)
        if getattr(profile, "id", None) != agent_id:
            logger.error("[Scheduler] Personal commitment Agent profile did not match")
            return {"status": "skipped", "error": "owner mismatch"}
        from agent.personal.commitments import CommitmentService

        result = CommitmentService(agent_id, source_session_id).run(
            commitment_id,
            occurrence_key=occurrence_key,
            expected_revision=expected_revision,
        )
        return result if isinstance(result, dict) else {"status": "failed", "error": "invalid service result"}
    except ValueError:
        # A pause, cancellation, deletion or revision change can race a due tick.
        # It is terminal for this slot; do not spin on the same occurrence.
        return {"status": "skipped", "error": "commitment changed"}
    except Exception:
        # Service/database failures are visible in the scheduler run history.
        # Consume this occurrence and let the next scheduled slot retry.
        logger.error("[Scheduler] Personal commitment execution failed")
        return {"status": "failed", "error": "execution failed"}
