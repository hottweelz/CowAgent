"""Synchronous delegation between independently configured agent workspaces."""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from agent.tools.base_tool import BaseTool, ToolResult
from bridge.context import Context
from bridge.reply import ReplyType
from common.log import logger
from agent.recovery.verification import (
    CONTRACT_SCHEMA, checks_failed, format_outcomes, normalize_contract, reported_outcomes,
)

# Marks delegated runs so they can be told apart from turns a user started.
TASK_SOURCE = "delegation"


def delegated_prompt(source_name: str, source_id: str, task: str) -> str:
    """What the teammate is actually asked. Shared with the path that serves
    a hand-off arriving from another process, so both read identically."""
    return (
        f"Delegated by Agent '{source_name}' ({source_id}).\n\n"
        f"Task:\n{task}\n\n"
        "Return a concise result to the delegating Agent. Do not address the user directly."
    )


def delegated_result_text(reply) -> str:
    """The teammate's answer as text for the delegating Agent.

    A teammate that sent files comes back as a file reply whose ``content``
    is the first file's URL; its prose rides in ``text_content``. Returning
    ``content`` alone would hand back a bare link and drop the answer.
    """
    if reply is None:
        return ""
    if reply.type not in (ReplyType.IMAGE_URL, ReplyType.FILE):
        return reply.content or ""
    parts = [getattr(reply, "text_content", "") or ""]
    for r in [reply] + list(getattr(reply, "extra_replies", None) or []):
        url = str(r.content or "")
        if not url:
            continue
        # Only a published image renders inline; a local path stays as it was.
        is_web = url.lower().startswith(("http://", "https://"))
        parts.append(f"![]({url})" if r.type == ReplyType.IMAGE_URL and is_web else url)
    return "\n\n".join(p for p in parts if p)


def format_delegate_result(
    source_name: str,
    target_name: str,
    content: str,
    status: str = "done",
    duration_seconds: float = 0,
    outcomes: Optional[dict] = None,
) -> str:
    """The delegation's outcome, written for a person.

    The tool returns JSON for the delegating model to parse, but whoever is
    watching wants to see who handed what to whom and read the teammate's
    answer as prose, not a JSON blob. So the same outcome goes out a second
    time as markdown: a "source → target" heading and the teammate's reply
    (which is itself markdown), exactly the shape the sub agent report uses.
    """
    from agent.tools.subagent.subagent import _format_duration

    heading = f"{source_name} → {target_name}"
    if duration_seconds:
        heading += f" · {_format_duration(duration_seconds)}"
    body = content or "(no output)"
    if outcomes is not None:
        body = format_outcomes(outcomes) + '\n\n' + body
    if status != "done":
        body = f"**{status}** — {body}"
    return f"### {heading}\n\n{body}"


class _DelegateView:
    """What someone following the run sees of one delegation call.

    The delegating Agent's context is unaffected: it still receives only the
    teammate's returned result, which is the whole point. This is the other
    audience — the person watching — for whom a teammate that reports nothing
    until it finishes is indistinguishable from one that hung.

    So the teammate's turn is relayed as its own turn: the events are passed
    through untouched, bracketed by a start/end pair naming who is speaking.
    A client that understands the pair attributes them to the teammate and
    renders them exactly as it renders any other reply; one that does not
    still has the delegation result on the call's card, as before. Without
    that attribution the prose would read as the delegating Agent suddenly
    talking about someone else's work, which is why it used to be dropped.
    """

    #: A teammate's turn looks like any other: prose, reasoning, tool calls.
    RELAYED = (
        "message_update",
        "reasoning_update",
        "tool_execution_start",
        "tool_execution_progress",
        "tool_execution_end",
    )

    #: Emitted around a relayed turn to say who it belongs to.
    START = "peer_message_start"
    END = "peer_message_end"

    def __init__(self, tool, card_id: str, source, target_id: str, target_name: str):
        self.tool = tool
        self.card_id = card_id
        self.source_id = getattr(source, "id", "") or ""
        self.source_name = getattr(source, "name", "") or self.source_id
        self.target_id = target_id
        self.target_name = target_name or target_id
        self._open = False

    def relay(self, event: dict) -> None:
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        data = event.get("data") or {}
        # A teammate handing work onward is still just another turn: pass its
        # markers up untouched so the chain reads as a flat sequence of turns
        # rather than turns nested inside turns.
        if event_type in (self.START, self.END):
            self.tool.emit_event(event_type, data)
            return
        if event_type not in self.RELAYED:
            return
        self.open()
        self.tool.emit_event(event_type, data)

    def open(self) -> None:
        """Announce the teammate's turn, once, when it first has something to say."""
        if self._open:
            return
        self._open = True
        self.tool.emit_event(
            self.START,
            {
                "card_id": self.card_id,
                "agent_id": self.target_id,
                "agent_name": self.target_name,
                "source_id": self.source_id,
                "source_name": self.source_name,
            },
        )

    def close(self, status: str = "done", outcomes=None) -> None:
        """End the teammate's turn, so what follows is the caller speaking again."""
        if not self._open:
            return
        self._open = False
        self.tool.emit_event(
            self.END,
            {"card_id": self.card_id, "agent_id": self.target_id, "status": status, **(outcomes or {})},
        )


