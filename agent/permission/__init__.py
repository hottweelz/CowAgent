"""Permission modes that bound what the Agent's tools are allowed to do."""

from agent.permission.policy import (
    DEFAULT_MODE,
    FULL_ACCESS,
    MODES,
    READ_ONLY,
    WORKSPACE_WRITE,
    Decision,
    check_tool_call,
    describe_mode,
    global_mode,
    normalize_mode,
)

__all__ = [
    "DEFAULT_MODE",
    "FULL_ACCESS",
    "MODES",
    "READ_ONLY",
    "WORKSPACE_WRITE",
    "Decision",
    "check_tool_call",
    "describe_mode",
    "global_mode",
    "normalize_mode",
    "Authority",
    "resolve_authority",
    "restricted_authority",
    "derive_authority",
    "authorize",
    "invoke",
]

from agent.permission.authority import Authority, resolve_authority, restricted_authority, derive_authority
from agent.permission.policy import authorize, invoke
