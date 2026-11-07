"""Running a sub agent: one task, its own context, a summary back.

The parent's context only ever sees the spawn call and the returned summary.
Everything the sub agent read, ran and discarded on the way stays out, which is
the point of spawning one at all.
"""

from __future__ import annotations

import contextvars
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from common.log import logger
from common.runtime_identity import identity_scope

# Nesting depth of the currently running work. 0 is the main Agent. Lives in a
# ContextVar rather than on the Agent because sub agents run on worker threads,
# and contextvars.copy_context() carries it across the handoff.
_depth: contextvars.ContextVar[int] = contextvars.ContextVar("cow_subagent_depth", default=0)


def current_depth() -> int:
    return _depth.get()


@dataclass(frozen=True)
class SubagentSettings:
    enabled: bool = True
    max_depth: int = 1
    max_concurrent: int = 3
    timeout_seconds: float = 300.0

    @classmethod
    def from_config(cls) -> "SubagentSettings":
        from config import conf

        raw = conf().get("subagent") or {}
        if not isinstance(raw, dict):
            logger.warning("[SubAgent] 'subagent' config must be an object; ignoring")
            raw = {}

        def _bounded(key, default, low, high, cast):
            try:
                value = cast(raw.get(key, default))
            except (TypeError, ValueError):
                logger.warning(f"[SubAgent] Invalid {key!r}; using {default}")
                return default
            if not low <= value <= high:
                logger.warning(
                    f"[SubAgent] {key}={value} out of range [{low}, {high}]; using {default}"
                )
                return default
            return value

        return cls(
            # On unless switched off: an install that has never heard of this
            # setting gets sub agents, which is the behaviour worth defaulting
            # to. Turning it off is the deliberate act.
            enabled=bool(raw.get("enabled", True)),
            max_depth=_bounded("max_depth", 1, 1, 5, int),
            max_concurrent=_bounded("max_concurrent", 3, 1, 10, int),
            timeout_seconds=_bounded("timeout_seconds", 300.0, 10.0, 3600.0, float),
        )


@dataclass
class SubagentTask:
    goal: str
    context: str = ""
    subagent_type: Optional[str] = None
    read_roots: tuple = ()
    write_roots: tuple = ()
    verification: Optional[dict] = None


def _build_brief(task: SubagentTask, template) -> str:
    parts = [template.prompt, "", "YOUR TASK:", task.goal.strip()]
    if task.context.strip():
        parts += ["", "CONTEXT:", task.context.strip()]
    if task.verification and any(task.verification.values()):
        import json
        parts += ["", "RESULT CHECKS:", json.dumps(task.verification, ensure_ascii=False)]
    return "\n".join(parts)


def _private_tools(parent, template, authority=None):
    """Construct fresh native tools only; never copy live tool resources."""
    from agent.tools.read.read import Read
    from agent.tools.write.write import Write
    from agent.tools.edit.edit import Edit
    from agent.tools.ls.ls import Ls
    from agent.tools.current_time.current_time import TimeTool
    from agent.tools.search_files.search_files import SearchFiles

    if authority is None:
        from agent.permission.authority import restricted_authority
        authority = restricted_authority(parent)
    allowed = {Read, Write, Edit, Ls, SearchFiles, TimeTool}
    cwd = (authority.read_roots or authority.write_roots or ("/",))[0]
    result = []
    for source in template.select_tools(list(parent.tools)):
        cls = type(source)
        if cls not in allowed:
            continue
        if cls is TimeTool:
            tool = cls()
        else:
            if not authority.read_roots and not authority.write_roots:
                continue
            tool = cls({"cwd": cwd})
            if cls is Read:
                # Missing relative paths must not fall back to shared knowledge.
                tool._shared_knowledge_path = lambda path: None
        result.append(tool)
    return result