@contextmanager
def _local_run_deadline(bridge, agent_id, request_id, session_id, seconds):
    """Cancel cooperatively at the deadline without detaching the running Agent."""
    from agent.protocol import get_cancel_registry

    registry = get_cancel_registry()
    default = bridge.agent_registry.default_agent_id
    key = bridge._cancel_key(agent_id, request_id, default)
    session_key = bridge._cancel_key(agent_id, session_id, default)
    # Register before starting the timer so a slow bridge setup cannot miss
    # an early cancellation.
    cancelled = registry.register(key, session_id=session_key)
    expired = threading.Event()

    def expire():
        expired.set()
        cancelled.set()  # Only this run's event, never a later registry entry.

    timer = threading.Timer(seconds, expire)
    timer.daemon = True
    try:
        timer.start()
        yield expired
    finally:
        timer.cancel()
        if timer.ident is not None:
            timer.join()
        if registry.get_event(key) is cancelled:
            registry.unregister(key)


@dataclass(frozen=True)
class DelegationPolicy:
    enabled: bool = True
    allowed_targets: Optional[Mapping[str, Tuple[str, ...]]] = None
    max_depth: int = 3
    timeout_seconds: float = 600.0
    max_message_chars: int = 8000

    @classmethod
    def from_config(cls, raw) -> "DelegationPolicy":
        if raw is False:
            return cls(enabled=False)
        if raw is None or raw is True:
            raw = {}
        if not isinstance(raw, Mapping):
            raise ValueError("agent_delegation must be an object or boolean")

        allow = raw.get("allowed_targets")
        normalized = None
        if allow is not None:
            if not isinstance(allow, Mapping):
                raise ValueError("allowed_targets must map source Agent IDs to lists")
            normalized = {}
            for source, targets in allow.items():
                if not isinstance(source, str) or not isinstance(targets, (list, tuple)):
                    raise ValueError("allowed_targets entries must contain lists")
                if not all(isinstance(target, str) for target in targets):
                    raise ValueError("allowed target IDs must be strings")
                normalized[source] = tuple(targets)

        max_depth = int(raw.get("max_depth", 3))
        timeout_seconds = float(raw.get("timeout_seconds", 600))
        max_message_chars = int(raw.get("max_message_chars", 8000))
        if not 1 <= max_depth <= 8:
            raise ValueError("max_depth must be between 1 and 8")
        if not 0.01 <= timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 0.01 and 3600")
        if not 1 <= max_message_chars <= 100000:
            raise ValueError("max_message_chars must be between 1 and 100000")
        return cls(
            enabled=bool(raw.get("enabled", True)),
            allowed_targets=normalized,
            max_depth=max_depth,
            timeout_seconds=timeout_seconds,
            max_message_chars=max_message_chars,
        )

    def allows(self, source_agent_id: str, target_agent_id: str) -> bool:
        if not self.enabled:
            return False
        if self.allowed_targets is None:
            return source_agent_id != target_agent_id
        targets = self.allowed_targets.get(source_agent_id, ())
        return "*" in targets or target_agent_id in targets


# One delegated target answers one turn at a time within a conversation, so
# concurrent hands-offs to the same relay session queue behind this lock rather
# than interleaving in the target's transcript.
_relay_locks = {}
_relay_locks_guard = threading.Lock()


def _relay_lock(session_id: str) -> threading.Lock:
    with _relay_locks_guard:
        return _relay_locks.setdefault(session_id, threading.Lock())


