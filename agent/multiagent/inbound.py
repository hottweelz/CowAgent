"""Serve an incoming hand-off: a delegated sub-task, a turn the user addressed
to a local teammate (``mode=speak``, answered as itself), or clearing that
teammate's context (``mode=clear``)."""

from __future__ import annotations

import hashlib
import time
from typing import Callable

from common.log import logger

CHUNK_EVENT = "event"
CHUNK_RESULT = "result"


def serve_invoke(payload: dict, agent_bridge, send_chunk: Callable[[dict], None]) -> None:
    """Refuse peer calls until the protocol carries enforceable authority."""
    request_id = str(payload.get("request_id") or "")
    addressed_id = str(payload.get("target_agent_id") or "").strip()
    error = "Remote invocation denied: unsupported authority protocol"
    logger.warning(f"[MultiAgent] hand-off {request_id or '?'} refused: {error}")
    send_chunk({
        "chunk_type": CHUNK_RESULT,
        "request_id": request_id,
        "status": "failed",
        "error": error,
        "agent_id": addressed_id,
        "agent_name": "",
    })


def _serve_speak(
    payload: dict,
    agent_bridge,
    send_chunk: Callable[[dict], None],
    *,
    target,
    local: Callable[[str], str],
    members: list,
    request_id: str,
    task: str,
    root_session_id: str,
) -> None:
    """Answer as ``target`` on its own copy of the conversation, seeded with the
    handed-over transcript; every chunk is forwarded as an event."""
    from agent.chat.service import ChatService

    def fail(error: str) -> None:
        logger.warning(f"[MultiAgent] speaking turn {request_id or '?'} failed: {error}")
        send_chunk({
            "chunk_type": CHUNK_RESULT,
            "request_id": request_id,
            "status": "failed",
            "error": error,
            "agent_id": target.id,
            "agent_name": target.name,
        })

    session_id = _speak_session_id(root_session_id)
    transcript = _attributed_history(payload.get("history"), local, target.id)
    spoken = []

    def relay(chunk) -> None:
        if not isinstance(chunk, dict):
            return
        if chunk.get("chunk_type") == "content":
            spoken.append(str(chunk.get("delta") or ""))
        try:
            send_chunk({
                "chunk_type": CHUNK_EVENT,
                "request_id": request_id,
                "event": {"type": "chunk", "data": chunk},
            })
        except Exception as exc:
            logger.debug(f"[MultiAgent] chunk forward failed: {exc}")

    started_at = time.monotonic()
    logger.info(
        f"[MultiAgent] speaking turn {request_id or '?'}: {target.id} answers in "
        f"conversation {root_session_id} ({len(transcript)} messages of history)"
    )
    try:
        ChatService(agent_bridge).run(
            query=task,
            session_id=session_id,
            send_chunk_fn=relay,
            channel_type="agent",
            agent_id=target.id,
            request_id=request_id or None,
            members=members,
            transcript=transcript,
        )
    except Exception as exc:
        return fail(str(exc))

    send_chunk({
        "chunk_type": CHUNK_RESULT,
        "request_id": request_id,
        "status": "done",
        "content": "".join(spoken),
        "agent_id": target.id,
        "agent_name": target.name,
        "duration": round(time.monotonic() - started_at, 3),
    })


def _serve_clear(payload: dict, send_chunk: Callable[[dict], None], *, target, request_id: str) -> None:
    """Clear this Agent's context for a conversation kept elsewhere."""
    from agent.chat.session_service import SessionService

    root_session_id = str(payload.get("root_session_id") or "")
    result = {
        "chunk_type": CHUNK_RESULT,
        "request_id": request_id,
        "status": "done",
        "agent_id": target.id,
        "agent_name": target.name,
    }
    if not root_session_id:
        send_chunk({**result, "status": "failed", "error": "root_session_id is required"})
        return
    try:
        SessionService().clear_context(
            _speak_session_id(root_session_id), agent_id=target.id, fanout=False
        )
        logger.info(f"[MultiAgent] cleared {target.id}'s context for conversation {root_session_id}")
    except Exception as exc:
        send_chunk({**result, "status": "failed", "error": str(exc)})
        return
    send_chunk(result)


def _speak_session_id(root_session_id: str) -> str:
    """Local session for a conversation kept elsewhere; stable across turns."""
    digest = hashlib.sha256(root_session_id.encode("utf-8")).hexdigest()[:16]
    return f"team_{digest}"


def _attributed_history(raw, local: Callable[[str], str], reader_id: str) -> list:
    """Wire history -> attributed messages, same as the shared-transcript restore."""
    from bridge.agent_initializer import AgentInitializer

    messages = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "")
        text = str(entry.get("text") or "")
        if role not in ("user", "assistant") or not text:
            continue
        message = {"role": role, "content": [{"type": "text", "text": text}]}
        author = local(entry.get("agent_id")) if role == "assistant" else ""
        if author:
            message["agent_id"] = author
        messages.append(message)
    return AgentInitializer._attribute_history(messages, reader_id)