def _build_child(parent, template, task: SubagentTask):
    """Create a fresh execution view with frozen task authority."""
    from agent.protocol.agent import Agent
    from agent.permission.authority import Authority, derive_authority, restricted_authority
    from agent.permission.filesystem import FileBroker
    import os

    parent_auth = restricted_authority(parent)
    if not isinstance(task.read_roots, (list, tuple)) or not isinstance(task.write_roots, (list, tuple)):
        raise ValueError("Worker roots must be lists")
    requested_read = tuple(task.read_roots)
    requested_write = tuple(task.write_roots)
    if any(not isinstance(p, str) or not os.path.isabs(p)
           for p in requested_read + requested_write):
        raise ValueError("Worker roots must be absolute paths")
    requested = Authority(parent_auth.mode, parent_auth.capabilities, requested_read, requested_write)
    limited = derive_authority(parent_auth, requested)
    if set(limited.read_roots) != set(requested.read_roots) or set(limited.write_roots) != set(requested.write_roots):
        raise ValueError("Worker root is outside parent authority")
    for root in requested.read_roots:
        FileBroker(parent_auth, root).locate(root)
    for root in requested.write_roots:
        FileBroker(parent_auth, root).locate(root, write=True)

    scratch = None
    if "fs.write" in parent_auth.capabilities:
        for root in parent_auth.write_roots:
            candidate = os.path.join(root, "worker-" + uuid.uuid4().hex)
            try:
                FileBroker(parent_auth, root).locate(candidate, write=True)
                fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    os.mkdir(os.path.basename(candidate), 0o700, dir_fd=fd)
                finally:
                    os.close(fd)
                scratch = candidate
                break
            except OSError:
                continue
    read_roots = requested.read_roots + ((scratch,) if scratch else ())
    write_roots = requested.write_roots + ((scratch,) if scratch else ())
    authority = derive_authority(parent_auth, Authority(parent_auth.mode, parent_auth.capabilities,
                                                          read_roots, write_roots))
    cwd = scratch or (authority.read_roots or authority.write_roots or (None,))[0]
    child = Agent(
        system_prompt=template.prompt,
        description=f"sub agent ({template.name})",
        model=parent.model,
        tools=_private_tools(parent, template, authority),
        output_mode="logger",
        max_steps=max(1, parent.max_steps // 2),
        max_context_tokens=parent.max_context_tokens,
        memory_manager=None,
        name=f"subagent:{template.name}",
        workspace_dir=cwd,
        skill_manager=None,
        enable_skills=False,
        runtime_info=None,
        skip_context_files=True,
    )
    child.extra_system_suffix = _build_brief(task, template)
    if scratch:
        child.extra_system_suffix += f"\n\nTASK WORKSPACE: {scratch}"
    child.task_workspace = scratch
    child._current_agent_id = getattr(parent, "_current_agent_id", None)
    child.project_dir = cwd
    child.permission_mode = authority.mode
    child.authority = authority
    return child


def _notify(on_state, index: int, state: Dict[str, Any]) -> None:
    """Report a task's state to the caller. Never lets a reporting problem
    reach the run it is only meant to describe."""
    if not on_state:
        return
    try:
        on_state(index, state)
    except Exception as e:
        logger.debug(f"[SubAgent] state callback failed: {e}")


def _open_run(parent, run_id: str, template) -> Optional[Any]:
    """Record the start of a spawned run, returning the store to close it with.

    None means the spawn is not being recorded, either because the parent's
    workspace is unknown — there is no database to attribute it to, and
    guessing a global one would write another workspace's history — or because
    the write failed. Bookkeeping never blocks a spawn.

    The parent's run id is read before the caller enters its own identity
    scope, so it is still the ambient one and becomes this run's parent.
    """
    workspace = getattr(parent, "workspace_dir", None)
    if not workspace:
        return None
    try:
        from agent.memory import get_conversation_store
        from common.utils import current_agent_run_id

        store = get_conversation_store(workspace)
        store.create_run(
            run_id,
            agent_id=getattr(parent, "_current_agent_id", "") or "",
            session_id=getattr(parent, "_current_session_id", "") or "",
            parent_run_id=current_agent_run_id() or "",
            extras={"subagent_type": template.name},
        )
        return store
    except Exception as e:
        logger.debug(f"[SubAgent] could not record run {run_id}: {e}")
        return None


# What the runs table calls a finished run, keyed by the status this module
# reports to its caller.
_RUN_STATUS = {"completed": "done", "cancelled": "cancelled", "failed": "failed",
               "timed_out": "timed_out", "timeout": "timed_out", "needs_review": "needs_review"}


def _close_run(store, run_id: str, result: Dict[str, Any]) -> None:
    """Mark a spawned run finished. Silent on failure, like _open_run."""
    if store is None:
        return
    try:
        store.finish_run(
            run_id,
            status=_RUN_STATUS.get(result.get("status", ""), "done"),
            error=str(result.get("error", "")),
        )
    except Exception as e:
        logger.debug(f"[SubAgent] could not close run {run_id}: {e}")


_POLL_SECONDS = 0.1
_PARENT_CANCELLED = "The parent run was cancelled."

# Time left on the budget when a still-running sub agent is told to wrap up,
# so it can write a report from what it has instead of being cut off with
# nothing. Long enough for one final model reply.
_WRAP_UP_MAX_SECONDS = 60.0
_WRAP_UP_FRACTION = 0.2
_WRAP_UP_INSTRUCTION = (
    "Your time budget is almost used up. Stop calling tools and reply now "
    "with what you have so far, noting anything left unfinished."
)


def _unfinished(index: int, template, status: str, error: str, on_state=None) -> Dict[str, Any]:
    """Result for a task that was stopped or timed out instead of finishing."""
    result = {"task_index": index, "subagent_type": template.name,
              "status": status, "error": error}
    from agent.recovery.verification import outcome_summary
    result.update(outcome_summary({'state': status}))
    _notify(on_state, index, result)
    return result


def _prepare_task(parent, template, task, timeout_seconds):
    """Persist the executable envelope before admitting work to the pool."""
    from agent.recovery.runtime import get_task_store, snapshot_child
    from common.runtime_identity import current_identity
    from agent.registry import get_agent_registry
    from agent.recovery.verification import normalize_contract

    task.verification = normalize_contract(task.verification)
    identity = current_identity()
    owner = getattr(parent, '_current_agent_id', None) or identity.agent_id
    if not owner:
        registry = get_agent_registry()
        matches = [p.id for p in registry.list(include_disabled=False)
                   if __import__('os').path.realpath(p.workspace) ==
                   __import__('os').path.realpath(parent.workspace_dir)]
        if len(matches) != 1:
            raise ValueError('Durable worker owner unavailable')
        owner = matches[0]
    session = getattr(parent, '_current_session_id', None) or identity.session_id or 'native-worker'
    principal = (getattr(parent, '_execution_agent_id', None)
                 or getattr(getattr(parent, 'model', None), 'agent_id', None)
                 or owner)
    if principal != owner:
        import copy
        authority_parent = copy.copy(parent)
        authority_parent._current_agent_id = principal
    else:
        authority_parent = parent
    child = _build_child(authority_parent, template, task)
    child._current_agent_id = principal
    spec = snapshot_child(child, task.goal, owner_id=owner, session_id=session,
                          kind='subagent', source_agent_id=principal, target_agent_id=principal,
                          parent_run_id=identity.run_id or '', timeout_seconds=timeout_seconds,
                          verification=task.verification)
    store = get_task_store()
    row = store.submit(owner, session, 'subagent', spec)
    return store, row['task_id'], child


def _run_one(parent, template, task: SubagentTask, index: int, cancel_event,
             on_state=None, on_event=None, steer_inbox=None, prepared=None) -> Dict[str, Any]:
    if cancel_event.is_set():
        return _unfinished(index, template, "cancelled", _PARENT_CANCELLED, on_state)
    started = time.time()
    run_id = uuid.uuid4().hex[:12]
    # Before identity_scope below, so the parent's run id is still ambient.
    run_store = _open_run(parent, run_id, template)
    result: Dict[str, Any] = {"task_index": index, "subagent_type": template.name}
    _notify(on_state, index, {"status": "running", "subagent_type": template.name})

    child_events = None
    if on_event:
        def child_events(event: Dict[str, Any]) -> None:
            # Same contract as _notify: watching a run must not be able to
            # break it.
            try:
                on_event(index, event)
            except Exception as e:
                logger.debug(f"[SubAgent] event callback failed: {e}")

    try:
        # A fresh run_id under the parent's agent and session: state written by
        # the sub agent lands in the right workspace, and its trace is
        # attributable to this spawn rather than to the parent's turn.
        with identity_scope(run_id=run_id):
            _depth.set(_depth.get() + 1)
            from agent.recovery.runtime import execute_task
            if prepared is None:
                prepared = _prepare_task(parent, template, task, SubagentSettings.from_config().timeout_seconds)
            journal, task_id, child = prepared
            result.update(execute_task(journal, task_id, build_child=lambda: child,
                                      cancel_event=cancel_event, on_event=child_events,
                                      steer_inbox=steer_inbox))
    except Exception as e:
        logger.warning(f"[SubAgent] task {index} ({template.name}) failed: {type(e).__name__}")
        result["status"] = "failed"
        result["error"] = "Worker initialization or execution failed"

    result["duration_seconds"] = round(time.time() - started, 2)
    _close_run(run_store, run_id, result)
    _notify(on_state, index, result)
    return result


def run_tasks(
    parent,
    tasks: List[SubagentTask],
    templates,
    settings: SubagentSettings,
    on_state=None,
    on_event=None,
    cancel_event=None,
) -> List[Dict[str, Any]]:
    """Run every task and return one result per task, in the order given.

    Tasks run concurrently. A task that times out is cancelled and reported as
    such rather than abandoned, so the parent always gets a full-length result
    list and can tell the difference between "nothing found" and "never ran".

    The optional parent ``cancel_event`` stops the whole spawn. Child timeout
    events stay independent and never set the parent event.

    `on_state(index, state)` is called as each task starts and again as it
    settles, so a caller can follow tasks individually while they run rather
    than learning about all of them at the end. Every task that reports a start
    reports an end, timeouts included.

    `on_event(index, event)` receives the sub agent's own stream events as they
    happen. What the parent's context sees is still only the returned summary;
    this is for whoever is watching the run, who otherwise spends the minutes
    it takes looking at a spinner.
    """
    from agent.protocol.steer import SteerInbox

    cancel_events = [threading.Event() for _ in tasks]
    steer_inboxes = [SteerInbox() for _ in tasks]
    resolved = []
    for task in tasks:
        name = task.subagent_type or ""
        resolved.append(templates[name] if name in templates else templates[_default_name(templates)])

    if cancel_event is not None and cancel_event.is_set():
        return [_unfinished(i, t, "cancelled", _PARENT_CANCELLED, on_state)
                for i, t in enumerate(resolved)]

    prepared = []
    initial_errors = {}
    for index, (task, template) in enumerate(zip(tasks, resolved)):
        try:
            prepared.append(_prepare_task(parent, template, task, settings.timeout_seconds))
        except Exception:
            prepared.append(None)
            initial_errors[index] = _unfinished(index, template, 'failed',
                                               'Durable task admission failed; no worker executed', on_state)

    pool = ThreadPoolExecutor(
        max_workers=min(len(tasks), settings.max_concurrent),
        thread_name_prefix="subagent",
    )
    try:
        futures = []
        for index, (task, template) in enumerate(zip(tasks, resolved)):
            if prepared[index] is None:
                futures.append(None)
                continue
            # copy_context carries both the runtime identity and the depth
            # counter into the worker thread; without it the sub agent would
            # run at depth 0 under the default Agent.
            ctx = contextvars.copy_context()
            futures.append(
                pool.submit(
                    ctx.run, _run_one, parent, template, task, index,
                    cancel_events[index], on_state, on_event, steer_inboxes[index],
                    prepared[index],
                )
            )

        deadline = time.time() + settings.timeout_seconds
        wrap_up_at = deadline - min(_WRAP_UP_MAX_SECONDS,
                                    settings.timeout_seconds * _WRAP_UP_FRACTION)
        wrapped_up = False
        results: List[Optional[Dict[str, Any]]] = [initial_errors.get(i) for i in range(len(tasks))]
        pending = {i: f for i, f in enumerate(futures) if f is not None}
        while True:
            for index in [i for i, f in pending.items() if f.done()]:
                results[index] = pending.pop(index).result()
            if not pending:
                break
            stopped = cancel_event is not None and cancel_event.is_set()
            if not wrapped_up and not stopped and time.time() >= wrap_up_at:
                wrapped_up = True
                for index in pending:
                    steer_inboxes[index].submit(_WRAP_UP_INSTRUCTION)
                logger.info(f"[SubAgent] Asked {len(pending)} task(s) to wrap up before the time budget runs out")
            remaining = deadline - time.time()
            if stopped or remaining <= 0:
                timeout_error = (
                    f"Exceeded the {settings.timeout_seconds:g}s sub agent budget. "
                    f"Split the task or raise subagent.timeout_seconds."
                )
                for index, future in pending.items():
                    # Tell the run to stop and close it out here: the worker winds
                    # down at its next checkpoint, which may be a whole LLM
                    # response away, and will not report this itself.
                    future.cancel()
                    journal, task_id, _ = prepared[index]
                    journal.request_stop(task_id, 'cancelled' if stopped else 'timed_out')
                    cancel_events[index].set()
                    results[index] = _unfinished(
                        index, resolved[index],
                        "cancelled" if stopped else "timed_out",
                        _PARENT_CANCELLED if stopped else timeout_error,
                        on_state,
                    )
                    results[index]['task_id'] = task_id
                break
            # Bounded so a user Stop reaches the children while they still run.
            wait(list(pending.values()), timeout=min(remaining, _POLL_SECONDS),
                 return_when=FIRST_COMPLETED)
    finally:
        # Deliberately not waiting: a `with` block would join the very threads
        # we just gave up on, so the tool call would overrun the budget it is
        # meant to enforce. Cancelled runs stop on their own and touch nothing
        # the parent shares.
        pool.shutdown(wait=False)

    return [r for r in results if r is not None]


def _default_name(templates) -> str:
    from agent.subagent.templates import DEFAULT_TEMPLATE_NAME

    if DEFAULT_TEMPLATE_NAME in templates:
        return DEFAULT_TEMPLATE_NAME
    return next(iter(templates))