class AgentDelegateTool(BaseTool):
    """Hand a bounded subtask to a teammate in this team conversation."""

    name = "agent_delegate"
    description = (
        "Delegate a task to a teammate in this team conversation and wait for "
        "its result. The teammates you can delegate to, and their IDs, are the "
        "ones listed in the team conversation section of your context. The "
        "teammate works in its own workspace and returns a result to you."
    )
    params = {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": (
                    "The teammate's Agent ID (the @id shown for them in the team "
                    "conversation section)."
                ),
            },
            "task": {
                "type": "string",
                "description": (
                    "A self-contained task for the teammate, with everything it "
                    "needs to act without seeing this conversation."
                ),
            },
            "verification": CONTRACT_SCHEMA,
        },
        "required": ["agent_id", "task"],
    }

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.agent_bridge = None
        self.current_context = None

    def _policy(self) -> DelegationPolicy:
        if self.config:
            return DelegationPolicy.from_config(self.config)
        from config import conf

        return DelegationPolicy.from_config(conf().get("agent_delegation", {}))

    @staticmethod
    def _session_id(
        source_agent_id: str, target_agent_id: str, root_session_id: str
    ) -> str:
        digest = hashlib.sha256(root_session_id.encode("utf-8")).hexdigest()[:16]
        return f"delegate_{source_agent_id}_{target_agent_id}_{digest}"

    def _inherited_permission_mode(self, source_agent_id: str) -> str | None:
        """The delegating Agent's permission mode, or None to leave the target's.

        A delegated run has its own session id with no prefs, so without this it
        would fall back to the global mode, like a sub agent would. `peek_agent`
        never builds an Agent; None means the source has no live instance.
        """
        session_id = (self.current_context.kwargs or {}).get("session_id")
        if not session_id:
            return None
        try:
            source = self.agent_bridge.peek_agent(session_id, source_agent_id)
        except Exception as e:
            logger.debug(f"[AgentDelegate] could not read the source's mode: {e}")
            return None
        if source is None:
            return None
        getter = getattr(source, "effective_permission_mode", None)
        return getter() if callable(getter) else None

    def _team_members(self, context_values: dict, source_agent_id: str) -> list:
        """The teammates the source Agent may delegate to this turn.

        Exactly the roster the "team conversation" prompt section lists: the
        conversation's host plus its members, minus the source itself and
        anyone the ACL forbids. Delegation is bounded to the people the Agent
        was actually told it is working with, so it can never hand work to an
        Agent outside the room. Returns ``[{id, name}]`` so an error can name
        the real options.

        The host is included because a guest answering the turn (the user
        addressed a teammate by name) is not the conversation owner, yet the
        prompt lists the owner as one of its teammates. Leaving the host out
        here — while the prompt keeps it in — is exactly what makes the model
        hand work to the host and the tool reject it. ``agent_id`` on the turn
        context is the conversation owner (routing overwrites it with the
        host), so it is the host from the guest's point of view.

        On a delegated turn the source runs in its own private session, which
        carries no ``members`` of its own; the original team's roster rides
        down the chain in the context instead (``delegation_members``), so a
        teammate can hand work onward to the same team, not just answer.
        """
        members = context_values.get("delegation_members")
        host_id = None
        if not members:
            session_id = str(
                context_values.get("delegation_root_session")
                or context_values.get("session_id")
                or ""
            )
            if not session_id:
                return []
            # The conversation owner (host). On a user-facing turn routing has
            # overwritten ``agent_id`` with the host, so it names the owner even
            # when a guest is the one speaking. Members are stored under the
            # host, so read them with the host id, not the speaking source.
            host_id = context_values.get("agent_id") or source_agent_id
            try:
                from agent.workspace import session_prefs

                members = session_prefs.get_prefs(session_id, host_id).get(
                    "members"
                )
            except Exception as exc:
                logger.warning(f"[AgentDelegate] Could not read team members: {exc}")
                return []

        policy = self._policy_safe()
        roster = []
        # The host is a delegable teammate too, listed first to match the prompt
        # roster ([host, *members]). A delegated (nested) turn skips this: there
        # is no user-facing host, and ``delegation_members`` already carries the
        # reachable team down the chain.
        candidate_ids = list(members or [])
        if host_id and host_id not in candidate_ids:
            candidate_ids.insert(0, host_id)
        for member_id in candidate_ids:
            if not member_id or member_id == source_agent_id:
                continue
            if policy is not None and not policy.allows(source_agent_id, member_id):
                continue
            # A teammate may be hosted in another process; the roster lists it
            # the same way, and the hand-off itself picks the route later.
            from agent.multiagent import resolve_teammate

            entry = resolve_teammate(member_id, self.agent_bridge.agent_registry)
            if entry is None:
                continue
            if any(item["id"] == entry["id"] for item in roster):
                continue
            roster.append({"id": entry["id"], "name": entry["name"]})
        return roster

    def _policy_safe(self) -> Optional[DelegationPolicy]:
        try:
            return self._policy()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _roster_hint(roster: list) -> str:
        """One-line "who you can actually delegate to" for an error message."""
        if not roster:
            return "There are no teammates you can delegate to in this conversation."
        names = ", ".join(f"{item['name']} ({item['id']})" for item in roster)
        return f"Teammates you can delegate to: {names}."

    def execute(self, params: dict) -> ToolResult:
        if self.agent_bridge is None or self.current_context is None:
            return ToolResult.fail("Agent delegation is not attached to this turn")

        try:
            policy = self._policy()
        except (TypeError, ValueError) as exc:
            return ToolResult.fail(f"Invalid delegation policy: {exc}")
        if not policy.enabled:
            return ToolResult.fail("Agent delegation is disabled")
        context_values = dict(self.current_context.kwargs)
        # The source is whoever is actually answering this turn. When the user
        # addressed a teammate by name, that guest (``speaker_agent_id``) is
        # speaking, not the conversation owner — routing overwrote ``agent_id``
        # with the host, so using it here would delegate under the host's
        # identity and reject the guest handing work to the host. Fall back to
        # ``agent_id`` for a delegated (nested) turn, which carries no speaker.
        source_agent_id = (
            context_values.get("speaker_agent_id") or context_values.get("agent_id")
        )
        if not source_agent_id:
            return ToolResult.fail("Source Agent could not be resolved")
        try:
            source = self.agent_bridge.agent_registry.get(source_agent_id)
        except (KeyError, ValueError):
            return ToolResult.fail(f"Source Agent '{source_agent_id}' is not available")

        roster = self._team_members(context_values, source.id)
        return self._delegate(params, policy, source, context_values, roster)

    def _delegate(
        self,
        params: dict,
        policy: DelegationPolicy,
        source,
        context_values: dict,
        roster: list,
    ) -> ToolResult:
        # The roster shows ids as "@id", so a model often passes the "@" too.
        # Strip it rather than reject a correct target on a cosmetic prefix.
        target_agent_id = (params.get("agent_id") or "").strip().lstrip("@")
        task = (params.get("task") or "").strip()
        if not target_agent_id or not task:
            return ToolResult.fail("agent_id and task are required for delegation")
        if len(task) > policy.max_message_chars:
            return ToolResult.fail(
                f"Delegated task exceeds {policy.max_message_chars} characters"
            )
        # The target must be a teammate in this conversation, not just any Agent
        # the ACL would allow: delegation stays inside the team the user set up.
        # Name the real options so the model can correct itself in one step
        # rather than guessing again.
        if target_agent_id not in {item["id"] for item in roster}:
            return ToolResult.fail(
                f"'{target_agent_id}' is not a teammate you can delegate to in this "
                f"conversation. {self._roster_hint(roster)}"
            )
        # The teammate is either an Agent of this process or one reached over
        # the installed transport. Everything up to the actual run treats the
        # two alike, so the guards below apply to both.
        from agent.multiagent import get_transport, peer as peer_of

        target = None
        peer_target = None
        try:
            target = self.agent_bridge.agent_registry.get(target_agent_id)
        except (KeyError, ValueError):
            peer_target = peer_of(target_agent_id)
            if peer_target is None or get_transport() is None:
                return ToolResult.fail(f"Target Agent '{target_agent_id}' is not available")
        target_id = target.id if target is not None else peer_target.id

        raw_trace = context_values.get("delegation_trace") or (source.id,)
        if not isinstance(raw_trace, (list, tuple)) or not all(
            isinstance(item, str) for item in raw_trace
        ):
            return ToolResult.fail("Delegation trace is invalid")
        trace = tuple(raw_trace)
        if not trace or trace[-1] != source.id:
            return ToolResult.fail("Delegation trace does not match the source Agent")
        if target_id in trace:
            return ToolResult.fail(
                f"Delegation cycle rejected: {' -> '.join((*trace, target_id))}"
            )
        if not policy.allows(source.id, target_id):
            return ToolResult.fail(
                f"Agent '{source.id}' is not allowed to delegate to '{target_id}'"
            )

        depth = int(context_values.get("delegation_depth", len(trace) - 1)) + 1
        if depth > policy.max_depth:
            return ToolResult.fail(
                f"Delegation depth {depth} exceeds the maximum {policy.max_depth}"
            )

        root_session_id = str(
            context_values.get("delegation_root_session")
            or context_values.get("session_id")
            or uuid.uuid4()
        )
        run_id = uuid.uuid4().hex

        # Relay the teammate's turn as it happens so a watcher can follow the
        # delegated work live. The card is this tool call, since one delegation
        # is one card.
        card_id = getattr(self, "tool_call_id", None) or run_id
        speaker = target if target is not None else peer_target
        view = _DelegateView(
            self, card_id, source,
            getattr(speaker, "id", "") or "",
            getattr(speaker, "name", "") or "",
        )

        if target is None:
            return ToolResult.fail("Remote delegation denied: unsupported authority protocol")

        session_id = self._session_id(source.id, target.id, root_session_id)
        request_id = f"delegate_{uuid.uuid4().hex}"

        # Never initialize or reuse the receiver's persistent Agent. Its public
        # profile and the explicitly selected project define its authority.
        try:
            from agent.permission.authority import derive_authority, restricted_authority
            from agent.permission.policy import strict_global_mode, strict_mode
            from agent.protocol.agent import Agent
            from agent.subagent.runner import _private_tools, _open_run, _close_run
            from agent.subagent.templates import GENERAL_PURPOSE
            from agent.workspace import project_store, session_prefs
            from common.runtime_identity import identity_scope
            from types import SimpleNamespace
            import os

            source_agent = getattr(self, "context", None)
            if source_agent is None:
                raise ValueError("Source Agent authority is unavailable")
            parent_auth = restricted_authority(source_agent)
            # The receiver session's explicit project is the only shared-root
            # grant; a missing project uses its configured workspace.
            selected = project_store.get_project_dir_strict(session_id, target.id)
            receiver_root = selected or target.workspace
            if not receiver_root or not os.path.isabs(receiver_root):
                raise ValueError("Receiver workspace authority is unavailable")
            prefs = session_prefs.get_prefs_strict(session_id, target.id)
            receiver_mode = (strict_mode(prefs["permission"]) if prefs.get("permission")
                             else strict_global_mode())
            # Resolve the receiver as the receiver, retaining its private-state
            # and sibling exclusions before intersecting the caller's grant.
            receiver_view = Agent("Restricted receiver authority", workspace_dir=target.workspace,
                                  enable_skills=False, skip_context_files=True)
            receiver_view._current_agent_id = target.id
            receiver_view.project_dir = receiver_root
            receiver_view.permission_mode = receiver_mode
            receiver_auth = restricted_authority(receiver_view)
            authority = derive_authority(parent_auth, receiver_auth)
            cwd = (authority.read_roots or authority.write_roots or (None,))[0]
            from bridge.agent_bridge import AgentLLMModel
            receiver_model = AgentLLMModel(self.agent_bridge.bridge)
            is_default = target.id == self.agent_bridge.agent_registry.default_agent_id
            receiver_model.set_agent_default(None if is_default else target.bot_type,
                                             None if is_default else target.model)
            child = Agent(
                system_prompt="You are a delegated worker. Complete only the assigned task.",
                description="restricted delegated worker", model=receiver_model,
                tools=_private_tools(source_agent, GENERAL_PURPOSE, authority),
                output_mode="logger", max_steps=max(1, source_agent.max_steps // 2),
                max_context_tokens=source_agent.max_context_tokens,
                memory_manager=None, workspace_dir=cwd, enable_skills=False,
                skill_manager=None, runtime_info=None, skip_context_files=True,
            )
            child._current_agent_id = target.id
            child.project_dir = cwd
            child.permission_mode = authority.mode
            child.authority = authority
        except Exception:
            return ToolResult.fail("Delegation authority or receiver model unavailable")

        prompt = delegated_prompt(source.name, source.id, task)
        try:
            import json
            verification = normalize_contract(params.get('verification'))
            if any(verification.values()):
                prompt += '\n\nRESULT CHECKS:\n' + json.dumps(verification, ensure_ascii=False)
            from agent.recovery.runtime import get_task_store, snapshot_child, execute_task
            child._recovery_source_session_id = context_values.get('session_id') or root_session_id
            child._recovery_target_session_id = session_id
            child._recovery_delegation_depth = depth
            child._recovery_delegation_trace = list(trace)
            owner_id = context_values.get('delegation_host_id') or context_values.get('agent_id') or source.id
            spec = snapshot_child(child, prompt, owner_id=owner_id, session_id=root_session_id,
                                  kind='delegate', source_agent_id=source.id, target_agent_id=target.id,
                                  timeout_seconds=policy.timeout_seconds, verification=verification)
            journal = get_task_store()
            durable = journal.submit(owner_id, root_session_id, 'delegate', spec)
            task_id = durable['task_id']
        except Exception:
            return ToolResult.fail('Durable delegation admission failed; no worker executed')
        lock = _relay_lock(session_id)
        if not lock.acquire(timeout=policy.timeout_seconds):
            journal.request_stop(task_id, 'timed_out')
            return ToolResult.fail(f"Delegation to '{target.id}' timed out waiting for the target to be free")
        started_at = time.monotonic()
        run_store = _open_run(source_agent, run_id, SimpleNamespace(name="delegation"))
        run_result = {"status": "failed"}
        with _local_run_deadline(self.agent_bridge, target.id, request_id,
                                 session_id, policy.timeout_seconds) as timed_out:
            try:
                from agent.protocol import get_cancel_registry
                key = self.agent_bridge._cancel_key(target.id, request_id,
                                                     self.agent_bridge.agent_registry.default_agent_id)
                local_cancel = get_cancel_registry().get_event(key)
                parent_cancel = getattr(self, "cancel_event", None)

                class CombinedCancel:
                    def is_set(self):
                        if timed_out.is_set():
                            journal.request_stop(task_id, 'timed_out')
                        return bool((local_cancel and local_cancel.is_set()) or
                                    (parent_cancel and parent_cancel.is_set()))

                cancel = CombinedCancel()
                with identity_scope(agent_id=target.id, session_id=session_id, run_id=run_id):
                    run_result = execute_task(journal, task_id, build_child=lambda: child,
                                              cancel_event=cancel, on_event=view.relay)
                if run_result['status'] != 'completed':
                    state = run_result['status']
                    message = ('Delegation cancelled' if state == 'cancelled' else
                               f'Delegation exceeded its {policy.timeout_seconds:g}s time budget'
                               if state == 'timed_out' else 'Delegated execution failed')
                    return ToolResult.fail(
                        f'{message}. Task: {task_id}',
                        ext_data={'task_id': task_id, 'status': state, **reported_outcomes(run_result)},
                        display=format_delegate_result(source.name, target.name, message, status='failed',
                                                       outcomes=run_result))
                from bridge.reply import Reply
                reply = Reply(ReplyType.TEXT, run_result.get('summary') or '')
            except Exception:
                run_result = {"status": "failed", "error": "Delegated execution failed"}
                return ToolResult.fail(f"Delegation to '{target.id}' failed")
            finally:
                _close_run(run_store, run_id, run_result)
                view.close("done" if run_result["status"] == "completed" and not checks_failed(run_result) else "failed",
                           reported_outcomes(run_result))
                lock.release()
        if run_result["status"] == "cancelled" and not timed_out.is_set():
            return ToolResult.fail("Delegation cancelled")
        duration = time.monotonic() - started_at

        if timed_out.is_set():
            message = f"Delegation to '{target.id}' exceeded its {policy.timeout_seconds:g}s time budget"
            return ToolResult.fail(message, display=format_delegate_result(
                source.name, target.name, message, status="failed", duration_seconds=duration,
            ))
        if reply is not None and reply.type == ReplyType.ERROR:
            display = format_delegate_result(
                source.name, target.name, str(reply.content), status="failed",
                duration_seconds=duration,
            )
            return ToolResult.fail(
                f"Delegation to '{target.id}' failed: {reply.content}", display=display
            )
        content = delegated_result_text(reply)
        display = format_delegate_result(
            source.name, target.name, content, status="done", duration_seconds=duration,
            outcomes=run_result,
        )
        result = {
                "run_id": run_id,
                "task_id": task_id,
                "attempt_id": run_result.get('attempt_id'),
                "agent_id": target.id,
                "agent_name": target.name,
                "delegated_by": source.id,
                "depth": depth,
                "session_id": session_id,
                "status": "done",
                "content": content,
                **reported_outcomes(run_result),
            }
        if checks_failed(run_result):
            return ToolResult.fail(result, display=display)
        return ToolResult.success(result, display=display)

    def _delegate_peer(self, *args, **kwargs) -> ToolResult:
        """Peers cannot enforce a caller's immutable authority yet."""
        return ToolResult.fail("Remote delegation denied: unsupported authority protocol")


def attach_agent_delegate_to_tool(tool, agent_bridge, context: Context) -> None:
    """Bind the current source turn and bridge to a delegation tool instance."""

    tool.agent_bridge = agent_bridge
    tool.current_context = context
